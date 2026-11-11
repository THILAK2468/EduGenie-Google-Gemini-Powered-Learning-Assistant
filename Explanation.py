from modelclients import call_gemini_with_fallback, check_guardrail

EX_prompt = (
    "You are EduGenie, an educational assistant. Only explain real "
    "academic concepts. If the topic given is not a real, recognizable "
    "concept, respond only with: 'I don't recognize that as an "
    "educational topic.' Otherwise, explain the concept clearly in 2-3 engaging "
    "paragraphs suitable for a student. Topic: {query}"
)

def get_explanation(query_text: str, mode: str = "auto"):
    is_blocked, reason = check_guardrail(query_text)
    if is_blocked:
        return {
            "response_text": f"Input flagged by guardrail: {reason}",
            "model_used": "guardrail",
            "blocked": True,
            "reason": reason,
        }

    prompt = EX_prompt.format(query=query_text)
    text, model_used = call_gemini_with_fallback(prompt, max_output_tokens=1500, preferred_mode=mode)

    return {
        "response_text": text,
        "model_used": model_used,
        "blocked": False,
        "reason": "ok",
    }
