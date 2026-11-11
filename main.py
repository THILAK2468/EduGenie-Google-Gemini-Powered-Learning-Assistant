import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from QNA import get_answer
from Explanation import get_explanation
from Quizmodule import get_quiz
from SummaryModule import summarize_text
from LearningPath import get_learning_path
from modelclients import (
    GEMINI_MODEL,
    GEMINI_FALLBACK_MODEL,
    ENABLE_LOCAL_LAMINI,
    CLOUD_PRIMARY_TIMEOUT,
    warmup_local_model_async,
)

BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-warm local model in background thread so zero cold-start latency on fallback
    warmup_local_model_async()
    yield

app = FastAPI(
    title="EduGenie",
    description="Ultra-Low-Latency Hybrid Educational Assistant",
    lifespan=lifespan
)

# Enable CORS for live cross-origin deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.cache = None


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.get("/health")
def health_check():
    """Health check endpoint for cloud monitoring and uptime probes."""
    return {
        "status": "healthy",
        "primary_model": GEMINI_MODEL,
        "primary_timeout_sec": CLOUD_PRIMARY_TIMEOUT,
        "fallback_model": GEMINI_FALLBACK_MODEL,
        "local_model_enabled": ENABLE_LOCAL_LAMINI,
    }


@app.get("/qa")
def qa_endpoints(
    user_id: str = Query(..., description="ID of the requesting user"),
    query_text: str = Query(..., description="The question to answer"),
    mode: str = Query("auto", description="Model preference: auto, cloud, or local"),
):
    if not query_text.strip():
        raise HTTPException(status_code=400, detail="query_text cannot be empty")

    result = get_answer(query_text, mode=mode)
    return {"user_id": user_id, "query_type": "qa", **result}


class ExplainRequest(BaseModel):
    user_id: str
    topic: str
    mode: str = "auto"


@app.post("/explain")
def explain_endpoint(req: ExplainRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic cannot be empty")
    result = get_explanation(req.topic, mode=req.mode)
    return {"user_id": req.user_id, "query_type": "explanation", **result}


class QuizRequest(BaseModel):
    user_id: str
    topic: str
    mode: str = "auto"


@app.post("/quiz")
def quiz_endpoint(req: QuizRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic cannot be empty")
    result = get_quiz(req.topic, mode=req.mode)
    return {"user_id": req.user_id, "query_type": "quiz", **result}


class SummarizeRequest(BaseModel):
    user_id: str
    text: str
    mode: str = "auto"


@app.post("/summarize")
def summarize_endpoint(req: SummarizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    result = summarize_text(req.text, mode=req.mode)
    return {"user_id": req.user_id, "query_type": "summarize", **result}


@app.get("/learn/recommendations")
def learning_recommendations_endpoint(
    user_id: str = Query(..., description="ID of the requesting user"),
    subject: str = Query(..., description="Subject to build a roadmap for"),
    mode: str = Query("auto", description="Model preference: auto, cloud, or local"),
):
    if not subject.strip():
        raise HTTPException(status_code=400, detail="subject cannot be empty")

    result = get_learning_path(subject, mode=mode)
    return {"user_id": user_id, "query_type": "learning_path", **result}


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    print(f"Starting EduGenie server on {host}:{port}...")
    uvicorn.run(app, host=host, port=port)
