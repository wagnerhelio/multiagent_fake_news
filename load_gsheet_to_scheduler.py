#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carrega uma planilha Google em CSV (URL de export) e enfileira no Orchestrator.
Uso:
  pip install pandas
  python load_gsheet_to_scheduler.py --csv "https://docs.google.com/spreadsheets/d/.../export?format=csv&gid=..." --limit 20 --process
Mapeamento automático tenta colunas: 'text' | 'Texto_Original' | 'conteudo'.
"""
import argparse
import pandas as pd
from multiagent_gut_scheduler import Orchestrator

def row_to_item(row: dict) -> dict:
    txt = row.get("text") or row.get("Texto_Original") or row.get("conteudo") or ""
    src = row.get("Fonte") or row.get("source") or "sheet"
    typ = row.get("type") or row.get("Tipo_Dado") or "text"
    return {"type": str(typ).lower(), "source": src, "raw_content": txt}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="URL de export CSV do Google Sheets")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--process", action="store_true")
    args = ap.parse_args()

    df = pd.read_csv(args.csv).head(args.limit)
    orch = Orchestrator()
    for _, row in df.iterrows():
        item = row_to_item(row.to_dict())
        meta = orch.ingest_and_enqueue(item)
        print(f"+ Enfileirado {meta['id']} cat={meta['category']} priority={meta['overall_priority']}")
    if args.process:
        out = orch.run_once()
        for o in out:
            print(f"✓ Relatório: {o['report']['report_path']}  label={o['consensus']['final_label']} score={o['consensus']['veracity_score']}")

if __name__ == "__main__":
    main()
