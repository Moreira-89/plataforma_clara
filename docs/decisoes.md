# Decisões

Registro curto do que foi decidido e por quê. Serve para não redebater o que já
foi resolvido — e para saber o que reconsiderar quando o contexto mudar.

## Sair do Reflex

**Decisão:** remover o Reflex e reconstruir como API + frontend separado.

**Por quê:** o Reflex acopla UI e servidor no mesmo processo e no mesmo modelo de
estado. Não dá para escalar as duas partes de forma independente, nem trocar uma
sem mexer na outra, nem ter um app móvel depois.

**Custo:** todas as telas foram descartadas e serão reescritas.

## Firebase Auth em vez de autenticação própria

**Decisão:** identidade, senha e emissão de token são do Firebase. O backend só
verifica a assinatura e lê as claims.

**Por quê:** a implementação anterior guardava hash bcrypt numa tabela própria,
sem token, sem refresh, sem recuperação de senha e sem login social. Cada um
desses itens é trabalho e risco que não agregam nada ao produto.

**Consequência:** sumiram o `bcrypt`, o serviço de autenticação e a coluna de
hash. O registro do usuário fica só com o vínculo entre o `uid` do Firebase e o
CPF/CNPJ do investidor, que é a chave dos aportes.

## PostgreSQL sai, sem Firestore no lugar dos aportes

**Decisão:** o banco operacional (Postgres) saiu e **não foi substituído por
Firestore** para os dados de aportes. Firestore, se entrar, fica restrito ao
vínculo Firebase UID ↔ CPF/CNPJ do investidor — e pode nem precisar de banco
separado, se esse vínculo virar custom claim no próprio token do Firebase.

**Por quê:** Firestore não agrega no servidor (sem `GROUP BY`); a consulta
central do produto é exatamente agregação — soma de volume e média de score
por bloco. Faria o time reimplementar em Python o que SQL já faz bem.

**Consequência:** saíram o Alembic e todo o histórico de migrações, o SQLModel,
o SQLAlchemy, o psycopg2 e os repositórios. **BigQuery vira a ferramenta de
consulta do dashboard** — ver a decisão seguinte sobre como.

## CSV removido; fonte dos dados de aportes em aberto

**Decisão:** o fluxo de a gestora subir um CSV foi removido do projeto por
completo — código, testes, documentação.

**Por quê:** não é assim que a plataforma vai operar com usuários reais. Pedir
para a gestora repetir um processo manual toda vez não escala nem faz sentido
operacional; a ideia é consultar direto algum serviço que já tenha esses
dados.

**Consequência:** `ingestion/` (processamento e carga do CSV) foi apagado
inteiro. Nada escreve mais em `tb_aporte` no BigQuery — inclusive
`agents/relatorio.py`, que consulta essa tabela, está com uma dependência
quebrada até essa decisão ser tomada.

!!! warning "Decisão em aberto — a mais urgente do projeto"
    Como os dados chegam à plataforma ainda não foi desenhado: qual serviço
    consultar, com que frequência, e como esses dados viram consulta no
    BigQuery. Nada deve ser implementado por cima disso (endpoints, dashboard)
    antes de resolver este ponto.

## BigQuery como ferramenta de consulta — AD-6

**Decisão:** o dashboard lê o BigQuery via tabela(s) "gold", recriadas sob
demanda (não em tempo real, não por job agendado sozinho). Registrado como
**AD-6** no roadmap do Notion.

**Por quê:** BigQuery faz `GROUP BY` de verdade, no banco — é o que ele foi
feito para fazer. Recriar sob demanda evita depender de agendamento (menos
infraestrutura a configurar) e ainda assim mantém uma cópia agregada barata
de ler, em vez de agregar a base inteira a cada carregamento de tela.

**Deliberadamente não decidido ainda:** quantas tabelas gold (uma por
consulta vs. uma granular com `GROUP BY` leve por cima) e se a recriação
também dispara automaticamente depois de cada carga de dado nova. Adiado de
propósito — o time vai mexer bastante no dashboard, e desenhar isso antes
disso estabilizar seria trabalho jogado fora. Depende da decisão anterior
(fonte dos dados) estar resolvida primeiro.

## Railway para hospedagem

**Decisão:** dois serviços no Railway, um para cada pasta do monorepo.

**Por quê:** já existe plano contratado. Cada serviço aponta o *root directory*
para `backend/` ou `frontend/` e builda o Dockerfile correspondente.

## Números simulados removidos

**Decisão:** apagar a evolução do AUM, o rendimento projetado e a rentabilidade
por bloco.

**Por quê:** não vinham de dado nenhum. Eram fatores fixos aplicados sobre o valor
atual e um hash SHA-1 do nome do bloco convertido em percentual. Apareciam na tela
ao lado de números reais, sem rótulo que os distinguisse.

**Regra que fica:** se a tela nova precisar desses campos, ou vêm de dado real, ou
vão rotulados como estimativa. Numa plataforma que se vende como transparência,
número inventado sem rótulo é o pior defeito possível.
