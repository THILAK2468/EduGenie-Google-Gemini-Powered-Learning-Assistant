import os
import gradio as gr
from pathlib import Path

# Import our optimized backend logic
from main import app as fastapi_app
from QNA import get_answer
from Explanation import get_explanation
from Quizmodule import get_quiz
from SummaryModule import summarize_text
from LearningPath import get_learning_path


def format_output(result: dict) -> str:
    """Helper to format response with model badge."""
    text = result.get("response_text", "")
    model = result.get("model_used", "unknown")
    blocked = result.get("blocked", False)

    if blocked:
        return f"⚠️ **Blocked by Guardrail**: {result.get('reason', 'Invalid input')}"

    badge = f"*(Served via: `{model}`)*\n\n"
    return badge + text


def ask_handler(question: str, mode: str) -> str:
    res = get_answer(question, mode=mode.lower().split()[0])
    return format_output(res)


def explain_handler(topic: str, mode: str) -> str:
    res = get_explanation(topic, mode=mode.lower().split()[0])
    return format_output(res)


def quiz_handler(topic: str, mode: str) -> str:
    res = get_quiz(topic, mode=mode.lower().split()[0])
    return format_output(res)


def summarize_handler(text: str, mode: str) -> str:
    res = summarize_text(text, mode=mode.lower().split()[0])
    return format_output(res)


def roadmap_handler(subject: str, mode: str) -> str:
    res = get_learning_path(subject, mode=mode.lower().split()[0])
    return format_output(res)


# Create clean, responsive Gradio interface
mode_choices = ["auto (⚡ Auto Hybrid ~1.5s)", "cloud (☁️ Gemini)", "local (💻 LaMini Offline ~7s)"]

with gr.Blocks(title="EduGenie — AI Study Assistant") as demo:
    gr.Markdown("# 🧞 EduGenie: AI-Powered Learning Assistant")
    gr.Markdown(
        "A hybrid AI educational companion combining ultra-low-latency cloud intelligence "
        "with offline local model fallbacks. Custom web UI also accessible at `/`."
    )

    with gr.Row():
        mode_dropdown = gr.Dropdown(
            choices=mode_choices,
            value=mode_choices[0],
            label="Execution Mode",
            info="Select model execution strategy"
        )

    with gr.Tabs():
        with gr.TabItem("💬 Ask"):
            with gr.Column():
                q_input = gr.Textbox(label="Your Question", placeholder="e.g. What is quantum entanglement?", lines=2)
                q_btn = gr.Button("Get Answer", variant="primary")
                q_out = gr.Markdown()
                q_btn.click(ask_handler, inputs=[q_input, mode_dropdown], outputs=q_out)

        with gr.TabItem("💡 Explain"):
            with gr.Column():
                ex_input = gr.Textbox(label="Topic to Explain", placeholder="e.g. Photosynthesis, Black Holes", lines=1)
                ex_btn = gr.Button("Explain Concept", variant="primary")
                ex_out = gr.Markdown()
                ex_btn.click(explain_handler, inputs=[ex_input, mode_dropdown], outputs=ex_out)

        with gr.TabItem("📝 Quiz"):
            with gr.Column():
                qz_input = gr.Textbox(label="Quiz Topic", placeholder="e.g. Newton's Laws of Motion", lines=1)
                qz_btn = gr.Button("Generate 5-Question Quiz", variant="primary")
                qz_out = gr.Markdown()
                qz_btn.click(quiz_handler, inputs=[qz_input, mode_dropdown], outputs=qz_out)

        with gr.TabItem("📄 Summarize"):
            with gr.Column():
                sm_input = gr.Textbox(label="Passage to Summarize", placeholder="Paste educational article or notes here...", lines=6)
                sm_btn = gr.Button("Summarize Passage", variant="primary")
                sm_out = gr.Markdown()
                sm_btn.click(summarize_handler, inputs=[sm_input, mode_dropdown], outputs=sm_out)

        with gr.TabItem("🗺️ Roadmap"):
            with gr.Column():
                lp_input = gr.Textbox(label="Subject", placeholder="e.g. Machine Learning, Calculus", lines=1)
                lp_btn = gr.Button("Generate Learning Roadmap", variant="primary")
                lp_out = gr.Markdown()
                lp_btn.click(roadmap_handler, inputs=[lp_input, mode_dropdown], outputs=lp_out)

# Mount our custom card-catalog FastAPI frontend and Gradio app together
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    # Launch Gradio on 7860 (Hugging Face default)
    demo.launch(server_name="0.0.0.0", server_port=port)
