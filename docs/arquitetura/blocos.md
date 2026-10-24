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
| `GET /empresas?busca=` | gestora | Busca por nome fantasia ou CNPJ (2+ caracteres, até 20 resultados), só empresas fora de qualquer bloco; cada empresa vem com `score` e `nota_risco` (a busca mostra a nota). |
| `POST /blocos` | gestora | Valida e cria o bloco. Responde 201 com o código gerado. |
| `GET /blocos` | qualquer perfil | Os blocos criados, do mais novo para o mais antigo, cada um com a cor da etiqueta, a quantidade de empresas, as `fatias` (a participação de cada empresa no capital do bloco, em %, da maior para a menor; é o que desenha a barra de empresas do cartão), o score e a nota de risco. |
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

## Investimentos do investidor (dados de demonstração)

`GET /investimentos` (só investidor) lista os blocos em que a conta logada "já investiu", com os mesmos
campos da lista de blocos (cor, score e nota) mais `valor_investido`, na ordem da lista (do mais recente
ao mais antigo). Não há tabela nem aporte real: `domain/investimentos.py` decide a carteira a partir de
um hash SHA-256 de (uid do investidor, id do bloco), então o resultado é estável, não depende dos demais
blocos e difere de uma conta para outra. Cerca de 40% dos blocos entram, com valor múltiplo de R$ 5 mil
entre R$ 5 mil e R$ 500 mil. Trocar isso por investimentos reais é mudar a origem dessa lista.

`GET /investimentos/resumo` (só investidor) soma a mesma carteira por etiqueta e devolve o
`total_investido` e, para cada pedra, `etiqueta`, `cor`, `total_investido`, `quantidade_blocos` e
`participacao` (fração de 0 a 1), da maior para a menor. A soma é regra de negócio e mora em
`domain/investimentos.py` (`resumir_por_etiqueta`); o endpoint só junta a cor da pedra.

`GET /investimentos/empresas` (só investidor) devolve o ranking das empresas da carteira, da que mais
recebe do dinheiro do investidor para a que menos. Para cada bloco investido o endpoint busca o
detalhe (uma consulta por bloco, em paralelo) e `domain/investimentos.py` (`ranquear_empresas`)
distribui o valor investido pela fatia de cada empresa no bloco (valor × percentual de liquidez); se a
empresa aparece em mais de um bloco, os valores se somam. Cada item traz nome, CNPJ, ramo, etiqueta e
cor, `capital_investido`, `participacao` (fração do total investido), score e nota. Sem o cadastro de
empresas o nome vem vazio e a tela mostra o CNPJ.

`GET /investimentos/rendimento` (só investidor) devolve o rendimento mensal dos 12 meses **fechados** antes
de hoje (horário de Brasília), do mais antigo para o mais novo: `total_investido`, `rendimento_total`,
`acumulado_percentual` e, para cada mês, `mes` (primeiro dia), `taxa_percentual`, `rendimento` (em R$) e
`acumulado_percentual` (composto). Como não existe histórico de aportes, o dado é de demonstração:
`domain/investimentos.py` (`rendimento_dos_ultimos_meses`) sorteia a taxa de cada mês a partir do hash de
(investidor, mês), entre 0,60% e 1,60%, então a série não muda entre chamadas nem quando chega o mês
seguinte; o rendimento em R$ é o total investido vezes a taxa. Sem nada investido, `meses` vem vazio.

## Score de risco

O score de cada uma das 490 empresas do cadastro é o **Score de Reputação Clara, versão perfil público (v0.1.1)**, calculado no BigQuery com dados públicos reais da CVM (Informe Mensal de FIDC, data-base ago/2026). Cada empresa fictícia
recebe o perfil de um cedente real do mesmo setor (o nome e o CNPJ continuam fictícios), e o score
soma quatro critérios: qualidade dos fundos que compram do cedente (40 pontos), permanência em 12
meses (25), risco do setor (20) e aceitação em fundos (15), com uma trava que limita a nota quando os
fundos têm inadimplência muito acima do mercado. O resultado está na tabela
`dados_fidc.tb_score_empresas` e é exportado para `backend/dados/scores_empresas.csv`, com as colunas
`id_empresa` e `score`.

- **Leitura:** `storage/scores.py` lê o CSV uma vez por processo (em cache) e ignora linhas
  malformadas ou fora de 0 a 100. Sem o arquivo, as telas mostram "—" em vez de falhar. Depois de
  editar o CSV é preciso reiniciar o backend.
- **Cálculo:** `GET /blocos` e `GET /blocos/{id}` devolvem `score` e `nota_risco` do bloco, e o
  detalhe também os de cada empresa. O score do bloco é a média ponderada pelo capital estimado de
  cada empresa (`domain/risco.py`, `score_ponderado`; empresas sem score ficam de fora). A nota vem
  de `classificar_nota`: 22 notas, AAA a D, em faixas iguais de cerca de 4,55 pontos. A mesma régua
  está em `dados_fidc.tb_escala_notas` (o painel da gestora lê dali a nota dos blocos) e no prompt
  do relatório.
- **Histórico:** `backend/dados/scores_empresas_historico.csv` traz o score e os pontos de cada
  critério por empresa e mês. Vem do SQL 15, tabela `dados_fidc.tb_score_empresas_historico`, com a
  mesma regra, recalculada mês a mês. Só o relatório em PDF usa esse arquivo, para os upgrades e
  downgrades; as telas continuam com o score atual.
- **Empacotamento:** os arquivos vão para a imagem do backend pelo `COPY . .` do Dockerfile.
- **Para atualizar (todo mês):** rodar de novo os SQLs do score no BigQuery (o 12 e depois o 15),
  exportar os dois CSVs, trocar em `backend/dados/` e reiniciar o backend. Para ler direto da tabela, basta mudar o `storage/scores.py`; o resto continua igual.

## Blocos de exemplo

Os blocos que aparecem hoje na plataforma são **dados fictícios de demonstração**: 26 blocos
(12 com uma pedra cada e 14 que repetem pedras, para os painéis de Blocos Investidos terem vários
blocos por pedra) montados com as empresas do cadastro, com responsável, capital, vencimento, datas de criação e
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
