# scheduler_adapter.py
from __future__ import annotations
import json
import sys
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
SCHED_SCRIPT = ROOT / "multiagent_gut_scheduler.py"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

_NATIVE = {}
try:
    from multiagent_gut_scheduler import enqueue_content, process_round, get_status  # type: ignore
    _NATIVE["ok"] = True
except Exception:
    _NATIVE["ok"] = False

def _run_cli(args: List[str]) -> Tuple[int, str]:
    """
    Executa o scheduler via CLI e retorna (returncode, saída completa).
    """
    cmd = [sys.executable, "-u", str(SCHED_SCRIPT)] + args
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), shell=False)
    out = ""
    if proc.stdout:
        out += proc.stdout
    if proc.stderr:
        # mantém stderr também (útil quando há Traceback)
        out += ("\n" if out else "") + proc.stderr
    return proc.returncode, out

def _parse_enqueued_id(text: str) -> Optional[str]:
    m = re.search(r"Enfileirado\s+([0-9a-fA-F-]{36})", text)
    return m.group(1) if m else None

def enqueue(content: str, content_type: str = "text", source: str = "ui", process_now: bool = False) -> Dict[str, str]:
    """
    Enfileira conteúdo. Em modo nativo usa funções do módulo, senão cai para o CLI.
    """
    if _NATIVE["ok"]:
        try:
            cid = enqueue_content(content=content, content_type=content_type, source=source)  # type: ignore
            if process_now:
                try:
                    process_round()  # type: ignore
                except Exception:
                    pass
            return {"id": str(cid), "status": "enqueued(native)", "stdout": ""}
        except Exception:
            # fallback para CLI
            pass

    args = ["--submit", "--type", content_type, "--source", source, "--content", content]
    if process_now:
        args.append("--process")

    code, out = _run_cli(args)
    cid = _parse_enqueued_id(out) or ""
    status = "enqueued+processed" if process_now else "enqueued"
    if code != 0:
        status = "error"
    return {"id": cid, "status": status, "stdout": (out or "").strip()}

def process_once() -> Dict[str, str]:
    if _NATIVE["ok"]:
        try:
            process_round()  # type: ignore
            return {"status": "processed(native)", "stdout": ""}
        except Exception:
            pass
    code, out = _run_cli(["--process"])
    return {"status": "processed" if code == 0 else "error", "stdout": (out or "").strip()}

def status_snapshot() -> Dict[str, object]:
    if _NATIVE["ok"]:
        try:
            st = get_status()  # type: ignore
            return {"native": True, "data": st}
        except Exception:
            pass
    reports = list_reports(limit=50)
    return {"native": False, "reports": reports, "reports_dir": str(REPORTS_DIR)}

def list_reports(limit: int = 100) -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    for p in sorted(REPORTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        items.append({"id": p.stem, "path": str(p)})
    return items

def read_report_json(report_id: str) -> Dict[str, object]:
    fp = (REPORTS_DIR / f"{report_id}.json")
    if not fp.exists():
        pt = Path(report_id)
        if pt.exists():
            fp = pt.resolve()
    if not fp.exists():
        return {"error": f"report not found: {report_id}"}
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"failed to read report: {e}", "path": str(fp)}
