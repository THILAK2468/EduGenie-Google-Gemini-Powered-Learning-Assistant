from modelclients import call_gemini_with_fallback, check_guardrail

QNA_PROMPT = (
    "You are EduGenie, an educational assistant. Only answer questions on "
    "academic or educational topics. If the question is nonsensical or "
    "unrelated to education, respond only with: 'I can only help with "
    "educational topics.' Question: {query}"
)

def get_answer(query_text: str, mode: str = "auto"):
    is_blocked, reason = check_guardrail(query_text)
    if is_blocked:
        return {
            "response_text": f"Input flagged by guardrail: {reason}",
            "model_used": "guardrail",
            "blocked": True,
            "reason": reason,
        }

    prompt = QNA_PROMPT.format(query=query_text)
    text, model_used = call_gemini_with_fallback(prompt, max_output_tokens=1000, preferred_mode=mode)

    return {
        "response_text": text,
        "model_used": model_used,
        "blocked": False,
        "reason": "ok",
    }
