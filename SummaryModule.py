from modelclients import call_gemini_with_fallback

Summary_Prompt =(
    "Summarize the following educational content in 5 sentences, "
    "preserving key facts. If the text is not coherent or educational "
    "in nature, respond only with: 'This text doesn't appear to be "
    "valid educational content.' Text: {query}"
)


def summarize_text(query_text):

    prompt = Summary_Prompt.format(query=query_text)
    text,model_used = call_gemini_with_fallback(prompt)

    return {
        "response_text" : text,
        "model_used" : model_used,
        "blocked"  : False,
        "reason"  : "ok",
    }