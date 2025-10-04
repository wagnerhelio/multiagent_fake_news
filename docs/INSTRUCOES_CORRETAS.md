# 🚀 INSTRUÇÕES CORRETAS PARA RODAR O SISTEMA

## ✅ COMANDOS CORRETOS (use exatamente estes):

### 1. Ativar o ambiente virtual:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Iniciar o servidor:
```powershell
python -m uvicorn app.serve_combined_app:app --reload --port 8000
```

## ⚠️ PROBLEMA IDENTIFICADO:

O arquivo `config/runtime_settings.json` estava com `"offline_mode": true`, por isso o sistema usava simulação ao invés das APIs reais.

**JÁ CORRIGI:** Agora está `"offline_mode": false`

## 🎯 PARA TESTAR AGORA:

1. **Acesse:** http://127.0.0.1:8000/ui
2. **Vá na aba "Configuração"**
3. **Verifique se está DESMARCADO:** "Ativar modo offline"
4. **Clique "Aplicar configurações"**
5. **Vá na aba "Enviar conteúdo"**
6. **Digite uma notícia falsa**
7. **Marque "Processar imediatamente"**
8. **Clique "Enviar"**

## 🔍 RESULTADO ESPERADO:

Nos logs deve aparecer:
- `[REAL] Verificando conteudo com OpenAI/Tavily`
- `[TAVILY] Encontradas X evidencias`
- `[OPENAI] Jornalista: [Veredicto]`
- `[OPENAI] Fact-Checker: [Veredicto]`
- etc.

## ❌ SE NÃO FUNCIONAR:

Execute este comando para testar diretamente:
```powershell
python -c "from scheduler.multiagent_gut_scheduler import enqueue_content, process_round; cid = enqueue_content('text', 'Teste de noticia falsa', source='test'); print(f'ID: {cid}'); result = process_round(max_items=1); print('OK')"
```

Deve aparecer logs `[REAL]`, `[TAVILY]`, `[OPENAI]`
