from modelclients import call_gemini_with_fallback, check_guardrail

Quiz_Prompt = (
    "You are EduGenie, an educational assistant. Only generate quizzes on "
    "real academic topics. If the topic is nonsensical or not a real "
    "subject, respond only with: 'I can't generate a quiz on that "
    "topic.' Otherwise, generate exactly 5 multiple-choice questions in "
    "this exact format for each:\n"
    "Q: <question>\nA) <option>\nB) <option>\nC) <option>\nD) <option>\n"
    "Correct: <letter>\n"
    "Topic: {query}"
)

def get_quiz(query_text: str, mode: str = "auto"):
    is_blocked, reason = check_guardrail(query_text)
    if is_blocked:
        return {
            "response_text": f"Input flagged by guardrail: {reason}",
            "model_used": "guardrail",
            "blocked": True,
            "reason": reason,
        }

    prompt = Quiz_Prompt.format(query=query_text)
    text, model_used = call_gemini_with_fallback(prompt, max_output_tokens=2000, preferred_mode=mode)

    return {
        "response_text": text,
        "model_used": model_used,
        "blocked": False,
        "reason": "ok",
    }
