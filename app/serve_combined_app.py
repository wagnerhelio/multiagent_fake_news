# serve_combined_app.py
# Servidor principal que combina FastAPI (API REST) + Gradio (UI Web)
# Acesso: http://127.0.0.1:8000/ui (interface) e http://127.0.0.1:8000/docs (API)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import gradio as gr
import os
import threading
import time

# Importa a API existente com endpoints /submit, /process, /status, /report
from legacy.fastapi_multiagent_gut_scheduler import app as api_app

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

# Variável global para armazenar a instância do Gradio
gradio_app = None

def start_gradio_server():
    """Inicia o servidor Gradio em uma thread separada"""
    global gradio_app
    try:
        # Importa a UI do Gradio
        from .gradio_multiagent_ui import build_ui
        
        # Constrói a UI
        gradio_app = build_ui()
        
        # Configurações para evitar problemas com API info
        gradio_app.config = gradio_app.config or {}
        gradio_app.config["show_api"] = False
        
        # Inicia o servidor Gradio na porta 7860
        gradio_app.launch(
            server_name="127.0.0.1",
            server_port=7860,
            share=False,
            show_api=False,
            quiet=True
        )
    except Exception as e:
        print(f"Erro ao iniciar servidor Gradio: {e}")

# Inicia o servidor Gradio em uma thread separada
gradio_thread = threading.Thread(target=start_gradio_server, daemon=True)
gradio_thread.start()

# Aguarda um pouco para o Gradio inicializar
time.sleep(2)

# Endpoint para redirecionar para a UI do Gradio
@app.get("/ui")
def redirect_to_gradio():
    """Redireciona para a interface do Gradio"""
    return RedirectResponse(url="http://127.0.0.1:7860")

# Endpoint de saúde adicional
@app.get("/health")
def health():
    return {"ok": True, "message": "Sistema Multiagente funcionando"}

# Endpoint para verificar se o Gradio está rodando
@app.get("/gradio-status")
def gradio_status():
    """Verifica se o servidor Gradio está rodando"""
    try:
        import requests
        response = requests.get("http://127.0.0.1:7860", timeout=2)
        return {"gradio_running": response.status_code == 200}
    except:
        return {"gradio_running": False}
