# Plataforma Clara

Plataforma web para transparência em FIDCs, com foco em:
- rastreabilidade de aportes por bloco de liquidez,
- dashboards para gestora e investidor,
- geração de relatório institucional em PDF com IA (ChatGroq).

## Visão Geral

A aplicação foi construída com **Reflex** e integra:
- **PostgreSQL/Supabase** para dados operacionais da plataforma,
- **BigQuery** para consulta analítica e histórico de aportes,
- **ChatGroq** para geração de relatório em linguagem natural.

## Principais Funcionalidades

1. **Cadastro e Login**
- Cadastro de usuários (`gestora` e `investidor`) com hash de senha (`bcrypt`).
- Login com sessão no estado do Reflex.

2. **Dashboards**
- Dashboard da gestora com visão global da carteira.
- Dashboard do investidor com visão personalizada por documento logado.

3. **Ingestão de CSV**
- Upload, validação e normalização de colunas obrigatórias.
- Escrita em banco operacional e envio para BigQuery.

4. **Explorar Blocos e Detalhes**
- Filtros de busca/setor/score.
- Página de detalhes por bloco com composição de empresas.

5. **Relatório IA (PDF)**
- Fluxo: `Selecionar -> Gerar -> Download`.
- Relatório consolidado com prompt institucional.
- Exclusão do arquivo temporário após geração/download.

## Arquitetura do Projeto

```text
plataforma_clara/
├─ plataforma_clara/
│  ├─ plataforma_clara.py        # bootstrap e registro de rotas
│  ├─ pages/                     # páginas UI (Reflex)
│  ├─ states/                    # estados e eventos (fluxos da aplicação)
│  ├─ services/                  # integrações e regras de negócio
│  ├─ model/                     # modelos SQLModel/Reflex
│  └─ components/                # componentes compartilhados de UI
├─ alembic/                      # migrações
├─ assets/                       # estáticos
├─ requirements.txt
└─ README.md
```

## Fluxos Técnicos

### 1) Autenticação
- Estado: `AutenticacaoState`
- Arquivo: `plataforma_clara/states/autenticacao_state.py`
- Responsabilidades:
  - valida credenciais com `bcrypt`,
  - normaliza documento do usuário logado,
  - redireciona conforme tipo de usuário.

### 2) Cadastro
- Estado: `CadastroUsuarioState`
- Arquivo: `plataforma_clara/states/cadastro_usuario_state.py`
- Responsabilidades:
  - valida formato de e-mail,
  - valida CPF/CNPJ,
  - aplica hash de senha e persiste usuário.

### 3) Dashboard
- Estado: `DashboardState`
- Serviços: `dashboard_service.py`
- Responsabilidades:
  - carrega métricas por investidor/gestora,
  - calcula KPIs e dados de gráfico,
  - mantém tabelas de transparência/ranking.

### 4) Ingestão de dados
- Estado: `IngestaoDadosState`
- Serviço: `csv_processor.py`
- Responsabilidades:
  - valida schema do CSV,
  - normaliza documentos/datas/números,
  - insere no banco e envia para BigQuery.

### 5) Relatório IA
- Estado: `AssistenteIAState`
- Serviço: `relatorio_ia_service.py`
- Responsabilidades:
  - identifica investidor logado,
  - consulta investimentos (BigQuery),
  - monta payload para prompt institucional,
  - chama ChatGroq e gera PDF com `markdown_pdf`,
  - remove arquivo local após leitura em bytes.

## Rotas da Aplicação

- `/` Home
- `/login-usuario` Login
- `/cadastro` Cadastro
- `/dashboard-gestora` Dashboard da gestora
- `/dashboard-investidor` Dashboard do investidor
- `/ingestao-dados` Ingestão de CSV
- `/explorar-blocos` Catálogo de blocos
- `/detalhes-bloco/[bloco_id]` Detalhes do bloco
- `/relatorios` Relatórios IA

## Configuração de Ambiente

Crie um arquivo `.env` na raiz com as variáveis necessárias:

```env
DATABASE_URL=postgresql://...
GOOGLE_APPLICATION_CREDENTIALS=arquivo-credenciais.json
GROQ_API_KEY=...
```

Observações:
- `DATABASE_URL`: conexão do banco usado pelo Reflex/SQLModel.
- `GOOGLE_APPLICATION_CREDENTIALS`: caminho para JSON de credenciais GCP.
- `GROQ_API_KEY`: chave da API Groq para geração de relatórios.

## Instalação e Execução

1. Criar e ativar ambiente virtual (opcional, recomendado):
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Instalar dependências:
```bash
pip install -r requirements.txt
```

3. Subir aplicação:
```bash
reflex run
```

4. Compilar (validação rápida de páginas/rotas):
```bash
reflex compile
```

## Banco e Migrações

Comandos comuns:

```bash
alembic upgrade head
alembic revision --autogenerate -m "descricao"
```

## Dependências Relevantes

- `reflex`
- `sqlmodel` / `sqlalchemy`
- `pandas`
- `google-cloud-bigquery`
- `langchain-groq` / `langchain-core`
- `markdown-pdf`
- `PyPDF2`
- `bcrypt`

## Padrões Adotados no Código

- Estado/fluxo em `states`, integração externa em `services`.
- Logs estruturados via `logging`.
- Evita `print` em produção.
- Sanitização de documento (somente dígitos) antes de filtro no banco.
- Tratamento de falhas de payload/token em IA com redução progressiva.

## Troubleshooting

### Erro `413 Request too large` (Groq)
- Causa: payload acima do limite de tokens da conta/modelo.
- Mitigação no projeto:
  - compactação de dados enviados ao prompt,
  - tentativas progressivas com payload reduzido,
  - limitação de trecho de referência e amostras.

### PDF de referência não encontrado
- O sistema continua sem bloquear geração.
- Ajuste o caminho/arquivo de referência se quiser usar few-shot completo.

### Sem dados no relatório
- Verifique se o documento do investidor logado existe na base de aportes do BigQuery.
- Valide se as credenciais GCP permitem consulta na tabela configurada.

### Falha no login
- Verifique hash de senha e e-mail normalizado.
- Confira se o usuário existe e se `tipo_usuario` é válido.

## Segurança

- Nunca versionar `.env` com chaves reais.
- Rotacionar credenciais se já foram expostas.
- Restringir permissões das contas de serviço GCP e banco.

## Estado Atual

Projeto funcional com:
- front-end padronizado,
- fluxos críticos operacionais,
- documentação técnica base consolidada.

Para evoluções futuras, recomenda-se adicionar:
- suíte de testes automatizados (unitários + integração),
- observabilidade de jobs assíncronos,
- controle de permissões por perfil de usuário.
