# serve_combined_app.py
from fastapi import FastAPI
import gradio as gr
from gradio_multiagent_ui import build_ui

app = FastAPI(title="Multiagent GUT Scheduler API + UI")

# Monte a UI do Gradio em /ui
demo = build_ui()
gr.mount_gradio_app(app, demo, path="/ui")

# (opcional) endpoint de saúde
@app.get("/health")
def health():
    return {"ok": True}
