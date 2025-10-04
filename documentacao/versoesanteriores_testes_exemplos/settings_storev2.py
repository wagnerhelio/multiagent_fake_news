
# settings_store.py
# Armazena e carrega chaves de API (opcional) sem usar .env.
# ATENÇÃO: salva em texto puro. Use somente em ambiente local seguro.
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

KEYS_PATH = Path(".keys.json")

def load_keys() -> Dict[str, Any]:
    if KEYS_PATH.exists():
        try:
            data = json.loads(KEYS_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"openai_api_key": "", "tavily_api_key": "", "online": True}
            return {
                "openai_api_key": data.get("openai_api_key", ""),
                "tavily_api_key": data.get("tavily_api_key", ""),
                "online": bool(data.get("online", True)),
            }
        except Exception:
            return {"openai_api_key": "", "tavily_api_key": "", "online": True}
    return {"openai_api_key": "", "tavily_api_key": "", "online": True}

def save_keys(openai_api_key: str, tavily_api_key: str, online: bool) -> None:
    data = {
        "openai_api_key": (openai_api_key or ""),
        "tavily_api_key": (tavily_api_key or ""),
        "online": bool(online),
    }
    KEYS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
