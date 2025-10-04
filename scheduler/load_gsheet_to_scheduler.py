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
from multiagent_gut_scheduler import enqueue_content, process_round

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
    for _, row in df.iterrows():
        item = row_to_item(row.to_dict())
        meta = enqueue_content(content_type=item['type'], source=item['source'], content=item['raw_content'])
        print(f"+ Enfileirado {meta['content_id']} cat={meta['category']} priority={meta['priority']}")
    if args.process:
        out = process_round()
        for o in out:
            print(f"✓ Processado: {o['content_id']}  label={o['consensus']['final_label']} score={o['consensus']['veracity_score']}")

if __name__ == "__main__":
    main()
