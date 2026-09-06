# Plataforma Clara

Plataforma de transparência e análise de risco para **FIDCs** (Fundos de
Investimento em Direitos Creditórios), ligando gestoras e investidores.

Projeto acadêmico (FIAP).

## O problema

Quem investe num FIDC costuma não saber onde o próprio dinheiro está. A gestora
tem os dados; o investidor recebe um extrato. A plataforma reduz essa assimetria.

## O que ela faz

**A gestora** envia um CSV de aportes. Cada linha é validada contra um contrato de
19 colunas, normalizada e carregada nos bancos.

**O investidor** enxerga a carteira agregada por Bloco de Liquidez — volume
alocado, score médio de risco e as empresas sacadas por trás de cada bloco — e
pode gerar um relatório consolidado em PDF, escrito por um LLM a partir dos dados
reais da própria carteira.

!!! note "O score não é calculado aqui"
    O `score_risco_interno` **chega pronto como coluna do CSV**. Não existe modelo
    de machine learning no repositório: a plataforma classifica e apresenta o
    score, não o produz.

## Estado atual

O projeto está **em reconstrução**. Nasceu como um monolito Reflex sobre
PostgreSQL; o Reflex e o Postgres foram removidos, e a aplicação está sendo
remontada como monorepo — backend FastAPI e frontend Vite — sobre o Google Cloud.

Já funciona: validação e processamento do CSV, carga no BigQuery, geração do
relatório por IA e as regras de negócio (classificação de risco, KPIs, formatação,
validação de CPF/CNPJ).

Ainda não existe: Firestore, Firebase Auth, Redis e os endpoints. Veja
[O que falta](pendencias.md).
