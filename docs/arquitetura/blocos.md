# Blocos de Liquidez (dados e rotas)

Como a criação de um bloco funciona por baixo. A regra de negócio está em
[Blocos de Liquidez](../produto/blocos-de-liquidez.md), na seção de Produto.

## Tabelas no BigQuery

Ficam no dataset configurado em `BIGQUERY_DATASET` (recomendado: `tabelas_silvers`).

**`tb_blocos_liquidez`**: uma linha por bloco.

| Coluna | Tipo | Observação |
| --- | --- | --- |
| `id_bloco` | STRING | UUID gerado pelo backend. |
| `codigo_identificacao` | STRING | `BLOCO_<PEDRA>_<ms>`. |
| `etiqueta` | STRING | Nome da pedra. |
| `capital_total` | NUMERIC | |
| `data_criacao` | DATE | Preenchida pelo sistema (Brasília). |
| `data_vencimento` | DATE | |
| `responsavel_tecnico` | STRING | |
| `observacao` | STRING | Opcional. |
| `criado_por_uid` | STRING | Uid da gestora no Firebase. |
| `criado_em` | TIMESTAMP | |

**`tb_blocos_empresas`**: uma linha por empresa dentro de um bloco. É aqui que mora o
vínculo entre bloco e empresa; o `id_bloco` **não** fica na tabela de empresas.

| Coluna | Tipo | Observação |
| --- | --- | --- |
| `id_bloco` | STRING | |
| `id_empresa` | STRING | |
| `cnpj` | STRING | Só dígitos. |
| `capital_estimado` | NUMERIC | Calculado no servidor. |
| `percentual_liquidez` | NUMERIC | Até 2 casas. |

Nome e ramo da empresa não são copiados: vêm do join com `tb_empresas_fidc`.

**`tb_empresas_fidc`** (cadastro de empresas, mantido por outra pessoa do grupo) mora em
**outro dataset**, `dados_fidc`, configurado em `BIGQUERY_DATASET_EMPRESAS`. Colunas:
`ID_EMPRESA` (INTEGER), `NOME_FANTASIA`, `RAZAO_SOCIAL`, `RAMO_EMPRESA` e `CNPJ` (STRING),
todas opcionais; hoje são 490 empresas fictícias. O backend converte o id para texto, tira
a máscara do CNPJ ao consultar e ignora linhas sem id ou sem CNPJ. As duas regiões dos
datasets precisam ser a mesma (hoje, `US`), porque o detalhe do bloco junta as duas tabelas.

Por isso são **dois datasets**: `BIGQUERY_DATASET` para as tabelas de blocos (escritas pela
aplicação) e `BIGQUERY_DATASET_EMPRESAS` para o cadastro (só leitura). Se os dois apontarem
para o mesmo dataset, as tabelas de blocos precisam existir nele (rode o job abaixo).

As tabelas de blocos são criadas por `python -m app.jobs.criar_tabelas_blocos`, que pode
rodar de novo sem apagar nada.

## Rotas

| Rota | Acesso | O que faz |
| --- | --- | --- |
| `GET /blocos/etiquetas` | qualquer perfil | As pedras e as cores. |
| `GET /empresas?busca=` | gestora | Busca por nome fantasia ou CNPJ (2+ caracteres, até 20 resultados), só empresas fora de qualquer bloco. |
| `POST /blocos` | gestora | Valida e cria o bloco. Responde 201 com o código gerado. |
| `GET /blocos` | qualquer perfil | Os blocos criados, do mais novo para o mais antigo, cada um com a cor da etiqueta, a quantidade de empresas, o score e a nota de risco. |
| `GET /blocos/{bloco_id}` | qualquer perfil | Um bloco com as suas empresas, da maior para a menor fatia, cada uma com o seu score e nota. |

Erros de `POST /blocos`: dados inválidos ou soma diferente de 100% (422), empresa fora do
cadastro (422), empresa já em outro bloco (409), tabela fora do ar (503). Em
`GET /blocos/{bloco_id}`, bloco inexistente responde 404.

No detalhe, nome e ramo das empresas vêm de um join com `tb_empresas_fidc`. Se o cadastro não
estiver acessível, o bloco sai com `nome_fantasia` e `ramo_atividade` vazios, em vez de
falhar. A `cor` vem da etiqueta; fica vazia se a pedra sair da lista.

## Como a criação funciona

1. `domain/blocos.py` valida tudo e calcula o capital estimado de cada empresa com
   `Decimal`, sem erro de ponto flutuante. O servidor não confia nos números da tela.
2. `storage/blocos.py` confere que as empresas existem e que nenhuma já está em um bloco.
3. Bloco e empresas são gravados numa **única transação** do BigQuery (um script
   `BEGIN TRANSACTION … COMMIT` com parâmetros), para não sobrar bloco pela metade.

As consultas são parametrizadas: o texto digitado nunca entra no SQL.

## Score de risco (dados de demonstração)

Os scores são **fictícios**: foram sorteados (inteiros de 0 a 100, semente fixa) para cada uma das
490 empresas do cadastro e gravados em `backend/dados/scores_empresas.csv`, com as colunas
`id_empresa` e `score`. Não há modelo nem tabela por trás.

- **Leitura:** `storage/scores.py` lê o CSV uma vez por processo (em cache) e ignora linhas
  malformadas ou fora de 0 a 100. Sem o arquivo, as telas mostram "—" em vez de falhar. Depois de
  editar o CSV é preciso reiniciar o backend.
- **Cálculo:** `GET /blocos` e `GET /blocos/{id}` devolvem `score` e `nota_risco` do bloco, e o
  detalhe também os de cada empresa. O score do bloco é a média ponderada pelo capital estimado de
  cada empresa (`domain/risco.py`, `score_ponderado`; empresas sem score ficam de fora). A nota vem
  da escala já existente em `classificar_nota`.
- **Empacotamento:** o arquivo vai para a imagem do backend pelo `COPY . .` do Dockerfile.
- **Para trocar por um score real:** basta o CSV (ou uma tabela, mudando só o `storage/scores.py`)
  trazer o score do modelo; o resto continua igual.

## Blocos de exemplo

Os blocos que aparecem hoje na plataforma são **dados fictícios de demonstração**: 12 blocos
montados com as empresas do cadastro, com responsável, capital, vencimento, datas de criação e
distribuição da liquidez sorteados (cada bloco soma exatamente 100%, e nenhuma empresa está em
dois blocos). Foram gravados com `criado_por_uid = 'seed-demo'`, pelas mesmas regras e pela mesma
transação da tela. O script que os gerou foi removido. Para apagá-los, no BigQuery:

```sql
DELETE FROM `plataforma-clara.tabelas_silvers.tb_blocos_empresas`
WHERE id_bloco IN (SELECT id_bloco FROM `plataforma-clara.tabelas_silvers.tb_blocos_liquidez`
                   WHERE criado_por_uid = 'seed-demo');
DELETE FROM `plataforma-clara.tabelas_silvers.tb_blocos_liquidez` WHERE criado_por_uid = 'seed-demo';
```

## CORS

O `main.py` libera as origens de `CORS_ORIGENS` (separadas por vírgula; padrão
`http://localhost:5173`). Em produção, é a URL pública do frontend. Mexe só em
`config/settings.py` e na variável; nada espalhado.

## Limites conhecidos

- Duas gestoras criando blocos ao mesmo tempo com a mesma empresa podem passar pela
  conferência de "empresa livre", porque o BigQuery não tem restrição de unicidade.
- Os capitais estimados somam o capital total só quando os centavos fecham; o servidor
  não redistribui centavos entre as empresas.
