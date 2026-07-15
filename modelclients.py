import os
import time
import torch
from google import genai
from google.genai import types
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from dotenv import load_dotenv
from huggingface_hub import login
 
load_dotenv()

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not found in ,env")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-flash-latest"

HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN:
    try:
        login(token = HF_TOKEN)
    except Exception as e:
           print(f"[auth] HF login failed ({e}); continuing without it. "
              f"If LaMini isn't cached yet, downloading may be slower.")
LAMINI_MODEL_NAME = "MBZUAI/LaMini-Flan-T5-783M"


_lamini_tokenizer = None
_lamini_model = None
_lamini_device = None

def _load_lamini():
    global _lamini_tokenizer,_lamini_model,_lamini_device

    if _lamini_model is not None:
        return
    
    print("[load] Loading Lamini_Flan-T5...")
    start = time.time()
    _lamini_tokenizer = AutoTokenizer.from_pretrained(LAMINI_MODEL_NAME)
    _lamini_model = AutoModelForSeq2SeqLM.from_pretrained(LAMINI_MODEL_NAME,use_safetensors=True)

    if torch.backends.mps.is_available():
        _lamini_device = torch.device("mps")
    elif torch.cuda.is_available():
        _lamini_device = torch.device("cuda")
    else:
        _lamini_device = torch.device("cpu")
    _lamini_model = _lamini_model.to(_lamini_device)
    print(f"[load] LaMini ready in {time.time() - start:.2f}s (device: {_lamini_device})")


def call_lamini(prompt,max_new_tokens=200):
    _load_lamini()
    inputs = _lamini_tokenizer(prompt,return_tensors="pt" , truncation=True, max_length = 512).to(_lamini_device)
    outputs = _lamini_model.generate(
        **inputs, max_new_tokens=max_new_tokens,temperature = 0.4,do_sample=True
    )
    return _lamini_tokenizer.decode(outputs[0],skip_special_tokens=True)


def call_gemini(prompt,max_output_tokens=1500):

    response = gemini_client.models.generate_content(
        model = GEMINI_MODEL,
        contents = prompt,
        config = types.GenerateContentConfig(
            max_output_tokens=max_output_tokens,temperature=0.4
        ),
    )
    return response.text or ""

def call_gemini_with_fallback(prompt,max_output_tokens=1500):
    try:
        text = call_gemini(prompt,max_output_tokens=max_output_tokens)
        return text,"gemini"
    
    except Exception as e:
        print(f"[fallback] Gemini failed ({e}); falling back to LaMini.")
        text = call_lamini(prompt)
        return text,"lamini-fallback"


print("Model Clients successfully")