#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import os, uuid

# Importa funções diretas do scheduler
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from scheduler.multiagent_gut_scheduler import (
    enqueue_content, 
    process_round, 
    get_status, 
    get_report,
    list_report_ids
)

app = FastAPI(title="Multiagent GUT Scheduler API")

@app.post("/submit")
async def submit_item(type: str = Form("text"),
                      source: str = Form("api"),
                      text: Optional[str] = Form(None),
                      file: Optional[UploadFile] = File(None)):
    """Envia conteúdo para análise"""
    raw = text or ""
    if file is not None:
        # Salva arquivo enviado
        up_dir = "../data/ingested"
        os.makedirs(up_dir, exist_ok=True)
        fname = f"{uuid.uuid4()}_{file.filename}"
        path = os.path.join(up_dir, fname)
        with open(path, "wb") as f:
            f.write(await file.read())
        raw = path
    
    # Enfileira o conteúdo
    meta = enqueue_content(content_type=type, source=source, content=raw)
    return JSONResponse(meta)

@app.post("/process")
async def process(max_items: int = 3):
    """Processa itens da fila"""
    out = process_round(capacity=max_items)
    return JSONResponse(out)

@app.get("/status")
async def status():
    """Retorna status do scheduler"""
    return JSONResponse(get_status())

@app.get("/report/{content_id}")
async def report(content_id: str):
    """Retorna relatório específico"""
    report_data = get_report(content_id)
    if not report_data:
        return JSONResponse({"error":"not_found"}, status_code=404)
    return JSONResponse(report_data)

@app.get("/reports")
async def list_reports():
    """Lista todos os relatórios disponíveis"""
    report_ids = list_report_ids()
    return JSONResponse({"report_ids": report_ids, "count": len(report_ids)})
