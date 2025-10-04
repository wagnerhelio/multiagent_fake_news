# Sistema Multiagente para Checagem de Fatos (Scheduler GUT) — Guia de Instalação (Windows + PowerShell)

Este guia explica **passo a passo** como instalar e usar o protótipo no **Windows**, usando **PowerShell**. Foi escrito para usuários leigos.

---

## 0) Pré-requisitos

- **Windows 10/11**
- **Python 3.9+** (ideal 3.11 ou 3.12)
  - Verifique no PowerShell:
    ```powershell
    python --version
    ```
  - Se **não** aparecer a versão, instale pelo site oficial do Python (marque a opção **"Add Python to PATH"** na instalação) e **reinicie** o PowerShell.

---

## 1) Baixar o projeto e abrir a pasta

1. Crie uma pasta para o projeto (ex.: `C:\Users\SEU_USUARIO\Downloads\multiagent_fake_news`).
2. Coloque **todos os arquivos** do projeto dentro dessa pasta.
3. Abra o **PowerShell** e vá para a pasta do projeto:
   ```powershell
   cd C:\Users\SEU_USUARIO\Downloads\multiagent_fake_news
   ```

> Dica: substitua `SEU_USUARIO` pelo seu nome de usuário do Windows.

---

## 2) Criar e ativar o ambiente virtual (venv)

> O ambiente virtual mantém as dependências isoladas.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Se aparecer erro de política de execução, rode **uma vez**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Depois **ative** de novo:
```powershell
.venv\Scripts\Activate.ps1
```

Para **desativar** o ambiente virtual no futuro:
```powershell
deactivate
```

---

## 3) Atualizar o `pip` (opcional, mas recomendado)

```powershell
python -m pip install --upgrade pip
```

---

## 4) Instalar dependências

O núcleo (CLI) roda **sem** bibliotecas externas. Para a **API** e a **UI conversacional**, instale:

```powershell
pip install fastapi uvicorn python-multipart gradio pandas
```

- `fastapi` + `uvicorn`: API web
- `python-multipart`: necessário para upload de arquivos via API
- `gradio`: interface conversacional (chat)
- `pandas`: para ler planilhas CSV

---

## 5) Testar o núcleo (CLI)

### 5.1) Demo automática
```powershell
python .\multiagent_gut_scheduler.py --demo
```
Você verá itens enfileirados e relatórios gerados em `.\reports\...json`.

### 5.2) Enviar um texto (via CLI) e processar na hora
```powershell
python .\multiagent_gut_scheduler.py --submit --type text --source "cli" --content "URGENTE: vídeo viral, possível fraude no congresso." --process
```
- Mostra o **ID** do conteúdo e cria um **relatório JSON** em `.\reports\<id>.json`.

### 5.3) Opções úteis
- Capacidade de processamento simultâneo (padrão 2):
  ```powershell
  python .\multiagent_gut_scheduler.py --demo --capacity 2
  ```
- Preempção (quanto maior, mais difícil preemptar; padrão 2):
  ```powershell
  python .\multiagent_gut_scheduler.py --demo --preemption 2
  ```

---

## 6) Rodar a API (FastAPI)

Inicie o servidor:
```powershell
uvicorn fastapi_multiagent_gut_scheduler:app --reload --port 8000
```
Abra no navegador: **http://127.0.0.1:8000/docs** (Swagger).

### 6.1) Enviar conteúdo (texto) pela API – PowerShell
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/submit" -Form @{
  type="text"; source="api"; text="URGENTE: rumor viral…"
}
```

### 6.2) Processar uma rodada
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/process?max_items=3"
```

### 6.3) Ver status do scheduler
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/status"
```

### 6.4) Baixar relatório (JSON)
```powershell
$ID="<cole_oq_veio_no_submit>"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/report/$ID" | Out-File -FilePath ".\report_$ID.json" -Encoding utf8
```

### 6.5) Enviar **arquivo** (ex.: imagem)
```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/submit" -Form @{
  type="image"; source="api"; file=Get-Item ".\minha_imagem.jpg"
}
```

> **Pare o servidor** com `CTRL + C` no PowerShell.

---

## 7) Rodar a UI Conversacional (Gradio)

Instale (se ainda não fez):
```powershell
pip install gradio
```

Inicie a UI:
```powershell
python .\chat_ui.py
```
Abra **http://127.0.0.1:7860** no navegador.  
- Digite um texto **ou** envie um arquivo.
- (Opcional) marque “**Processar rodada agora**” para já rodar o scheduler.
- A UI mostra: confirmação de fila (com GUT), **status** (ativos, preemptados, filas) e **links** de relatórios JSON.

---

## 8) Carregar conteúdos a partir da Planilha (Google Sheets → CSV)

1) Publique a planilha ou gere o link CSV:
- No Google Sheets: **Arquivo → Compartilhar → Publicar na web** (ou adapte o link para `export?format=csv&gid=...`).

2) Rode o loader:
```powershell
pip install pandas
python .\load_gsheet_to_scheduler.py --csv "https://docs.google.com/spreadsheets/d/SEU_ID/export?format=csv&gid=2114918615" --limit 20 --process
```

> O script tenta mapear colunas como `text`, `Texto_Original` ou `conteudo` automaticamente.

---

## 9) Onde encontro os resultados?

- **Relatórios JSON:** `.\reports\<content_id>.json`
- **Uploads:** `.\uploads\...`
- **Estados (em memória):** veja em `GET /status` ou na UI conversacional.

---

## 10) Como funciona (resumo rápido)

- **Filas por formato**: `text`, `image`, `audio`, `video`.
- **Prioridade GUT**: heurística (1–5 para Gravidade/UrGência/Tendência) → `prioridade = G × U × T`.
- **Preempção controlada**: itens de menor prioridade podem ser **preemptados** quando chega algo muito mais prioritário.
- **Unidades de Checagem**: grupos com **≥5** checadores (especialistas + independentes, níveis bronze/prata/ouro, com reputação).
- **Consenso (probit-like)**: média ponderada (reputação × confiança) → **score de veracidade** e **rótulo** (Verdadeiro / Descontextualizado / Enganoso / Falso).
- **Estados**: `new` → `in_analysis` → (`preempted`/`in_review`) → `closed`.
- **Relatório**: JSON explicável com GUT, checadores, votos, pesos e decisão final.

---

## 11) Erros comuns e como resolver

- **"python" não é reconhecido**  
  Instale o Python e **marque** “Add Python to PATH”. Feche e reabra o PowerShell.

- **Erro ao ativar venv (política de execução)**  
  Rode uma vez:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
  Depois ative:  
  ```powershell
  .venv\Scripts\Activate.ps1
  ```

- **API reclama do `python-multipart`**  
  Rode:
  ```powershell
  pip install python-multipart
  ```

- **Porta já em uso (8000 ou 7860)**  
  Feche programas que estejam usando a porta **ou** use outra porta:
  ```powershell
  uvicorn fastapi_multiagent_gut_scheduler:app --reload --port 8001
  ```
  ```powershell
  python .\chat_ui.py --port 7861
  ```

- **Permissões de escrita**  
  Garanta que a pasta do projeto permita gravar em `.\reports\` e `.\uploads\`.

---

## 12) Comandos rápidos (cola)

```powershell
# Dentro da pasta do projeto
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install fastapi uvicorn python-multipart gradio pandas

# CLI (demo)
python .\multiagent_gut_scheduler.py --demo

# CLI (enviar texto e processar)
python .\multiagent_gut_scheduler.py --submit --type text --source "cli" --content "Meu texto" --process

# API
uvicorn fastapi_multiagent_gut_scheduler:app --reload --port 8000
# Docs: http://127.0.0.1:8000/docs

# UI Conversacional
python .\chat_ui.py
# UI: http://127.0.0.1:7860

# Loader Planilha (CSV)
python .\load_gsheet_to_scheduler.py --csv "https://docs.google.com/spreadsheets/d/SEU_ID/export?format=csv&gid=2114918615" --limit 20 --process
```

---

## 13) Personalização rápida

- **Capacidade simultânea** (padrão 2):
  ```powershell
  python .\multiagent_gut_scheduler.py --demo --capacity 3
  ```
- **Limite de preempção** (padrão 2):
  ```powershell
  python .\multiagent_gut_scheduler.py --demo --preemption 1.5
  ```

Pronto! Se travar em algum passo, copie e cole aqui o erro completo que eu te ajudo a ajustar.
