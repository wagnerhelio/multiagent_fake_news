#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
import os, uuid

from multiagent_gut_scheduler import Orchestrator

app = FastAPI(title="Multiagent GUT Scheduler API")
orch = Orchestrator()

@app.post("/submit")
async def submit_item(type: str = Form("text"),
                      source: str = Form("api"),
                      text: Optional[str] = Form(None),
                      file: Optional[UploadFile] = File(None)):
    raw = text or ""
    if file is not None:
        up_dir = "./uploads"; os.makedirs(up_dir, exist_ok=True)
        fname = f"{uuid.uuid4()}_{file.filename}"
        path = os.path.join(up_dir, fname)
        with open(path, "wb") as f:
            f.write(await file.read())
        raw = path
    meta = orch.ingest_and_enqueue({"type": type, "source": source, "raw_content": raw})
    return JSONResponse(meta)

@app.post("/process")
async def process(max_items: int = 3):
    out = orch.run_once(max_items=max_items)
    return JSONResponse(out)

@app.get("/status")
async def status():
    return JSONResponse(orch.scheduler.get_queue_status())

@app.get("/report/{content_id}")
async def report(content_id: str):
    path = os.path.join("./reports", f"{content_id}.json")
    if not os.path.exists(path):
        return JSONResponse({"error":"not_found"}, status_code=404)
    return FileResponse(path, media_type="application/json", filename=f"{content_id}.json")
