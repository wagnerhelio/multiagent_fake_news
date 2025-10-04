#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import uuid
import time
from typing import Dict, Any

class IngestionAgent:
    """
    Agente de ingestão simples: atribui ID único, preserva campos básicos
    e normaliza estrutura para o pipeline.
    """
    def __init__(self, output_dir: str = "./ingested"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def ingest_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        # Campos mínimos esperados: type ('text'|'image'|'audio'|'video'), source, raw_content (texto ou caminho de arquivo)
        content_id = content.get("id") or str(uuid.uuid4())
        ts = int(time.time())
        norm = {
            "id": content_id,
            "received_at": ts,
            "type": content.get("type", "text"),
            "source": content.get("source", "unknown"),
            "raw_content": content.get("raw_content", ""),
            "status": "new",
            "metadata": content.get("metadata", {}),
        }
        return norm
