# Plataforma Clara

> Plataforma de transparência e análise de risco para FIDCs (Fundos de Investimento em Direitos Creditórios), conectando gestoras e investidores com score de risco, visualização de Blocos de Liquidez e relatórios gerados por IA.

Projeto acadêmico (FIAP).

📖 **[Documentação completa](docs/index.md)** — problema, produto, arquitetura e roadmap.
*(link temporário para a pasta do repositório; troca pelo GitHub Pages assim que a branch existir.)*

---

## O problema, em uma frase

Quem investe num FIDC hoje enxerga pouco além de um extrato. A gestora sabe
exatamente onde o dinheiro está e com que risco; o investidor, não — a não
ser que peça. A Clara existe para fechar essa distância: dar ao investidor a
mesma visão que a gestora já tem, agregada por **Bloco de Liquidez**, com
score de risco por empresa e um relatório em PDF gerado por IA a partir dos
dados reais da própria carteira.

O nome é literal: transparência sem intermediário escondendo a informação.

Para o detalhe — o problema por completo, como cada perfil usa a plataforma,
a arquitetura escolhida e por quê, e o que falta implementar — ver a
[documentação](docs/index.md).

---

## Documentação

Este repositório é um monorepo — `backend/` (FastAPI) e `frontend/` (Vite) —
em reconstrução ativa. Toda a documentação vive em `docs/`, publicada com
MkDocs:

```bash
docker compose up docs   # http://localhost:8080
```

- **[Visão Geral](docs/index.md)** — o problema, a ideia, os stakeholders.
- **[Produto](docs/produto/index.md)** — como a plataforma funciona, sem tecnologia.
- **[Arquitetura](docs/arquitetura/index.md)** — stack, infraestrutura, diagrama, backend, e como rodar o projeto.
- **[Roadmap](docs/roadmap/index.md)** — o que está em andamento e o que é backlog.

## Como rodar

```bash
docker compose up --build
```

Detalhes de setup, variáveis de ambiente e comandos de teste estão em
[Arquitetura → Desenvolvimento](docs/arquitetura/desenvolvimento.md).
