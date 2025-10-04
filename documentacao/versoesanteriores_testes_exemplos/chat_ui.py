#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
chat_ui.py — Interface conversacional (Gradio) para o Sistema Multiagente com Scheduler GUT
-------------------------------------------------------------------------------------------
Recursos:
- Chat para envio de texto OU upload (imagem / áudio / vídeo) — detecta o tipo automaticamente.
- Campo opcional de "Temática" (category_hint) e override manual de GUT (G/U/T).
- Botão "Processar agora" para executar seleção de checadores, consenso e gerar relatório.
- Painel lateral com Status (filas/ativos/preemptados) e lista de relatórios gerados na sessão.
- Memória de conversa por sessão.

Executar localmente:
  pip install gradio
  python chat_ui.py

Depois, acesse: http://127.0.0.1:7860/

Importante: Este UI importa o Orchestrator de multiagent_gut_scheduler.py (mesmo diretório).
"""
from __future__ import annotations

import os
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

import gradio as gr

from multiagent_gut_scheduler import Orchestrator

REPORTS_DIR = Path("./reports")
UPLOADS_DIR = Path("./uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def detect_type_from_upload(file_path: Optional[str]) -> str:
    if not file_path:
        return "text"
    ext = Path(file_path).suffix.lower()
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"]:
        return "image"
    if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
        return "video"
    if ext in [".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]:
        return "audio"
    return "text"


def summarize_status(status: Dict[str, Any]) -> str:
    def size_of(x):
        if isinstance(x, list):
            return len(x)
        if isinstance(x, dict):
            return len(x)
        return 0

    s_active = size_of(status.get("active_checks", []))
    s_preempted = size_of(status.get("preempted", {}))
    queues = status.get("queues", {})
    q_lines = []
    for qname, items in queues.items():
        q_lines.append(f"- {qname}: {len(items)}")
    q_block = "\n".join(q_lines) if q_lines else "- (vazio)"
    return f"""**Status do Scheduler**
Ativos: {s_active}
Preemptados: {s_preempted}
Filas:
{q_block}
"""


def build_orchestrator() -> Orchestrator:
    # Limiar de preempção pode ser parametrizado via env PREEMPTION_THRESHOLD
    threshold = int(os.getenv("PREEMPTION_THRESHOLD", "2"))
    return Orchestrator(reports_dir=str(REPORTS_DIR), preemption_threshold=threshold)


def enqueue_item(orch: Orchestrator,
                 text_input: str,
                 file_obj,
                 category_hint: Optional[str],
                 gut_g: Optional[int],
                 gut_u: Optional[int],
                 gut_t: Optional[int]) -> Dict[str, Any]:
    """Prepara o dict para ingestão e enfileira no scheduler (com tentativa de preempção imediata)."""
    if file_obj:
        # Salva upload com timestamp
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"upload_{ts}{Path(file_obj.name).suffix}"
        dst = UPLOADS_DIR / filename
        with open(dst, "wb") as f:
            f.write(file_obj.read())
        content_type = detect_type_from_upload(str(dst))
        raw_content = str(dst.resolve())
        source = f"Upload::{file_obj.name}"
    else:
        content_type = "text"
        raw_content = text_input or ""
        source = "Chat"

    item = {
        "type": content_type,
        "source": source,
        "raw_content": raw_content,
    }
    # Campos auxiliares
    if category_hint:
        item["category_hint"] = category_hint.strip()

    meta = orch.ingest_and_enqueue(item)

    # Override manual de GUT (se fornecido)
    altered = False
    if gut_g or gut_u or gut_t:
        if gut_g is not None:
            meta["gut_gravidade"] = int(gut_g)
            altered = True
        if gut_u is not None:
            meta["gut_urgencia"] = int(gut_u)
            altered = True
        if gut_t is not None:
            meta["gut_tendencia"] = int(gut_t)
            altered = True
        if altered:
            # Recalcula prioridade composta
            g = meta.get("gut_gravidade", 1)
            u = meta.get("gut_urgencia", 1)
            t = meta.get("gut_tendencia", 1)
            meta["overall_priority"] = int(g) * int(u) * int(t)

    return meta


def process_once(orch: Orchestrator, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    return orch.run_once(max_items=max_items)


# ===================== Gradio App =====================
with gr.Blocks(css="footer{visibility:hidden}") as demo:
    gr.Markdown("# 🧠💬 Sistema Multiagente — Interface Conversacional\n"
                "Envie texto ou anexe imagem/áudio/vídeo. O sistema fará ingestão → categorização → GUT → fila por formato, "
                "aplicará **preempção** se necessário, processará com 5 checadores, fará **consenso** e emitirá relatório.")

    # Estado de sessão
    orch_state = gr.State(build_orchestrator())
    reports_state = gr.State([])  # lista de (content_id, report_path)

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=420, type="messages", avatar_images=(None, None))
            with gr.Row():
                text_in = gr.Textbox(label="Mensagem / Texto", placeholder="Cole a notícia ou descrição aqui...", lines=3)
            file_in = gr.File(label="Upload (imagem/áudio/vídeo)", file_count="single", type="binary")
            with gr.Row():
                category_hint = gr.Textbox(label="Temática (opcional)", placeholder="ex.: política, saúde, economia...")
            with gr.Accordion("GUT (override manual — opcional)", open=False):
                gut_g = gr.Slider(1, 5, step=1, label="Gravidade (G)")
                gut_u = gr.Slider(1, 5, step=1, label="Urgência (U)")
                gut_t = gr.Slider(1, 5, step=1, label="Tendência (T)")
                # valores em branco significam "não sobrescrever"
                gut_g.value = None
                gut_u.value = None
                gut_t.value = None

            with gr.Row():
                process_now = gr.Checkbox(value=True, label="Processar agora (executa checadores + consenso + relatório)")
                max_items = gr.Slider(1, 10, value=3, step=1, label="Limite de itens a processar na rodada")

            with gr.Row():
                send_btn = gr.Button("➤ Enviar")
                clear_btn = gr.Button("Limpar conversa")

        with gr.Column(scale=2):
            status_md = gr.Markdown("**Status aparecerá aqui**")
            reports_md = gr.Markdown("**Relatórios desta sessão aparecerão aqui**")

            refresh_btn = gr.Button("Atualizar status")
            run_btn = gr.Button("Rodar Scheduler (manualmente)")

    # --------- Callbacks ---------
    def on_send(orch: Orchestrator, history: List[Dict], rstate: List, text, file, cat, g, u, t, do_process, maxn):
        user_msg = text or (getattr(file, "name", None) and f"[Upload] {getattr(file, 'name', '')}") or "(vazio)"
        history = (history or []) + [{"role": "user", "content": user_msg}]

        meta = enqueue_item(orch, text, file, cat, g, u, t)
        cid = meta.get("id")
        pri = meta.get("overall_priority")
        catg = meta.get("category")
        gut = (meta.get("gut_gravidade"), meta.get("gut_urgencia"), meta.get("gut_tendencia"))
        reply = f"Item enfileirado.\n\n**ID**: `{cid}`\n**Categoria**: `{catg}`\n**GUT**: G={gut[0]}, U={gut[1]}, T={gut[2]}\n**Prioridade**: `{pri}`"

        # Processamento imediato
        new_reports = rstate or []
        if do_process:
            outputs = process_once(orch, max_items=int(maxn) if maxn else None)
            if not outputs:
                reply += "\n\n_Nenhum item processado nesta rodada._"
            else:
                reply += "\n\n**Relatórios gerados:**\n"
                for out in outputs:
                    rid = out["content_id"]
                    rpath = out["report"].get("report_path")
                    reply += f"- `{rid}` → `{rpath}`\n"
                    new_reports.append((rid, rpath))

        # Atualiza status
        status = orch.scheduler.get_queue_status()
        status_txt = summarize_status(status)

        # Markdown de relatórios
        if new_reports:
            rep_lines = [f"- `{rid}` → `{rpath}`" for rid, rpath in new_reports]
            rep_md = "**Relatórios nesta sessão:**\n" + "\n".join(rep_lines)
        else:
            rep_md = "_Nenhum relatório ainda._"

        history += [{"role": "assistant", "content": reply}]
        return history, status_txt, rep_md, new_reports

    def on_refresh(orch: Orchestrator, rstate: List):
        status = orch.scheduler.get_queue_status()
        status_txt = summarize_status(status)
        if rstate:
            rep_lines = [f"- `{rid}` → `{rpath}`" for rid, rpath in rstate]
            rep_md = "**Relatórios nesta sessão:**\n" + "\n".join(rep_lines)
        else:
            rep_md = "_Nenhum relatório ainda._"
        return status_txt, rep_md

    def on_run(orch: Orchestrator, rstate: List, maxn):
        outputs = process_once(orch, max_items=int(maxn) if maxn else None)
        new_reports = rstate or []
        info = ""
        if not outputs:
            info = "_Nenhum item processado nesta rodada._"
        else:
            info = "**Relatórios gerados:**\n"
            for out in outputs:
                rid = out["content_id"]
                rpath = out["report"].get("report_path")
                info += f"- `{rid}` → `{rpath}`\n"
                new_reports.append((rid, rpath))

        status = orch.scheduler.get_queue_status()
        status_txt = summarize_status(status)
        rep_lines = [f"- `{rid}` → `{rpath}`" for rid, rpath in new_reports] if new_reports else []
        rep_md = "**Relatórios nesta sessão:**\n" + "\n".join(rep_lines) if rep_lines else "_Nenhum relatório ainda._"

        # Escreve info no chatbot também
        return status_txt, rep_md, new_reports, [{"role": "assistant", "content": info}]

    def on_clear():
        return [], "_Status limpo_", "_Sem relatórios_", []

    send_btn.click(
        on_send,
        inputs=[orch_state, chatbot, reports_state, text_in, file_in, category_hint, gut_g, gut_u, gut_t, process_now, max_items],
        outputs=[chatbot, status_md, reports_md, reports_state]
    )

    refresh_btn.click(
        on_refresh,
        inputs=[orch_state, reports_state],
        outputs=[status_md, reports_md]
    )

    run_btn.click(
        on_run,
        inputs=[orch_state, reports_state, max_items],
        outputs=[status_md, reports_md, reports_state, chatbot],
    )

    clear_btn.click(on_clear, outputs=[chatbot, status_md, reports_md, reports_state])

if __name__ == "__main__":
    demo.queue().launch()
