
# gradio_multiagent_ui.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import gradio as gr

# Núcleo do seu protótipo
try:
    from multiagent_gut_scheduler import enqueue_content, process_round, get_status  # type: ignore
except Exception:
    # Fallback para nomes alternativos (caso estejam em outro arquivo)
    from multiagent_gut_scheduler import enqueue_content, process_round  # type: ignore
    def get_status() -> Dict[str, Any]:
        return {"active": 0, "preempted": 0, "queues": {"text": 0, "image": 0, "audio": 0, "video": 0}}

# Agentes auxiliares configuráveis
from evidence_agent import configure_keys as configure_tavily, search_evidence
from llm_helper import configure_keys as configure_openai, extract_claim, summarize_evidence
from settings_store import load_keys, save_keys

def _detect_type(file_obj: Optional[gr.File]) -> str:
    if file_obj and getattr(file_obj, "mime_type", None):
        mt = file_obj.mime_type or ""
        if mt.startswith("image/"): return "image"
        if mt.startswith("audio/"): return "audio"
        if mt.startswith("video/"): return "video"
    return "text"

def build_ui() -> gr.Blocks:
    initial = load_keys()
    # aplica configuração inicial (sem exigir .env)
    configure_tavily(initial.get("tavily_api_key"), initial.get("online", True))
    configure_openai(initial.get("openai_api_key"), initial.get("online", True))

    with gr.Blocks(title="Sistema de Checagem — Conversa", theme=gr.themes.Soft(primary_hue="orange")) as demo:
        gr.Markdown("#### MVP: contexto → filas por formato → preempção → 5 checadores → consenso → relatório JSON")

        with gr.Tab("Conversar"):
            chatbot = gr.Chatbot(label="Chatbot", height=240)
            text_input = gr.Textbox(label="Texto (opcional se enviar arquivo)")
            file_input = gr.File(label="Upload (imagem/áudio/vídeo)", file_count="single")
            with gr.Row():
                process_now = gr.Checkbox(value=True, label="Processar rodada agora")
                max_items = gr.Slider(1, 10, value=3, step=1, label="Max itens por rodada")
            send_btn = gr.Button("Enviar", variant="primary")
            results = gr.Dataframe(headers=["content_id", "label", "score", "report_path"], interactive=False, wrap=True)
            status_bar = gr.Markdown("…")

        with gr.Tab("Configurações"):
            gr.Markdown("**Chaves de API (opcional)** — Sem `.env`. Você pode executar **offline** se preferir.")
            openai_key = gr.Textbox(label="OpenAI API Key", type="password", value=initial.get("openai_api_key", ""))
            tavily_key = gr.Textbox(label="Tavily API Key", type="password", value=initial.get("tavily_api_key", ""))
            online_toggle = gr.Checkbox(label="Ativar modo ONLINE (usa internet: OpenAI/Tavily)", value=bool(initial.get("online", True)))
            persist_toggle = gr.Checkbox(label="Salvar em disco (.keys.json) — texto puro (use apenas localmente)", value=False)
            with gr.Row():
                apply_btn = gr.Button("Aplicar configurações", variant="primary")
                load_btn = gr.Button("Carregar do disco (.keys.json)")

            cfg_status = gr.Markdown("Configuração não aplicada ainda.")

        with gr.Tab("API /docs"):
            gr.HTML('<iframe src="/docs" style="width:100%; height:78vh; border:0;"></iframe>')

        with gr.Tab("Sobre"):
            gr.Markdown("""
            Sistema Multiagente para Checagem de Fatos com Scheduler Inteligente (GUT).
            Esta UI integra **conversa + upload**, **processo de preempção**, **relatórios JSON**, e **/docs** no mesmo servidor.
            Agora com **modo ONLINE/OFFLINE** e configuração de chaves **OpenAI** e **Tavily** pela própria tela.
            """)

        # ----- Funções de UI -----
        def _apply_keys(openai_api: str, tavily_api: str, online: bool, persist: bool):
            configure_openai(openai_api, online)
            configure_tavily(tavily_api, online)
            if persist:
                save_keys(openai_api, tavily_api, online)
            status = get_status()
            note = f"Online: {'ON' if online else 'OFF'} · OpenAI: {'OK' if bool(openai_api) else '—'} · Tavily: {'OK' if bool(tavily_api) else '—'}"
            return f"✅ Configurações aplicadas. {note}\n\n**Status**: {status}"

        apply_btn.click(_apply_keys, inputs=[openai_key, tavily_key, online_toggle, persist_toggle], outputs=[cfg_status])

        def _load_from_disk():
            data = load_keys()
            return data.get("openai_api_key", ""), data.get("tavily_api_key", ""), bool(data.get("online", True)), "Chaves carregadas do .keys.json (atenção: texto puro)."

        load_btn.click(_load_from_disk, inputs=None, outputs=[openai_key, tavily_key, online_toggle, cfg_status])

        def _submit(text: str, file) -> Dict[str, Any]:
            ctype = _detect_type(file)
            source = "ui"
            content = text or ""
            file_path = file.name if file else None
            # Extração de claim assistida (OpenAI opcional) para qualificar a busca
            claim = extract_claim(content, "Geral")
            enqueue_kwargs = {
                "type": ctype,
                "source": source,
                "content": claim or content or (file_path or ""),
                "file_path": file_path,
            }
            try:
                content_id = enqueue_content(**enqueue_kwargs)
            except TypeError:
                # fallback caso assinatura seja diferente
                content_id = enqueue_content(ctype, source, content or (file_path or ""), file_path=file_path)
            return {"content_id": content_id, "ctype": ctype, "claim": claim}

        def _process(max_items_value: int) -> List[Dict[str, Any]]:
            try:
                processed = process_round(max_items_value)
            except TypeError:
                processed = process_round()
            # processed deve ser lista de dicts com fields esperados
            out = []
            for p in processed or []:
                out.append({
                    "content_id": p.get("content_id"),
                    "label": p.get("label"),
                    "score": p.get("score"),
                    "report_path": p.get("report_path"),
                })
            return out

        def _on_send(chat, text, file, proc_now, max_items_value):
            # Enfileira
            enq = _submit(text, file)
            c_id = enq["content_id"]
            claim = enq["claim"]
            chip = f"Enfileirado: {c_id} | GUT: auto | prioridade: auto"
            chat = chat + [[None, chip]]

            rows = []
            if proc_now:
                rows = _process(int(max_items_value))
                # Apresenta resultados no chat
                for r in rows:
                    chat.append([None, f"{r['content_id']} → {r['label']} (score={r['score']}) · arquivo: {r['report_path']}"])

            # Atualiza status
            try:
                st = get_status()
            except Exception:
                st = {"active": "?", "preempted": "?", "queues": {}}
            st_txt = f"Ativos: {st.get('active', 0)} · Preemptados: {st.get('preempted', 0)} · Filas: {st.get('queues', {})}"
            return chat, rows, st_txt, ""

        send_btn.click(_on_send, inputs=[chatbot, text_input, file_input, process_now, max_items], outputs=[chatbot, results, status_bar, text_input])

    return demo

if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="127.0.0.1", server_port=7860, show_api=False)
