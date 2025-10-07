# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import io
import re
import json
import time
import uuid
import math
import heapq
import hashlib
import random
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# Integração com APIs externas
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

# Carregar configurações
def load_runtime_settings() -> Dict[str, Any]:
    """Carrega configurações do arquivo runtime_settings.json"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "runtime_settings.json")
        print(f"[DEBUG] Tentando carregar config de: {config_path}")
        print(f"[DEBUG] Arquivo existe: {os.path.exists(config_path)}")
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"[DEBUG] Config carregada: {config}")
                return config
    except Exception as e:
        print(f"[DEBUG] Erro ao carregar config: {e}")
        pass
    print("[DEBUG] Usando config padrão (offline)")
    return {
        "openai_api_key": None,
        "tavily_api_key": None,
        "use_openai": False,
        "use_tavily": False,
        "offline_mode": True
    }

RUNTIME_SETTINGS = load_runtime_settings()


# ------------------------------
# Config e diretórios
# ------------------------------

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

# estados possíveis
STATE_NEW = "new"
STATE_QUEUED = "queued"
STATE_ACTIVE = "active"
STATE_PREEMPTED = "preempted"
STATE_DONE = "done"

FORMATS = {"text", "image", "audio", "video"}

# capacidade default de "unidades" simultâneas (slots ativos)
DEFAULT_CAPACITY = 2
DEFAULT_PREEMPTION_FACTOR = 1.5  # novo >= fator * menor_ativo  -> preempção

# ------------------------------
# Heurísticas simples de categorização por assunto (não o formato!)
# Opcional — usado apenas para log/relatório.
# ------------------------------

CATEGORY_SETS = {
    "Política": {
        "congresso", "governo", "presidente", "senado", "camara", "deputado",
        "lei", "decreto", "prefeito", "vereador", "eleição", "partido"
    },
    "Saúde": {
        "saúde", "hosp", "hospital", "médic", "posto", "vacina", "vírus",
        "covid", "gripe", "sus", "doença", "tratamento"
    },
    "Economia": {
        "fgts", "imposto", "inflação", "dólar", "real", "pib",
        "salário", "emprego", "renda", "auxílio", "caixa", "banco"
    },
    "Esportes": {
        "jogo", "gol", "time", "campeonato", "torcida", "técnico",
        "clube", "partida", "futebol", "basquete", "vôlei"
    },
    "Mundo": {
        "onu", "nato", "guerra", "fronteira", "embaixada", "sanção",
        "internacional", "acordo", "diplomacia"
    },
}


def guess_category_from_text(text: str) -> str:
    t = text.lower()
    scores = {k: 0 for k in CATEGORY_SETS.keys()}
    for cat, keys in CATEGORY_SETS.items():
        for kw in keys:
            if kw in t:
                scores[cat] += 1
    # desempate simples
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else "Geral"


# ------------------------------
# Cálculo GUT e prioridade
# ------------------------------

def normalize_gut(gut: Optional[Tuple[int, int, int]]) -> Tuple[int, int, int]:
    """
    G, U, T entre 1..5. Se None, usa heurística branda (3/3/3),
    e aumenta para 4/4/3 se texto contém gatilhos de urgência/gravidade.
    """
    if gut is not None:
        g, u, t = gut
        g = max(1, min(5, int(g)))
        u = max(1, min(5, int(u)))
        t = max(1, min(5, int(t)))
        return g, u, t

    # heurística simples baseada em gatilhos de linguagem
    return (3, 3, 3)


def gut_from_text_heuristic(text: str) -> Tuple[int, int, int]:
    t = text.lower()

    g = 3
    u = 3
    tr = 3

    if any(x in t for x in ["morte", "fraude", "golpe", "crime", "emergência"]):
        g = min(5, g + 1)
    if any(x in t for x in ["urgente", "agora", "imediato", "alerta"]):
        u = min(5, u + 1)
    if any(x in t for x in ["viral", "compartilhe", "espalhando", "tendência"]):
        tr = min(5, tr + 1)

    return g, u, tr


def compute_priority(gut: Tuple[int, int, int]) -> int:
    """
    Converte GUT em prioridade inteira. Peso: G 5x, U 3x, T 2x.
    Faixa típica: 10..50.
    """
    g, u, t = gut
    score = g * 5 + u * 3 + t * 2
    return int(score)


# ------------------------------
# Estruturas básicas
# ------------------------------

@dataclass(order=True)
class PrioritizedItem:
    # heapq é min-heap; usamos -priority para simular max-heap
    sort_index: int
    priority: int = field(compare=False)
    content_id: str = field(compare=False)


@dataclass
class ContentItem:
    content_id: str
    fmt: str  # text|image|audio|video
    source: str
    content: str  # texto ou caminho do arquivo
    category: str
    gut: Tuple[int, int, int]
    priority: int
    state: str = STATE_NEW
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    preemptions: int = 0


# ------------------------------
# Estado global em memória
# ------------------------------

class SchedulerState:
    def __init__(self):
        self.queues: Dict[str, List[PrioritizedItem]] = {f: [] for f in FORMATS}
        self.items: Dict[str, ContentItem] = {}  # id -> item
        self.active: Dict[str, ContentItem] = {}  # id -> item
        self.capacity: int = DEFAULT_CAPACITY
        self.preemption_factor: float = DEFAULT_PREEMPTION_FACTOR

    # -------- filas ----------
    def push_queue(self, item: ContentItem):
        heapq.heappush(
            self.queues[item.fmt],
            PrioritizedItem(sort_index=-item.priority, priority=item.priority, content_id=item.content_id),
        )

    def pop_best_across_queues(self) -> Optional[ContentItem]:
        """Seleciona o topo de todas as filas por maior prioridade."""
        best_fmt = None
        best_pri = None
        for fmt, q in self.queues.items():
            if q:
                pri = q[0].priority  # maior porque sort_index é negativo
                if best_pri is None or pri > best_pri:
                    best_pri = pri
                    best_fmt = fmt
        if best_fmt is None:
            return None
        top = heapq.heappop(self.queues[best_fmt])
        return self.items[top.content_id]

    def peek_min_active_priority(self) -> Optional[int]:
        if not self.active:
            return None
        return min(x.priority for x in self.active.values())


SCHED = SchedulerState()


# ------------------------------
# Simulação de checagem (5 agentes) + consenso
# ------------------------------

AGENT_TIERS = ["bronze", "prata", "ouro"]
AGENT_TIER_WEIGHT = {"bronze": 0.8, "prata": 1.0, "ouro": 1.2}


def _rng_from_id(cid: str) -> random.Random:
    seed = int(hashlib.sha256(cid.encode("utf-8")).hexdigest()[:16], 16)
    return random.Random(seed)


def simulate_checkers_and_consensus(item: ContentItem) -> Dict[str, Any]:
    """
    Verificação de conteúdo usando APIs reais (OpenAI + Tavily) quando disponíveis,
    ou simulação como fallback.
    """
    # Recarregar configurações para pegar mudanças da UI
    settings = load_runtime_settings()
    
    # Debug: imprimir configurações carregadas
    print(f"[DEBUG] Configurações carregadas:")
    print(f"  offline_mode: {settings.get('offline_mode', False)}")
    print(f"  use_openai: {settings.get('use_openai', True)}")
    print(f"  openai_api_key: {'***' + settings.get('openai_api_key', '')[-4:] if settings.get('openai_api_key') else 'None'}")
    
    # Debug: verificar condições
    offline_mode = settings.get("offline_mode", False)
    use_openai = settings.get("use_openai", True)
    openai_key = settings.get("openai_api_key")
    
    print(f"[DEBUG] Condições:")
    print(f"  not offline_mode: {not offline_mode}")
    print(f"  use_openai: {use_openai}")
    print(f"  has openai_key: {bool(openai_key)}")
    print(f"  condition result: {not offline_mode and use_openai and bool(openai_key)}")
    
    # Se não estiver em modo offline e tiver as chaves, usar APIs reais
    if not offline_mode and use_openai and openai_key:
        try:
            return _real_verification(item, settings)
        except Exception as e:
            print(f"Erro na verificação real, usando simulação: {e}")
    
    # Fallback para simulação
    return _simulate_checking(item)


def _real_verification(item: ContentItem, settings: Dict[str, Any]) -> Dict[str, Any]:
    """Verificação usando APIs reais"""
    print(f"[REAL] Verificando conteudo com OpenAI/Tavily: {item.content_id}")
    
    results = {
        "openai_analysis": None,
        "tavily_evidence": None,
        "checkers": [],
        "evidence": [],
        "method": "real_apis"
    }
    
    # Verificar se é arquivo de mídia (não texto)
    is_media_file = item.fmt in ["image", "audio", "video"]
    
    # 1. Para arquivos de mídia: primeiro extrair contexto, depois buscar no Tavily
    extracted_context = None
    if is_media_file and OPENAI_AVAILABLE and settings.get("openai_api_key"):
        try:
            print(f"[CONTEXTO] Extraindo contexto do arquivo de mídia: {item.fmt}")
            from openai import OpenAI
            openai_client = OpenAI(api_key=settings["openai_api_key"])
            
            # Extrair contexto do arquivo de mídia
            import os
            file_path = item.content
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else "Desconhecido"
            file_name = os.path.basename(file_path)
            
            context_prompt = f"""
Você é um especialista em análise de mídia. Com base nas informações do arquivo abaixo, 
extraia o CONTEXTO e CONTEÚDO principal para busca na web.

ARQUIVO: {item.fmt.upper()}
Nome: {file_name}
Caminho: {file_path}
Tamanho: {file_size} bytes

Extraia:
1. Assunto principal (ex: "política", "saúde", "economia")
2. Eventos/pessoas mencionadas
3. Palavras-chave para busca web
4. Contexto temporal (se mencionado)

Responda apenas com as palavras-chave e contexto extraído, separadas por vírgula.
"""
            
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Você extrai contexto de arquivos de mídia para busca web."},
                    {"role": "user", "content": context_prompt}
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            extracted_context = response.choices[0].message.content.strip()
            print(f"[CONTEXTO] Contexto extraído: {extracted_context[:100]}...")
            
        except Exception as e:
            print(f"[CONTEXTO] Erro ao extrair contexto: {e}")
    
    # 2. Buscar evidências com Tavily (para texto OU mídia com contexto)
    if TAVILY_AVAILABLE and settings.get("use_tavily", True) and settings.get("tavily_api_key"):
        try:
            if not is_media_file:
                # Para texto: usar conteúdo direto
                query = _extract_search_terms(item.content)
                print(f"[TAVILY] Buscando evidencias para texto: {item.content_id}")
            elif extracted_context:
                # Para mídia: usar contexto extraído
                query = _extract_search_terms(extracted_context)
                print(f"[TAVILY] Buscando evidencias para mídia com contexto: {item.content_id}")
            else:
                # Para mídia sem contexto: usar nome do arquivo
                import os
                file_name = os.path.basename(item.content)
                query = _extract_search_terms(file_name)
                print(f"[TAVILY] Buscando evidencias para mídia (nome do arquivo): {item.content_id}")
            
            tavily = TavilyClient(api_key=settings["tavily_api_key"])
            search_results = tavily.search(query, max_results=5)
            results["tavily_evidence"] = search_results.get("results", [])
            results["evidence"] = results["tavily_evidence"]
            results["search_query"] = query
            results["extracted_context"] = extracted_context if is_media_file else None
            print(f"[TAVILY] Encontradas {len(results['evidence'])} evidencias")
        except Exception as e:
            print(f"[TAVILY] Erro na busca: {e}")
            results["tavily_evidence"] = {"error": str(e)}
    else:
        print(f"[TAVILY] Tavily não disponível ou desabilitado")
        results["tavily_evidence"] = {"message": "Tavily não disponível"}
    
    # 2. Configurar OpenAI
    openai_client = None
    if OPENAI_AVAILABLE and settings.get("openai_api_key"):
        try:
            from openai import OpenAI
            openai_client = OpenAI(api_key=settings["openai_api_key"])
            print(f"[OPENAI] Analisando conteudo: {item.content_id}")
        except Exception as e:
            print(f"[OPENAI] Erro na configuracao: {e}")
    
    # 3. Análise com OpenAI - 5 checkers diferentes
    if openai_client and settings.get("openai_api_key"):
        try:
            # Prompts diferentes para mídia vs texto
            if is_media_file:
                checker_prompts = [
                    ("Especialista em Mídia", "Você é um especialista em análise de mídia. Analise a credibilidade e autenticidade deste arquivo"),
                    ("Detector de Deepfake", "Você é um especialista em detecção de manipulação de mídia. Verifique se há sinais de adulteração"),
                    ("Analista Forense", "Você é um analista forense digital. Avalie a integridade e origem deste arquivo"),
                    ("Verificador de Conteúdo", "Você é um verificador de conteúdo. Determine se este arquivo é autêntico"),
                    ("Especialista em Metadados", "Você é um especialista em metadados. Analise as informações técnicas do arquivo")
                ]
            else:
                checker_prompts = [
                    ("Jornalista", "Você é um jornalista experiente. Analise se esta informação é verdadeira"),
                    ("Fact-Checker", "Você é um especialista em fact-checking. Verifique a veracidade"),
                    ("Pesquisador", "Você é um pesquisador acadêmico. Avalie a credibilidade"),
                    ("Analista", "Você é um analista de mídia. Determine se é desinformação"),
                    ("Verificador", "Você é um verificador independente. Classifique a informação")
                ]
            
            openai_results = []
            
            for i, (role, prompt) in enumerate(checker_prompts):
                try:
                    # Conteúdo diferente para mídia vs texto
                    if is_media_file:
                        # Para arquivos de mídia, analisar metadados + contexto + evidências
                        import os
                        file_path = item.content
                        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else "Desconhecido"
                        file_name = os.path.basename(file_path)
                        
                        content_for_analysis = f"""
ARQUIVO DE MÍDIA: {item.fmt.upper()}
Nome do arquivo: {file_name}
Caminho: {file_path}
Tamanho: {file_size} bytes
Formato: {item.fmt}
"""
                        
                        # Adicionar contexto extraído se disponível
                        if extracted_context:
                            content_for_analysis += f"\nCONTEXTO EXTRAÍDO: {extracted_context}"
                        
                        # Adicionar evidências do Tavily se disponível
                        evidence_text = ""
                        if results["evidence"]:
                            evidence_text = f"\n\nEvidências encontradas na web: {results['evidence'][:2]}"
                    else:
                        # Para texto: usar conteúdo direto
                        content_for_analysis = item.content
                        evidence_text = ""
                        if results["evidence"]:
                            evidence_text = f"\n\nEvidências encontradas: {results['evidence'][:2]}"
                    
                    response = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Conteúdo: {content_for_analysis}{evidence_text}\n\nResponda com: VERDADEIRO, FALSO, ENGANOSO, ou DESCONTEXTUALIZADO, seguido de uma breve explicação."}
                        ],
                        max_tokens=200,
                        temperature=0.3 + (i * 0.1)
                    )
                    
                    result_text = response.choices[0].message.content.strip()
                    verdict = "Verdadeiro"
                    confidence = 0.8
                    
                    # Extrair veredicto
                    if "FALSO" in result_text.upper():
                        verdict = "Falso"
                    elif "ENGANOSO" in result_text.upper():
                        verdict = "Enganoso"
                    elif "DESCONTEXTUALIZADO" in result_text.upper():
                        verdict = "Descontextualizado"
                    
                    checker_result = {
                        "id": f"openai-{role.lower()}",
                        "role": role,
                        "tier": ["bronze", "prata", "ouro"][i % 3],
                        "reputation": [0.8, 1.0, 1.2][i % 3],
                        "verdict": verdict,
                        "confidence": confidence,
                        "reasoning": result_text[:150] + "..." if len(result_text) > 150 else result_text,
                        "source": "openai"
                    }
                    
                    results["checkers"].append(checker_result)
                    openai_results.append(checker_result)
                    print(f"[OPENAI] {role}: {verdict}")
                    
                except Exception as e:
                    print(f"[OPENAI] Erro no checker {role}: {e}")
                    error_checker = {
                        "id": f"openai-{role.lower()}-error",
                        "role": role,
                        "tier": "bronze",
                        "reputation": 0.5,
                        "verdict": "Erro",
                        "confidence": 0.0,
                        "reasoning": f"Erro na análise: {str(e)}",
                        "source": "openai",
                        "error": str(e)
                    }
                    results["checkers"].append(error_checker)
            
            results["openai_analysis"] = {
                "checkers_count": len(openai_results),
                "successful_checks": len([c for c in openai_results if "error" not in c]),
                "results": openai_results
            }
            
        except Exception as e:
            print(f"[OPENAI] Erro geral na análise: {e}")
            results["openai_analysis"] = {"error": str(e)}
    
    # 4. Calcular consenso
    if results["checkers"]:
        consensus = _calculate_real_consensus(results["checkers"], results["evidence"])
        consensus["analysis_breakdown"] = {
            "openai": results["openai_analysis"],
            "tavily": results["tavily_evidence"],
            "method": "real_apis",
            "total_checkers": len(results["checkers"]),
            "extracted_context": extracted_context if is_media_file else None,
            "search_query": results.get("search_query", "")
        }
        return consensus
    else:
        # Se não conseguiu usar APIs, usar simulação mas marcar como fallback
        print("[FALLBACK] Usando simulacao - APIs nao disponíveis")
        fallback = _simulate_checking(item)
        fallback["method"] = "simulation_fallback"
        fallback["reason"] = "APIs não disponíveis ou com erro"
        return fallback


def _extract_search_terms(content: str) -> str:
    """Extrai termos de busca do conteúdo"""
    # Remover palavras comuns e extrair palavras-chave
    stop_words = {"o", "a", "os", "as", "de", "da", "do", "das", "dos", "em", "na", "no", "para", "por", "com", "que", "e", "é", "foi", "ser", "são"}
    words = re.findall(r'\w+', content.lower())
    keywords = [w for w in words if len(w) > 3 and w not in stop_words]
    return " ".join(keywords[:5])  # Primeiras 5 palavras-chave


def _calculate_real_consensus(checkers: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula consenso dos checkers reais"""
    if not checkers:
        return {"veracity_score": 0.5, "final_label": "Descontextualizado"}
    
    # Contagem de veredictos ponderada por reputação
    verdict_weights = {}
    total_weight = 0
    
    for checker in checkers:
        verdict = checker["verdict"]
        weight = checker["reputation"] * checker["confidence"]
        verdict_weights[verdict] = verdict_weights.get(verdict, 0) + weight
        total_weight += weight
    
    # Veredicto mais forte
    if verdict_weights:
        final_verdict = max(verdict_weights.keys(), key=lambda k: verdict_weights[k])
        confidence_score = verdict_weights[final_verdict] / total_weight if total_weight > 0 else 0.5
    else:
        final_verdict = "Descontextualizado"
        confidence_score = 0.5
    
    # Converter para score de veracidade (1 = verdadeiro, 0 = falso)
    if final_verdict == "Verdadeiro":
        veracity_score = confidence_score
    else:
        veracity_score = 1.0 - confidence_score
    
    return {
        "checkers": checkers,
        "evidence": evidence,
        "veracity_score": round(veracity_score, 3),
        "final_label": final_verdict
    }


def _simulate_checking(item: ContentItem) -> Dict[str, Any]:
    """Simulação de verificação (fallback)"""
    print(f"[SIMULATION] Verificacao offline para: {item.content_id}")
    rng = _rng_from_id(item.content_id)

    # compor 5 perfis
    n_spec = rng.choice([2, 3])
    n_gen = 5 - n_spec

    def mk_agent(i: int, specialist: bool) -> Dict[str, Any]:
        tier = rng.choices(AGENT_TIERS, weights=[0.5, 0.35, 0.15], k=1)[0]
        repu = AGENT_TIER_WEIGHT[tier]
        # confiança base 0.6..0.95 com leve viés pela prioridade
        conf = min(0.95, 0.6 + (item.priority / 100.0) * 0.25 + rng.random() * 0.2)
        # voto: 1 = verdadeiro, 0 = falso (heurística aleatória controlada)
        # quanto maior a prioridade, maior chance de "falso" (conteúdo crítico tende a ser rumor)
        p_true = 0.55 - (item.priority / 100.0) * 0.2
        vote_true = 1 if rng.random() < p_true else 0
        label = "Verdadeiro" if vote_true == 1 else rng.choices(
            ["Falso", "Descontextualizado", "Enganoso", "Sátira"],
            weights=[0.55, 0.25, 0.15, 0.05],
            k=1
        )[0]
        return {
            "id": f"offline-agente-{i+1}",
            "tier": tier,
            "especialista": specialist,
            "reputacao": round(repu, 3),
            "confianca": round(conf, 3),
            "parecer_label": label,
            "parecer_true": vote_true,
            "source": "offline_simulation"
        }

    agents = [mk_agent(i, True) for i in range(n_spec)] + \
             [mk_agent(n_spec + j, False) for j in range(n_gen)]

    # consenso: média ponderada (reputação * confiança)
    num, den = 0.0, 0.0
    label_hist = {}
    for a in agents:
        w = a["reputacao"] * a["confianca"]
        num += w * a["parecer_true"]
        den += w
        label_hist[a["parecer_label"]] = label_hist.get(a["parecer_label"], 0) + w

    score_true = num / den if den > 0 else 0.5  # 0..1 prob de "verdadeiro"

    # rótulo final: se score_true for baixo, "Falso"; se alto "Verdadeiro";
    # faixa central: escolhe o mais votado entre rótulos "negativos" simulados
    if score_true >= 0.75:
        final_label = "Verdadeiro"
    elif score_true <= 0.35:
        final_label = "Falso"
    else:
        # escolhe o mais pesado dentre os demais rótulos
        # se não houver, use "Descontextualizado"
        if label_hist:
            # remove 'Verdadeiro' da disputa se existir
            label_hist2 = {k: v for k, v in label_hist.items() if k != "Verdadeiro"}
            if label_hist2:
                final_label = max(label_hist2, key=label_hist2.get)
            else:
                final_label = "Descontextualizado"
        else:
            final_label = "Descontextualizado"

    return {
        "checkers": agents,
        "veracity_score": round(score_true, 3),
        "final_label": final_label,
        "method": "offline_simulation",
        "analysis_breakdown": {
            "openai": {"status": "offline", "message": "Modo offline ativo"},
            "tavily": {"status": "offline", "message": "Modo offline ativo"},
            "method": "offline_simulation",
            "total_checkers": len(agents)
        }
    }


# ------------------------------
# Relatórios
# ------------------------------

def save_report(item: ContentItem, consensus: Dict[str, Any]) -> str:
    rep = {
        "content_id": item.content_id,
        "format": item.fmt,
        "source": item.source,
        "category": item.category,
        "gut": {"G": item.gut[0], "U": item.gut[1], "T": item.gut[2]},
        "priority": item.priority,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "preemptions": item.preemptions,
        "consensus": consensus,
    }
    path = os.path.join(REPORTS_DIR, f"{item.content_id}.json")
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    return path


def get_report(content_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(REPORTS_DIR, f"{content_id}.json")
    if not os.path.isfile(path):
        return None
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_report_ids() -> List[str]:
    if not os.path.isdir(REPORTS_DIR):
        return []
    ids = []
    for fn in os.listdir(REPORTS_DIR):
        if fn.endswith(".json"):
            ids.append(fn[:-5])
    # mais recentes primeiro pela data de modificação
    ids.sort(key=lambda cid: os.path.getmtime(os.path.join(REPORTS_DIR, f"{cid}.json")), reverse=True)
    return ids


# ------------------------------
# API pública para UI/FASTAPI
# ------------------------------

def enqueue_content(content_type: str,
                    content: str,
                    source: str = "ui",
                    category: Optional[str] = None,
                    gut: Optional[Tuple[int, int, int]] = None) -> str:
    """
    Enfileira um item.
    - content_type: "text" | "image" | "audio" | "video"
    - content: texto ou caminho do arquivo
    - category: categoria temática opcional (Política, Saúde, …). Se None e for texto, tenta deduzir.
    - gut: (G,U,T) opcional. Se None, tenta heurística leve (e reforço para texto).
    """
    fmt = content_type.lower().strip()
    if fmt not in FORMATS:
        fmt = "text"

    if gut is None:
        gut = gut_from_text_heuristic(content) if fmt == "text" else normalize_gut(None)
    else:
        gut = normalize_gut(gut)

    if category is None and fmt == "text":
        category = guess_category_from_text(content)
    elif category is None:
        category = "Geral"

    priority = compute_priority(gut)

    cid = str(uuid.uuid4())
    item = ContentItem(
        content_id=cid,
        fmt=fmt,
        source=source,
        content=content,
        category=category,
        gut=gut,
        priority=priority,
        state=STATE_QUEUED,
    )
    SCHED.items[cid] = item
    SCHED.push_queue(item)

    # Preempção no enfileiramento, se necessário
    min_active = SCHED.peek_min_active_priority()
    if min_active is not None and len(SCHED.active) >= SCHED.capacity:
        if item.priority >= int(SCHED.preemption_factor * min_active):
            # preempta o mais fraco
            weakest_id, weakest_item = min(SCHED.active.items(), key=lambda kv: kv[1].priority)
            # move de volta para fila
            weakest_item.state = STATE_PREEMPTED
            weakest_item.preemptions += 1
            weakest_item.updated_at = time.time()
            SCHED.active.pop(weakest_id, None)
            SCHED.push_queue(weakest_item)

    print(f"+ Enfileirado {cid} cat={category} priority={priority}")
    return cid


def _assign_slot_and_process(item: ContentItem) -> Dict[str, Any]:
    """
    Aloca o item como ativo e executa a "checagem" (simulada) imediatamente.
    Retorna o dicionário de saída do relatório (resumido).
    """
    item.state = STATE_ACTIVE
    item.updated_at = time.time()
    SCHED.active[item.content_id] = item

    # simula processamento (sincrono para MVP)
    consensus = simulate_checkers_and_consensus(item)

    item.state = STATE_DONE
    item.updated_at = time.time()
    SCHED.active.pop(item.content_id, None)

    report_path = save_report(item, consensus)

    out = {
        "content_id": item.content_id,
        "priority": item.priority,
        "label": consensus["final_label"],
        "score": consensus["veracity_score"],
        "report_path": report_path,
    }
    return out


def process_round(capacity: int = DEFAULT_CAPACITY,
                  preemption: float = DEFAULT_PREEMPTION_FACTOR,
                  max_items: int = 3) -> Dict[str, Any]:
    """
    Processa uma rodada:
      - atualiza capacidade e limiar
      - até 'max_items' itens, enquanto houver slots livres
      - pega o maior entre as filas por formato
    """
    SCHED.capacity = int(max(1, capacity))
    SCHED.preemption_factor = float(preemption)

    processed: List[Dict[str, Any]] = []

    while len(processed) < int(max_items):
        # respeita limite de slots ativos
        if len(SCHED.active) >= SCHED.capacity:
            break

        item = SCHED.pop_best_across_queues()
        if item is None:
            break

        # processa
        out = _assign_slot_and_process(item)
        processed.append(out)
        print(f"[OK] Relatorio: {out['report_path']}  label={out['label']} score={out['score']}")

    status = get_status()
    status["processed_this_round"] = processed
    return status


def get_status() -> Dict[str, Any]:
    qs = {fmt: len(q) for fmt, q in SCHED.queues.items()}
    return {
        "active": [
            {"content_id": it.content_id, "priority": it.priority, "fmt": it.fmt, "category": it.category}
            for it in SCHED.active.values()
        ],
        "queues": qs,
        "capacity": SCHED.capacity,
        "preemption_factor": SCHED.preemption_factor,
        "reports_total": len(list_report_ids()),
    }


# ------------------------------
# CLI para testes manuais
# ------------------------------

def _demo_seed_items():
    samples = [
        ("text", "URGENTE: vídeo viral mostra suposta fraude no congresso! Compartilhe agora."),
        ("text", "Reviravolta no FGTS: saque liberado para todos os trabalhadores!"),
        ("text", "Clube vence por 3x0 e torcida lota o estádio no clássico de domingo."),
        ("text", "Novo surto de gripe atinge cidades do interior; veja como se proteger."),
        ("text", "Moeda dispara com incertezas no cenário internacional, dizem analistas."),
    ]
    for fmt, txt in samples:
        enqueue_content(fmt, txt, source="demo")


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Roda uma demo com itens simulados")
    parser.add_argument("--submit", action="store_true", help="Envia um único item")
    parser.add_argument("--type", dest="type_", default="text", help="text|image|audio|video")
    parser.add_argument("--source", default="cli")
    parser.add_argument("--content", default="", help="Texto ou caminho do arquivo")
    parser.add_argument("--process", action="store_true", help="Processa imediatamente uma rodada")
    parser.add_argument("--capacity", type=int, default=DEFAULT_CAPACITY, help="Capacidade de unidades ativas")
    parser.add_argument("--preemption", type=float, default=DEFAULT_PREEMPTION_FACTOR,
                        help="Limiar de preempção (novo >= limiar * menor_ativo)")
    parser.add_argument("--max_items", type=int, default=3, help="Máximo por rodada")

    args = parser.parse_args()

    if args.demo:
        _demo_seed_items()

    if args.submit:
        if not args.content:
            print("ERRO: --content vazio")
            return
        cid = enqueue_content(args.type_, args.content, source=args.source)
        print(f"enviado: {cid}")

    if args.process:
        process_round(capacity=args.capacity, preemption=args.preemption, max_items=args.max_items)


if __name__ == "__main__":
    main()
