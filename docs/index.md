# Visão Geral

Plataforma de transparência e análise de risco para **FIDCs** (Fundos de
Investimento em Direitos Creditórios).

Projeto acadêmico (FIAP).

## Por onde começar

- **[Negócio](negocio/index.md)** — o que é um FIDC, a "caixa-preta" que a
  plataforma resolve, quem ganha o quê e o impacto no mercado.
- **[Produto](produto/index.md)** — o que cada perfil vê e faz na plataforma.
- **[Arquitetura](arquitetura/index.md)** — como a plataforma é construída.
- **[Roadmap](roadmap/index.md)** — o que está em andamento e o que vem depois.

## Em poucas palavras

Um FIDC reúne o dinheiro de vários investidores e aplica em recebíveis. Quem
decide onde alocar esse dinheiro é a gestora do fundo; quem tem o dinheiro aplicado
é o investidor, que hoje enxerga pouco além de um extrato. A Plataforma Clara
funciona como uma lente de aumento: dá ao investidor uma visão direta e sempre
atualizada de onde o dinheiro dele está. Detalhes em
[O problema](negocio/problema.md) e [A solução](negocio/solucao.md).

## Stakeholders

| Quem | O que quer da plataforma |
| --- | --- |
| **Investidor** | Saber onde o dinheiro está, com que risco, sem precisar pedir para ninguém. |
| **Gestora** (hoje, a Núclea) | Mostrar essa informação para os investidores sem ter que montar um relatório manual a cada pedido. |

## O que a plataforma não é

Não é uma ferramenta de gestão de carteira, nem decide onde alocar recursos —
isso continua sendo trabalho da gestora. A plataforma só **expõe**, de forma
clara e verificável, uma decisão que já foi tomada. O score de risco é a
previsão de um modelo de machine learning; hoje o modelo não está no
repositório e o score entra como dado pronto.

## Estado do projeto

O projeto está em reconstrução ativa — a implementação técnica muda com
frequência. Para o estado atual do que já existe e do que falta, ver o
[Roadmap](roadmap/index.md). Este documento (Visão Geral) descreve o problema e a
ideia, que não mudam a cada sprint.
