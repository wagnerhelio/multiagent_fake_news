# -*- coding: utf-8 -*-
"""
Gradio UI — comportment A (standalone)
----------------------------------------
• Sobe um app Gradio em http://127.0.0.1:7860/
• Usa diretamente o módulo multiagent_gut_scheduler (enqueue, process, status, reports)
• Aba de Config: inserir chaves (OpenAI/Tavily) e ligar/desligar modo offline
• Aba Enviar/Processar: envia conteúdo, processa rodada, acompanha filas/relatórios
• Aba Busca Web: faz busca via Tavily (ou fallback DDG) com/sem internet

Dependências: gradio, (opcional) requests. O restante é o que seu projeto já tem.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import gradio as gr

# --- helpers opcionais (chaves e busca web) ---
# Como o scheduler agora tem integração direta, vamos usar configurações simples
def configure_openai(key: Optional[str] = None) -> Dict[str, Any]:
    """Configura OpenAI (agora integrado no scheduler)"""
    if key and key.strip():
        return {"ok": True, "using_openai": True, "detail": "OpenAI configurado"}
    else:
        return {"ok": True, "using_openai": False, "detail": "Chave OpenAI não fornecida"}

def configure_tavily(key: Optional[str] = None) -> Dict[str, Any]:
    """Configura Tavily (agora integrado no scheduler)"""
    if key and key.strip():
        return {"ok": True, "using_tavily": True, "detail": "Tavily configurado"}
    else:
        return {"ok": True, "using_tavily": False, "detail": "Chave Tavily não fornecida"}

def tavily_search(query: str, k: int = 5, offline_mode: bool = False) -> List[Dict[str, Any]]:
    """Busca web (placeholder - agora feita pelo scheduler)"""
    return [{"title": "Busca integrada", "url": "", "snippets": [f"Busca por '{query}' será feita pelo scheduler durante a verificação"]}]

def ddg_fallback(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Fallback DuckDuckGo (placeholder)"""
    return [{"title": "fallback", "url": "", "snippets": [f"Busca por: {query}"]}]

# --- núcleo do sistema (scheduler) ---
from scheduler.multiagent_gut_scheduler import (  # type: ignore
    enqueue_content,
    process_round,
    get_status,
    get_report,
    list_report_ids,
)

APP_TITLE = "🧠 Sistema Multiagente de Checagem (GUT + Preempção) — UI"


# =========================
# Estado em memória da UI
# =========================
def _default_flags() -> Dict[str, Any]:
    return {
        "offline_mode": False,
        "use_openai": True,
        "use_tavily": True,
        "openai_key": "",
        "tavily_key": "",
    }


# ---------------------------
# Funções de callback Gradio
# ---------------------------
def ui_apply_settings(
    openai_key: str,
    tavily_key: str,
    offline: bool,
    use_openai: bool,
    use_tavily: bool,
    state: Dict[str, Any],
    logs: List[str],
):
    try:
        state = dict(state or {})
        logs = list(logs or [])

        # Atualizar estado
        state["offline_mode"] = bool(offline)
        state["use_openai"] = bool(use_openai)
        state["use_tavily"] = bool(use_tavily)
        state["openai_key"] = (openai_key or "").strip()
        state["tavily_key"] = (tavily_key or "").strip()

        # Validar configurações
        openai_cfg = {"ok": True, "using_openai": False}
        tavily_cfg = {"ok": True, "using_tavily": False}

        if not offline and use_openai:
            openai_cfg = configure_openai(state["openai_key"])
        elif use_openai:
            openai_cfg = {"ok": True, "using_openai": False, "detail": "Modo offline ativo"}

        if not offline and use_tavily:
            tavily_cfg = configure_tavily(state["tavily_key"])
        elif use_tavily:
            tavily_cfg = {"ok": True, "using_tavily": False, "detail": "Modo offline ativo"}

        # Log das configurações
        mode_desc = "OFFLINE" if offline else "ONLINE"
        msg = f"Modo {mode_desc} - OpenAI={use_openai} Tavily={use_tavily}"
        logs.append(msg)

        # Salvar configurações no arquivo
        try:
            config_path = os.path.join(os.path.dirname(__file__), "..", "config", "runtime_settings.json")
            config_data = {
                "openai_api_key": state.get("openai_key", ""),
                "tavily_api_key": state.get("tavily_key", ""),
                "use_openai": state["use_openai"],
                "use_tavily": state["use_tavily"],
                "offline_mode": state["offline_mode"]
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logs.append("Configuracoes salvas em runtime_settings.json")
        except Exception as e:
            logs.append("ERRO ao salvar configuracoes: " + str(e))

        # Preparar resposta de status
        status_cfg = {
            "ok": True, 
            "offline_mode": state["offline_mode"], 
            "use_tavily": state["use_tavily"],
            "use_openai": state["use_openai"],
            "openai": openai_cfg, 
            "tavily": tavily_cfg
        }

        return (
            json.dumps(status_cfg, ensure_ascii=False, indent=2),
            state,
            "\n".join(logs),
        )
        
    except Exception as e:
        error_msg = "ERRO na aplicacao das configuracoes: " + str(e)
        logs.append(error_msg)
        
        # Retornar estado de erro
        error_status = {
            "ok": False,
            "error": str(e),
            "offline_mode": offline,
            "use_openai": use_openai,
            "use_tavily": use_tavily
        }
        
        return (
            json.dumps(error_status, ensure_ascii=False, indent=2),
            state or {},
            "\n".join(logs),
        )


def ui_submit(
    ctype: str,
    text: str,
    fileobj,
    immediate: bool,
    max_items: int,
    state: Dict[str, Any],
    logs: List[str],
):
    logs = list(logs or [])
    state = dict(state or _default_flags())

    ctype = (ctype or "text").strip().lower()
    content = (text or "").strip()

    # se não for texto, usar arquivo enviado (caminho temporário do gradio)
    if ctype != "text":
        if fileobj is None:
            return ("Selecione um arquivo para image/audio/video.", gr.update(), gr.update(choices=[]), "\n".join(logs))
        content = fileobj.name  # caminho temporário

    try:
        cid = enqueue_content(ctype, content, source="ui")
        logs.append(f"Enfileirado {cid}")
        result = f"OK: enfileirado • id={cid}"
    except Exception as e:
        result = f"ERRO ao enfileirar: {e}"
        logs.append(result)
        return (result, gr.update(), gr.update(choices=list_report_ids())), "\n".join(logs)

    # processar imediatamente?
    processed_info = ""
    if immediate:
        try:
            status = process_round(max_items=int(max_items))
            
            # Formatar resultado de forma mais clara com análises separadas
            processed_items = status.get("processed_this_round", [])
            if processed_items:
                processed_info = f"=== PROCESSAMENTO CONCLUÍDO ===\n"
                for item in processed_items:
                    content_id = item.get('content_id', 'N/A')
                    
                    # Buscar relatório para extrair análises separadas
                    try:
                        report = get_report(content_id)
                        if report:
                            consensus = report.get("consensus", {})
                            breakdown = consensus.get("analysis_breakdown", {})
                            
                            processed_info += f"""
Item: {content_id}
Prioridade: {item.get('priority', 'N/A')}
Resultado FINAL: {item.get('label', 'N/A')}
Score FINAL: {item.get('score', 'N/A')}

=== ANÁLISES SEPARADAS ===
"""
                            
                            # Análises OpenAI
                            checkers = consensus.get("checkers", [])
                            openai_checkers = [c for c in checkers if c.get("source") == "openai"]
                            
                            if openai_checkers:
                                processed_info += "OPENAI:\n"
                                for checker in openai_checkers:
                                    processed_info += f"  {checker.get('role', 'N/A')}: {checker.get('verdict', 'N/A')}\n"
                            
                            # Evidências Tavily
                            evidence = consensus.get("evidence", [])
                            if evidence:
                                processed_info += f"TAVILY: {len(evidence)} evidências encontradas\n"
                                for i, ev in enumerate(evidence[:2], 1):
                                    processed_info += f"  {i}. {ev.get('title', 'N/A')[:50]}...\n"
                            else:
                                processed_info += "TAVILY: Nenhuma evidência encontrada\n"
                            
                            # Contexto extraído (para mídia)
                            extracted_context = breakdown.get("extracted_context")
                            if extracted_context:
                                processed_info += f"CONTEXTO EXTRAÍDO: {extracted_context[:100]}...\n"
                            
                            # Query de busca usada
                            search_query = breakdown.get("search_query")
                            if search_query:
                                processed_info += f"BUSCA REALIZADA: {search_query}\n"
                            
                            # Método usado
                            method = breakdown.get("method", "N/A")
                            processed_info += f"MÉTODO: {method}\n"
                        else:
                            processed_info += f"""
Item: {content_id}
Prioridade: {item.get('priority', 'N/A')}
Resultado: {item.get('label', 'N/A')}
Score: {item.get('score', 'N/A')}
Relatório: {item.get('report_path', 'N/A')}
"""
                    except Exception as e:
                        processed_info += f"""
Item: {content_id}
Prioridade: {item.get('priority', 'N/A')}
Resultado: {item.get('label', 'N/A')}
Score: {item.get('score', 'N/A')}
Erro ao carregar detalhes: {e}
"""
                
                processed_info += f"\n=== STATUS COMPLETO ===\n{json.dumps(status, ensure_ascii=False, indent=2)}"
            else:
                processed_info = f"Nenhum item processado.\n\n{json.dumps(status, ensure_ascii=False, indent=2)}"
            
            logs.append("processed")
        except Exception as e:
            processed_info = f"ERRO no processamento: {e}"
            logs.append(processed_info)

    # atualizar dropdown de relatórios
    report_ids = list_report_ids()

    # status resumido
    try:
        status_json = json.dumps(get_status(), ensure_ascii=False, indent=2)
    except Exception:
        status_json = "{}"

    return (
        f"{result}\n\n{processed_info}",
        gr.update(value=status_json),
        gr.update(choices=report_ids),
        "\n".join(logs),
    )


def ui_process(capacity: int, preemption: float, max_items: int, logs: List[str]):
    logs = list(logs or [])
    try:
        status = process_round(capacity=int(capacity), preemption=float(preemption), max_items=int(max_items))
        logs.append("processed")
        return json.dumps(status, ensure_ascii=False, indent=2), gr.update(choices=list_report_ids()), "\n".join(logs)
    except Exception as e:
        logs.append(f"ERRO: {e}")
        return f"ERRO: {e}", gr.update(choices=list_report_ids()), "\n".join(logs)


def ui_refresh_status():
    try:
        status = get_status()
        return json.dumps(status, ensure_ascii=False, indent=2), gr.update(choices=list_report_ids())
    except Exception:
        return "{}", gr.update(choices=list_report_ids())


def ui_load_report(report_id: str):
    if not report_id:
        return "Selecione um relatório."
    rep = get_report(report_id)
    if rep is None:
        return f"Relatório não encontrado: {report_id}"
    
    # Formatar relatório de forma mais legível
    try:
        consensus = rep.get("consensus", {})
        breakdown = consensus.get("analysis_breakdown", {})
        
        formatted_report = f"""
=== RELATÓRIO DE VERIFICAÇÃO ===
ID: {rep.get('content_id', 'N/A')}
Categoria: {rep.get('category', 'N/A')}
Prioridade: {rep.get('priority', 'N/A')}

=== RESULTADO FINAL ===
Veredicto: {consensus.get('final_label', 'N/A')}
Score de Veracidade: {consensus.get('veracity_score', 'N/A')}
Método: {breakdown.get('method', 'N/A')}

=== ANÁLISES OPENAI ==="""
        
        checkers = consensus.get("checkers", [])
        openai_checkers = [c for c in checkers if c.get("source") == "openai"]
        
        if openai_checkers:
            for checker in openai_checkers:
                formatted_report += f"""
{checker.get('role', 'N/A')} ({checker.get('tier', 'N/A')}):
  Veredicto: {checker.get('verdict', 'N/A')}
  Confiança: {checker.get('confidence', 'N/A')}
  Análise: {checker.get('reasoning', 'N/A')[:200]}...
"""
        else:
            formatted_report += "\nNenhuma análise OpenAI encontrada."
        
        # Contexto extraído (para mídia)
        extracted_context = breakdown.get("extracted_context")
        if extracted_context:
            formatted_report += f"""

=== CONTEXTO EXTRAÍDO DO ARQUIVO ===
{extracted_context}
"""
        
        # Query de busca usada
        search_query = breakdown.get("search_query")
        if search_query:
            formatted_report += f"""

=== QUERY DE BUSCA ===
{search_query}
"""
        
        # Evidências Tavily
        evidence = consensus.get("evidence", [])
        if evidence and len(evidence) > 0:
            formatted_report += f"""

=== EVIDÊNCIAS TAVILY ({len(evidence)} encontradas) ==="""
            for i, ev in enumerate(evidence[:3], 1):  # Mostrar apenas as 3 primeiras
                formatted_report += f"""
{i}. {ev.get('title', 'N/A')}
   URL: {ev.get('url', 'N/A')}
   Relevância: {ev.get('score', 'N/A')}
"""
        else:
            formatted_report += f"""

=== EVIDÊNCIAS TAVILY ===
Nenhuma evidência encontrada na web.
"""
        
        formatted_report += f"""

=== RELATÓRIO COMPLETO (JSON) ===
{json.dumps(rep, ensure_ascii=False, indent=2)}"""
        
        return formatted_report
        
    except Exception as e:
        return f"Erro ao formatar relatório: {e}\n\nJSON original:\n{json.dumps(rep, ensure_ascii=False, indent=2)}"


def ui_web_search(query: str, k: int, state: Dict[str, Any], logs: List[str]):
    logs = list(logs or [])
    state = dict(state or _default_flags())
    if not query.strip():
        return "Digite uma consulta.", "\n".join(logs)
    try:
        results = tavily_search(query, k=int(k), offline_mode=bool(state.get("offline_mode", False)))
        out = {"query": query, "k": k, "offline": state.get("offline_mode", False), "results": results}
        logs.append(f"🌐 web_search('{query}') -> {len(results)} itens")
        return json.dumps(out, ensure_ascii=False, indent=2), "\n".join(logs)
    except Exception as e:
        logs.append(f"ERRO web_search: {e}")
        return f"ERRO: {e}", "\n".join(logs)


# ============
# Build UI
# ============
def build_ui() -> gr.Blocks:
    with gr.Blocks(title=APP_TITLE, theme=gr.themes.Soft()) as demo:
        gr.Markdown(f"# {APP_TITLE}")

        st_state = gr.State(_default_flags())
        st_logs: gr.State = gr.State([])  # lista de strings

        with gr.Tab("Configuração (chaves e modo)"):
            with gr.Row():
                openai_key = gr.Textbox(label="OpenAI API Key", type="password", placeholder="sk-...", lines=1)
                tavily_key = gr.Textbox(label="Tavily API Key (opcional)", type="password", placeholder="tvly-...", lines=1)
            with gr.Row():
                offline = gr.Checkbox(label="Ativar modo offline (desmarca para online)", value=False)
                use_openai = gr.Checkbox(label="Usar OpenAI (agentes internos)", value=True)
                use_tavily = gr.Checkbox(label="Usar Tavily (busca web)", value=True)
                btn_apply = gr.Button("Aplicar configurações", variant="primary")

            cfg_status = gr.Code(label="Status configuração", language="json")

            btn_apply.click(
                ui_apply_settings,
                inputs=[openai_key, tavily_key, offline, use_openai, use_tavily, st_state, st_logs],
                outputs=[cfg_status, st_state, st_logs],
            )

        with gr.Tab("Enviar conteúdo / Processar / Relatórios"):
            with gr.Row():
                ctype = gr.Dropdown(choices=["text", "image", "audio", "video"], value="text", label="Tipo")
                immediate = gr.Checkbox(label="Processar imediatamente", value=True)

            text = gr.Textbox(label="Conteúdo / URL / Texto", lines=8, placeholder="Cole o texto aqui (para imagem/áudio/vídeo, envie arquivo em 'Upload').")
            upload = gr.File(label="Upload (imagem/áudio/vídeo)")

            with gr.Accordion("Processar rodada agora", open=False):
                max_items = gr.Slider(1, 10, value=3, step=1, label="Max itens por rodada")
                capacity = gr.Slider(1, 10, value=2, step=1, label="Capacidade (unidades ativas)")
                preemption = gr.Slider(1.0, 3.0, value=1.5, step=0.1, label="Fator de preempção (novo >= fator * menor_ativo)")
                btn_process = gr.Button("Processar rodada", variant="secondary")

            btn_send = gr.Button("Enviar", variant="primary")

            result_box = gr.Textbox(label="Resultado do envio", lines=6)
            status_box = gr.Code(label="Status", language="json")
            report_select = gr.Dropdown(choices=list_report_ids(), label="Relatórios disponíveis (ID)")
            btn_refresh = gr.Button("Atualizar status/relatórios")
            report_view = gr.Code(label="Relatório selecionado", language="json")

            # Logs
            logs = gr.Textbox(label="Logs", lines=10)

            # Wiring
            btn_send.click(
                ui_submit,
                inputs=[ctype, text, upload, immediate, max_items, st_state, st_logs],
                outputs=[result_box, status_box, report_select, st_logs],
            )

            btn_process.click(
                ui_process,
                inputs=[capacity, preemption, max_items, st_logs],
                outputs=[status_box, report_select, st_logs],
            )

            btn_refresh.click(
                ui_refresh_status,
                inputs=None,
                outputs=[status_box, report_select],
            )

            report_select.change(ui_load_report, inputs=[report_select], outputs=[report_view])

            # exibir logs atuais
            st_logs.change(lambda L: "\n".join(L or []), inputs=[st_logs], outputs=[logs])

        with gr.Tab("Busca Web (Tavily/DDG)"):
            with gr.Row():
                q = gr.Textbox(label="Consulta", placeholder="ex.: 'FGTS 2024 comunicado CAIXA'", lines=1)
                k = gr.Slider(1, 10, value=5, step=1, label="Top-K")
                btn_search = gr.Button("Buscar")
            search_out = gr.Code(label="Resultados", language="json")
            btn_search.click(ui_web_search, inputs=[q, k, st_state, st_logs], outputs=[search_out, st_logs])

        gr.Markdown("—")

    return demo


if __name__ == "__main__":
    demo = build_ui()
    # Porta padrão 7860 (pode trocar com GRADIO_SERVER_PORT=xxxx)
    demo.launch(server_name="127.0.0.1", server_port=int(os.getenv("GRADIO_SERVER_PORT", "7860")))
