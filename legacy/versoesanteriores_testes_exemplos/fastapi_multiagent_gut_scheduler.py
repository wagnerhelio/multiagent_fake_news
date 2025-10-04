"""
FastAPI: Sistema Multiagente para Checagem de Fatos com Scheduler GUT Preemptivo
Autor: ChatGPT (para Wagner)

Execute:
  pip install fastapi uvicorn "pydantic>=2" 
  python fastapi_multiagent_gut_scheduler.py  # (modo standalone)
  # ou
  uvicorn fastapi_multiagent_gut_scheduler:app --host 0.0.0.0 --port 8080 --reload

Endpoints:
  POST   /submit                 -> enfileira conteúdo {formato,G,U,T,payload}
  GET    /status/{conteudo_id}   -> estado, histórico e unidade
  GET    /report/{conteudo_id}   -> relatório JSON (se fechado)
  GET    /reports                -> lista de relatórios disponíveis
  GET    /queue                  -> snapshot das filas e execuções
  POST   /simulate?n=12&seed=42  -> injeta N conteúdos sintéticos (opcional, p/ teste)
  GET    /health                 -> status do serviço

Observações:
 - Protótipo in-memory + JSONs persistidos em ./reports/.
 - Preempção agressiva quando chega item com prioridade > fator*atual (fator=1.35).
 - Cada unidade tem capacidade concorrente=2 e >=7 perfis; cada tarefa consulta ≥5 perfis.
 - Consenso explicável (logit com pesos de reputação), rótulo final por faixas de score.
"""
from __future__ import annotations

import argparse
import asyncio
import enum
import heapq
import json
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

# -----------------------------
# Domínio
# -----------------------------
class Formato(str, enum.Enum):
    TEXTO = "texto"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGEM = "imagem"

class Estado(str, enum.Enum):
    NOVO = "novo"
    EM_ANALISE = "em_analise"
    PREEMPTADO = "preemptado"
    EM_REVISAO = "em_revisao"
    FECHADO = "fechado"

@dataclass(order=True)
class PrioritizedItem:
    prioridade_negativa: float
    t_arrival: float
    item: "Conteudo" = field(compare=False)

@dataclass
class Conteudo:
    id: str
    formato: Formato
    G: int
    U: int
    T: int
    prioridade: float
    payload: Dict[str, Any]
    estado: Estado = Estado.NOVO
    historico: List[str] = field(default_factory=list)
    t_criacao: float = field(default_factory=time.time)
    t_inicio: Optional[float] = None
    t_fim: Optional[float] = None
    unidade: Optional[str] = None

    def registrar(self, msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.historico.append(f"[{ts}] {msg}")

@dataclass
class PerfilChecador:
    id: str
    especialidade: Formato
    reputacao: float

@dataclass
class UnidadeChecagem:
    id: str
    nome: str
    perfis: List[PerfilChecador]
    capacidade_concorrente: int = 2
    em_execucao: Dict[str, asyncio.Task] = field(default_factory=dict)

    def capacidade_livre(self) -> int:
        return max(0, self.capacidade_concorrente - len(self.em_execucao))

class FilaFormato:
    def __init__(self, formato: Formato) -> None:
        self.formato = formato
        self._heap: List[PrioritizedItem] = []
        self._arrival_counter = 0
        self.lock = asyncio.Lock()

    def __len__(self) -> int:
        return len(self._heap)

    async def push(self, c: Conteudo) -> None:
        async with self.lock:
            self._arrival_counter += 1
            heapq.heappush(self._heap, PrioritizedItem(-c.prioridade, self._arrival_counter, c))

    async def pop(self) -> Optional[Conteudo]:
        async with self.lock:
            if not self._heap:
                return None
            return heapq.heappop(self._heap).item

    async def requeue(self, c: Conteudo) -> None:
        await self.push(c)

class Consenso:
    @staticmethod
    def combinar_pareceres(pareceres: List[Dict[str, Any]]) -> Dict[str, Any]:
        eps = 1e-6
        logits, pesos = [], []
        for p in pareceres:
            prob = min(max(p["prob_verdade"], eps), 1 - eps)
            w = max(eps, p.get("reputacao", 0.5))
            logit = math.log(prob / (1 - prob))
            logits.append(logit)
            pesos.append(w)
        num = sum(l * w for l, w in zip(logits, pesos))
        den = sum(pesos) or eps
        mean_logit = num / den
        var = 0.5 if len(logits) < 2 else (sum((l - (sum(logits)/len(logits)))**2 for l in logits) / (len(logits)-1))
        sd = (var + eps) ** 0.5
        score = 1 / (1 + math.exp(-mean_logit))
        low = 1 / (1 + math.exp(-(mean_logit - 1.96 * sd)))
        high = 1 / (1 + math.exp(-(mean_logit + 1.96 * sd)))
        return {
            "score_verdade": score,
            "z_score": mean_logit / (sd or 1.0),
            "intervalo_conf": [low, high],
            "decisoes_intermediarias": {
                "logits": logits,
                "pesos": pesos,
                "mean_logit": mean_logit,
                "sd_logit": sd,
            },
        }

class Preemptado(Exception):
    pass

class Scheduler:
    def __init__(self, unidades: List[UnidadeChecagem]) -> None:
        self.filas: Dict[Formato, FilaFormato] = {f: FilaFormato(f) for f in Formato}
        self.unidades = {u.id: u for u in unidades}
        self.running: Dict[str, Conteudo] = {}
        self._stop = False

    async def submit(self, c: Conteudo) -> None:
        c.registrar("Conteúdo recebido e enfileirado")
        await self.filas[c.formato].push(c)

    def parar(self) -> None:
        self._stop = True

    async def loop_despacho(self, tick_ms: int = 300) -> None:
        while not self._stop:
            await self._despachar()
            await asyncio.sleep(tick_ms / 1000)

    async def _despachar(self) -> None:
        for unidade in self.unidades.values():
            livre = unidade.capacidade_livre()
            if livre <= 0:
                continue
            for _ in range(livre):
                melhor = await self._pop_global_top()
                if not melhor:
                    break
                await self._iniciar_execucao(unidade, melhor)

    async def _pop_global_top(self) -> Optional[Conteudo]:
        candidatos: List[Tuple[float, Conteudo, FilaFormato]] = []
        popped: List[Tuple[FilaFormato, Conteudo]] = []
        for fila in self.filas.values():
            c = await fila.pop()
            if c:
                candidatos.append((c.prioridade, c, fila))
                popped.append((fila, c))
        if not candidatos:
            return None
        candidatos.sort(key=lambda t: t[0], reverse=True)
        melhor = candidatos[0]
        for fila, c in popped:
            if c.id != melhor[1].id:
                await fila.requeue(c)
        return melhor[1]

    async def _iniciar_execucao(self, unidade: UnidadeChecagem, c: Conteudo) -> None:
        c.estado = Estado.EM_ANALISE
        c.t_inicio = time.time()
        c.unidade = unidade.id
        c.registrar(f"Despachado para unidade {unidade.nome}")
        task = asyncio.create_task(self._processar_conteudo(unidade, c))
        unidade.em_execucao[c.id] = task
        self.running[c.id] = c

    async def _processar_conteudo(self, unidade: UnidadeChecagem, c: Conteudo) -> None:
        try:
            await self._checar_preempcao(c)
            # Tempo de análise sintético
            base = max(0.5, min(4.0, 2.5 - (c.prioridade - 10) * 0.1))
            await asyncio.sleep(base)
            pareceres = self._pareceres_da_unidade(unidade, c)
            consenso = Consenso.combinar_pareceres(pareceres)
            relatorio = self._montar_relatorio(c, unidade, pareceres, consenso)
            salvar_relatorio(relatorio, c.id)
            c.estado = Estado.FECHADO
            c.t_fim = time.time()
            c.registrar("Análise concluída e relatório emitido")
        except Preemptado:
            c.estado = Estado.PREEMPTADO
            c.registrar("Tarefa preemptada: retornando à fila")
            await self.filas[c.formato].requeue(c)
        except Exception as e:
            c.estado = Estado.EM_REVISAO
            c.registrar(f"Erro: {e}")
        finally:
            unidade.em_execucao.pop(c.id, None)
            self.running.pop(c.id, None)

    async def _checar_preempcao(self, c: Conteudo) -> None:
        fator = 1.35
        top = await self._pop_global_top()
        if top:
            await self.filas[top.formato].requeue(top)
            if top.prioridade > c.prioridade * fator:
                raise Preemptado()

    def _pareceres_da_unidade(self, unidade: UnidadeChecagem, c: Conteudo) -> List[Dict[str, Any]]:
        pref = [p for p in unidade.perfis if p.especialidade == c.formato]
        outros = [p for p in unidade.perfis if p.especialidade != c.formato]
        random.shuffle(pref); random.shuffle(outros)
        escolhidos = (pref + outros)[: max(5, min(len(unidade.perfis), 7))]
        pareceres = []
        for p in escolhidos:
            base = 0.5 + random.uniform(-0.15, 0.15)
            ajuste = (c.prioridade - 27) * 0.01
            prob = min(max(base - abs(ajuste), 0.05), 0.95)
            pareceres.append({
                "checador_id": p.id,
                "especialidade": p.especialidade,
                "reputacao": round(p.reputacao, 3),
                "prob_verdade": round(prob, 4),
                "justificativa": f"Heurística considerando sinais do formato {c.formato}.",
            })
        return pareceres

    def _montar_relatorio(self, c: Conteudo, unidade: UnidadeChecagem, pareceres: List[Dict[str, Any]], consenso: Dict[str, Any]) -> Dict[str, Any]:
        score = consenso["score_verdade"]
        rotulo = rotular(score)
        return {
            "conteudo_id": c.id,
            "formato": c.formato,
            "prioridade_GUT": {"G": c.G, "U": c.U, "T": c.T, "prioridade": c.prioridade},
            "estado_final": str(c.estado),
            "unidade": {"id": unidade.id, "nome": unidade.nome},
            "checadores_env": pareceres,
            "consenso": consenso,
            "rotulo_final": rotulo,
            "payload_resumo": {k: v for k, v in c.payload.items() if k in ("titulo", "fonte", "hash")},
            "historico": c.historico,
            "tempos": {"inicio": c.t_inicio, "fim": c.t_fim, "duracao": (c.t_fim or time.time()) - (c.t_inicio or time.time()) if c.t_inicio else None},
        }

# -----------------------------
# Utilidades
# -----------------------------
def gerar_id(prefixo: str = "C") -> str:
    return f"{prefixo}-{uuid.uuid4().hex[:8]}"

def calcular_prioridade_gut(G: int, U: int, T: int) -> float:
    return float(G * U * T)

def criar_unidade(nome: str, seed: Optional[int] = None) -> UnidadeChecagem:
    rnd = random.Random(seed) if seed is not None else random
    perfis = []
    especialidades = list(Formato)
    for i in range(7):
        esp = rnd.choice(especialidades)
        reput = max(0.2, min(0.98, rnd.random() * 0.9 + 0.1))
        perfis.append(PerfilChecador(id=f"P-{nome[:3].upper()}-{i+1}", especialidade=esp, reputacao=reput))
    return UnidadeChecagem(id=gerar_id("U"), nome=nome, perfis=perfis, capacidade_concorrente=2)

# Persistência simples de relatórios
def salvar_relatorio(relatorio: Dict[str, Any], conteudo_id: str) -> None:
    os.makedirs("reports", exist_ok=True)
    path = os.path.join("reports", f"relatorio_{conteudo_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)

def listar_relatorios() -> List[str]:
    if not os.path.isdir("reports"):
        return []
    return sorted([f for f in os.listdir("reports") if f.startswith("relatorio_") and f.endswith(".json")])

# -----------------------------
# FastAPI Schemas
# -----------------------------
class SubmitPayload(BaseModel):
    formato: Formato = Field(..., description="texto|audio|video|imagem")
    G: int = Field(..., ge=1, le=5)
    U: int = Field(..., ge=1, le=5)
    T: int = Field(..., ge=1, le=5)
    payload: Dict[str, Any] = Field(default_factory=dict)

# -----------------------------
# Aplicação FastAPI
# -----------------------------
app = FastAPI(title="Scheduler GUT Preemptivo", version="0.1.0")

# estado global simples (protótipo)
UNIDADES = [
    criar_unidade("Grupo Aruana", seed=1),
    criar_unidade("Grupo Anhanguera", seed=2),
    criar_unidade("Grupo MeiaPonte", seed=3),
]
SCHED = Scheduler(UNIDADES)
TASK_LOOP: Optional[asyncio.Task] = None
REGISTRY: Dict[str, Conteudo] = {}

@app.on_event("startup")
async def startup():
    global TASK_LOOP
    if TASK_LOOP is None:
        TASK_LOOP = asyncio.create_task(SCHED.loop_despacho(tick_ms=250))

@app.on_event("shutdown")
async def shutdown():
    SCHED.parar()
    if TASK_LOOP:
        try:
            await TASK_LOOP
        except Exception:
            pass

@app.get("/health")
async def health():
    return {"status": "ok", "running": len(SCHED.running), "filas": {f.value: len(SCHED.filas[f]) for f in Formato}}

@app.post("/submit")
async def submit(data: SubmitPayload):
    c = Conteudo(
        id=gerar_id(),
        formato=data.formato,
        G=data.G,
        U=data.U,
        T=data.T,
        prioridade=calcular_prioridade_gut(data.G, data.U, data.T),
        payload=data.payload,
    )
    REGISTRY[c.id] = c
    await SCHED.submit(c)
    return {"conteudo_id": c.id, "prioridade": c.prioridade, "estado": c.estado}

@app.get("/status/{conteudo_id}")
async def status(conteudo_id: str):
    c = REGISTRY.get(conteudo_id)
    if not c:
        raise HTTPException(404, "Conteúdo não encontrado")
    return {
        "conteudo_id": c.id,
        "estado": c.estado,
        "unidade": c.unidade,
        "historico": c.historico,
        "prioridade_GUT": {"G": c.G, "U": c.U, "T": c.T, "prioridade": c.prioridade},
    }

@app.get("/report/{conteudo_id}")
async def report(conteudo_id: str):
    path = os.path.join("reports", f"relatorio_{conteudo_id}.json")
    if not os.path.isfile(path):
        c = REGISTRY.get(conteudo_id)
        if c and c.estado != Estado.FECHADO:
            raise HTTPException(409, "Relatório ainda não disponível (processando)")
        raise HTTPException(404, "Relatório não encontrado")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)

@app.get("/reports")
async def reports():
    return {"arquivos": listar_relatorios()}

@app.get("/queue")
async def queue():
    return {
        "filas": {f.value: len(SCHED.filas[f]) for f in Formato},
        "running": [cid for cid in SCHED.running.keys()],
        "unidades": {u.nome: list(u.em_execucao.keys()) for u in UNIDADES},
    }

@app.post("/simulate")
async def simulate(n: int = Query(12, ge=1, le=200), seed: Optional[int] = Query(None)):
    if seed is not None:
        random.seed(seed)
    formatos = list(Formato)
    for i in range(n):
        G, U, T = random.randint(1,5), random.randint(1,5), random.randint(1,5)
        c = Conteudo(
            id=gerar_id(),
            formato=random.choice(formatos),
            G=G, U=U, T=T,
            prioridade=calcular_prioridade_gut(G,U,T),
            payload={"titulo": f"Caso {uuid.uuid4().hex[:6]}", "fonte": random.choice(["rede_social","portal","mensageria","blog"]), "hash": uuid.uuid4().hex},
        )
        REGISTRY[c.id] = c
        await SCHED.submit(c)
        # injeta alguns críticos
        if i in {3, 7}:
            c2 = Conteudo(
                id=gerar_id(), formato=random.choice(formatos), G=5, U=5, T=5,
                prioridade=calcular_prioridade_gut(5,5,5),
                payload={"titulo": "ALTA PRIORIDADE - Caso crítico", "fonte": "portal", "hash": uuid.uuid4().hex},
            )
            REGISTRY[c2.id] = c2
            await SCHED.submit(c2)
    return {"enfileirados": n}

# -----------------------------
# Execução standalone (opcional)
# -----------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    import uvicorn
    uvicorn.run("fastapi_multiagent_gut_scheduler:app", host=args.host, port=args.port, reload=False)
