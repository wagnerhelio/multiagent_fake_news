# -*- coding: utf-8 -*-
"""
categorization_agent.py
-----------------------
Agente de categorização explicável (por assunto), independente do formato.
Pode ser usado pelo scheduler na etapa "B: Pré-processamento e Categorização".

API principal:
    - categorize_text(text: str) -> dict
    - categorize_content(fmt: str, content: str, metadata: dict | None) -> dict
    - get_available_categories() -> List[str]
    - register_categories(custom_map: Dict[str, set[str]])  # opcional para ampliar

A saída sempre traz:
{
  "category": "Economia",
  "confidence": 0.78,
  "matched": {"Economia": ["fgts", "banco"]},
  "explanation": "palavras-chave batendo em Economia",
}
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, Optional

# Mapa de categorias -> conjunto de palavras/raízes
_CATEGORY_KEYWORDS: Dict[str, Set[str]] = {
    "Política": {
        "congresso", "governo", "presidente", "senado", "câmara", "camara",
        "deputado", "ministro", "prefeito", "vereador", "eleição", "partido",
        "pl", "vetou", "decreto", "lei", "stf", "tse"
    },
    "Saúde": {
        "saúde", "saude", "hospital", "hosp", "médic", "medic", "posto",
        "vacina", "vírus", "virus", "covid", "gripe", "doença", "doenca",
        "tratamento", "sus", "contágio", "contagio", "surt"
    },
    "Economia": {
        "fgts", "imposto", "inflação", "inflacao", "dólar", "dolar", "pib",
        "salário", "salario", "emprego", "renda", "auxílio", "auxilio",
        "caixa", "banco", "economia", "conta", "tarifa"
    },
    "Esportes": {
        "jogo", "gol", "time", "campeonato", "torcida", "técnico", "tecnico",
        "clube", "partida", "futebol", "basquete", "vôlei", "volei", "atleta",
        "olímp", "olimp", "copa", "final"
    },
    "Mundo": {
        "onu", "nato", "guerra", "fronteira", "embaixada", "sanção", "sancao",
        "internacional", "acordo", "diplomacia", "russia", "china", "eua",
        "conflict", "israel", "palestina"
    },
    "Geral": set(),  # fallback
}


def register_categories(custom_map: Dict[str, List[str] | Set[str]]) -> None:
    """Permite ampliar ou substituir o dicionário de categorias/keywords."""
    for cat, keys in custom_map.items():
        _CATEGORY_KEYWORDS[cat] = set(keys)


def get_available_categories() -> List[str]:
    return list(_CATEGORY_KEYWORDS.keys())


def _tokenize(text: str) -> List[str]:
    t = text.lower()
    # separa por caracteres não alfanuméricos, preserva acentos simples
    toks = re.findall(r"[a-záéíóúâêôàçãõü0-9]+", t, flags=re.IGNORECASE)
    return toks


def _score_categories(text: str) -> Dict[str, int]:
    toks = _tokenize(text)
    joined = " ".join(toks)
    scores: Dict[str, int] = {k: 0 for k in _CATEGORY_KEYWORDS.keys()}
    for cat, keys in _CATEGORY_KEYWORDS.items():
        if not keys:
            continue
        for kw in keys:
            if kw in joined:
                scores[cat] += 1
    return scores


def _explain(scores: Dict[str, int], text: str) -> Dict[str, List[str]]:
    """Retorna as keywords que bateram por categoria."""
    joined = " ".join(_tokenize(text))
    matched: Dict[str, List[str]] = {}
    for cat, keys in _CATEGORY_KEYWORDS.items():
        hits = [kw for kw in keys if kw and kw in joined]
        if hits:
            matched[cat] = hits
    return matched


def categorize_text(text: str) -> Dict[str, object]:
    """Categorização por texto livre."""
    if not text or not text.strip():
        return {
            "category": "Geral",
            "confidence": 0.0,
            "matched": {},
            "explanation": "sem conteúdo",
        }
    scores = _score_categories(text)
    # melhor categoria
    best = max(scores, key=lambda k: scores[k])
    matched = _explain(scores, text)
    total_hits = sum(scores.values())
    conf = 0.0
    if total_hits > 0:
        conf = min(0.95, 0.55 + 0.1 * scores[best] + 0.05 * (scores[best] - max([v for k, v in scores.items() if k != best] + [0])))
    return {
        "category": best if scores[best] > 0 else "Geral",
        "confidence": round(conf, 3),
        "matched": matched,
        "explanation": f"palavras-chave batendo em {best}" if scores[best] > 0 else "sem match, fallback Geral",
    }


def categorize_content(fmt: str, content: str, metadata: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """
    Categoriza independentemente do formato:
      - text: usa o próprio conteúdo
      - image/audio/video: tenta metadata["hint"] ou content como caminho/legenda
    """
    fmt = (fmt or "text").lower().strip()
    meta_text = (metadata or {}).get("hint", "") if metadata else ""

    if fmt == "text":
        return categorize_text(content)
    else:
        # heurística simples: usa metadata/hint se houver; senão, usa o nome/caminho
        base = meta_text or (content or "")
        if not base:
            return {"category": "Geral", "confidence": 0.0, "matched": {}, "explanation": "sem informações para inferir"}
        return categorize_text(base)


# ----------------------
# Teste rápido CLI
# ----------------------
if __name__ == "__main__":
    samples = [
        "URGENTE: vídeo viral mostra suposta fraude no congresso! Compartilhe agora.",
        "Reviravolta no FGTS: saque liberado para todos os trabalhadores!",
        "Clube vence por 3x0 e torcida lota o estádio no clássico de domingo.",
        "Novo surto de gripe atinge cidades do interior; veja como se proteger.",
        "Moeda dispara com incertezas no cenário internacional.",
        "Texto genérico que não bate em nada.",
    ]
    for s in samples:
        out = categorize_text(s)
        print(s, "=>", out["category"], out["confidence"], "|", out["matched"])
