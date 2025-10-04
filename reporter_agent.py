#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, time
from typing import Dict, Any

class ReporterAgent:
    """
    Gera relatório JSON explicável.
    """
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, content_meta: Dict[str, Any], checkers, checks, consensus) -> Dict[str, Any]:
        report = {
            "content": {
                "id": content_meta.get("id"),
                "received_at": content_meta.get("received_at"),
                "type": content_meta.get("type"),
                "source": content_meta.get("source"),
                "category": content_meta.get("category"),
                "gut": {
                    "gravidade": content_meta.get("gut_gravidade"),
                    "urgencia": content_meta.get("gut_urgencia"),
                    "tendencia": content_meta.get("gut_tendencia"),
                    "prioridade": content_meta.get("overall_priority"),
                },
                "raw_excerpt": (content_meta.get("raw_content","") or "")[:300],
            },
            "checkers": checkers,
            "individual_findings": checks,
            "consensus": {
                "veracity_score": consensus.get("veracity_score"),
                "final_label": consensus.get("final_label"),
                "explanation": consensus.get("explanation"),
            },
            "generated_at": int(time.time())
        }
        path = os.path.join(self.output_dir, f"{content_meta.get('id')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return {"report_path": path, "report_json": report}
