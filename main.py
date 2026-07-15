 
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel
import uvicorn
 
from QNA import get_answer
from Explanation import get_explanation
from Quizmodule import get_quiz
from SummaryModule import summarize_text
from LearningPath import get_learning_path

BASE_DIR =  Path(__file__).resolve().parent
app = FastAPI(title="EduGenie")

app.mount("/static", StaticFiles(directory=BASE_DIR /"static"),name="static")
templates = Jinja2Templates(directory=str(BASE_DIR/"templates"))

templates.env.cache = None

@app.get("/")
def home(request:Request):
    return templates.TemplateResponse(request,"index.html",{})


@app.get("/qa")
def qa_endpoints(
    user_id = Query(..., description="ID of the requesting user"),
    query_text = Query(..., description="The question to answer"),

):
    if not query_text.strip():
        raise HTTPException(status_code=400,detail="query_text cannot be empty")
    
    result = get_answer(query_text)
    return {"user_id":user_id,"query_type":"qa",**result}

class ExplainRequest(BaseModel):
    user_id:str
    topic:str


@app.post("/explain")
def explain_endpoint(req:ExplainRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=400,detail="topic cannot be empty")
    result = get_explanation(req.topic)
    return {"user_id":req.user_id,"query_type":"explanation",**result}



class QuizRequest(BaseModel):
    user_id:str
    topic:str

@app.post("/quiz")
def quiz_endpoint(req:QuizRequest):
    if not req.topic.strip():
        raise HTTPException(status_code=400,detail="topic cannot be empty")
    result = get_quiz(req.topic)
    return {"user_id":req.user_id,"query_type":"quiz",**result}


class SummarizeRequest(BaseModel):
    user_id:str
    text:str

@app.post("/summarize")
def summarize_endpoint(req:SummarizeRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400,detail="topic cannot be empty")
    result = summarize_text(req.text)
    return {"user_id":req.user_id,"query_type":"summarize",**result}

@app.get("/learn/recommendations")
def learning_recommendations_endpoint(
    user_id = Query(...,description="ID of the requesting user"),
    subject = Query(...,description="Subject to build a roadmap for"),
):
    if not subject.strip():
        raise HTTPException(status_code=400,detail="subject cannot be empty")
    
    result = get_learning_path(subject)
    return {"user_id":user_id,"query_type": "learning_path",**result}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost",port=8000)