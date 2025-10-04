#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any, List, Tuple
from math import sqrt
try:
    from math import erf
except Exception:
    # fallback simple erf approximation
    import math
    def erf(x):
        # Abramowitz & Stegun approximation
        t = 1.0 / (1.0 + 0.5*abs(x))
        tau = t*math.exp(-x*x - 1.26551223 + 1.00002368*t + 0.37409196*t*t + 0.09678418*t**3 - 0.18628806*t**4 + 0.27886807*t**5 - 1.13520398*t**6 + 1.48851587*t**7 - 0.82215223*t**8 + 0.17087277*t**9)
        return 1 - tau if x >= 0 else tau - 1

def norm_cdf(x: float) -> float:
    # CDF da normal padrão via erf
    return 0.5 * (1 + erf(x / 1.4142135623730951))

class ConsensusAgent:
    """
    Agregador 'probit-like':
      1) Mapeia rótulos dos checadores para p in [0..1]
      2) Média ponderada por reputação * confiança
      3) Converte em z via probit inverso aproximado (apenas para explicação)
      4) Define rótulo final por faixas
    """
    LABEL_P = {
        "Verdadeiro": 0.9,
        "Sátira": 0.7,
        "Descontextualizado": 0.55,
        "Enganoso": 0.35,
        "Inconclusivo": 0.5,
        "Falso": 0.1,
    }

    def aggregate(self, content_meta: Dict[str, Any], checks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not checks:
            return {
                "veracity_score": 0.5,
                "final_label": "Inconclusivo",
                "explanation": "Sem pareceres suficientes para consenso."
            }
        ws = []
        ps = []
        for r in checks:
            w = max(0.1, r.get("reputation", 0.6)) * max(0.5, r.get("confidence", 0.6))
            p = self.LABEL_P.get(r.get("proposed_label", "Inconclusivo"), 0.5)
            ws.append(w); ps.append(p)
        wsum = sum(ws)
        p_hat = sum(w*p for w, p in zip(ws, ps)) / wsum if wsum else 0.5

        # z-score "probit-like" para explicar (usamos inversa numérica simples via busca, sem scipy)
        # aproximação: achar z tal que norm_cdf(z) ~= p_hat
        # bisseção em [-6, 6]
        lo, hi = -6.0, 6.0
        for _ in range(40):
            mid = (lo+hi)/2
            if norm_cdf(mid) < p_hat:
                lo = mid
            else:
                hi = mid
        z = (lo+hi)/2

        # Rótulo final por faixas
        if p_hat >= 0.75:
            label = "Verdadeiro"
        elif p_hat >= 0.6:
            label = "Sátira" if self._majority_label(checks) == "Sátira" else "Descontextualizado"
        elif p_hat >= 0.4:
            label = "Enganoso"
        else:
            label = "Falso"

        expl = {
            "weighted_probability": round(p_hat, 3),
            "z_probit_like": round(z, 3),
            "votes": self._vote_breakdown(checks),
            "weights_hint": "Peso = reputação × confiança (normalizado)."
        }
        return {"veracity_score": float(round(p_hat, 3)), "final_label": label, "explanation": expl}

    def _vote_breakdown(self, checks: List[Dict[str, Any]]) -> Dict[str, int]:
        out = {}
        for r in checks:
            lbl = r.get("proposed_label", "Inconclusivo")
            out[lbl] = out.get(lbl, 0) + 1
        return out

    def _majority_label(self, checks: List[Dict[str, Any]]) -> str:
        votes = self._vote_breakdown(checks)
        return max(votes, key=votes.get)
