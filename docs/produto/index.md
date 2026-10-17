# Produto

Como a plataforma funciona do ponto de vista de quem usa — sem entrar em qual
tecnologia resolve cada parte. Para isso, ver [Arquitetura](../arquitetura/index.md).

Dois perfis usam a plataforma: **investidor** e **gestora**. Cada um vê uma
versão diferente dos mesmos dados.

## Fluxo do investidor

1. **Login.** O investidor entra com e-mail e senha.
2. **Visão geral.** A primeira tela mostra o total investido, o ranking das empresas que mais recebem do
   dinheiro dele e um **cubo 3D** em que cada empresa ocupa uma região proporcional à sua fatia (passar
   o mouse mostra o valor; clicar abre os blocos da etiqueta). Há também a interface do chat "Assistente
   Clara", ainda sem modelo de linguagem por trás.
3. **Blocos de Liquidez.** A lista de todos os blocos, com busca e ordenação. Cada cartão abre a **ficha
   do bloco**: etiqueta, vencimento, score, a tabela de empresas (com CNPJ, ramo, capital e score de
   cada uma) e o **bloco visual**, um cubo com a porcentagem do capital que vai para cada empresa. É a
   tela que dá nome ao produto: não existe "confia em mim", existe a lista.
4. **Blocos Investidos.** Os blocos em que o investidor já investiu, com busca, filtro por etiqueta e
   ordenação por valor investido, score ou vencimento. A ficha mostra também quanto do dinheiro dele
   está em cada empresa. Ver [Blocos de Liquidez](blocos-de-liquidez.md).
5. **Relatório.** O investidor pede um relatório consolidado em PDF, escrito em linguagem natural por um
   assistente de IA a partir da carteira dele, vê a prévia na própria tela e baixa o arquivo. Ver
   [Relatório](relatorio.md).

## Fluxo da gestora

1. **Login.** Depois de entrar, a gestora cai na tela de criação de blocos.
2. **Dashboard consolidado.** A gestora vê a mesma visão por Bloco de
   Liquidez, mas sem filtro de investidor — é o fundo inteiro.
3. **Tabela de empresas.** Uma visão de todas as empresas sacadas (que devem
   os recebíveis) no fundo, com valor total alocado, nota de risco e status
   de adimplência de cada uma.
4. **Criação de blocos.** A gestora monta um Bloco de Liquidez: escolhe a
   etiqueta, define o capital, adiciona empresas e distribui o capital entre
   elas. Ver [Blocos de Liquidez](blocos-de-liquidez.md).

!!! warning "Como os dados entram no sistema: ainda não definido"
    O fluxo original — a gestora subindo uma planilha manualmente — foi
    removido de propósito: não é assim que a plataforma vai operar com
    usuários reais. A ideia é que os dados venham de uma consulta direta a
    algum sistema que já os tenha, mas **isso ainda não foi desenhado**. É a
    decisão mais urgente do projeto. Ver [Roadmap](../roadmap/index.md).

## O que o score de risco é — e o que não é

O score de risco de cada empresa vai de 0 a 100, e **maior score significa menor risco**. A
plataforma traduz esse número numa nota (A+ a C-) e num status de adimplência, mas **não calcula**
o score. A ideia do grupo é que ele venha de um modelo de machine learning (um Random Forest que
analisa o histórico da empresa: valor de aporte, prazo, taxa de retorno, bloco setorial, categoria
técnica). Esse modelo ainda não existe.

**Hoje, os scores são de demonstração**: foram sorteados de 0 a 100 para cada empresa e ficam em
`backend/dados/scores_empresas.csv`. Ver [Dados de demonstração](#regra-de-produto-dado-inventado-so-como-demonstracao-declarada).

## Regra de produto: dado inventado só como demonstração declarada

Em algum momento a plataforma já mostrou números que pareciam dados reais mas eram simulados
(evolução de patrimônio, rendimento projetado) sem nenhum rótulo avisando isso. Numa plataforma
que se vende pela transparência, número inventado sem aviso é o pior defeito possível.

**Regra que fica:** em produção, qualquer número exibido ou vem de dado real, ou é explicitamente
rotulado como estimativa.

**Exceção declarada, os dados de demonstração.** Enquanto o projeto é acadêmico e não tem dados
reais, os dados da plataforma são **fictícios**: as empresas (geradas com a biblioteca Faker, do
Python), os blocos de exemplo e os scores de risco (sorteados de 0 a 100). Por decisão do grupo, o
front-end **não** os rotula, mas esta documentação, o README e a apresentação declaram, de forma
explícita, que são fictícios. Nenhum outro número inventado pode aparecer nas telas.
