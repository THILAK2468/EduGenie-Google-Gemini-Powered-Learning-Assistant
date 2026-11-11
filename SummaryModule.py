from modelclients import call_gemini_with_fallback, check_guardrail

Summary_Prompt = (
    "Summarize the following educational content in 3-5 clear sentences, "
    "preserving key facts. If the text is not coherent or educational "
    "in nature, respond only with: 'This text doesn't appear to be "
    "valid educational content.' Text: {query}"
)

def summarize_text(query_text: str, mode: str = "auto"):
    is_blocked, reason = check_guardrail(query_text)
    if is_blocked:
        return {
            "response_text": f"Input flagged by guardrail: {reason}",
            "model_used": "guardrail",
            "blocked": True,
            "reason": reason,
        }

    prompt = Summary_Prompt.format(query=query_text)
    text, model_used = call_gemini_with_fallback(prompt, max_output_tokens=1200, preferred_mode=mode)

    return {
        "response_text": text,
        "model_used": model_used,
        "blocked": False,
        "reason": "ok",
    }
