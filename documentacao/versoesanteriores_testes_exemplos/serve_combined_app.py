
# serve_combined_app.py
# Monta o Gradio (UI) dentro do FastAPI já existente, servindo tudo em :8000
# - UI acessível em /ui
# - Swagger em /docs
# - Endpoints REST preservados

from fastapi import FastAPI
import gradio as gr

# sua API já pronta (precisa expor "app = FastAPI(...)")
from fastapi_multiagent_gut_scheduler import app as api_app

# UI preparada para montagem
from gradio_multiagent_ui import build_ui

# Reaproveita a instância FastAPI existente
app: FastAPI = api_app

# Constrói o Blocks do Gradio e monta em /ui
ui = build_ui()
gr.mount_gradio_app(app, ui, path="/ui")
