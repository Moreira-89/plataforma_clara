# Plataforma Clara — Documentação Técnica

> Plataforma de transparência e análise de risco para FIDCs (Fundos de Investimento em Direitos Creditórios), conectando Gestoras e Investidores com score preditivo, dashboards interativos e relatórios gerados por IA.

---

## Índice

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura do Sistema](#2-arquitetura-do-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Estrutura do Projeto](#4-estrutura-do-projeto)
5. [Fluxos Principais](#5-fluxos-principais)
6. [Banco de Dados](#6-banco-de-dados)
7. [Serviços Externos](#7-serviços-externos)
8. [Configuração e Variáveis de Ambiente](#8-configuração-e-variáveis-de-ambiente)
9. [Como Executar](#9-como-executar)
10. [Padrões de Código](#10-padrões-de-código)

---

## 1. Visão Geral

A **Plataforma Clara** resolve um problema crítico do mercado de FIDCs: a assimetria de informação entre gestoras e investidores. A gestora pode fazer upload de dados de alocação via CSV, e os investidores têm acesso a um dashboard personalizado com:

- Score de risco preditivo (**Score Nuclea**) por empresa sacada
- Visualização dos **Blocos de Liquidez** onde seu capital está alocado
- **Relatórios consolidados em PDF**, gerados por IA com análise de risco

### Perfis de Usuário

| Perfil | Acesso | Funcionalidades |
|--------|--------|-----------------|
| **Gestora** | Portal da Gestora | Upload de CSVs, visão geral do FIDC, gráficos de AUM |
| **Investidor** | Portal do Investidor | Portfólio pessoal, exploração de blocos, download de relatórios PDF |

---

## 2. Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Reflex UI)                         │
│  pages/     ←  components/sidebar.py  ←  states/  ←  services/    │
│  (Páginas)     (Componentes reutilizáveis)  (Estado)  (I/O externo) │
└────────────────────────────┬────────────────────────────────────────┘
                             │ WebSocket (estado reativo)
┌────────────────────────────▼────────────────────────────────────────┐
│                  BACKEND (Reflex Server — FastAPI)                  │
│                     Event Handlers + @rx.event                      │
└──────┬──────────────────────────────────────────┬───────────────────┘
       │                                          │
┌──────▼───────┐                        ┌────────▼────────┐
│  PostgreSQL   │                        │   Google BigQuery │
│  (Supabase)   │                        │  plataforma-clara │
│  tb_usuario   │                        │  dados_fidc.tb_   │
│  tb_aporte    │                        │  aporte           │
└───────────────┘                        └──────────────────┘
                                                  │
                                         ┌────────▼────────┐
                                         │   ChatGroq API   │
                                         │  (LLaMA 3 70B)  │
                                         │  Geração de PDF  │
                                         └──────────────────┘
```

### Princípios Arquiteturais

- **Full-stack Python único**: O Reflex compila o frontend em React + WebSocket e expõe o backend via FastAPI — tudo escrito em Python.
- **Estado reativo**: As variáveis de `rx.State` são sincronizadas automaticamente entre o servidor e o browser via WebSocket.
- **Async-first**: Operações I/O (banco, BigQuery, Groq) são sempre executadas em `asyncio.to_thread` para não bloquear o event loop.
- **Dupla persistência**: Cada aporte é salvo no PostgreSQL (consultas OLTP e autenticação) **e** no BigQuery (analytics e agregações OLAP).

---

## 3. Stack Tecnológico

| Camada | Tecnologia | Versão / Detalhes |
|--------|-----------|-------------------|
| Framework | [Reflex](https://reflex.dev) | Full-stack Python (compila para React + FastAPI) |
| Banco de dados principal | PostgreSQL via [Supabase](https://supabase.com) | ORM: SQLAlchemy (embutido no Reflex) |
| Banco de dados analítico | [Google BigQuery](https://cloud.google.com/bigquery) | Dataset `dados_fidc`, tabela `tb_aporte` |
| IA / LLM | [ChatGroq](https://console.groq.com) — LLaMA 3 70B | Geração de análise de risco em texto |
| Geração de PDF | [WeasyPrint](https://weasyprint.org) | Converte Markdown/HTML para PDF binário |
| Processamento de dados | [Pandas](https://pandas.pydata.org) | Normalização e limpeza dos CSVs |
| Autenticação | [bcrypt](https://pypi.org/project/bcrypt/) | Hash seguro de senhas (12 rounds) |
| Ícones | [Lucide Icons](https://lucide.dev) | Embutido no Reflex via `rx.icon()` |
| Design System | [Radix UI](https://www.radix-ui.com) | Tokens de cor via `rx.color()` |

---

## 4. Estrutura do Projeto

```
plataforma_clara/
├── plataforma_clara.py          # Entry point: registro de rotas e instanciação do app
├── rxconfig.py                  # Configurações do Reflex (DB URL, app name)
│
├── model/
│   └── schemas.py               # Modelos SQLAlchemy: tb_usuario, tb_aporte
│
├── states/
│   ├── autenticacao_state.py    # Login, logout, sessão do usuário logado
│   ├── cadastro_usuario_state.py # Cadastro: validação de CPF/CNPJ, hash bcrypt
│   ├── dashboard_state.py       # Estado base: KPIs, gráficos, tabelas (gestora + investidor)
│   ├── explorar_blocos_state.py # Filtros de busca de blocos (herda DashboardState)
│   ├── detalhes_bloco_state.py  # Detalhes de um bloco específico (herda DashboardState)
│   ├── ingestao_dados_state.py  # Upload de CSV → Supabase + BigQuery
│   └── assistente_ia_state.py   # Geração e download de relatório PDF via Groq
│
├── services/
│   ├── bigquery_utils.py        # Singleton do cliente BigQuery + gerenciamento de credenciais
│   ├── dashboard_service.py     # Queries analíticas: métricas de blocos e aportes
│   ├── csv_processor.py         # Limpeza, validação e normalização de CSVs
│   └── relatorio_ia_service.py  # Pipeline: BigQuery → Groq → Markdown → PDF (WeasyPrint)
│
├── components/
│   └── sidebar.py               # Sidebars reutilizáveis: sidebar_gestora(), sidebar_investidor()
│
└── pages/
    ├── pg_home.py               # Landing page pública
    ├── pg_login.py              # Formulário de login
    ├── pg_cadastro_usuario.py   # Formulário de cadastro (gestora ou investidor)
    ├── pg_dashboard_gestora.py  # Dashboard com AUM, gráficos e tabela de aportes
    ├── pg_dashboard_investidor.py # Dashboard com portfólio e tabela de transparência
    ├── pg_ingestao_dados.py     # Upload de CSV e histórico de processamento
    ├── pg_explorar_blocos.py    # Listagem e filtro de blocos disponíveis
    ├── pg_detalhes_bloco.py     # KPIs, composição e empresas de um bloco específico
    └── pg_relatorios.py         # Seleção e geração de relatório consolidado PDF
```

---

## 5. Fluxos Principais

### 5.1 Fluxo de Ingestão de Dados (CSV → Supabase + BigQuery)

```
Gestora faz upload do CSV
         │
         ▼
IngestaoDadosState.lidar_com_upload_de_arquivo()
         │
         ├─► Valida extensão (.csv) e presença do arquivo
         │
         ├─► asyncio.to_thread(_processar_arquivo)
         │       │
         │       ├─► csv_processor.processar_arquivo_csv()
         │       │       └── Limpeza, tipagem e normalização (Pandas)
         │       │
         │       ├─► rx.session().bulk_insert_mappings(tb_aporte, ...)
         │       │       └── INSERT em lote no PostgreSQL (Supabase)
         │       │
         │       └─► Retorna lista de dicts para BigQuery
         │
         └─► yield IngestaoDadosState.enviar_dados_bigquery(dados)
                 └── background task: client.load_table_from_dataframe()
                         └── Append na tabela dados_fidc.tb_aporte (BQ)
```

### 5.2 Fluxo de Autenticação

```
Usuário submete e-mail + senha
         │
         ▼
AutenticacaoState.fazer_login()
         │
         ├─► asyncio.to_thread(_verificar_credenciais)
         │       │
         │       ├─► SELECT * FROM tb_usuario WHERE email = ?
         │       │
         │       └─► bcrypt.checkpw(senha_plain, hash_armazenado)
         │
         ├─► Armazena documento_usuario_logado no estado (persiste na sessão)
         │
         └─► rx.redirect("/dashboard-investidor" | "/dashboard-gestora")
```

### 5.3 Fluxo de Geração de Relatório IA

```
Investidor clica em "Gerar PDF"
         │
         ▼
AssistenteIAState.gerar_e_baixar_relatorio()
         │
         ├─► Recupera documento do investidor via get_state(AutenticacaoState)
         │
         ├─► asyncio.to_thread(gerar_relatorio_consolidado_investidor)
         │       │
         │       ├─► BigQuery: SELECT aportes WHERE documento = ?
         │       │
         │       ├─► Monta contexto (JSON com métricas agregadas)
         │       │
         │       ├─► ChatGroq API: LLaMA 3 70B gera análise em Markdown
         │       │       └── Retry progressivo em caso de token limit error
         │       │
         │       └─► WeasyPrint: converte Markdown → HTML → PDF (bytes)
         │
         └─► yield rx.download(data=pdf_bytes, filename=...)
```

---

## 6. Banco de Dados

### PostgreSQL (Supabase) — Dados Operacionais

#### `tb_usuario`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_usuario` | Integer PK | ID auto-incrementado |
| `tipo_usuario` | String | `"gestora"` ou `"investidor"` |
| `nome_usuario` | String | Nome completo |
| `email_usuario` | String (UNIQUE) | Login único |
| `identificador_usuario` | String | CPF (11 dígitos) ou CNPJ (14 dígitos) |
| `senha_hash_usuario` | String | Hash bcrypt (12 rounds) |

#### `tb_aporte`
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id_aporte_uuid` | String PK | UUID v4 gerado no momento do upload |
| `documento_investidor_cpf_cnpj` | String | CPF/CNPJ do investidor (vinculação) |
| `fundo_origem_id` | String | Identificador do FIDC origem |
| `nome_fundo_investidor` | String | Nome comercial do fundo |
| `empresa_sacada_nome` | String | Empresa financiada (sacada) |
| `cnpj_sacado_limpo` | String | CNPJ da empresa sacada (somente dígitos) |
| `valor_aporte_compra` | Float | Valor de compra do ativo |
| `valor_mercado_atual` | Float | Valor de mercado atualizado |
| `quantidade_papeis_adquiridos` | Float | Quantidade de títulos |
| `data_vencimento` | Date | Vencimento da operação |
| `data_referencia_competencia` | Date | Competência do upload |
| `prazo_vencimento_dias` | Integer | Dias até o vencimento |
| `status_prazo_vencimento` | String | `"Vencido"`, `"A vencer"` etc. |
| `taxa_retorno_pre_fixada` | Float | Taxa de retorno pré-fixada |
| `bloco_liquidez_setorial` | String | Nome do bloco de liquidez |
| `categoria_tecnica_ativo` | String | Categoria do ativo (ex: Recebível) |
| `codigo_identificacao_isin` | String | Código ISIN do ativo |
| `score_risco_interno` | Float | Score Nuclea (0–100) |
| `flag_outlier_valor` | String | Flag de outlier detectado pelo CSV processor |

### BigQuery — Analytics e Relatórios

- **Projeto:** `plataforma-clara`
- **Dataset:** `dados_fidc`
- **Tabela:** `tb_aporte` (schema idêntico ao PostgreSQL, com datas como STRING ISO 8601)
- **Operação:** `WRITE_APPEND` — novos registros são acumulados a cada upload

---

## 7. Serviços Externos

### BigQuery (`services/bigquery_utils.py`)
- Gerencia credenciais via variável de ambiente `GOOGLE_APPLICATION_CREDENTIALS` (JSON string ou caminho de arquivo)
- Implementa padrão Singleton para evitar múltiplas instâncias do cliente por processo

### ChatGroq (`services/relatorio_ia_service.py`)
- Modelo: `llama3-70b-8192` (8.192 tokens de contexto)
- Implementa retry progressivo: em caso de `RateLimitError` de tokens, reduz o contexto enviado em 20% por tentativa (máximo 3 tentativas)
- Temperatura 0 para máxima determinismo nas análises de risco

### Dashboard Service (`services/dashboard_service.py`)
- Executa queries analíticas no PostgreSQL (SQLAlchemy ORM)
- `buscar_metricas_blocos_liquidez`: total alocado, score médio e quantidade de aportes por bloco (com filtro opcional por CPF de investidor)
- `buscar_metricas_gerais_gestora`: visão geral sem filtro por investidor
- `buscar_tabela_aportes_gestora`: top 50 aportes ordenados por valor de mercado

---

## 8. Configuração e Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto ou exporte as variáveis no shell:

```bash
# Conexão com o PostgreSQL (Supabase)
DATABASE_URL=postgresql://postgres:[SENHA]@[HOST]:5432/postgres

# Credenciais do Google Cloud (BigQuery)
# Opção A: JSON completo como string (ideal para deploy em PaaS)
GOOGLE_APPLICATION_CREDENTIALS='{"type": "service_account", "project_id": "plataforma-clara", ...}'

# Opção B: Caminho para arquivo JSON local (ideal para desenvolvimento)
GOOGLE_APPLICATION_CREDENTIALS=/caminho/para/service-account.json

# Chave de API do Groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### `rxconfig.py`

```python
import reflex as rx

config = rx.Config(
    app_name="plataforma_clara",
    db_url=os.environ.get("DATABASE_URL"),
)
```

---

## 9. Como Executar

### Pré-requisitos

- Python 3.11+
- Conta no Supabase com o banco configurado
- Service Account do Google Cloud com permissão `bigquery.dataEditor`
- Chave de API do Groq

### Instalação

```bash
# Clone o repositório
git clone https://github.com/Moreira-89/plataforma_clara.git
cd plataforma_clara

# Crie e ative o ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais
```

### Executar em Desenvolvimento

```bash
reflex run
# Acesse: http://localhost:3000
```

### Inicializar o Banco de Dados

```bash
# O Reflex cria as tabelas automaticamente na primeira execução
# (via rx.Model + SQLAlchemy metadata.create_all)
reflex db init
reflex db migrate
reflex db upgrade
```

---

## 10. Padrões de Código

### Documentação (obrigatório em todos os módulos)

Todo arquivo segue o padrão `@user_global`:

```python
# -----------------------------------------------------------------------------
# NOME DA SEÇÃO (Ex: INICIALIZAÇÃO, ENDPOINTS, ROTINAS DE BANCO)
# -----------------------------------------------------------------------------

def minha_funcao(arg: str) -> str:
    """
    Resumo principal da função.

    COMO FUNCIONA:
        1. Passo Um — Descrição do que acontece e por quê.
        2. Passo Dois — Justificativa técnica da decisão.
        3. Passo Três — Comportamento em caso de erro.

    Args:
        arg (str): Descrição do parâmetro e valores esperados.

    Returns:
        str: Descrição do retorno e formato.

    Raises:
        ValueError: Quando acontece X.
    """
    # --- 1. PASSO UM ---
    # Comentário inline explicando o "porquê", não apenas o "o quê".
```

### Padrões de UI (Reflex)

- **Cores**: sempre usar tokens `rx.color("gray", 12)` — nunca hexadecimais hardcoded
- **Badges dinâmicos**: usar `rx.cond` para determinar `color_scheme` reativamente
- **Sidebars**: importar de `components/sidebar.py` (nunca duplicar)
- **Operações pesadas**: sempre em `asyncio.to_thread` para não bloquear a UI

### Logs

Todos os módulos usam `logging.getLogger(__name__)` (nunca `print()`):

```python
logger = logging.getLogger(__name__)
logger.info("Usuário autenticado: %s", email)
logger.warning("Dado ausente no CSV: %s", campo)
logger.exception("Erro inesperado ao processar arquivo.")  # Inclui traceback
```

---

## Licença

Projeto acadêmico — Faculdade. Todos os direitos reservados.
