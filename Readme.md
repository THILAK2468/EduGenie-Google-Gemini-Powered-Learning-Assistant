# EduGenie

A lightweight AI-powered educational assistant that helps students understand concepts, get answers, generate quizzes, summarize study material, and receive personalized learning roadmaps — combining a fast local model with a cloud model for reliability.

## Features

- **Ask** — direct question answering
- **Explain** — plain-terms concept explanations
- **Quiz** — 5-question multiple-choice quizzes on any topic
- **Summarize** — condenses a pasted passage into a short summary
- **Roadmap** — beginner → intermediate → advanced learning path for any subject

## Architecture

| Module | Model | Notes |
|---|---|---|
| Ask | Gemini (`gemini-flash-latest`) | Falls back to LaMini-Flan-T5 if Gemini fails |
| Explain | LaMini-Flan-T5-783M (local) | No quota limit, no network dependency |
| Quiz | Gemini | Falls back to LaMini-Flan-T5 if Gemini fails |
| Summarize | Gemini | Falls back to LaMini-Flan-T5 if Gemini fails |
| Roadmap | Gemini | Falls back to LaMini-Flan-T5 if Gemini fails |

Every request first passes through a lightweight guardrail check that rejects nonsensical or clearly off-topic input before any model is called, protecting API quota and keeping responses on-topic.

**Backend:** FastAPI
**Frontend:** HTML + CSS + vanilla JS
**Cloud model:** Google Gemini (`google-genai`)
**Local model:** LaMini-Flan-T5-783M (Hugging Face `transformers`)

## Project structure

```
Modules/
├── main.py              # FastAPI app — routes and endpoint definitions
├── modelclients.py       # Gemini + LaMini setup, fallback logic, guardrail
├── QNA.py                # /qa
├── Explanation.py        # /explain
├── Quizmodule.py         # /quiz
├── SummaryModule.py      # /summarize
├── LearningPath.py       # /learn/recommendations
├── requirements.txt
├── .env.example           # copy to .env and fill in your own keys
├── static/
│   ├── style.css
│   └── script.js
└── templates/
    └── index.html
```

## Setup

1. **Clone the repo and enter the project folder**
   ```
   git clone <your-repo-url>
   cd EduGenie/Modules
   ```

2. **Create and activate a virtual environment**
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```

3. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

4. **Set up your environment variables**

   Copy `.env.example` to `.env` and fill in your own keys:
   ```
   GOOGLE_API_KEY=your-gemini-api-key-here
   HF_TOKEN=your-huggingface-token-here
   ```
   - Get a Gemini API key from [Google AI Studio](https://aistudio.google.com).
   - Get a Hugging Face token from [huggingface.co](https://huggingface.co) → Settings → Access Tokens (Read role is enough).

5. **Run the app**
   ```
   python main.py
   ```
   Then open **http://localhost:8000** in your browser.

   > First run will download the LaMini-Flan-T5 model (~3GB) — this can take a while depending on your connection. If a teammate has already downloaded it, you can copy their cached model folder instead of re-downloading (see `.cache/huggingface/hub/` under your OS user folder).

## API endpoints

| Method | Endpoint | Body / Params |
|---|---|---|
| GET | `/qa` | `user_id`, `query_text` (query params) |
| POST | `/explain` | `{ "user_id", "topic" }` |
| POST | `/quiz` | `{ "user_id", "topic" }` |
| POST | `/summarize` | `{ "user_id", "text" }` |
| GET | `/learn/recommendations` | `user_id`, `subject` (query params) |

All endpoints return:
```json
{
  "user_id": "...",
  "query_type": "...",
  "response_text": "...",
  "model_used": "gemini | lamini | lamini-fallback",
  "blocked": false,
  "reason": "ok"
}
```

Interactive API docs are available at **http://localhost:8000/docs** once the server is running.

## Notes

- `demo-user` is currently hardcoded as the frontend's `user_id` — there's no real authentication system yet.
- The free Gemini tier has daily/per-minute request limits; the app automatically falls back to the local model if a request fails for any reason (rate limit, outage, etc.), so the app stays usable even when Gemini is unavailable.