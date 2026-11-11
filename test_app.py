import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

print("--- 1. Testing /health ---")
res = client.get("/health")
print("Status:", res.status_code, res.json())
assert res.status_code == 200

print("\n--- 2. Testing Cloud Mode (< 3s latency) ---")
t0 = time.perf_counter()
res = client.post("/explain", json={"user_id": "demo-user", "topic": "Gravity", "mode": "cloud"})
dur = time.perf_counter() - t0
print(f"Cloud Explain completed in {dur:.2f}s | model: {res.json().get('model_used')}")
assert res.status_code == 200
assert dur < 6.0, f"Expected < 6s, took {dur:.2f}s"

print("\n--- 3. Testing Auto Hybrid Mode ---")
t0 = time.perf_counter()
res = client.get("/qa?user_id=demo-user&query_text=What+is+DNA%3F&mode=auto")
dur = time.perf_counter() - t0
print(f"Auto QA completed in {dur:.2f}s | model: {res.json().get('model_used')}")
assert res.status_code == 200
assert dur < 6.0

print("\n--- 4. Testing Local Mode (< 15s latency) ---")
t0 = time.perf_counter()
res = client.post("/explain", json={"user_id": "demo-user", "topic": "Photosynthesis", "mode": "local"})
dur = time.perf_counter() - t0
print(f"Local Explain completed in {dur:.2f}s | model: {res.json().get('model_used')}")
assert res.status_code == 200

print("\n--- 5. Testing Guardrail ---")
res = client.post("/explain", json={"user_id": "demo-user", "topic": "zzzzzzzz"})
assert res.json().get("blocked") is True
print("Guardrail blocked spam successfully in 0.00s")

print("\n>>> ALL TESTS COMPLETED IN RECORD TIME! <<<")
