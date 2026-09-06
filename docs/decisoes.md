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

## Firestore em vez de PostgreSQL

**Decisão:** o banco operacional passa a ser o Firestore.

**Por quê:** concentrar o ecossistema no Google Cloud, junto do Firebase e do
BigQuery, simplificando credenciais e integrações.

**Consequência:** saíram o Alembic e todo o histórico de migrações, o SQLModel, o
SQLAlchemy, o psycopg2 e os repositórios. As agregações do dashboard, que eram
`GROUP BY` em SQL, precisam ser refeitas.

!!! warning "O que reconsiderar"
    A consulta central do produto é agregação: soma de volume e média de score por
    bloco. Isso é o que SQL faz bem e o que Firestore não faz — lá a agregação
    vira código na aplicação ou consulta ao BigQuery. Se o dashboard ficar lento
    ou o código de agregação ficar complexo, esta é a decisão a revisitar.

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
