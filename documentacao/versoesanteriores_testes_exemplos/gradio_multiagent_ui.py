
# gradio_multiagent_ui.py
# UI conversacional do Sistema, preparada para ser montada dentro do FastAPI (/ui)
# Opção B: tudo na mesma origem/porta. Inclui uma aba com o Swagger (/docs).

from __future__ import annotations
import os
import mimetypes
from typing import List, Tuple, Optional

import gradio as gr

# Importa as funções do seu scheduler para evitar chamadas HTTP internas.
# Estas funções já existem no seu projeto (usadas pelo CLI e pelo loader).
try:
    from multiagent_gut_scheduler import enqueue_content, process_round, get_status  # type: ignore
except Exception:  # fallback gentil caso o módulo mude
    enqueue_content = None
    process_round = None
    get_status = None


def _infer_ctype(text: str, file_path: Optional[str]) -> str:
    """Decide o tipo de conteúdo a partir do arquivo ou texto."""
    if file_path:
        mime, _ = mimetypes.guess_type(file_path)
        if mime:
            if mime.startswith("image/"):
                return "image"
            if mime.startswith("audio/"):
                return "audio"
            if mime.startswith("video/"):
                return "video"
        # fallback pelo sufixo
        suffix = os.path.splitext(file_path)[1].lower()
        if suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
            return "image"
        if suffix in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}:
            return "audio"
        if suffix in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
            return "video"
    return "text" if (text and text.strip()) else "text"


def _safe_status_text() -> str:
    """Gera uma linha de status resumida das filas/ativos."""
    try:
        if get_status is None:
            return "Status: (indisponível nesta build)."
        st = get_status()
        # Esperado: {'active': int, 'preempted': int, 'queues': {'text':N,'image':N,'audio':N,'video':N}}
        q = st.get("queues", {}) if isinstance(st, dict) else {}
        return (f"Ativos: {st.get('active', 0)} • Preemptados: {st.get('preempted', 0)} • "
                f"Filas: {{'text': {q.get('text',0)}, 'image': {q.get('image',0)}, "
                f"'audio': {q.get('audio',0)}, 'video': {q.get('video',0)}}}")
    except Exception:
        return "Status: erro ao ler."


def handle_submit(history: List[Tuple[str, str]],
                  text: str,
                  file: Optional[gr.File],
                  process_now: bool,
                  max_items: int):
    """Ação do botão Enviar."""

    # Verificações básicas
    if enqueue_content is None or process_round is None:
        history = history + [("Sistema", "Funções internas do scheduler não encontradas. Verifique os imports.")]
        return history, None, _safe_status_text()

    file_path = None
    if file is not None:
        # Gradio fornece um objeto com atributo 'name' apontando para um arquivo temporário
        file_path = getattr(file, "name", None)

    ctype = _infer_ctype(text or "", file_path)
    try:
        content_id = enqueue_content(
            ctype=ctype,
            source="ui",
            text=text if ctype == "text" else None,
            file_path=file_path,
            gut=None
        )
    except Exception as e:
        history = history + [("Sistema", f"Falha ao enfileirar: {e}")]
        return history, None, _safe_status_text()

    msg = f"Enfileirado: {content_id} | type={ctype} | prioridade=GUT (auto)"
    history = history + [("Sistema", msg)]

    results = []
    if process_now:
        try:
            reports = process_round(max_items=max_items)
            for r in reports or []:
                cid = r.get("content_id", "")
                label = r.get("label", "")
                score = r.get("score", "")
                rpath = r.get("report_path", "")
                results.append([cid, label, score, rpath])
                history += [("Sistema", f"{cid} → {label} (score={score}) • arquivo: {rpath}")]
        except Exception as e:
            history += [("Sistema", f"Falha ao processar rodada: {e}")]

    # Monta um dataframe simples (Gradio aceita lista de listas)
    table = None
    if results:
        table = results  # será exibido num DataFrame com headers

    return history, table, _safe_status_text()


def build_ui():
    """Constroi a UI Gradio (usada tanto standalone quanto montada no FastAPI)."""
    with gr.Blocks(theme=gr.themes.Soft(), title="Sistema de Checagem — Conversa") as demo:
        gr.Markdown("### MVP: contexto → filas por formato → preempção → 5 checadores → consenso → relatório JSON")

        with gr.Tab("Conversar"):
            history = gr.Chatbot(label="Chatbot", height=280)
            with gr.Row():
                text = gr.Textbox(label="Texto (opcional se enviar arquivo)", lines=3, placeholder="Cole aqui a notícia ou boato...")
            with gr.Row():
                file = gr.File(label="Upload (imagem/áudio/vídeo)", file_count="single")
            with gr.Accordion("Opções", open=False):
                process_now = gr.Checkbox(value=True, label="Processar rodada agora")
                max_items = gr.Slider(1, 10, value=3, step=1, label="Max itens por rodada")

            with gr.Row():
                btn = gr.Button("Enviar", variant="primary")
                btn_clear = gr.Button("Limpar histórico", variant="secondary")

            results = gr.Dataframe(
                headers=["content_id", "label", "score", "report_path"],
                datatype=["str", "str", "number", "str"],
                interactive=False,
                wrap=True,
                height=160,
                label="Resultados da última rodada"
            )

            status = gr.Markdown(_safe_status_text())

            def _clear_hist():
                return []

            btn_clear.click(_clear_hist, outputs=history)

            btn.click(
                handle_submit,
                inputs=[history, text, file, process_now, max_items],
                outputs=[history, results, status],
            )

        with gr.Tab("API /docs"):
            gr.HTML(
                """
                <style>.swagger-frame { width: 100%; height: 78vh; border: 0; border-radius: 8px; }</style>
                <div><iframe class="swagger-frame" src="/docs"></iframe></div>
                """
            )

        with gr.Tab("Sobre"):
            gr.Markdown(
                """
**Sistema Multiagente para Checagem de Fatos com Scheduler Inteligente**  
- Recebe conteúdos (texto/imagem/áudio/vídeo) já categorizados ou a categorizar
- Mantém filas por formato
- Aplica preempção por GUT (gravidade/urgência/tendência)
- Despacha para unidades de checagem (≥5 perfis)
- Combina pareceres (consenso probabilístico)
- Gera relatório explicável (JSON em `/reports`)

> Esta interface conversa diretamente com o núcleo Python (sem HTTP).
> A aba **API /docs** expõe os mesmos recursos REST.
                """
            )
    return demo


# Permite rodar standalone em 7860, se desejar (não obrigatório na Opção B)
if __name__ == "__main__":
    ui = build_ui()
    ui.launch(server_name="127.0.0.1", server_port=7860)
