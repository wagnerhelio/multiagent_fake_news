#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Dict, Any, List
import random

class CheckerSelectionAgent:
    """
    Seleciona um grupo de 5 checadores (≥2 especialistas + ≥2 independentes).
    Níveis: bronze, prata, ouro. Especialidade segue a categoria do conteúdo.
    """
    def __init__(self):
        self.levels = ["bronze", "prata", "ouro"]

    def select_checkers(self, category: str, n: int = 5) -> List[Dict[str, Any]]:
        n = max(5, n)
        k_spec = random.randint(2, 3)
        k_ind = n - k_spec
        checkers = []

        for i in range(k_spec):
            checkers.append({
                "id": f"spec-{category[:3].lower()}-{i+1}",
                "role": "especialista",
                "level": random.choices(self.levels, weights=[0.5, 0.35, 0.15])[0],
                "specialty": category,
                "reputation": random.uniform(0.6, 0.95),
            })
        for i in range(k_ind):
            checkers.append({
                "id": f"ind-{i+1}",
                "role": "independente",
                "level": random.choices(self.levels, weights=[0.6, 0.3, 0.1])[0],
                "specialty": "geral",
                "reputation": random.uniform(0.5, 0.9),
            })
        random.shuffle(checkers)
        return checkers
