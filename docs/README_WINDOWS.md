# Sistema Multiagente para Checagem de Fatos — Guia Windows

Sistema inteligente de verificação de fatos com interface web intuitiva. Analisa textos, imagens e outros conteúdos usando múltiplos agentes especializados.

## 🚀 Início Rápido (3 passos)

1. **Instalar dependências:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Iniciar o sistema:**
   ```powershell
   uvicorn serve_combined_app:app --reload --port 8000
   ```

3. **Abrir no navegador:**
   - **Interface principal:** http://127.0.0.1:8000/ui
   - **API (documentação):** http://127.0.0.1:8000/docs

---

## 📋 Pré-requisitos

- **Windows 10/11**
- **Python 3.9+** (recomendado 3.11 ou 3.12)
- **PowerShell** (já vem com Windows)

### Verificar Python
```powershell
python --version
```
Se não aparecer a versão, instale pelo [python.org](https://python.org) marcando **"Add Python to PATH"** e reinicie o PowerShell.

---

## 🛠️ Instalação Completa

### 1) Preparar ambiente
```powershell
# Ir para a pasta do projeto
cd C:\Users\SEU_USUARIO\Documents\GitHub\multiagent_fake_news

# Criar ambiente virtual (recomendado)
python -m venv .venv
.venv\Scripts\Activate.ps1

# Se der erro de política, execute uma vez:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 2) Instalar dependências
```powershell
# Atualizar pip
python -m pip install --upgrade pip

# Instalar tudo que precisa
pip install -r requirements.txt
```

---

## 🖥️ Como Usar o Sistema

### Interface Web (Recomendado)
```powershell
# Iniciar servidor
uvicorn serve_combined_app:app --reload --port 8000
```

**Abra no navegador:** http://127.0.0.1:8000/ui

#### Funcionalidades da Interface:
1. **Configuração:** Adicionar chaves API (OpenAI/Tavily) e modo offline
2. **Enviar Conteúdo:** Texto, arquivos (imagem, áudio, vídeo)
3. **Processar:** Analisar conteúdo com agentes especializados
4. **Relatórios:** Ver resultados detalhados da verificação
5. **Busca Web:** Testar integração com Tavily/DuckDuckGo

### API REST (Para desenvolvedores)
**Documentação:** http://127.0.0.1:8000/docs

#### Exemplos de uso via PowerShell:
```powershell
# Enviar texto para análise
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/submit" -Form @{
  type="text"; source="api"; text="URGENTE: rumor viral sobre política..."
}

# Processar itens na fila
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/process?max_items=3"

# Ver status do sistema
Invoke-RestMethod -Uri "http://127.0.0.1:8000/status"

# Baixar relatório
$ID="seu-id-aqui"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/report/$ID" | Out-File -FilePath ".\report_$ID.json" -Encoding utf8
```

### Modo CLI (Para testes)
```powershell
# Demo automática
python .\multiagent_gut_scheduler.py --demo

# Enviar texto e processar
python .\multiagent_gut_scheduler.py --submit --type text --source "cli" --content "Texto para verificar" --process
```

---

## 📊 Importação em Lote (Google Sheets/CSV)

Para processar múltiplos conteúdos de uma vez:

```powershell
# Carregar da planilha Google
python .\load_gsheet_to_scheduler.py --csv "https://docs.google.com/spreadsheets/d/SEU_ID/export?format=csv&gid=2114918615" --limit 20 --process

# Carregar arquivo CSV local
python .\load_gsheet_to_scheduler.py --csv ".\meu_arquivo.csv" --limit 50 --process
```

**Como preparar a planilha:**
1. Google Sheets: **Arquivo → Compartilhar → Publicar na web**
2. Copie o link e adicione `&export?format=csv&gid=0`
3. O script detecta automaticamente colunas como `text`, `Texto_Original` ou `conteudo`

---

## 📁 Onde Encontrar os Resultados

- **Relatórios JSON:** `.\reports\<content_id>.json`
- **Arquivos enviados:** `.\ingested\`
- **Status em tempo real:** Interface web ou API `/status`

---

## 📁 Estrutura de Arquivos e Funcionamento

### Visão Geral do Sistema

O sistema funciona em **4 camadas principais**:

1. **UI (Gradio)**: Interface web em http://127.0.0.1:8000/ui
2. **API (FastAPI)**: Endpoints REST (/submit, /process, /status, /report/{id})
3. **Agendador (Scheduler)**: Orquestra filas, prioridades e agentes
4. **Agentes**: Módulos especializados para cada etapa da verificação

### Fluxo Completo

```
UI → settings_store → runtime_settings.json (chaves/flags)
UI → scheduler_adapter.enqueue_content() → multiagent_gut_scheduler (fila + prioridade GUT)
UI → scheduler_adapter.process_round() → Unidade de Checagem (5 agentes)
     → cada agente avalia (LLM + evidências) → consenso → score + rótulo
     → reporter_agent → reports/{content_id}.json
UI → lê status/relatórios via scheduler_adapter
```

### 📂 O Que Cada Arquivo Faz

#### 🖥️ **Infraestrutura/UI/API**

**`serve_combined_app.py`** ⭐ **ENTRADA PRINCIPAL**
- Ponto de entrada do servidor
- Combina FastAPI (API) + Gradio (UI) na mesma porta
- Monta a UI em `/ui` e expõe endpoints REST

**`gradio_multiagent_ui.py`**
- Interface web com 3 abas: Configuração, Enviar/Processar, Busca Web
- Gerencia chaves API e modo offline
- Chama o scheduler para enfileirar, processar e mostrar relatórios

**`settings_store.py`**
- Persiste configurações em `runtime_settings.json`
- Gerencia chaves OpenAI/Tavily e flags (offline_mode, use_openai, use_tavily)

**`scheduler_adapter.py`**
- Camada de compatibilidade entre UI e scheduler
- Tenta importar funções do `multiagent_gut_scheduler.py`
- Fallback para evitar quebra da UI

**`fastapi_multiagent_gut_scheduler.py`**
- API REST pura (sem UI)
- Endpoints: `/submit`, `/process`, `/status`, `/report/{id}`
- Importado pelo `serve_combined_app.py`

**`chat_ui.py`** (Legado)
- UI antiga/simplificada para testes
- Pode ser movida para pasta `legacy/`

#### 🧠 **Núcleo do Scheduler e Agentes**

**`multiagent_gut_scheduler.py`** ⭐ **CORAÇÃO DO SISTEMA**
- Agendador principal com GUT + filas por formato + preempção
- Funções principais:
  - `enqueue_content()`: enfileira com categoria e prioridade GUT
  - `process_round()`: processa itens respeitando capacidade
  - `get_status()`, `list_report_ids()`, `get_report()`

**`ingestion_agent.py`**
- Normaliza conteúdo recebido (texto/áudio/vídeo/imagem)
- Salva arquivos em `ingested/`
- Extrai metadados (origem, tamanho, tipo)

**`categorization_agent.py`**
- Classifica em categorias: Política, Saúde, Economia, Mundo, Esportes, Geral
- Usa LLM (quando online) ou heurística (offline)

**`priority_agent.py`**
- Calcula matriz GUT: Gravidade, Urgência, Tendência (1-5 cada)
- Define prioridade combinada e bucket de fila

**`checker_selection_agent.py`**
- Monta Unidade de Checagem com 5 perfis:
  - 2-4 especialistas (Bronze/Prata/Ouro)
  - 2-3 independentes
- Pondera especialidade e reputação

**`checking_unit_agent.py`**
- Executa avaliação individual de cada perfil
- Usa LLM (online) ou parecer simulado (offline)

**`evidence_agent.py`**
- Coleta evidências na web (Tavily + DuckDuckGo fallback)
- Sumariza e organiza evidências

**`consensus_agent.py`**
- Combina 5 pareceres com lógica probit/ponderada
- Gera score de veracidade (0-1) e rótulo final

**`reporter_agent.py`**
- Gera relatório JSON explicável
- Salva em `reports/{content_id}.json`
- Inclui: GUT, checadores, evidências, score, rótulo

#### 🛠️ **Utilidades e Scripts**

**`llm_helper.py`**
- Wrapper para OpenAI (quando habilitado)
- Funções: extrair alegação, resumir evidências, análise textual
- Modo offline retorna saídas "stub" controladas

**`tavily_helper.py`**
- Wrapper para Tavily (busca web)
- Fallback para DuckDuckGo quando desabilitado/offline

**`load_gsheet_to_scheduler.py`**
- Script CLI para importar lotes de planilhas Google/CSV
- Útil para processamento em massa

#### 📋 **Configuração e Dados**

**`requirements.txt`**
- Lista de dependências Python

**`runtime_settings.json`**
- Gerado automaticamente pela UI
- Armazena chaves API e configurações

**`runtime_settings.exemple`**
- Template de exemplo (sem chaves reais)

**Pastas:**
- `reports/`: Relatórios JSON gerados
- `ingested/`: Arquivos enviados para análise
- `documentacao/`: Documentação e versões antigas

#### 📦 **Arquivos Legado (Podem ser Movidos)**

**`fastapi_multiagent_gut_scheduler.py`** (Standalone)
- Versão antiga do servidor só-API
- Recomendado: usar `serve_combined_app.py` (mais completo)

**`chat_ui.py`**
- UI antiga/simplificada para testes
- Recomendado: mover para `legacy/`

**`scheduler_agent.py`**
- Se não for usado pelo scheduler atual
- Recomendado: mover para `legacy/`

**`runtime_settings.exemple`**
- Recomendado: renomear para `runtime_settings.example` e mover para `config/`

### 🗂️ **Estrutura Recomendada (Organização)**

Para deixar o projeto mais intuitivo, considere organizar assim:

```
multiagent_fake_news/
├─ app/                        # UI + API + helpers
│  ├─ serve_combined_app.py
│  ├─ gradio_multiagent_ui.py
│  ├─ settings_store.py
│  ├─ scheduler_adapter.py
│  ├─ llm_helper.py
│  └─ tavily_helper.py
├─ scheduler/                  # Orquestração
│  └─ multiagent_gut_scheduler.py
├─ agents/                     # Todos os agentes
│  ├─ ingestion_agent.py
│  ├─ categorization_agent.py
│  ├─ priority_agent.py
│  ├─ checker_selection_agent.py
│  ├─ checking_unit_agent.py
│  ├─ evidence_agent.py
│  ├─ consensus_agent.py
│  └─ reporter_agent.py
├─ data/
│  ├─ ingested/
│  └─ reports/
├─ config/
│  ├─ runtime_settings.json
│  └─ runtime_settings.example
├─ docs/
│  └─ README_WINDOWS.md
├─ legacy/                     # Para não confundir
│  ├─ fastapi_multiagent_gut_scheduler.py
│  ├─ chat_ui.py
│  └─ scheduler_agent.py
├─ requirements.txt
└─ LICENSE
```

**Dica:** Após reorganizar, ajuste os imports relativos nos arquivos.

---

## ⚙️ Como o Sistema Funciona

### Fluxo de Verificação:
1. **Recebimento:** Conteúdo é categorizado (Política, Saúde, Economia, etc.)
2. **Priorização GUT:** Calcula Gravidade, Urgência e Tendência (1-5 cada)
3. **Seleção de Agentes:** Escolhe 5 verificadores especializados + independentes
4. **Análise:** Cada agente avalia o conteúdo usando LLM + evidências web
5. **Consenso:** Combina pareceres ponderados por reputação
6. **Resultado:** Score (0-1) + rótulo (Verdadeiro/Falso/Enganoso/Descontextualizado)

### Recursos Avançados:
- **Preempção:** Itens críticos podem interromper análises menos prioritárias
- **Modo Offline:** Funciona sem APIs externas (com resultados simulados)
- **Busca Web:** Integração com Tavily e DuckDuckGo para evidências
- **Múltiplos Formatos:** Texto, imagem, áudio, vídeo

---

## 🔧 Solução de Problemas

### Problemas Comuns:

**❌ "python" não é reconhecido**
- Instale Python pelo [python.org](https://python.org) marcando **"Add Python to PATH"**
- Feche e reabra o PowerShell

**❌ Erro de política de execução (venv)**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

**❌ Porta 8000 já em uso**
```powershell
# Use outra porta
uvicorn serve_combined_app:app --reload --port 8001
# Acesse: http://127.0.0.1:8001/ui
```

**❌ Dependências em falta**
```powershell
pip install --upgrade -r requirements.txt
```

**❌ Permissões de escrita**
- Execute PowerShell como **Administrador**
- Ou mova o projeto para uma pasta sem restrições

---

## 📋 Comandos de Referência Rápida

```powershell
# Configuração inicial
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Iniciar sistema (principal)
uvicorn serve_combined_app:app --reload --port 8000
# Acesse: http://127.0.0.1:8000/ui

# Testes CLI
python .\multiagent_gut_scheduler.py --demo
python .\multiagent_gut_scheduler.py --submit --type text --source "cli" --content "Teste" --process

# Importação em lote
python .\load_gsheet_to_scheduler.py --csv "URL_DA_PLANILHA" --limit 20 --process
```

---

## 🎯 Configurações Avançadas

### Ajustar Capacidade de Processamento:
```powershell
# Processar até 3 itens simultaneamente (padrão: 2)
python .\multiagent_gut_scheduler.py --demo --capacity 3
```

### Ajustar Sensibilidade de Preempção:
```powershell
# Preempção mais agressiva (padrão: 2.0)
python .\multiagent_gut_scheduler.py --demo --preemption 1.5
```

### Modo Offline:
- Ative na interface web em **Configuração**
- Ou edite `runtime_settings.json`: `"offline_mode": true`

---

## 🆘 Precisa de Ajuda?

Se encontrar algum problema:
1. Copie a mensagem de erro completa
2. Verifique se seguiu todos os passos da instalação
3. Confirme que o ambiente virtual está ativado
4. Teste primeiro com o comando `--demo`

**Sistema funcionando?** 🎉  
Agora você pode verificar fatos de forma automatizada e inteligente!
