# Arquitetura do Sistema Multiagente para Checagem de Fatos

## 1. Introdução

Este documento descreve a arquitetura proposta para o Sistema Multiagente de Checagem de Fatos com Scheduler Inteligente, conforme os requisitos e o descritivo do problema fornecidos. O sistema visa automatizar e otimizar o processo de verificação de conteúdo multimodal, integrando análise automática com checagem humana especializada, orquestrada por um scheduler preemptivo por prioridade.

## 2. Componentes Principais

O sistema será composto pelos seguintes agentes e módulos principais:

### 2.1. Agente de Ingestão de Conteúdo

**Função:** Responsável por receber novos conteúdos multimídia (texto, imagem, áudio, vídeo) e prepará-los para o processamento inicial. Este agente garante que os conteúdos sejam padronizados e enriquecidos com metadados básicos antes de serem encaminhados para categorização.

**Entradas:** Conteúdo multimídia em diversos formatos.

**Saídas:** Conteúdo padronizado com metadados.

### 2.2. Agente de Pré-processamento e Categorização (IA Treinada)

**Função:** Utiliza modelos de IA treinados para analisar o conteúdo recebido, extrair metadados relevantes e identificar sua categoria principal (e.g., Política, Saúde, Economia, Mundo, Esportes, Geral). Este agente é crucial para a organização inicial do fluxo de trabalho.

**Entradas:** Conteúdo padronizado do Agente de Ingestão.

**Saídas:** Conteúdo categorizado com metadados de categoria.

### 2.3. Agente de Atribuição de Prioridade (Matriz GUT - IA Treinada)

**Função:** Após a categorização, este agente aplica a Matriz GUT (Gravidade, Urgência, Tendência) para atribuir um score de prioridade ao conteúdo. Este score é fundamental para o scheduler inteligente, determinando a ordem de processamento e a aplicação de preempção.

**Entradas:** Conteúdo categorizado.

**Saídas:** Conteúdo com score GUT e prioridade atribuída.

### 2.4. Scheduler Central

**Função:** O coração do sistema, responsável por monitorar as filas de conteúdo, gerenciar a capacidade das Unidades de Checagem e aplicar a política de preempção. Ele balanceia a carga de trabalho e garante que conteúdos de maior prioridade sejam processados primeiro, suspendendo itens de menor prioridade se necessário.

**Entradas:** Conteúdo com prioridade GUT, status das Unidades de Checagem.

**Saídas:** Tarefas despachadas para Unidades de Checagem, conteúdos preemptados.

### 2.5. Filas por Formato e Prioridade

**Função:** Armazenam os conteúdos aguardando checagem, organizados por formato (texto, áudio, vídeo, imagem) e sub-organizados por prioridade GUT. Interagem com o Scheduler Central para sinalizar disponibilidade e consumo de recursos.

**Entradas:** Conteúdo com prioridade GUT.

**Saídas:** Conteúdo disponível para checagem.

### 2.6. Agente de Seleção e Alocação de Checadores

**Função:** Seleciona e aloca um grupo de N=5 checadores virtuais para cada tarefa de checagem. Este grupo é composto por analisadores específicos (Bronze, Prata, Ouro, com especialidade e reputação) e analisadores independentes (jornalistas gerais), garantindo uma combinação de especialização e imparcialidade.

**Entradas:** Tarefa de checagem, perfis de checadores disponíveis.

**Saídas:** Grupo de 5 checadores alocados para a tarefa.

### 2.7. Unidades de Checagem (Agentes Checadores Virtuais)

**Função:** Representam os checadores virtuais que analisam o conteúdo e fornecem seus pareceres individuais sobre a veracidade ou tipo de desinformação. Cada unidade processa uma tarefa e retorna um parecer.

**Entradas:** Conteúdo para checagem, informações da tarefa.

**Saídas:** Pareceres individuais dos checadores.

### 2.8. Agente de Consenso (Módulo Probit/Problok)

**Função:** Recebe os pareceres individuais dos 5 checadores e aplica uma lógica probabilística inspirada em probit/problok para combiná-los. Gera um Score de Veracidade Final e um Rótulo Final da Informação (e.g., Verdadeiro, Falso, Conteúdo Enganoso).

**Entradas:** Pareceres individuais dos checadores.

**Saídas:** Score de veracidade final, rótulo final da informação.

### 2.9. Agente Relator

**Função:** Compila todas as informações relevantes da checagem (conteúdo original, prioridade GUT, painel de checadores, pareceres individuais, score de veracidade, rótulo final e explicação do consenso) e gera um relatório final explicável. Este relatório pode ser exportado em formatos como JSON ou PDF.

**Entradas:** Conteúdo original, metadados da checagem, resultados do consenso.

**Saídas:** Relatório final em formato digital.

## 3. Fluxo de Operação

O fluxo de operação do sistema segue as seguintes etapas:

1.  **Recebimento de Conteúdo:** O Agente de Ingestão recebe novos conteúdos multimídia.
2.  **Pré-processamento e Categorização:** O Agente de Pré-processamento e Categorização analisa e categoriza o conteúdo.
3.  **Atribuição de Prioridade:** O Agente de Atribuição de Prioridade aplica a Matriz GUT e define a prioridade.
4.  **Gestão de Filas:** O conteúdo é inserido nas Filas por Formato e Prioridade, aguardando o Scheduler Central.
5.  **Despacho e Preempção:** O Scheduler Central monitora as filas e a capacidade, despachando tarefas e aplicando preempção quando necessário.
6.  **Seleção de Checadores:** O Agente de Seleção e Alocação de Checadores forma um grupo de 5 checadores.
7.  **Checagem:** As Unidades de Checagem analisam o conteúdo e fornecem pareceres.
8.  **Consenso:** O Agente de Consenso combina os pareceres e gera o score e rótulo final.
9.  **Relatório:** O Agente Relator gera o relatório final da checagem.

## 4. Considerações Técnicas

*   **Tecnologias:** Python para o desenvolvimento dos agentes e lógica de negócio. Possível uso de frameworks de agentes (e.g., `mesa`, `spade`) para a orquestração. Bancos de dados para persistência de informações de conteúdo, checadores e resultados.
*   **Escalabilidade:** A arquitetura modular permite a escalabilidade horizontal dos agentes, especialmente das Unidades de Checagem, para lidar com volumes crescentes de conteúdo.
*   **Explicabilidade:** O módulo de Consenso e o Agente Relator são projetados para garantir a explicabilidade dos resultados, um requisito chave do sistema.
*   **Scheduler Inteligente:** A implementação do scheduler deve considerar algoritmos de balanceamento de carga e a lógica de preempção baseada na matriz GUT.

## 5. Próximos Passos

Com base nesta arquitetura, os próximos passos incluem a definição detalhada das interfaces entre os agentes, a seleção de tecnologias específicas para cada módulo e a implementação gradual de cada componente.
