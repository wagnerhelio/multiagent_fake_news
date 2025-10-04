# -*- coding: utf-8 -*-
from __future__ import annotations

"""
llm_helper.py
--------------
Utilitários para uso (opcional) de LLM na extração de alegações e
na sumarização de evidências. Funciona online (OpenAI) e offline
(fallbacks heurísticos). Compatível com chamadas:
- configure_keys(api_key, online=..., **kwargs)
- extract_claim(text)
- summarize_evidence(evidence_items)

Não lança exceções se OpenAI não estiver instalado ou sem chave.
"""

import os
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# -----------------------------
# Flags de execução (opcionais)
# -----------------------------
def _get_runtime_flags_safe() -> Dict[str, Any]:
    """
    Lê flags de execução de settings_store, se existir.
    Garante defaults quando não existir.
    """
    defaults = {
        "use_openai": True,
        "offline_mode": False,
    }
    try:
        from settings_store import get_runtime_flags  # type: ignore
        flags = get_runtime_flags()
        if not isinstance(flags, dict):
            return defaults
        for k, v in defaults.items():
            flags.setdefault(k, v)
        return flags
    except Exception:
        return defaults


# -----------------------------
# Configuração de chaves
# -----------------------------
def configure_keys(api_key: Optional[str], online: Optional[bool] = None, **_kwargs) -> None:
    """
    Configura a chave da OpenAI em tempo de execução.
    Aceita 'online' e **kwargs para compatibilidade (ignorados aqui).

    Observação: o modo online/offline é tratado pelo settings_store
    em outro fluxo (apply_runtime_flags). Aqui apenas setamos a chave.
    """
    if not api_key:
        logger.info("configure_keys: nenhuma chave OpenAI fornecida.")
        return

    key = api_key.strip()
    os.environ["OPENAI_API_KEY"] = key

    # Compatibilidade com SDK legacy (openai<1) se estiver instalado
    try:
        import openai  # type: ignore
        if hasattr(openai, "api_key"):
            openai.api_key = key
    except Exception:
        pass

    logger.info("configure_keys: OPENAI_API_KEY configurada em ambiente.")


# -----------------------------
# Client OpenAI (dinâmico)
# -----------------------------
def _build_openai_client() -> Tuple[Optional[str], Any]:
    """
    Tenta criar cliente OpenAI. Suporta:
    - SDK novo (from openai import OpenAI)
    - SDK legacy (import openai)

    Retorna (modo, client)
      modo: "new" | "legacy" | None
      client: objeto client/import ou None
    """
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None, None

    # Tenta SDK novo
    try:
        from openai import OpenAI  # type: ignore
        client = OpenAI(api_key=api_key)
        return "new", client
    except Exception:
        pass

    # Tenta SDK legacy
    try:
        import openai  # type: ignore
        if hasattr(openai, "api_key"):
            openai.api_key = api_key
        return "legacy", openai
    except Exception:
        pass

    return None, None


def _should_use_openai() -> bool:
    flags = _get_runtime_flags_safe()
    if flags.get("offline_mode"):
        return False
    if not flags.get("use_openai", True):
        return False
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


# -----------------------------
# Chamadas auxiliares ao LLM
# -----------------------------
_PREFERRED_MODELS = [
    # Ordem de preferência; o helper tenta usar o primeiro que existir
    "gpt-4o-mini",  # SDK novo
    "gpt-4o",       # SDK novo
    "gpt-3.5-turbo" # SDK legacy (ampla compatibilidade)
]


def _chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Optional[str]:
    """
    Faz uma chamada de chat completion ao OpenAI, tentando SDK novo e depois legacy.
    Retorna o texto ou None em caso de falha (sem exceção subir).
    """
    if not _should_use_openai():
        return None

    mode, client = _build_openai_client()
    if mode is None or client is None:
        return None

    # SDK novo
    if mode == "new":
        try:
            for model in _PREFERRED_MODELS:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        temperature=temperature,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    )
                    content = (resp.choices[0].message.content or "").strip()
                    if content:
                        return content
                except Exception:
                    continue
        except Exception as e:
            logger.warning("OpenAI(new) falhou: %s", e)
        return None

    # SDK legacy
    try:
        for model in reversed(_PREFERRED_MODELS):  # tenta primeiro gpt-3.5-turbo aqui
            try:
                # type: ignore[attr-defined]
                resp = client.ChatCompletion.create(
                    model=model,
                    temperature=temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
                content = (resp["choices"][0]["message"]["content"] or "").strip()
                if content:
                    return content
            except Exception:
                continue
    except Exception as e:
        logger.warning("OpenAI(legacy) falhou: %s", e)

    return None


# -----------------------------
# APIs usadas pela UI
# -----------------------------
def extract_claim(text: str, max_chars: int = 240) -> str:
    """
    Extrai a alegação central do texto.
    - Se OpenAI estiver disponível e online, usa LLM.
    - Caso contrário, fallback heurístico: primeira frase/trecho relevante.
    """
    text = (text or "").strip()
    if not text:
        return ""

    system = "Você é um assistente de checagem. Extraia a alegação factual central de forma objetiva e curta."
    user = (
        "Texto:\n"
        f"{text}\n\n"
        "Responda apenas com a alegação central, sem comentários. "
        f"Limite a ~{max_chars} caracteres."
    )

    llm = _chat_completion(system, user, temperature=0.0)
    if llm:
        return llm[:max_chars].strip()

    # Fallback simples (offline): primeira sentença ou recorte curto
    enders = [".", "!", "?"]
    cut = min(len(text), max_chars)
    snippet = text[:cut]
    for i, ch in enumerate(snippet):
        if ch in enders and i > 30:  # evita frases minúsculas
            return snippet[: i + 1].strip()
    return snippet.strip()


def _normalize_evidence_item(item: Any) -> str:
    """
    Aceita str ou dict com campos comuns (title/url/snippet/content).
    Retorna uma string concisa representando a evidência.
    """
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        content = str(item.get("content") or item.get("snippet") or "").strip()
        parts = [p for p in [title, content, url] if p]
        return " — ".join(parts) if parts else ""
    return str(item)


def summarize_evidence(evidence_items: List[Any], max_chars: int = 700) -> str:
    """
    Gera um resumo estruturado das evidências.
    - Se OpenAI disponível, sumariza com LLM.
    - Caso contrário, fallback concatena os principais pontos.
    """
    items = [_normalize_evidence_item(x) for x in (evidence_items or [])]
    items = [x for x in items if x]

    if not items:
        return "Sem evidências coletadas."

    joined = "\n- " + "\n- ".join(items[:10])  # limita 10 p/ segurança de prompt
    system = (
        "Você é um analista. Dado um conjunto de evidências, produza um resumo neutro, "
        "apontando convergências e divergências, e quaisquer conflitos de informação. "
        "Seja objetivo e cite fontes pelo título/URL quando claro."
    )
    user = f"Evidências:{joined}\n\nResuma em até {max_chars} caracteres."

    llm = _chat_completion(system, user, temperature=0.2)
    if llm:
        return llm[:max_chars].strip()

    # Fallback offline: retorna uma colagem organizada
    head = "Resumo (offline): principais pontos encontrados:"
    body = joined
    colado = f"{head}\n{body}"
    return colado[:max_chars].strip()
