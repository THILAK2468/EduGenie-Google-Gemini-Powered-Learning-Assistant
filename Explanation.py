from modelclients import call_lamini

EX_prompt = (
     "You are EduGenie, an educational assistant. Only explain real "
    "academic concepts. If the topic given is not a real, recognizable "
    "concept, respond only with: 'I don't recognize that as an "
    "educational topic.' Topic: {query}"
)
def get_explanation(query_text):
    prompt = EX_prompt.format(query=query_text)
    text = call_lamini(prompt)

    return {

        "response_text" : text,
        "model_used"  :"lamini",
        "blocked" : False,
        "reason" : "ok",
     }
