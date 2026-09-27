# Plataforma Clara

Plataforma de transparência e análise de risco para **FIDCs** (Fundos de
Investimento em Direitos Creditórios), ligando gestoras e investidores.

Projeto acadêmico (FIAP).

## O problema

Quem investe num FIDC costuma não saber onde o próprio dinheiro está. A gestora
tem os dados; o investidor recebe um extrato. A plataforma reduz essa assimetria.

## O que ela faz

**O investidor** enxerga a carteira agregada por Bloco de Liquidez — volume
alocado, score médio de risco e as empresas sacadas por trás de cada bloco — e
pode gerar um relatório consolidado em PDF, escrito por um LLM a partir dos dados
reais da própria carteira.

!!! note "O score não é calculado aqui"
    O `score_risco_interno` **chega pronto**, calculado por fora. Não existe
    modelo de machine learning no repositório: a plataforma classifica e
    apresenta o score, não o produz.

!!! warning "Como os dados dos aportes chegam: ainda não decidido"
    A gestora não sobe mais CSV — esse fluxo foi removido de propósito, não é
    assim que a plataforma vai operar de verdade. O que substitui isso (consultar
    algum serviço externo que já tenha esses dados) não está desenhado. Veja
    [O que falta](pendencias.md).

## Estado atual

O projeto está **em reconstrução**. Nasceu como um monolito Reflex sobre
PostgreSQL; o Reflex e o Postgres foram removidos, e a aplicação está sendo
remontada como monorepo — backend FastAPI e frontend Vite — sobre o Google Cloud.

Já funciona: o gerador de relatório por IA e as regras de negócio (classificação
de risco, KPIs, formatação, validação de CPF/CNPJ).

Ainda não existe: nenhuma fonte de dados de aportes, Firestore, Firebase Auth,
Redis, CORS e os endpoints — nem `/health`. Veja [O que falta](pendencias.md).
