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
| `GET /blocos` | qualquer perfil | Os blocos criados, do mais novo para o mais antigo, cada um com a cor da etiqueta e a quantidade de empresas. |
| `GET /blocos/{bloco_id}` | qualquer perfil | Um bloco com as suas empresas, da maior para a menor fatia. |

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

## CORS

O `main.py` libera as origens de `CORS_ORIGENS` (separadas por vírgula; padrão
`http://localhost:5173`). Em produção, é a URL pública do frontend. Mexe só em
`config/settings.py` e na variável; nada espalhado.

## Limites conhecidos

- Duas gestoras criando blocos ao mesmo tempo com a mesma empresa podem passar pela
  conferência de "empresa livre", porque o BigQuery não tem restrição de unicidade.
- Os capitais estimados somam o capital total só quando os centavos fecham; o servidor
  não redistribui centavos entre as empresas.
