#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UI Conversacional (simples e eficaz) — somente funcionalidades do contexto:
- Enviar texto ou upload (imagem/áudio/vídeo)
- Enfileirar → Scheduler por formato → Preempção
- Processar rodada (checadores>=5 → consenso probit-like → relatório JSON)
- Ver status + links de relatórios
"""
import gradio as gr
from multiagent_gut_scheduler import Orchestrator

orch = Orchestrator()

def send_and_maybe_process(user_text, user_file, process_now, max_items):
    msg = user_text or (user_file.name if user_file else "")
    meta = None
    if user_file:
        # salvar para caminho e usar como raw_content
        import uuid, os, shutil
        updir = "./uploads"; os.makedirs(updir, exist_ok=True)
        fname = f"{uuid.uuid4()}_{user_file.name}"
        path = os.path.join(updir, fname)
        with open(path, "wb") as f:
            f.write(user_file.read())
        meta = orch.ingest_and_enqueue({"type": _infer_type(path), "source": "ui", "raw_content": path})
    else:
        meta = orch.ingest_and_enqueue({"type": "text", "source": "ui", "raw_content": user_text or ""})

    reply = f"Enfileirado: **{meta['id']}** | cat=`{meta['category']}` | GUT=`{meta['gut_gravidade']}/{meta['gut_urgencia']}/{meta['gut_tendencia']}` | prioridade=`{meta['overall_priority']}`"
    reports_block = "_Sem relatórios gerados ainda._"

    if process_now:
        out = orch.run_once(max_items=int(max_items))
        if out:
            lines = []
            for o in out:
                lines.append(f"- `{o['content_id']}` → **{o['consensus']['final_label']}** (score={o['consensus']['veracity_score']}) • arquivo: `{o['report']['report_path']}`")
            reports_block = "\n".join(lines)
        else:
            reports_block = "_Nenhum item processado nesta rodada._"

    status = orch.scheduler.get_queue_status()
    status_md = f"**Ativos:** {len(status['active_checks'])} • **Preemptados:** {len(status['preempted'])} • **Filas:** {status['queues']}"
    return reply, status_md, reports_block

def _infer_type(path: str) -> str:
    ext = path.lower().split(".")[-1]
    if ext in ("png","jpg","jpeg","gif","webp","bmp"): return "image"
    if ext in ("mp4","mov","avi","mkv","webm"): return "video"
    if ext in ("mp3","wav","m4a","aac","ogg","flac"): return "audio"
    return "text"

with gr.Blocks(css="footer{visibility:hidden}") as demo:
    gr.Markdown("# 🧠 Sistema de Checagem — Conversa\n**MVP**: contexto → filas por formato → preempção → 5 checadores → consenso → relatório JSON")
    chat = gr.Chatbot(height=360, type="messages")
    txt = gr.Textbox(label="Texto (opcional se enviar arquivo)", lines=3)
    file = gr.File(label="Upload (imagem/áudio/vídeo)", file_count="single", type="binary")
    with gr.Row():
        process_now = gr.Checkbox(value=True, label="Processar rodada agora")
        max_items = gr.Slider(1, 10, value=3, step=1, label="Max itens por rodada")
    send = gr.Button("Enviar")

    status_md = gr.Markdown()
    reports_md = gr.Markdown()

    def on_send(history, text, f, pnow, maxn):
        reply, status, reports = send_and_maybe_process(text, f, pnow, maxn)
        history = (history or []) + [{"role":"user","content": text or (f and f.name) or ""},
                                     {"role":"assistant","content": reply}]
        return history, status, reports, None, ""

    send.click(on_send, inputs=[chat, txt, file, process_now, max_items], outputs=[chat, status_md, reports_md, file, txt])

if __name__ == "__main__":
    demo.queue().launch()
