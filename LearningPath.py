from modelclients import call_gemini_with_fallback, check_guardrail

LP_Prompt = (
    "You are EduGenie, an educational assistant. Only create learning "
    "roadmaps for real academic subjects. If the subject is not real or "
    "recognizable, respond only with: 'I don't recognize that as a "
    "subject I can build a roadmap for.' Otherwise, structure the "
    "response into exactly three sections labeled 'Beginner:', "
    "'Intermediate:', and 'Advanced:', each with 3-4 bullet point "
    "topics. Subject: {query}"
)

def get_learning_path(query_text: str, mode: str = "auto"):
    is_blocked, reason = check_guardrail(query_text)
    if is_blocked:
        return {
            "response_text": f"Input flagged by guardrail: {reason}",
            "model_used": "guardrail",
            "blocked": True,
            "reason": reason,
        }

    prompt = LP_Prompt.format(query=query_text)
    text, model_used = call_gemini_with_fallback(prompt, max_output_tokens=2000, preferred_mode=mode)

    return {
        "response_text": text,
        "model_used": model_used,
        "blocked": False,
        "reason": "ok",
    }
