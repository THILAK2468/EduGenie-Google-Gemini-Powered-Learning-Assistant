# EduGenie

A lightweight, hybrid AI-powered educational assistant that helps students understand concepts, get answers, generate quizzes, summarize study material, and receive personalized learning roadmaps — combining ultra-low-latency cloud intelligence with multi-tier fallbacks and local model support.

## Features

- **Ask** (`/qa`) — direct academic question answering
- **Explain** (`/explain`) — plain-terms concept explanations in depth
- **Quiz** (`/quiz`) — 5-question multiple-choice quizzes with interactive answers
- **Summarize** (`/summarize`) — condenses pasted passages into clear summaries
- **Roadmap** (`/learn/recommendations`) — beginner → intermediate → advanced study roadmaps
- **Health Probe** (`/health`) — uptime and model health monitor

## Hybrid Architecture & Resilient Fallback Strategy

EduGenie uses a 4-tier hybrid strategy designed for sub-2-second latency and 99.9% uptime:

```
                  ┌──────────────────────┐
                  │ User Request Inflow  │
                  └──────────┬───────────┘
                             │
                  ┌──────────▼───────────┐
                  │ Lightweight Guardrail│ ──> [Rejected] Empty / Nonsense
                  └──────────┬───────────┘
                             │ Validated
        ┌────────────────────┼────────────────────┐
        │                    │                    │
 ┌──────▼──────┐      ┌──────▼──────┐      ┌──────▼──────┐
 │ Tier 1:     │      │ Tier 2:     │      │ Tier 3:     │
 │ Gemini 3.5  │ ──X─>│ Gemini 3.1  │ ──X─>│ Local LaMini│
 │ Flash       │ Fail │ Flash-Lite  │ Fail │ Flan-T5     │
 │ (~1.5s)     │      │ (~1.2s)     │      │ (CPU/GPU)   │
 └─────────────┘      └─────────────┘      └──────┬──────┘
                                                  │ Fail
                                           ┌──────▼──────┐
                                           │ Tier 4:     │
                                           │ Offline     │
                                           │ Safe Msg    │
                                           └─────────────┘
```

1. **Lightweight Guardrail**: Rejects empty queries, single-character gibberish, and spam instantly without consuming model quota or waiting for network round-trips.
2. **Tier 1 (Primary Cloud Model)**: `gemini-3.5-flash` delivers rich, nuanced responses in ~1.5–4.5 seconds.
3. **Tier 2 (Cloud Fallback)**: If the primary model encounters rate limits (429), high demand (503), or times out, the system automatically falls back to `gemini-3.1-flash-lite` in ~1.2–4s.
4. **Tier 3 (Local Offline Fallback)**: If the cloud is unreachable or offline, the local `MBZUAI/LaMini-Flan-T5-783M` model handles requests locally (enabled via `ENABLE_LOCAL_LAMINI=true`).
5. **Tier 4 (Graceful Degradation)**: Clean user-friendly offline message instead of HTTP 500 crashes.

## Environment Configuration

Configure keys in `.env`:

```env
GOOGLE_API_KEY="your-gemini-api-key"
GEMINI_API_KEY="your-gemini-api-key"
HF_TOKEN="your-huggingface-token"

# Fast, high-reliability primary model
GEMINI_MODEL=gemini-3.5-flash

# Rapid secondary cloud fallback model
GEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite

# Set to true for local CPU/GPU fallback, or false for lightweight cloud containers
ENABLE_LOCAL_LAMINI=true
```

## Running Locally

1. **Activate your environment**:
   ```powershell
   .\venv\Scripts\activate   # Windows
   source venv/bin/activate  # macOS/Linux
   ```

2. **Install requirements**:
   ```bash
   pip install -r Modules/requirements.txt
   ```

3. **Start the server**:
   ```bash
   cd Modules
   python main.py
   ```
   Open **http://localhost:8000** in your browser.

## Live Cloud Deployment

### Option 1: Render (Recommended 1-Click)
1. Push your repository to GitHub.
2. Link your GitHub repo to [Render](https://render.com).
3. Render automatically detects `render.yaml`. Add your `GOOGLE_API_KEY` in Render's environment dashboard.
4. Your application will be live with an HTTPS URL in 2 minutes!

### Option 2: Railway / Heroku
1. Connect repo to Railway or Heroku.
2. It automatically runs using the included `Procfile`:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
3. Set `GOOGLE_API_KEY` in service variables.

### Option 3: Docker Container
```bash
docker build -t edugenie .
docker run -p 8000:8000 -e GOOGLE_API_KEY="your-key" edugenie
```
