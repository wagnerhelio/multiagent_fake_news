# serve_combined_app.py
# Servidor principal que combina FastAPI (API REST) + Gradio (UI Web)
# Acesso: http://127.0.0.1:8000/ui (interface) e http://127.0.0.1:8000/docs (API)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr

# Importa a API existente com endpoints /submit, /process, /status, /report
from legacy.fastapi_multiagent_gut_scheduler import app as api_app

# Importa a UI do Gradio
from .gradio_multiagent_ui import build_ui

# Usa a instância FastAPI existente (com todos os endpoints)
app: FastAPI = api_app

# Adiciona CORS para permitir acesso de outros domínios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constrói e monta a UI do Gradio em /ui
demo = build_ui()
gr.mount_gradio_app(app, demo, path="/ui")

# Endpoint de saúde adicional
@app.get("/health")
def health():
    return {"ok": True, "message": "Sistema Multiagente funcionando"}
