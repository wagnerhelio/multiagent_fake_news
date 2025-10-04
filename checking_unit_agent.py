#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any, List
import random

class CheckingUnitAgent:
    """
    Simula a análise de um conteúdo por um grupo de checadores.
    Cada checador devolve: label sugerido + confiança [0.5..0.95].
    """
    LABELS = ["Verdadeiro", "Falso", "Enganoso", "Descontextualizado", "Sátira", "Inconclusivo"]

    def __init__(self):
        pass

    def _auto_label(self, text: str) -> str:
        t = (text or "").lower()
        if any(w in t for w in ["não aconteceu", "fabricado", "deepfake", "falso", "fake"]):
            return "Falso"
        if any(w in t for w in ["sátira", "humor"]):
            return "Sátira"
        if any(w in t for w in ["fora de contexto", "descontextualizado"]):
            return "Descontextualizado"
        if any(w in t for w in ["parcialmente", "meia verdade", "enganoso"]):
            return "Enganoso"
        if t.strip():
            return "Verdadeiro"
        return "Inconclusivo"

    def check(self, content_meta: Dict[str, Any], checkers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        base_label = self._auto_label(content_meta.get("raw_content", ""))
        results = []
        for c in checkers:
            # Variação leve por reputação e nível
            conf = random.uniform(0.55, 0.95) * (0.9 + 0.2 * (1 if c["level"] == "ouro" else 0) + 0.1 * (1 if c["level"] == "prata" else 0))
            conf = min(conf, 0.98)
            # pequena chance de discordância para simular diversidade
            label = base_label
            if random.random() < 0.2:
                label = random.choice([l for l in self.LABELS if l != base_label])
            results.append({
                "checker_id": c["id"],
                "role": c["role"],
                "level": c["level"],
                "reputation": c["reputation"],
                "proposed_label": label,
                "confidence": round(conf, 3),
            })
        return results
