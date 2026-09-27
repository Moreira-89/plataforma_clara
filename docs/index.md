# Visão Geral

Plataforma de transparência e análise de risco para **FIDCs** (Fundos de
Investimento em Direitos Creditórios).

Projeto acadêmico (FIAP).

## O problema

Um FIDC reúne o dinheiro de vários investidores e aplica em recebíveis —
direitos de receber pagamentos que empresas têm a receber de terceiros. Quem
decide onde alocar esse dinheiro é a gestora do fundo. Quem tem o dinheiro
aplicado é o investidor.

O investidor, hoje, enxerga pouco além de um extrato. Não sabe, sem perguntar,
em quais empresas o dinheiro dele está, qual o risco de cada uma, nem como
isso mudou desde o último relatório. A informação existe — a gestora a tem —
mas não chega ao investidor de um jeito que ele consiga consultar sozinho.

## A ideia

Dar ao investidor uma visão direta e sempre atualizada de onde o dinheiro dele
está: agregado por **Bloco de Liquidez** (um agrupamento de risco/setor), com
o volume alocado, o score de risco de cada empresa por trás do bloco, e um
relatório em PDF que explica a carteira em linguagem natural, gerado por IA a
partir dos dados reais daquele investidor — não um relatório genérico.

O nome do produto é literal: **Clara** é a promessa de que o investidor vê o
que a gestora já vê, sem intermediário escondendo a informação.

## Stakeholders

| Quem | O que quer da plataforma |
| --- | --- |
| **Investidor** | Saber onde o dinheiro está, com que risco, sem precisar pedir para ninguém. |
| **Gestora** | Mostrar essa informação para os investidores sem ter que montar um relatório manual a cada pedido. |
| **Núclea** (ou fonte equivalente) | Fornece o score de risco de cada empresa — a plataforma não calcula esse número, só o apresenta. |

## O que a plataforma não é

Não é uma ferramenta de gestão de carteira, nem decide onde alocar recursos —
isso continua sendo trabalho da gestora. A plataforma só **expõe**, de forma
clara e verificável, uma decisão que já foi tomada. Não há modelo de machine
learning no repositório: o score de risco é um dado de entrada, não um
cálculo da plataforma.

## Estado do projeto

O projeto está em reconstrução ativa — a implementação técnica muda com
frequência. Para o estado atual do que já existe e do que falta, ver o
[Roadmap](roadmap/index.md). Este documento (Visão Geral) descreve o problema e a
ideia, que não mudam a cada sprint.
