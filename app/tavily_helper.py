# tavily_helper.py
from __future__ import annotations

import os
import re
import json
import time
import html
from typing import List, Dict, Optional
from urllib.parse import urlencode, quote_plus

import requests

# ---------------------------
#   ESTADO EM MEMÓRIA
# ---------------------------
_TAVILY_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
_ONLINE_MODE: bool = not (os.getenv("OFFLINE_MODE", "false").lower() in {"1", "true", "yes"})


def configure_tavily(api_key: Optional[str], online: bool = True) -> Dict[str, object]:
    """
    Configura a chave do Tavily e o modo online/offline em runtime.
    """
    global _TAVILY_KEY, _ONLINE_MODE
    _TAVILY_KEY = api_key or _TAVILY_KEY
    _ONLINE_MODE = bool(online)
    return {"use_tavily": bool(_TAVILY_KEY), "offline_mode": not _ONLINE_MODE}


# ---------------------------
#   Fallback DuckDuckGo
# ---------------------------
def _clean_text(txt: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(txt or "")).strip()


def ddg_fallback(query: str, k: int = 5) -> List[Dict[str, str]]:
    """
    Fallback muito simples usando DuckDuckGo (HTML) sem libs extras.
    Retorna uma lista normalizada: [{title, url, snippet}, ...]
    """
    results: List[Dict[str, str]] = []
    try:
        url = "https://html.duckduckgo.com/html/"
        payload = {"q": query}
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; MultiAgent-GUT/1.0; +local)",
        }
        r = requests.post(url, data=payload, headers=headers, timeout=12)
        if r.status_code != 200:
            return results

        # Parse simples dos resultados
        # Cada resultado costuma ter <a class="result__a" href="...">Título</a>
        # O snippet pode aparecer em <a>…</a> vizinho ou em <div class="result__snippet">…</div>
        html_text = r.text

        # Captura blocos de resultados
        blocks = re.split(r'<div class="result[^"]*">', html_text)[1:]
        for b in blocks:
            # title + link
            m = re.search(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.S | re.I)
            if not m:
                continue
            link = html.unescape(m.group(1))
            title = _clean_text(re.sub(r"<[^>]+>", "", m.group(2)))

            # snippet
            m2 = re.search(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', b, re.S | re.I)
            if not m2:
                m2 = re.search(r'<div[^>]*class="result__snippet"[^>]*>(.*?)</div>', b, re.S | re.I)
            snippet = _clean_text(re.sub(r"<[^>]+>", "", m2.group(1))) if m2 else ""

            results.append({"title": title, "url": link, "snippet": snippet})
            if len(results) >= k:
                break

    except Exception:
        # silencioso: se der erro, devolve lista vazia
        return results

    return results


# ---------------------------
#   Tavily (com fallback)
# ---------------------------
def tavily_search(
    query: str,
    k: int = 5,
    api_key: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    offline_mode: Optional[bool] = None,
) -> List[Dict[str, str]]:
    """
    Busca na Web usando Tavily. Se:
      - não houver chave,
      - estiver offline,
      - ou a API falhar,
    cai no fallback do DuckDuckGo.

    Retorna lista normalizada: [{title, url, snippet}, ...]
    """
    key = api_key or _TAVILY_KEY
    online = _ONLINE_MODE if offline_mode is None else not offline_mode

    if not online:
        return []  # modo offline: sem rede

    # Tenta Tavily se tiver chave
    if key:
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": key,
                "query": query,
                "max_results": int(k),
                "include_domains": include_domains or [],
            }
            headers = {"Content-Type": "application/json"}
            r = requests.post(url, data=json.dumps(payload), headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                items = data.get("results") or []
                out: List[Dict[str, str]] = []
                for it in items:
                    out.append(
                        {
                            "title": _clean_text(it.get("title") or ""),
                            "url": it.get("url") or "",
                            "snippet": _clean_text(it.get("content") or it.get("snippet") or ""),
                        }
                    )
                    if len(out) >= k:
                        break
                return out
            # Status não-200 → fallback
        except Exception:
            pass

    # Sem chave ou falha na API → fallback
    return ddg_fallback(query, k=k)


# ---------------------------
#   Utilitários simples
# ---------------------------
def web_search(
    query: str,
    k: int = 5,
    use_tavily: bool = True,
    api_key: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    offline_mode: Optional[bool] = None,
) -> List[Dict[str, str]]:
    """
    Wrapper: se use_tavily=True tenta Tavily; se não, vai direto ao fallback DDG.
    """
    if use_tavily:
        return tavily_search(
            query=query,
            k=k,
            api_key=api_key,
            include_domains=include_domains,
            offline_mode=offline_mode,
        )
    # Força fallback
    if offline_mode:
        return []
    return ddg_fallback(query, k=k)
