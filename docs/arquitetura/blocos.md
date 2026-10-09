# Blocos de Liquidez (dados e rotas)

Como a criação de um bloco funciona por baixo. A regra de negócio está em
[Blocos de Liquidez](../produto/blocos-de-liquidez.md), na seção de Produto.

## Tabelas no BigQuery

Ficam no dataset configurado em `BIGQUERY_DATASET` (hoje `tabelas_silvers`).

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

Nome e ramo da empresa não são copiados: vêm do join com `tb_empresas`.

**`tb_empresas`** (cadastro, criado por outra pessoa do grupo) deve ter `id_empresa`,
`nome_fantasia`, `razao_social`, `cnpj` e `ramo_atividade`. O backend converte o id para
texto e tira a máscara do CNPJ ao consultar, então o tipo do id e o formato do CNPJ não
importam.

As tabelas de blocos são criadas por `python -m app.jobs.criar_tabelas_blocos`, que pode
rodar de novo sem apagar nada.

## Rotas

| Rota | Acesso | O que faz |
| --- | --- | --- |
| `GET /blocos/etiquetas` | qualquer perfil | As pedras e as cores. |
| `GET /empresas?busca=` | gestora | Busca por nome fantasia ou CNPJ (2+ caracteres, até 20 resultados), só empresas fora de qualquer bloco. |
| `POST /blocos` | gestora | Valida e cria o bloco. Responde 201 com o código gerado. |

Erros de `POST /blocos`: dados inválidos ou soma diferente de 100% (422), empresa fora do
cadastro (422), empresa já em outro bloco (409), tabela fora do ar (503).

## Como a criação funciona

1. `domain/blocos.py` valida tudo e calcula o capital estimado de cada empresa com
   `Decimal`, sem erro de ponto flutuante. O servidor não confia nos números da tela.
2. `storage/blocos.py` confere que as empresas existem e que nenhuma já está em um bloco.
3. Bloco e empresas são gravados numa **única transação** do BigQuery (um script
   `BEGIN TRANSACTION … COMMIT` com parâmetros), para não sobrar bloco pela metade.

As consultas são parametrizadas: o texto digitado nunca entra no SQL.

## Limites conhecidos

- Duas gestoras criando blocos ao mesmo tempo com a mesma empresa podem passar pela
  conferência de "empresa livre", porque o BigQuery não tem restrição de unicidade.
- Os capitais estimados somam o capital total só quando os centavos fecham; o servidor
  não redistribui centavos entre as empresas.
