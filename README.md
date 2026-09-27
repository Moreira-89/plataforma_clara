# Plataforma Clara

> Plataforma de transparência e análise de risco para FIDCs (Fundos de Investimento em Direitos Creditórios), conectando gestoras e investidores com score de risco, visualização de Blocos de Liquidez e relatórios gerados por IA.

Projeto acadêmico (FIAP).

---

## Documentação

Este repositório é um monorepo — `backend/` (FastAPI) e `frontend/` (Vite) —
em reconstrução ativa. Toda a documentação (o problema que o produto resolve,
como ele funciona, a arquitetura escolhida e o roadmap) vive em `docs/`,
publicada com MkDocs:

```bash
docker compose up docs   # http://localhost:8080
```

- **Visão Geral** — o problema, a ideia, os stakeholders.
- **Produto** — como a plataforma funciona, sem tecnologia.
- **Arquitetura** — stack, infraestrutura, diagrama, backend, e como rodar o projeto.
- **Roadmap** — o que está em andamento e o que é backlog.

## Como rodar

```bash
docker compose up --build
```

Detalhes de setup, variáveis de ambiente e comandos de teste estão em
**Arquitetura → Desenvolvimento**, dentro da documentação acima.
