Sistema Multiagente para Checagem de Fatos com Scheduler
Inteligente
Contexto:
Com a crescente circulação de notícias falsas em múltiplas mídias (texto, imagem,
áudio e vídeo), mídias distorcidas (imagem e vídeo) e conteúdos fora do contexto, a sociedade
demanda sistemas capazes de *avaliar, priorizar e verificar* conteúdos em larga escala. O
surgimento de *IA generativa* torna o problema ainda mais desafiador, pois amplia a
capacidade de criar conteúdos sintéticos convincentes.
Neste cenário, uma agência de checagem virtual está sendo desenvolvida,
necessitando de ferramentas que combinem *análise automática multimodal* com *checagem
humana especializada*, orquestradas por mecanismos de governança e reputação.
Desafio:
Desenvolver um *sistema multiagente* que implemente um *scheduler inteligente
preemptivo por prioridade (GUT)* para organizar o fluxo de checagem de conteúdos
multimodais, com as seguintes capacidades:
● Scheduler Central - recebe conteúdos em filas de entrada, já previamente categorizados
por formato e prioridade (matriz GUT). Executa o balanceamento de carga entre
unidades de checagem disponíveis. Aplica política de preempção: se não houver
capacidade, itens de menor prioridade podem ser suspensos (estado de espera) em
favor de conteúdos mais críticos.
● Filas por Formato - mantêm filas específicas (texto, áudio, vídeo, imagem). Interagem
com o scheduler para sinalizar disponibilidade e consumo de recursos.
● Expedição - que despacha de acordo com a prioridade baseada na *matriz GUT*
(gravidade, urgência, tendência) e aplica *preempção* sempre que conteúdos de maior
prioridade chegarem.
● Unidades de Checagem - representam “grupos” de checadores anonimizados,
compostos por no mínimo 5 perfis virtuais com atributos de especialidade e reputação.
Recebem tarefas do scheduler, processam o conteúdo e retornam pareceres com a
avaliação.
● Consenso - combina os pareceres dos checadores virtuais usando lógica probabilística
inspirada no algoritmo **probit/problok**. Gera um score de veracidade e atribui rótulo
final de acordo com o tipo de desinformação.
● Relator - que produz um relatório final legível, contendo: conteúdo analisado, prioridade
atribuída, painel de checadores envolvidos, score de veracidade e rótulo final.
Requisitos
1. Conteúdos chegam pré-categorizados por formato (texto, áudio, vídeo, imagem) e
prioridade. O scheduler deve garantir balanceamento de carga e uso ótimo da
capacidade de atendimento.
2. Implementar preempção controlada: conteúdos de menor prioridade podem ser
suspensos e recolocados em espera.

--- PAGE 1 ---

3. Cada checagem deve envolver mínimo de 5 checadores virtuais com perfis
anonimizados.
4. O consenso final deve ser explicável (relatório mostra como o resultado foi atingido)
5. O sistema deve lidar com *múltiplos conteúdos concorrentes* em diferentes estados
(novo, em análise, preemptado, em revisão, fechado).
6. Deve haver *gestão de filas com preempção* (conteúdos de menor prioridade são
suspensos e reencaminhados para espera quando não há capacidade).
7. O relatório final deve ser exportável em formato digital (ex.: JSON ou PDF).
Produto Esperado
Um protótipo funcional de sistema multiagente que simula o funcionamento de um
Scheduler de Checagem de fatos, capaz de:
● receber conteúdos multimídia categorizados;
● gerenciar filas por formato e prioridade;
● despachar tarefas para unidades de checagem anônimas;
● aplicar preempção quando necessário;
● consolidar pareceres em relatórios explicativos com score de veracidade.
Fluxo:
1. recebimento pacote de notícia
2. categorizar - dados treinados IA
3. matriz GUT - definir severidade - dados treinados AI
4. definir fila de acordo com categoria X severidade
5. definir N=5 agentes de acordo com categoria e severidade
6. N1=2 ou 3 ou 4 analisador bronze, prata, ouro especifico para categoria
7. N2=2 ou 3 ou 4 analisador independente = jornalista geral
8. verificação da informação
9. classificação da informação
10. geração de relatório
A ser definido:
1. quais as categorias ?
2. quais os critérios de severidade ?
3. quais os critérios de preempcao ?
4. tamanho da fila ?

--- PAGE 2 ---

Explicação do Fluxograma:
A: Início: Recebimento de Conteúdo Multimídia (Pacote de
Notícias)
● É o ponto de entrada de novos conteúdos no sistema.
Estes conteúdos podem ser textos, imagens, áudios ou
vídeos.
B: Pré-processamento e Categorização (IA Treinada)
● B1: O sistema utiliza uma IA treinada para analisar
o conteúdo recebido, extrair metadados relevantes e
identificar sua Categoria principal.
● B2: O conteúdo é categorizado.
● A SER DEFINIDO: Quais as Categorias? Este é um
ponto crucial onde a agência precisará definir a
granularidade das categorias (ex: "Política", "Saúde",
"Economia", "Mundo", "Esportes", "Geral", etc.).
C: Atribuição de Prioridade (Matriz GUT - IA Treinada)
● C1: Após a categorização, outra IA treinada avalia
o conteúdo para atribuir a ele um Score GUT
(Gravidade, Urgência, Tendência). Este score
determinará a prioridade do item.
● C2: O conteúdo agora possui um score GUT.
● A SER DEFINIDO: Quais os Critérios de Severidade
(GUT)? A agência deve estabelecer as regras e a
escala para G, U e T (ex: 1 a 5 para cada, com
descrições claras para cada nível).

--- PAGE 3 ---

D: Gestão de Filas e Scheduler Central:
● D1: O conteúdo é inserido na fila específica que
combina sua Categoria e seu Score GUT (ex:
"Fila_Política_GUT_Alta", "Fila_Saúde_GUT_Média").
Isso ajuda a organizar e segmentar o fluxo de trabalho.
● D2: O conteúdo aguarda em sua fila.
● A SER DEFINIDO: Tamanho da Fila? A capacidade
máxima de itens em cada fila pode precisar ser
definida, impactando a gestão de recursos e o
envelhecimento de itens.
E: Processo: Scheduler Central - Monitoramento de Filas e
Capacidade de Checagem
● O Scheduler Central atua como o maestro,
monitorando constantemente todas as filas e a
disponibilidade das Unidades de Checagem (os
grupos de agentes).
F: Scheduler: Capacidade de Checagem Disponível OU
Conteúdo de Prioridade Mais Alta Chegou? (Decisão)
● Este é o ponto de decisão principal do scheduler. Ele
verifica se há recursos (agentes) disponíveis para
checar os conteúdos nas filas OU se um novo
conteúdo de prioridade significativamente mais alta
(com base no GUT) chegou e demanda atenção
imediata.

--- PAGE 4 ---

G: Aplicação da Política de Preempção
● G1: Se um conteúdo de prioridade mais alta chega e
as unidades de checagem estão ocupadas com itens
de menor prioridade, o scheduler suspende o
processamento do item de menor prioridade (Estado:
Preemptado/Espera). Esse conteúdo de menor
prioridade retorna à sua fila, mas com um status que
indica que foi preemptado e aguarda para ser
retomado.
● A SER DEFINIDO: Quais os Critérios de
Preempção? É necessário definir o limiar de prioridade
para que a preempção seja acionada. (Ex: um item
GUT 5 U 5 T 5 sempre preempta um item GUT 3 U 3 T
3, mas um GUT 4 U 4 T 4 pode não preemptar um
GUT 4 U 3 T 3).
H: Seleção e Alocação de N=5 Agentes (Unidades de
Checagem)
● Se há capacidade disponível (ou após a preempção e
priorização de um novo item), o scheduler seleciona 5
agentes para formar uma Unidade de Checagem.
● H1: São identificados 2 a 4 analisadores
específicos (com perfis Bronze, Prata, Ouro
indicando diferentes níveis de especialidade e
reputação) cuja especialidade corresponda à
Categoria e Severidade do conteúdo.
● H2: São identificados 2 a 4 analisadores
independentes (jornalistas gerais) para garantir uma
perspectiva mais ampla e menos enviesada.
● H3: Um grupo de 5 agentes é formado, garantindo a
combinação de especialização e independência.
● A SER DEFINIDO: Tamanho da Carteira de
Avaliadores x Categoria? Quantos agentes existem
em cada categoria de especialidade e qual a sua
distribuição (Bronze, Prata, Ouro)? Isso impactará a
capacidade e a qualidade da checagem.

--- PAGE 5 ---

I: Verificação e Análise da Informação (Pelos N=5 Agentes)
● I1: Os 5 agentes designados analisam o conteúdo e
cada um fornece seu Parecer Individual sobre a
veracidade ou tipo de desinformação.
J: Classificação e Consenso (Módulo Probit/Problok)
● J1: O sistema recebe os 5 pareceres individuais. O
Módulo de Consenso aplica uma lógica
probabilística inspirada em probit/problok
para combinar esses pareceres. A reputação e
especialidade dos agentes podem ser usadas como
pesos nesse cálculo para um consenso mais refinado.
(Em estatística , a função probit converte uma
probabilidade (um número entre 0 e 1) em uma
pontuação. Essa pontuação indica quantos
desvios-padrão da média um valor de uma
distribuição normal padrão (ou "curva de sino")
está.)
● J2: O resultado é um Score de Veracidade Final
(um valor numérico) e um Rótulo Final da
Informação (ex: "Verdadeiro", "Falso", "Conteúdo
Enganoso", "Descontextualizado", "Sátira", etc.).

--- PAGE 6 ---

K: Geração de Relatório Explicável (Relator)
● K1: O Relator compila todas as informações
relevantes: o conteúdo original, a prioridade GUT
atribuída, o painel de checadores que atuaram, seus
pareceres individuais, o score de veracidade final, o
rótulo final e, crucialmente, uma explicação de
como o consenso foi atingido (tornando-o
explicável).
● K2: O Relatório Final é gerado e pode ser
exportado em formatos como JSON ou PDF.
L: Fim
● O ciclo de checagem para aquele item de conteúdo
está concluído.
Probit (Modelo Probit)
Probit é um termo estatístico que se refere a um modelo estatístico de regressão para
variáveis dependentes binárias. Isso significa que ele é usado para prever a probabilidade de
um evento ocorrer quando esse evento tem apenas duas categorias de resultado (por exemplo,
sim/não, verdadeiro/falso, sucesso/fracasso).
Características Principais:
1. Variável Dependente Binária: O resultado que você está tentando prever é uma
escolha entre duas opções. No seu caso, poderia ser a probabilidade de uma notícia ser
"Verdadeira" versus "Falsa", ou a probabilidade de um checador concordar com uma
determinada afirmação.

--- PAGE 7 ---

2. Função de Ligação (Link Function): O modelo probit usa a função de distribuição
cumulativa normal padrão inversa (também conhecida como "função probit") para
transformar a combinação linear das variáveis preditoras em uma probabilidade. Em
termos mais simples, ele assume que existe uma variável latente subjacente (não
diretamente observável) que segue uma distribuição normal, e quando essa variável
latente excede um certo limite, o evento binário ocorre.
3. Interpretação: Diferente de outros modelos como a regressão logística (logit), os
coeficientes do modelo probit não são diretamente interpretáveis como odds ratios. A
interpretação é feita em termos de "efeitos marginais" – como uma mudança em uma
variável preditora afeta a probabilidade do evento.
4. Aplicações: É amplamente utilizado em campos como economia (escolha do
consumidor), biometria (dose-resposta), psicometria e em qualquer área onde se
precise modelar decisões ou eventos binários.
No contexto do seu projeto: O modelo probit poderia ser usado para combinar os pareceres
dos N=5 checadores virtuais. Por exemplo, cada parecer poderia ser uma variável
preditora, e o modelo estimaria a probabilidade final de a informação ser "Verdadeira" ou
"Falsa", considerando a "confiança" ou "reputação" de cada checador como pesos ou variáveis
adicionais.

--- PAGE 8 ---

