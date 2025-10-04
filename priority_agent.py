#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any

class PriorityAgent:
    """
    Atribui GUT com regras simples e determinísticas para MVP.
    G, U, T ∈ [1..5]. overall_priority = G*U*T.
    """
    def __init__(self):
        pass

    def _score_from_text(self, text: str) -> Dict[str, int]:
        text = (text or "").lower()
        G = U = T = 2  # base

        # Gravidade por termos
        if any(w in text for w in ["morte", "ataque", "fraude", "crime", "emergência"]):
            G = 5
        elif any(w in text for w in ["corrupção", "epidemia", "desastre"]):
            G = 4
        elif any(w in text for w in ["alerta", "investigação", "controverso"]):
            G = 3

        # Urgência
        if any(w in text for w in ["urgente", "agora", "breaking"]):
            U = 5
        elif any(w in text for w in ["hoje", "imediato"]):
            U = 4
        elif any(w in text for w in ["recente", "novo"]):
            U = 3

        # Tendência (viralidade)
        if any(w in text for w in ["viral", "trending", "compartilhar", "whatsapp"]):
            T = 5
        elif any(w in text for w in ["polêmica", "debate", "rumor"]):
            T = 4
        elif any(w in text for w in ["repercussão", "comentado"]):
            T = 3

        return {"G": G, "U": U, "T": T}

    def assign_priority(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        gut = self._score_from_text(meta.get("raw_content", ""))
        meta = dict(meta)
        meta["gut_gravidade"] = gut["G"]
        meta["gut_urgencia"] = gut["U"]
        meta["gut_tendencia"] = gut["T"]
        meta["overall_priority"] = gut["G"] * gut["U"] * gut["T"]
        return meta
