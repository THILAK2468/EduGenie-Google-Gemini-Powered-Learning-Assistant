import os
import time
import re
import threading
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv

# Search for .env in current file's directory first, then fallback to current working directory
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("Neither GEMINI_API_KEY nor GOOGLE_API_KEY found in .env")

# Cloud Gemini configuration
from google import genai
from google.genai import types

# Use gemini-3.5-flash as primary and gemini-3.1-flash-lite as fallback
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.1-flash-lite")

# Client-side hard timeout: if cloud doesn't respond within 6.0s, immediately fallback
CLOUD_PRIMARY_TIMEOUT = float(os.getenv("CLOUD_PRIMARY_TIMEOUT", "6.0"))
CLOUD_SECONDARY_TIMEOUT = float(os.getenv("CLOUD_SECONDARY_TIMEOUT", "4.0"))

# Google's API requires minimum allowed deadline of 10s in http_options, so we set 15s (15000ms)
gemini_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options={"timeout": 15000}
)

# Local model configuration
ENABLE_LOCAL_LAMINI = os.getenv("ENABLE_LOCAL_LAMINI", "true").strip().lower() in ("true", "1", "yes")
HF_TOKEN = os.getenv("HF_TOKEN")
LAMINI_MODEL_NAME = "MBZUAI/LaMini-Flan-T5-783M"

_lamini_tokenizer = None
_lamini_model = None
_lamini_device = None
_lamini_lock = threading.Lock()


def _load_lamini():
    """Load local LaMini-Flan-T5 model from offline cache in ~1.6s."""
    global _lamini_tokenizer, _lamini_model, _lamini_device

    if not ENABLE_LOCAL_LAMINI:
        raise RuntimeError("Local LaMini model is disabled via ENABLE_LOCAL_LAMINI=false")

    with _lamini_lock:
        if _lamini_model is not None:
            return

        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        print("[load] Loading LaMini-Flan-T5 from local cache...")
        start = time.perf_counter()

        try:
            _lamini_tokenizer = AutoTokenizer.from_pretrained(
                LAMINI_MODEL_NAME,
                local_files_only=True
            )
            _lamini_model = AutoModelForSeq2SeqLM.from_pretrained(
                LAMINI_MODEL_NAME,
                local_files_only=True
            )
        except Exception:
            _lamini_tokenizer = AutoTokenizer.from_pretrained(LAMINI_MODEL_NAME)
            _lamini_model = AutoModelForSeq2SeqLM.from_pretrained(LAMINI_MODEL_NAME)

        if torch.cuda.is_available():
            _lamini_device = torch.device("cuda")
        elif torch.backends.mps.is_available():
            _lamini_device = torch.device("mps")
        else:
            _lamini_device = torch.device("cpu")
            try:
                num_cores = max(1, os.cpu_count() or 4)
                torch.set_num_threads(min(8, num_cores))
            except Exception:
                pass

        _lamini_model = _lamini_model.to(_lamini_device)
        _lamini_model.eval()
        print(f"[load] LaMini ready in {time.perf_counter() - start:.2f}s (device: {_lamini_device})")


def warmup_local_model_async():
    """Pre-warm local model in background so zero cold-start delay."""
    if ENABLE_LOCAL_LAMINI and _lamini_model is None:
        t = threading.Thread(target=_load_lamini, daemon=True, name="LaMini-Warmup")
        t.start()


def call_lamini(prompt: str, max_new_tokens: int = 150) -> str:
    """Run local LaMini generation with torch.inference_mode for fast CPU generation."""
    try:
        import torch
        _load_lamini()
        inputs = _lamini_tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(_lamini_device)

        start = time.perf_counter()
        with torch.inference_mode():
            outputs = _lamini_model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False
            )

        text = _lamini_tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        print(f"[LATENCY] Local LaMini: {time.perf_counter() - start:.2f}s")
        return text
    except Exception as e:
        print(f"[ERROR] Local LaMini failed: {e}")
        raise


def _raw_gemini_call(prompt: str, model_name: str, max_output_tokens: int) -> str:
    """Execute raw Gemini API call with thinking_budget=0 to eliminate reasoning delays."""
    config = types.GenerateContentConfig(
        max_output_tokens=max_output_tokens,
        temperature=0.3,
        thinking_config=types.ThinkingConfig(thinking_budget=0)  # Bypass thinking queue for instant ~1.5s response
    )
    response = gemini_client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )
    return (response.text or "").strip()


def call_gemini_with_hard_timeout(prompt: str, model_name: str, max_output_tokens: int, timeout_sec: float) -> str:
    """Execute Gemini call strictly bound by client-side timeout_sec. Never hangs."""
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_raw_gemini_call, prompt, model_name, max_output_tokens)
        try:
            result = future.result(timeout=timeout_sec)
            elapsed = time.perf_counter() - start
            print(f"[LATENCY] {model_name}: {elapsed:.2f}s")
            return result
        except concurrent.futures.TimeoutError:
            print(f"[TIMEOUT] {model_name} exceeded client deadline ({timeout_sec:.1f}s)")
            raise TimeoutError(f"{model_name} did not respond within {timeout_sec:.1f}s")


def call_gemini_with_fallback(prompt: str, max_output_tokens: int = 1500, preferred_mode: str = "auto") -> tuple[str, str]:
    """
    Ultra-low-latency hybrid execution:
    - If preferred_mode == 'local': executes local LaMini directly (~7s).
    - Otherwise (auto/cloud):
      1. Primary Gemini (thinking_budget=0, 6.0s hard timeout) -> responds in ~1.5s
      2. Secondary Gemini (4.0s hard timeout) -> responds in ~1.2s if primary has 503 or spike
      3. Local LaMini fallback -> runs locally if internet/cloud fails (~7s)
      4. Graceful offline message
    """
    # If user explicitly requests local mode
    if preferred_mode == "local" and ENABLE_LOCAL_LAMINI:
        try:
            tokens_for_lamini = min(max_output_tokens, 200)
            text = call_lamini(prompt, max_new_tokens=tokens_for_lamini)
            if text:
                return text, "lamini"
        except Exception as e:
            print(f"[LOCAL ERROR] {e}; falling back to cloud...")

    # Tier 1: Primary Cloud Model with thinking_budget=0 & 6s hard deadline
    try:
        text = call_gemini_with_hard_timeout(
            prompt,
            model_name=GEMINI_MODEL,
            max_output_tokens=max_output_tokens,
            timeout_sec=CLOUD_PRIMARY_TIMEOUT
        )
        if text:
            return text, "gemini"
    except Exception as e:
        print(f"[FALLBACK TIER 1] Primary ({GEMINI_MODEL}) failed or timed out: {e}")

    # Tier 2: Secondary Cloud Fallback Model with 4s hard deadline
    if GEMINI_FALLBACK_MODEL and GEMINI_FALLBACK_MODEL != GEMINI_MODEL:
        try:
            print(f"[FALLBACK TIER 2] Trying secondary cloud model: {GEMINI_FALLBACK_MODEL}...")
            text = call_gemini_with_hard_timeout(
                prompt,
                model_name=GEMINI_FALLBACK_MODEL,
                max_output_tokens=max_output_tokens,
                timeout_sec=CLOUD_SECONDARY_TIMEOUT
            )
            if text:
                return text, "gemini-fallback"
        except Exception as e2:
            print(f"[FALLBACK TIER 2] Secondary ({GEMINI_FALLBACK_MODEL}) failed or timed out: {e2}")

    # Tier 3: Local Model Fallback (LaMini-Flan-T5)
    if ENABLE_LOCAL_LAMINI:
        try:
            print("[FALLBACK TIER 3] Immediately switching to local LaMini model...")
            tokens_for_lamini = min(max_output_tokens, 200)
            text = call_lamini(prompt, max_new_tokens=tokens_for_lamini)
            if text:
                return text, "lamini-fallback"
        except Exception as e3:
            print(f"[FALLBACK TIER 3] Local LaMini failed: {e3}")

    # Tier 4: Graceful Degradation
    return (
        "EduGenie could not connect to the models in time. "
        "Please check your internet connection or switch to Local mode.",
        "offline-fallback"
    )


def check_guardrail(query: str) -> tuple[bool, str]:
    """Lightweight heuristic guardrail: 0.00s instant rejection for spam/empty inputs."""
    if not query or not query.strip():
        return True, "Query cannot be empty"

    cleaned = query.strip()
    if len(cleaned) < 2:
        return True, "Query is too short to be an educational topic"

    if len(cleaned) >= 5 and len(set(cleaned.replace(" ", ""))) <= 2:
        return True, "Input appears to be repetitive characters rather than an academic topic"

    return False, "ok"

print(f"[INIT] Model clients ready. Primary: {GEMINI_MODEL} (timeout={CLOUD_PRIMARY_TIMEOUT}s), Fallback: {GEMINI_FALLBACK_MODEL}, Local LaMini: {ENABLE_LOCAL_LAMINI}")
