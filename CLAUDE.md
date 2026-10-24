# CLAUDE.md — plataforma_clara

## Visão Geral

A Plataforma Clara reduz a assimetria de informação entre gestoras e investidores em FIDCs (Fundos de Investimento em Direitos Creditórios). Investidores acessam dashboard com score de risco, visualização de Blocos de Liquidez e relatórios em PDF gerados por IA. Projeto acadêmico (FIAP).

**Como os dados dos aportes chegam à plataforma ainda não foi decidido.** O upload manual de CSV pela gestora foi removido de propósito — não faz sentido operacionalmente. A ideia é consultar direto algum serviço que já tenha esses dados, mas isso não está desenhado. Não invente esse fluxo.

**Monorepo em reconstrução.** O projeto nasceu como monolito Reflex; o Reflex e o Postgres foram removidos, e a aplicação está sendo remontada como backend FastAPI + frontend Vite, sobre GCP.

## Comandos

```bash
# Backend (o .venv fica na raiz do repositório, onde o editor o procura)
python -m venv .venv && source .venv/bin/activate   # Python 3.12
cd backend
pip install -r requirements.txt
cp .env.example .env          # preencher antes de subir
uvicorn main:app --reload     # http://localhost:8000/docs

ruff check ..                 # lint (config no pyproject.toml da raiz)

# Frontend
cd frontend
npm install
npm run dev                   # http://localhost:5173

# Tudo junto: backend (8000), frontend (5173), RedisInsight (8001), docs (8080)
docker compose up --build
docker compose up docs      # só a documentação
```

Use Python 3.12. O `requirements.txt` fixa `pandas~=2.3.3`, que não tem wheel para 3.14 — a instalação falha ao compilar dependências transitivas.

**O projeto não tem testes automatizados**, por decisão do dono (o projeto é acadêmico e testes unitários não importam agora). A pasta `backend/tests/`, o `pytest.ini` e as dependências do pytest foram removidos. Não recriar testes sem pedido; a CI só roda o lint (`ruff check ..`).

## Arquitetura

Dois serviços independentes no mesmo repositório, cada um com o seu `Dockerfile`, para virarem dois serviços separados no Railway. O frontend fala com o backend por HTTP, usando a URL pública do serviço. Em desenvolvimento, o proxy do Vite atende `/api`; o CORS libera as origens de `CORS_ORIGENS` (em produção, a URL do frontend).

```
┌──────────────┐        HTTP        ┌──────────────┐
│  frontend/   │ ─────────────────▶ │  backend/    │
│  Vite+nginx  │                    │  FastAPI     │
└──────────────┘                    └──────┬───────┘
                                           │
        ┌──────────────┬─────────────┬─────┴────────┐
        ▼              ▼             ▼              ▼
   Firebase Auth   Firestore     BigQuery        Redis
   (identidade)   (operacional)  (analítico)     (cache)
                                      │
                                      ▼
                                 ChatGroq → relatório PDF
```

Dentro do backend a direção das dependências é regra dura:

```
api/ ──▶ agents/ · storage/ ──▶ domain/
(entrega)  (orquestração/IO)  (regras puras)
```

- **`domain/`** — regras de negócio puras. **Não pode importar `fastapi`, nem `agents/`, `api/` ou `storage/`.** É o que atravessa qualquer troca de stack intacto.
- **`api/`** — endpoints, schemas de entrada/saída e dependências do FastAPI. Só orquestra.
- **`agents/`** — tudo de IA: prompt, chamada ao LLM, montagem do relatório.
- **`storage/`** — clientes de persistência e credenciais (BigQuery, Firebase e Firestore; Redis a entrar).
- **`config/`** — `settings.py` é o **único** lugar que lê variável de ambiente.
- **`jobs/`** — tarefas de fundo e agendadas.

## Stack

| Camada | Tecnologia |
|---|---|
| Hospedagem | Railway (dois serviços: backend e frontend) |
| API | FastAPI + uvicorn |
| Frontend | Vite, servido por nginx |
| Autenticação | Firebase Auth (perfil na claim `perfil`) |
| Dados operacionais | Firestore (só identidade: perfil e CPF/CNPJ) |
| Dados analíticos | Google BigQuery (dataset em `BIGQUERY_DATASET`) |
| Cache | Redis *(a implementar)* |
| LLM | ChatGroq via Langchain |
| PDF | `markdown-pdf` |
| Dados | pandas |
| Score | Nenhum modelo de ML no repositório — o score é o Score de Reputação Clara (perfil público), calculado no BigQuery com dados públicos da CVM (`dados_fidc.tb_score_empresas`) e lido de `backend/dados/scores_empresas.csv` |

## Estrutura de Diretórios

```
backend/
  main.py                  # cria o app e monta o lifespan. Só montagem.
  Dockerfile
  requirements.txt
  .env.example
  app/
    agents/                #   IA: relatorio.py, prompt.py (todos os prompts), analise_carteira.py (números do relatório), layout_pdf.py (design do PDF) e assets (fontes, logo)
    api/lifespan.py        #   ciclo de vida da aplicação
    api/endpoints/         #   saude, auth, dashboard, blocos, empresas, investimentos, relatorios
    api/dependencias.py    #   usuário do token e controle de acesso por perfil
    api/carteira.py        #   carteira do investidor (blocos investidos, valor e empresas)
    api/schemas/           #   contratos Pydantic de entrada e saída
    config/                #   settings.py (env) e logging.py
    domain/                #   risco, metricas, painel, formatacao, identidade, blocos, investimentos, relatorios, erros
    jobs/                  #   criar_gestora.py e criar_tabelas_blocos.py (CLIs)
    storage/               #   bigquery, empresas, blocos, painel, scores, firebase (token + Firestore), usuarios, credenciais
  dados/                   # scores_empresas.csv e scores_empresas_historico.csv (Score de Reputação Clara e o histórico mensal, exportados do BigQuery, lidos por storage/scores.py)
frontend/
  Dockerfile               # build Node → nginx
  vite.config.js           # proxy /api em dev; lista as páginas do build
  index.html               # home
  paginas/                 # uma pasta por área, um HTML por tela
    login.html               # Entrar e Criar conta, numa tela dividida (cadastro.html só redireciona para login.html?modo=cadastro)
    gestora/visao-geral.html, gestao-blocos.html   # visão geral (gráficos de mercado, blocos, setores e alertas); a gestão inclui o pop-up de criação de bloco
    investidor/visao-geral.html, blocos-de-liquidez.html, blocos-investidos.html, relatorio.html
  src/css/                 # tokens, base, movimento (animações), componentes e cubo (principal.css junta tudo)
    paginas/               #   um CSS por tela ou grupo de telas
  src/js/nucleo/           # api, firebase, rotas, ui, menu — usados por todas as telas
  src/js/paginas/          # um script por tela (espelha paginas/)
  src/img/
  .env.example
docs/                      # documentação MkDocs
mkdocs.yml
docker-compose.yml         # backend + frontend + redis-stack + docs
pyproject.toml             # config do ruff, repositório inteiro
pyrightconfig.json         # extraPaths para o editor resolver `from app...`
.vscode/settings.json      # interpretador
```

## Pontos de Atenção

Instruções do dono do projeto. Valem sobre qualquer padrão default.

- **Comentário no código é curto** — no máximo uma linha, dizendo o que aquele trecho faz. Explicação longa (o porquê de uma decisão, histórico, armadilha conhecida) vai para markdown em `docs/`. Não encher arquivo de comentário.
- **Mudanças grandes estão autorizadas.** O projeto é acadêmico, ainda sem usuários. Apagar pasta, remover biblioteca, refazer camada inteira: pode. Não travar pedindo confirmação a cada passo, não repetir aviso de risco já respondido, e não tratar como perda o trabalho que vai ser refeito.
- **Conferir o disco, não só o Git.** `git ls-files` não mostra diretório vazio, porque o Git não versiona diretório. Depois de remover coisa, verificar com `find`/`ls` — é o que o editor mostra.
- **O `.env` fica em `backend/`**, não na raiz. Junto com o `.env.example` de cada serviço.
- **`docs/` é MkDocs**, servido em <http://localhost:8080>. A organização atual é provisória e vai mudar.

## Convenções de Código

- **Docstrings obrigatórias** em todo módulo: resumo, seção "COMO FUNCIONA" com passos numerados, `Args`, `Returns`, `Raises`. A restrição de tamanho acima vale para comentários, não para docstrings.
- **Logs**: sempre `logging.getLogger(__name__)`. Nunca `print()`.
- **I/O bloqueante** (BigQuery, Groq, Firestore): sempre dentro de `asyncio.to_thread` quando chamado de código assíncrono.
- **Regra de negócio**: mora em `domain/`. Endpoint só orquestra — se um cálculo aparece dentro de um handler, está no lugar errado.
- **Configuração**: só `config/settings.py` lê o ambiente. Nenhum `os.getenv` espalhado.

## Restrições Rígidas

- Nunca commitar `.env` ou credenciais de service account. Não manter arquivo de credencial na raiz do repositório — o `COPY . .` do Docker o levaria para dentro da imagem.
- Nunca reintroduzir número inventado como se fosse dado real. A evolução do AUM, o rendimento projetado e a rentabilidade por bloco eram fatores fixos e um hash do nome do bloco, exibidos ao lado de números reais sem rótulo. Foram removidos. Fora dos dados de demonstração, ou vêm de dado real, ou vão rotulados como estimativa.
- **Exceção, por decisão do dono do projeto:** os dados de demonstração (empresas geradas com Faker, blocos de exemplo, a carteira de investimentos de cada investidor e o rendimento mensal dos últimos 12 meses dela, ambos sorteados de forma estável em `domain/investimentos.py`) são fictícios e o front-end **não** os rotula (nenhuma tela traz aviso de dado fictício). A documentação, o README e a apresentação declaram que são fictícios. Nenhum outro número inventado pode aparecer nas telas.
- A régua de 22 notas (AAA a D, faixas iguais de ~4,55 pontos) existe em três lugares e precisa ficar idêntica: `domain/risco.py`, a tabela `dados_fidc.tb_escala_notas` no BigQuery (o painel da gestora lê a nota dos blocos de lá) e a tabela do `agents/prompt.py`. Mudou um, muda os três.
- Nunca implementar autenticação própria: quem cuida de identidade e senha é o Firebase. O backend verifica o token e lê as claims.
- Nunca chamar a API do Groq fora de `agents/relatorio.py` — é o único lugar com o retry progressivo (4 tentativas com cortes crescentes no texto de referência, nas movimentações e nas empresas enviadas à IA) tratado para `APIStatusError` 413. O modelo recebe só `conteudo_oficial` (números calculados por `agents/analise_carteira.py`); o limite do Groq gratuito é 8.000 tokens por minuto.
- Nunca importar camada de entrega dentro de `domain/`. É essa regra que faz trocar de stack ser uma troca, e não uma reescrita.
- Nunca assumir que existe modelo de ML no projeto: o score de risco é um dado de entrada (hoje, o CSV exportado do BigQuery), não um cálculo da plataforma. O modelo real (Random Forest de 0 a 100) é uma ideia do grupo, ainda sem código.

## Variáveis de Ambiente

Cada serviço tem o seu modelo: `backend/.env.example` e `frontend/.env.example`. O `.env` real nunca entra no repositório.

```
GOOGLE_APPLICATION_CREDENTIALS={"type": "service_account", ...}  # ou caminho de arquivo
PROJECT_ID=plataforma-clara
BIGQUERY_DATASET=tabelas_silvers                                 # tabelas de blocos
BIGQUERY_DATASET_EMPRESAS=dados_fidc                             # cadastro de empresas (tb_empresas_fidc)
CORS_ORIGENS=http://localhost:5173                               # separadas por vírgula
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=gsk_...
LLM_MODEL_NAME="groq:openai/gpt-oss-120b"
LLM_TEMPERATURE=0.1
```

Não criar variável de ambiente nova sem que algo a consuma.

## O Que Ainda Não Existe

Não invente que existe. Nesta ordem:

1. **Fonte dos dados de aportes.** O upload de CSV foi removido de propósito (não é assim que a plataforma vai operar). Ainda não existe nenhum mecanismo que traga esses dados para a plataforma — nem CSV, nem consulta a serviço externo, nada. É a decisão mais urgente em aberto.
2. **Investimento real.** O botão "Alocar dinheiro" só mostra uma confirmação e não grava nada; os "Blocos Investidos" vêm de uma carteira de demonstração. Como o investidor aporta de verdade não foi definido.
3. **Endpoints do produto** — funcionam `GET /health`, `/auth/*`, `/blocos` (etiquetas, criar, listar e detalhar), `GET /empresas` e `GET /investimentos`, `/investimentos/resumo`, `/investimentos/empresas` e `/investimentos/rendimento` (carteira e rendimento de demonstração) e `/relatorios` (pedir, consultar o estado e baixar o PDF); a busca de empresas lê `dados_fidc.tb_empresas_fidc`. O relatório por IA usa a carteira de demonstração do investidor (a mesma fonte do cubo e do ranking da visão geral), e os PDFs ficam só em memória do processo. `GET /dashboard/gestora` devolve a visão geral da gestora (views da CVM e `vw_blocos_score`, no BigQuery); `/dashboard/investidor` exige o perfil certo, mas responde 501 até ter fonte de dados.
4. **Redis** — declarado no compose, sem cliente na aplicação.
5. **Score de risco.** O score vem do Score de Reputação Clara, versão perfil público (v0.1.1), calculado com dados públicos da CVM: cada empresa fictícia recebe o perfil de um cedente real do mesmo setor. Falta o grupo validar os pesos (40/25/20/15) e a trava de risco, e versionar no repositório os SQLs que geram o score. O modelo de machine learning que o grupo imagina não existe, nem o histórico de aportes que ele usaria.
6. **Agregações do dashboard** — `domain/metricas.py` tem as regras de consolidação, mas nada as alimenta. Depende do item 1.
7. **Chatbot.** A interface do "Assistente Clara" existe na Visão geral, sem LLM e sem endpoint (o ponto de ligação é `responder` em `frontend/src/js/paginas/investidor/chat.js`).
8. **Persistência dos relatórios.** Os PDFs ficam só em memória do processo (`storage/relatorios.py`) e somem ao reiniciar; falta guardá-los em storage.
