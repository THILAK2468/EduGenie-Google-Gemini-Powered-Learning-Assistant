from modelclients import call_gemini_with_fallback

LP_Prompt = (
  "You are EduGenie, an educational assistant. Only create learning "
    "roadmaps for real academic subjects. If the subject is not real or "
    "recognizable, respond only with: 'I don't recognize that as a "
    "subject I can build a roadmap for.' Otherwise, structure the "
    "response into exactly three sections labeled 'Beginner:', "
    "'Intermediate:', and 'Advanced:', each with 3-4 bullet point "
    "topics. Subject: {query}"   
)

def get_learning_path(query_text):

    prompt = LP_Prompt.format(query=query_text)
    text,model_used = call_gemini_with_fallback(prompt,max_output_tokens=2000)

    return {
        "response_text" : text,
        "model_used" : model_used,
        "blocked"  : False,
        "reason"  : "ok",
    }