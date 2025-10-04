# settings_store.py
from pathlib import Path
import json
import os
from typing import Dict, Any

STORE_FILE = Path("../config/runtime_settings.json")
DEFAULTS: Dict[str, Any] = {
    "openai_api_key": None,
    "tavily_api_key": None,
    "use_openai": True,
    "use_tavily": True,
    "offline_mode": False,
}

def _read_store() -> Dict[str, Any]:
    if STORE_FILE.exists():
        try:
            with STORE_FILE.open("r", encoding="utf-8") as f:
                data = json.load(f)
            merged = {**DEFAULTS, **(data or {})}
            return merged
        except Exception:
            return DEFAULTS.copy()
    return DEFAULTS.copy()

def _write_store(data: Dict[str, Any]) -> None:
    tmp = STORE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(STORE_FILE)

# --------- API usada pela UI (gradio_multiagent_ui.py) ---------

def load_keys() -> Dict[str, Any]:
    """Retorna as chaves, preferindo o arquivo; se vazio, cai para variáveis de ambiente."""
    s = _read_store()
    openai_key = s.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    tavily_key = s.get("tavily_api_key") or os.getenv("TAVILY_API_KEY")
    return {
        "openai_api_key": openai_key,
        "tavily_api_key": tavily_key,
    }

def save_keys(openai_api_key=None, tavily_api_key=None) -> Dict[str, Any]:
    """Persiste chaves e espelha em variáveis de ambiente desta sessão."""
    s = _read_store()
    if openai_api_key is not None and str(openai_api_key).strip() != "":
        s["openai_api_key"] = str(openai_api_key).strip()
        os.environ["OPENAI_API_KEY"] = s["openai_api_key"]
    if tavily_api_key is not None and str(tavily_api_key).strip() != "":
        s["tavily_api_key"] = str(tavily_api_key).strip()
        os.environ["TAVILY_API_KEY"] = s["tavily_api_key"]
    _write_store(s)
    return {
        "openai_api_key": s.get("openai_api_key"),
        "tavily_api_key": s.get("tavily_api_key"),
    }

def get_runtime_flags() -> Dict[str, Any]:
    """Retorna os flags de execução usados no app."""
    s = _read_store()
    return {
        "use_openai": bool(s.get("use_openai", True)),
        "use_tavily": bool(s.get("use_tavily", True)),
        "offline_mode": bool(s.get("offline_mode", False)),
    }

def apply_runtime_flags(use_openai=None, use_tavily=None, offline_mode=None) -> Dict[str, Any]:
    """Atualiza flags no arquivo e reflete em variáveis de ambiente simples."""
    s = _read_store()

    if use_openai is not None:
        s["use_openai"] = bool(use_openai)
    if use_tavily is not None:
        s["use_tavily"] = bool(use_tavily)
    if offline_mode is not None:
        s["offline_mode"] = bool(offline_mode)

    os.environ["USE_OPENAI"] = "1" if s["use_openai"] else "0"
    os.environ["USE_TAVILY"] = "1" if s["use_tavily"] else "0"
    os.environ["OFFLINE_MODE"] = "1" if s["offline_mode"] else "0"

    _write_store(s)
    return {
        "use_openai": s["use_openai"],
        "use_tavily": s["use_tavily"],
        "offline_mode": s["offline_mode"],
    }

# (opcional) utilitário para ler tudo
def load_all() -> Dict[str, Any]:
    return _read_store()
