# Sistema Multiagente para Checagem de Fatos

Sistema inteligente de verificação de fatos com interface web intuitiva. Analisa textos, imagens e outros conteúdos usando múltiplos agentes especializados.

## 🚀 Início Rápido

1. **Instalar dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Iniciar o sistema:**
   ```bash
   uvicorn app.serve_combined_app:app --reload --port 8000
   ```

3. **Abrir no navegador:**
   - **Interface principal:** http://127.0.0.1:8000/ui
   - **API (documentação):** http://127.0.0.1:8000/docs

## 📁 Estrutura do Projeto

```
multiagent_fake_news/
├─ app/                        # UI + API + helpers
│  ├─ serve_combined_app.py    # ⭐ ENTRADA PRINCIPAL
│  ├─ gradio_multiagent_ui.py
│  ├─ settings_store.py
│  ├─ scheduler_adapter.py
│  ├─ llm_helper.py
│  └─ tavily_helper.py
├─ scheduler/                  # Orquestração
│  ├─ multiagent_gut_scheduler.py  # ⭐ CORAÇÃO DO SISTEMA
│  └─ load_gsheet_to_scheduler.py
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
│  ├─ ingested/                # Arquivos enviados
│  └─ reports/                 # Relatórios JSON
├─ config/
│  ├─ runtime_settings.json    # Configurações (gerado automaticamente)
│  └─ runtime_settings.example # Template
├─ docs/
│  └─ README_WINDOWS.md        # Guia detalhado para Windows
├─ legacy/                     # Arquivos antigos
│  ├─ fastapi_multiagent_gut_scheduler.py
│  ├─ chat_ui.py
│  └─ scheduler_agent.py
├─ requirements.txt
└─ LICENSE
```

## 📖 Documentação

Para usuários Windows, consulte o guia completo: **[docs/README_WINDOWS.md](docs/README_WINDOWS.md)**

## 🔧 Desenvolvimento

O sistema funciona em 4 camadas:
1. **UI (Gradio)**: Interface web em `/ui`
2. **API (FastAPI)**: Endpoints REST em `/docs`
3. **Agendador**: Orquestra filas e prioridades
4. **Agentes**: Módulos especializados para verificação

## 📝 Licença

Veja o arquivo [LICENSE](LICENSE) para detalhes.
