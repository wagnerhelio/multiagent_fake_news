
# evidence_agent.py
# Integração opcional com Tavily para buscar evidências.
from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

# Estado global simples (ajustado via configure_keys)
TAVILY_KEY: Optional[str] = None
ONLINE_ENABLED: bool = True

try:
    from tavily import TavilyClient  # pip install tavily-python
except Exception:
    TavilyClient = None  # Permite rodar offline sem quebrar

_client: Optional['TavilyClient'] = None

def configure_keys(tavily_api_key: Optional[str] = None, online: Optional[bool] = None) -> None:
    """Configura chave da Tavily e modo online/offline durante a execução."""
    global TAVILY_KEY, ONLINE_ENABLED, _client
    if tavily_api_key is not None:
        TAVILY_KEY = tavily_api_key.strip() or None
        _client = None  # reseta cliente
    if online is not None:
        ONLINE_ENABLED = bool(online)
        _client = None

def _get_client() -> Optional['TavilyClient']:
    global _client
    if not ONLINE_ENABLED:
        return None
    key = TAVILY_KEY or os.environ.get("TAVILY_API_KEY")
    if not key or TavilyClient is None:
        return None
    if _client is None:
        try:
            _client = TavilyClient(api_key=key)
        except Exception:
            _client = None
    return _client

def search_evidence(query: str, max_results: int = 6, include_domains: Optional[List[str]] = None) -> Dict[str, Any]:
    """Busca fontes para embasar a checagem.
    Retorna {answer: str|None, results: [{title,url,snippet,score}], used: 'tavily'|'offline'|'none'}
    """
    if not query or not query.strip():
        return {"answer": None, "results": [], "used": "none"}

    client = _get_client()
    if client is None:
        # modo offline ou sem chave: retorna vazio mas anotando
        return {"answer": None, "results": [], "used": "offline"}

    try:
        resp = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            include_domains=include_domains or None,
        )
    except Exception:
        # Falhou a chamada — degrade
        return {"answer": None, "results": [], "used": "offline"}

    out = []
    for r in resp.get("results", []):
        out.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content") or r.get("snippet"),
            "score": r.get("score", 0),
        })
    return {"answer": resp.get("answer"), "results": out, "used": "tavily"}
