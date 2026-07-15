from modelclients import call_gemini_with_fallback
QNA_PROMPT = (
     "You are EduGenie, an educational assistant. Only answer questions on "
    "academic or educational topics. If the question is nonsensical or "
    "unrelated to education, respond only with: 'I can only help with "
    "educational topics.' Question: {query}"
)

def get_answer(query_text):

    prompt = QNA_PROMPT.format(query=query_text)
    text,model_used = call_gemini_with_fallback(prompt)

    return{
        "response_text" : text,
        "model_used" : model_used,
        "blocked"  : False,
        "reason"  : "ok",
    }