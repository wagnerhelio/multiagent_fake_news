"""
Protótipo: Sistema Multiagente para Checagem de Fatos com Scheduler GUT Preemptivo
Autor: ChatGPT (para Wagner)
Requisitos atendidos:
 - Filas por formato (texto, áudio, vídeo, imagem)
 - Scheduler central com preempção por prioridade (matriz GUT)
 - Unidades de checagem compostas por 5+ perfis virtuais (anonimizados, com especialidade e reputação)
 - Expedição/Despacho considerando prioridade GUT e capacidade
 - Consenso explicável (agregação probabilística com pesos de reputação; inspirado em probit/logit)
 - Relatório final exportável em JSON
 - Estados: novo, em_analise, preemptado, em_revisao, fechado

Como executar (exemplo):
    python multiagent_gut_scheduler.py --demo 12 --seed 42 --tick-ms 200

Isso vai simular a chegada e processamento de 12 conteúdos multimodais e salvar relatórios em ./reports/.

Dependências: apenas Python 3.10+ (usa asyncio, dataclasses, typing, json, random, uuid, heapq)
"""
from __future__ import annotations

import asyncio
import dataclasses
import enum
import heapq
import json
import math
import os
import random
import statistics
import string
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# -----------------------------
# Modelos básicos
# -----------------------------

class Formato(enum.StrEnum):
    TEXTO = "texto"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGEM = "imagem"

class Estado(enum.StrEnum):
    NOVO = "novo"
    EM_ANALISE = "em_analise"
    PREEMPTADO = "preemptado"
    EM_REVISAO = "em_revisao"
    FECHADO = "fechado"

@dataclass(order=True)
class PrioritizedItem:
    # heapq usa o primeiro campo para ordenar (menor primeiro). Como queremos MAIOR prioridade primeiro,
    # usamos prioridade_negativa = -prioridade (maior prioridade => menor valor aqui)
    prioridade_negativa: float
    t_arrival: float
    item: "Conteudo" = field(compare=False)

@dataclass
class Conteudo:
    id: str
    formato: Formato
    # Matriz GUT: gravidade, urgencia, tendencia (1..5)
    G: int
    U: int
    T: int
    prioridade: float  # calculada: G*U*T (ou versão log/normalizada)
    payload: Dict[str, Any]
    estado: Estado = Estado.NOVO
    historico: List[str] = field(default_factory=list)
    t_criacao: float = field(default_factory=time.time)
    t_inicio: Optional[float] = None
    t_fim: Optional[float] = None
    unidade: Optional[str] = None  # id da unidade de checagem

    def registrar(self, msg: str) -> None:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.historico.append(f"[{ts}] {msg}")

@dataclass
class PerfilChecador:
    id: str
    especialidade: Formato
    reputacao: float  # 0.0 .. 1.0 (peso)

@dataclass
class UnidadeChecagem:
    id: str
    nome: str
    perfis: List[PerfilChecador]
    capacidade_concorrente: int = 2  # quantos conteúdos pode processar em paralelo
    # execução corrente: conteudo_id -> task
    em_execucao: Dict[str, asyncio.Task] = field(default_factory=dict)

    def capacidade_livre(self) -> int:
        return max(0, self.capacidade_concorrente - len(self.em_execucao))

# -----------------------------
# Fila por formato (priority queue)
# -----------------------------
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
            p = heapq.heappop(self._heap)
            return p.item

    async def peek_lowest_running_candidate(self) -> Optional[Conteudo]:
        # retorna o de MENOR prioridade (fim do heap após ordenar), para facilitar a preempção cruzada se necessário
        async with self.lock:
            if not self._heap:
                return None
            # heap não dá peek do pior; copiamos e pegamos o max por prioridade_negativa
            worst = max(self._heap, key=lambda it: it.prioridade_negativa)
            return worst.item

    async def requeue(self, c: Conteudo) -> None:
        await self.push(c)

# -----------------------------
# Consenso (inspirado em probit/logit)
# -----------------------------
class Consenso:
    @staticmethod
    def combinar_pareceres(pareceres: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Recebe lista de pareceres individuais com campos:
            - prob_verdade (0..1)
            - reputacao (0..1)
            - justificativa (str)
        Retorna:
            - score_verdade (0..1)
            - z_score (float)
            - intervalo_conf (low, high)
            - decisoes_intermediarias
        Método: converte prob em logit, faz média ponderada pelos pesos (reputação),
        retorna sigmoid para voltar ao espaço [0,1]. Aproxima a ideia de um modelo probit/logit
        agregando opiniões com pesos (sem treinamento supervisionado).
        """
        eps = 1e-6
        logits = []
        pesos = []
        for p in pareceres:
            prob = min(max(p["prob_verdade"], eps), 1 - eps)
            w = max(eps, p.get("reputacao", 0.5))
            logit = math.log(prob / (1 - prob))
            logits.append(logit)
            pesos.append(w)
        # média ponderada
        num = sum(l * w for l, w in zip(logits, pesos))
        den = sum(pesos) or eps
        mean_logit = num / den
        # variância ponderada (estimativa simples)
        if len(logits) > 1:
            mean_simple = sum(logits) / len(logits)
            var = sum((l - mean_simple) ** 2 for l in logits) / (len(logits) - 1)
        else:
            var = 0.5  # heurística
        z = mean_logit / math.sqrt(var + eps)
        score = 1 / (1 + math.exp(-mean_logit))
        # intervalo de confiança aproximado no espaço do logit (±1.96*sd)
        sd = math.sqrt(var + eps)
        low_logit = mean_logit - 1.96 * sd
        high_logit = mean_logit + 1.96 * sd
        low = 1 / (1 + math.exp(-low_logit))
        high = 1 / (1 + math.exp(-high_logit))
        return {
            "score_verdade": score,
            "z_score": z,
            "intervalo_conf": [low, high],
            "decisoes_intermediarias": {
                "logits": logits,
                "pesos": pesos,
                "mean_logit": mean_logit,
                "sd_logit": sd,
            },
        }

# -----------------------------
# Scheduler Central com preempção por prioridade GUT
# -----------------------------
class Scheduler:
    def __init__(self, unidades: List[UnidadeChecagem]) -> None:
        self.filas: Dict[Formato, FilaFormato] = {f: FilaFormato(f) for f in Formato}
        self.unidades = {u.id: u for u in unidades}
        self.running: Dict[str, Conteudo] = {}  # conteudo_id -> conteudo
        self.lock = asyncio.Lock()
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
        # Para cada unidade, tente preencher capacidade com os itens de MAIOR prioridade
        for unidade in self.unidades.values():
            livre = unidade.capacidade_livre()
            if livre <= 0:
                continue
            for _ in range(livre):
                # Escolhe a fila com item de maior prioridade global
                melhor_item = await self._pop_global_top()
                if not melhor_item:
                    break
                await self._iniciar_execucao(unidade, melhor_item)

    async def _pop_global_top(self) -> Optional[Conteudo]:
        # Examina o topo de todas as filas e pega o melhor (maior prioridade). Como não temos peek,
        # fazemos pop tentativa em cada fila ordenando pelo item no topo (custo ok para protótipo).
        candidatos: List[Tuple[float, Conteudo, Formato]] = []
        # Tentamos pop e, se não for o melhor, colocamos de volta
        popped: List[Tuple[FilaFormato, Conteudo]] = []

        for f, fila in self.filas.items():
            c = await fila.pop()
            if c:
                candidatos.append((c.prioridade, c, f))
                popped.append((fila, c))
        if not candidatos:
            return None
        candidatos.sort(key=lambda t: t[0], reverse=True)
        melhor = candidatos[0][1]
        # Devolve os demais para as respectivas filas
        for fila, c in popped:
            if c.id != melhor.id:
                await fila.requeue(c)
        return melhor

    async def _iniciar_execucao(self, unidade: UnidadeChecagem, c: Conteudo) -> None:
        c.estado = Estado.EM_ANALISE
        c.t_inicio = time.time()
        c.unidade = unidade.id
        c.registrar(f"Despachado para unidade {unidade.nome} (capacidade atual: {len(unidade.em_execucao)}/{unidade.capacidade_concorrente})")
        task = asyncio.create_task(self._processar_conteudo(unidade, c))
        unidade.em_execucao[c.id] = task
        self.running[c.id] = c

    async def _processar_conteudo(self, unidade: UnidadeChecagem, c: Conteudo) -> None:
        try:
            # Antes de processar, checa se chegou algo de prioridade MUITO maior que justifique preempção imediata
            await self._checar_preempcao(c)
            # Simula tempo de análise proporcional ao inverso da prioridade, limitado por [0.5s, 4s]
            base = max(0.5, min(4.0, 2.5 - (c.prioridade - 10) * 0.1))
            await asyncio.sleep(base)
            # Executa checagem por pelo menos 5 perfis
            pareceres = self._pareceres_da_unidade(unidade, c)
            consenso = Consenso.combinar_pareceres(pareceres)
            # Monta relatório
            relatorio = self._montar_relatorio(c, unidade, pareceres, consenso)
            self._salvar_relatorio(relatorio, c.id)
            c.estado = Estado.FECHADO
            c.t_fim = time.time()
            c.registrar("Análise concluída e relatório emitido")
        except Preemptado:
            c.estado = Estado.PREEMPTADO
            c.registrar("Tarefa preemptada: retornando para a fila")
            await self.filas[c.formato].requeue(c)
        except Exception as e:
            c.estado = Estado.EM_REVISAO
            c.registrar(f"Erro na análise: {e}. Encaminhado para revisão")
        finally:
            # Libera slot
            unidade.em_execucao.pop(c.id, None)
            self.running.pop(c.id, None)

    async def _checar_preempcao(self, c: Conteudo) -> None:
        """Política de preempção: se existir item enfileirado com prioridade > prioridade_do_c * fator,
        pode-se interromper c e reencaminhar. Fator ajusta agressividade."""
        fator = 1.35
        # olha os topos indiretos das filas para ver possíveis itens críticos
        melhores: List[Conteudo] = []
        for fila in self.filas.values():
            cand = await fila.peek_lowest_running_candidate()  # reuso para inspeção
            # A função acima retorna o PIOR da fila; mas queremos detectar se há alguém MUITO melhor.
            # Em vez disso, faremos um pop+push rápido e pegar o melhor global para inspecionar.
        top = await self._pop_global_top()
        if top:
            # Reposiciona top para não consumi-lo aqui
            await self.filas[top.formato].requeue(top)
            if top.prioridade > c.prioridade * fator:
                raise Preemptado()

    def _pareceres_da_unidade(self, unidade: UnidadeChecagem, c: Conteudo) -> List[Dict[str, Any]]:
        # Seleciona 5+ perfis com preferência pela especialidade igual ao formato
        preferidos = [p for p in unidade.perfis if p.especialidade == c.formato]
        outros = [p for p in unidade.perfis if p.especialidade != c.formato]
        random.shuffle(preferidos)
        random.shuffle(outros)
        escolhidos = (preferidos + outros)[: max(5, min(len(unidade.perfis), 7))]
        pareceres = []
        for p in escolhidos:
            # Gera um parecer sintético: quanto maior a prioridade (GUT), mais cautelosos (prob próxima de 0.5)
            base = 0.5 + random.uniform(-0.15, 0.15)
            ajuste = (c.prioridade - 27) * 0.01  # centra em GUT=3*3*3=27
            prob = min(max(base - abs(ajuste), 0.05), 0.95)
            pareceres.append({
                "checador_id": p.id,
                "especialidade": p.especialidade,
                "reputacao": round(p.reputacao, 3),
                "prob_verdade": round(prob, 4),
                "justificativa": f"Análise heurística considerando sinais e contexto do formato {c.formato}.",
            })
        return pareceres

    def _montar_relatorio(self, c: Conteudo, unidade: UnidadeChecagem, pareceres: List[Dict[str, Any]], consenso: Dict[str, Any]) -> Dict[str, Any]:
        score = consenso["score_verdade"]
        rotulo = self._rotular(score)
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

    def _rotular(self, score: float) -> str:
        if score >= 0.8:
            return "VERDADEIRO"
        if score >= 0.6:
            return "MAIORIA_VERDADEIRO"
        if score > 0.4:
            return "INDETERMINADO/CONTEXTO"
        if score > 0.2:
            return "MAIORIA_FALSO"
        return "FALSO"

    def _salvar_relatorio(self, relatorio: Dict[str, Any], conteudo_id: str) -> None:
        os.makedirs("reports", exist_ok=True)
        path = os.path.join("reports", f"relatorio_{conteudo_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(relatorio, f, ensure_ascii=False, indent=2)

class Preemptado(Exception):
    pass

# -----------------------------
# Utilidades de geração de dados
# -----------------------------

def gerar_id(prefixo: str = "C") -> str:
    return f"{prefixo}-{uuid.uuid4().hex[:8]}"

def calcular_prioridade_gut(G: int, U: int, T: int) -> float:
    # Produto G*U*T; também retornamos uma versão suavizada (log) se desejado.
    return float(G * U * T)

def criar_conteudo_sintetico(formato: Formato) -> Conteudo:
    G = random.randint(1, 5)
    U = random.randint(1, 5)
    T = random.randint(1, 5)
    p = calcular_prioridade_gut(G, U, T)
    payload = {
        "titulo": f"{formato.upper()} | Caso {uuid.uuid4().hex[:6]}",
        "fonte": random.choice(["rede_social", "portal", "mensageria", "blog"]),
        "hash": uuid.uuid4().hex,
        "metadados": {"tamanho": random.randint(10, 1000), "lingua": random.choice(["pt", "en", "es"])},
    }
    return Conteudo(id=gerar_id(), formato=formato, G=G, U=U, T=T, prioridade=p, payload=payload)

def criar_unidade(nome: str, seed: Optional[int] = None) -> UnidadeChecagem:
    if seed is not None:
        rnd = random.Random(seed)
    else:
        rnd = random
    especialidades = list(Formato)
    perfis = []
    for i in range(7):
        esp = rnd.choice(especialidades)
        reput = max(0.2, min(0.98, rnd.random() * 0.9 + 0.1))
        perfis.append(PerfilChecador(id=f"P-{nome[:3].upper()}-{i+1}", especialidade=esp, reputacao=reput))
    return UnidadeChecagem(id=gerar_id("U"), nome=nome, perfis=perfis, capacidade_concorrente=2)

# -----------------------------
# Simulação/CLI
# -----------------------------
import argparse

async def simulacao(demo: int = 12, seed: Optional[int] = None, tick_ms: int = 300) -> None:
    if seed is not None:
        random.seed(seed)
    unidades = [
        criar_unidade("Grupo Aruana", seed=1),
        criar_unidade("Grupo Anhanguera", seed=2),
        criar_unidade("Grupo MeiaPonte", seed=3),
    ]
    sched = Scheduler(unidades)
    loop_task = asyncio.create_task(sched.loop_despacho(tick_ms=tick_ms))

    formatos = list(Formato)
    # Gera chegadas escalonadas
    for i in range(demo):
        c = criar_conteudo_sintetico(random.choice(formatos))
        await sched.submit(c)
        await asyncio.sleep(random.uniform(0.05, 0.4))
        # injeta alguns de prioridade alta para acionar preempção
        if i in {3, 7}:
            c2 = Conteudo(
                id=gerar_id(),
                formato=random.choice(formatos),
                G=5,
                U=5,
                T=5,
                prioridade=calcular_prioridade_gut(5, 5, 5),
                payload={"titulo": "ALTA PRIORIDADE - Caso crítico", "fonte": "portal", "hash": uuid.uuid4().hex},
            )
            await sched.submit(c2)
    # aguarda terminar a fila
    while any(len(f) > 0 for f in sched.filas.values()) or len(sched.running) > 0:
        await asyncio.sleep(0.25)
    sched.parar()
    await loop_task

    print("Simulação concluída. Relatórios em ./reports/ .")


def main():
    parser = argparse.ArgumentParser(description="Protótipo Scheduler GUT Preemptivo")
    parser.add_argument("--demo", type=int, default=12, help="Quantidade de conteúdos a simular")
    parser.add_argument("--seed", type=int, default=None, help="Seed aleatória para reprodutibilidade")
    parser.add_argument("--tick-ms", type=int, default=300, help="Intervalo de despacho em ms")
    args = parser.parse_args()
    asyncio.run(simulacao(demo=args.demo, seed=args.seed, tick_ms=args.tick_ms))

if __name__ == "__main__":
    main()
