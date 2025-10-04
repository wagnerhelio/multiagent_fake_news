
# serve_combined_app.py
# Monta FastAPI (sua API) + Gradio UI no mesmo servidor/porta.
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr

# Importa sua API existente
from fastapi_multiagent_gut_scheduler import app as api_app  # mantém endpoints /submit, /process, /status, /report

# Constrói a UI (Gradio) e monta em /ui
from gradio_multiagent_ui import build_ui

app: FastAPI = api_app  # alias para clareza

# CORS (opcional, se for usar de outro domínio)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta o Gradio em /ui sem quebrar /docs
demo = build_ui()
gr.mount_gradio_app(app, demo, path="/ui")
