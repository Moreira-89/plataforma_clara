# Blocos de Liquidez

Um **Bloco de Liquidez** é um conjunto de empresas, montado pela gestora, em que o
capital do fundo é distribuído. Esta página descreve as telas de blocos (a lista, para gestora e investidor, e o
formulário de criação, só da gestora).

## Etiquetas

Cada bloco recebe uma **etiqueta**: o nome de uma pedra rara, com uma cor própria.
A cor será usada na tela do investidor para dar identidade visual a cada bloco.

| Etiqueta | Cor | Etiqueta | Cor |
| --- | --- | --- | --- |
| Diamante | `#E8F4F8` | Opala Negra | `#0B0B1E` |
| Rubi | `#E0115F` | Jadeíte | `#40826D` |
| Safira | `#0F52BA` | Taaffeite | `#D8BFD8` |
| Esmeralda | `#50C878` | Grandidierite | `#2F4F4F` |
| Alexandrita | `#4B5320` | Musgravite | `#4A3B4E` |
| Tanzanita | `#6A5ACD` | Painita | `#7B1818` |
| Turmalina Paraíba | `#00E5EE` | Benitoíta | `#3F00FF` |
| Poudretteite | `#FFC0CB` | | |

A lista mora em `domain/blocos.py` e chega ao frontend por `GET /blocos/etiquetas`.
Duas cores têm pouco contraste (Diamante, quase branco, e Opala Negra, quase preto);
por isso a cor é usada como detalhe visual, nunca como cor de texto.

O mesmo nome de pedra pode ser usado em vários blocos. O que os distingue é o
**código de identificação**: `BLOCO_<PEDRA>_<número>`, em que o número é o instante da
criação em milissegundos e o nome da pedra perde acentos e espaços
(`Turmalina Paraíba` vira `TURMALINA_PARAIBA`). O código é gerado ao salvar.

## As telas de blocos

A mesma tela serve aos dois perfis, com nomes e permissões diferentes. É a primeira tela
que cada um vê depois de entrar.

| | Gestora | Investidor |
| --- | --- | --- |
| Nome | **Gestão de Blocos** | **Blocos de Liquidez** |
| Cartões, busca e "Ver mais detalhes" | sim | sim |
| Botão **Criar novo bloco** | sim (abre o formulário num pop-up) | não |
| Botão **Alocar dinheiro** no pop-up | não | sim; pede e mostra a confirmação do investimento, sem gravar nada ainda |
| Responsável técnico, data de criação e observação no pop-up | sim | não |

**Cartões.** Um cartão por bloco criado, sempre do mais recente para o mais antigo.
Cada cartão mostra a etiqueta (com a cor da pedra), o código do bloco (os 8 primeiros
caracteres do id), a nota de risco, a quantidade de empresas, o vencimento e o botão
**Ver mais detalhes**. Clicar em qualquer ponto do cartão abre a ficha do bloco (o pop-up de detalhes).

**Busca e filtros.** A barra de busca procura pelo código do bloco (o id) ou pelo nome da
etiqueta. **Ver tudo** limpa a busca e volta à ordem padrão. O filtro de ordem tem
**Mais recentes** (o padrão) e **Maior score**.

**Ficha do bloco (pop-up "Ver mais detalhes").** Mostra a etiqueta, a data de vencimento e o score do
bloco, o **bloco visual** (descrito abaixo) e a tabela de empresas, com nome, CNPJ, ramo, capital
estimado e score de risco de cada uma. Cada cartão abre a ficha do seu próprio bloco.

**Bloco visual.** É um cubo mágico em CSS 3D (sem WebGL nem biblioteca de gráficos), que gira com o
mouse e mostra **qual porcentagem do capital do bloco vai para cada empresa**. É um componente único
(`src/js/paginas/blocos/cubo.js`): ele não tem valores fixos, lê as empresas e as porcentagens de
liquidez do bloco aberto e só então desenha, então cada ficha mostra um cubo diferente; a
proporcionalidade e o comportamento são os mesmos em todas.

- As 6 faces têm 3x3 adesivos, 54 no total, que representam **100% do capital do bloco**. Cada
  **empresa** ocupa uma região de adesivos proporcional à sua porcentagem.
- A repartição usa o método do maior resto e dá ao menos 1 adesivo a cada empresa. Cada adesivo vale
  cerca de 1,85%, então o cubo é aproximado; a porcentagem exata aparece no balão e a tabela traz os
  valores. Passando de 54 empresas, as menores se juntam em "Outras empresas" (em cinza).
- A cor é a da etiqueta (pedra) do bloco, com tons diferentes para distinguir as empresas.
- Passar o mouse destaca todos os adesivos da empresa e mostra um balão com o nome e a porcentagem.
- Ao abrir, o cubo surge e os adesivos acendem em sequência (cerca de 1 segundo, só `opacity` e
  `transform`, leve para a GPU); a animação é desligada para quem pede menos movimento no sistema.

**Score de risco.** Cada empresa tem um score de 0 a 100 (maior score, menor risco), traduzido numa
nota: **A+** a partir de 80, **A** a partir de 70, **A-** a partir de 60, **B+** a partir de 50, **B** a
partir de 40 e **C-** abaixo disso. O score do bloco é a **média dos scores das empresas, ponderada
pelo capital** que cada uma recebe no bloco. Os cartões mostram só a **nota**; o pop-up mostra a nota
e o número (por exemplo, "A- · 67") do bloco e de cada empresa. O filtro **Maior score** ordena os
blocos do maior para o menor.

!!! info "Dados de demonstração"
    Os scores são **fictícios**: foram sorteados de 0 a 100 para cada empresa, sem modelo por trás,
    e ficam em `backend/dados/scores_empresas.csv`. As empresas (Faker) e os blocos de exemplo também
    são fictícios. As telas não trazem esse aviso; ele fica aqui, no README e na apresentação.

**Menu lateral.** Todas as telas de quem está logado (a Gestão de Blocos e os Blocos de
Liquidez) têm o mesmo menu à esquerda, fixo: o logo no topo, o item da área do perfil
(destacado quando é a tela atual) e, no rodapé, o e-mail de quem entrou e o botão **Sair**.
A home não tem esse menu. Telas novas entram na lista de itens do menu e passam a aparecer em
todas as páginas.

## Telas do investidor

**Visão geral.** É a primeira tela do investidor depois do login. Tem duas faixas no topo (o **total
investido**, e a quantidade de etiquetas e de blocos investidos) e três blocos:

- **Ranking de empresas:** as 10 empresas que mais recebem do dinheiro do investidor, com posição,
  nome (ou CNPJ, se o cadastro estiver fora do ar), ramo, etiqueta, valor, percentual do total e uma
  barra proporcional à primeira. O valor de cada empresa é o investido no bloco vezes a fatia dela nele.
- **Cubo 3D das empresas da carteira**, descrito abaixo.
- **Assistente Clara:** a interface de um chatbot (mensagens, campo de texto e botão Enviar). **Ainda
  não há LLM por trás**: a saudação e a resposta ("ainda não estou conectado a um modelo...") são
  textos fixos, a conversa só existe na página e nada é enviado ao backend.

Todos os números vêm da carteira; nenhum é estimado.

**O cubo da Visão geral.** É o mesmo componente do bloco visual da ficha (CSS 3D, 54 adesivos que
representam **100% do dinheiro do investidor**), mas lê a carteira inteira: cada **empresa** ocupa uma
região proporcional à fatia dela nesse dinheiro (a mesma que o ranking mostra). A cor é a da etiqueta
(pedra) do bloco da empresa, com tons diferentes para distinguir as empresas. Passar o mouse destaca a
região da empresa e mostra um balão com nome, valor investido e percentual; clicar leva a **Blocos
Investidos** filtrado pela etiqueta da empresa (em "Outras empresas" não há clique). O cubo da ficha de
cada bloco, descrito acima, mostra só as empresas de um bloco.

**Alocar dinheiro.** No pop-up de detalhes de um bloco, o investidor clica em **Alocar dinheiro**; a
tela pergunta "Confirmar o investimento no bloco ...?", com **Cancelar** e **Confirmar investimento**,
e depois mostra "Investimento confirmado.". Ainda não há aporte de verdade por trás: a confirmação não
grava nada.

**Blocos Investidos.** Lista os blocos em que o investidor já investiu, numa grade de cartões igual à da
tela de Blocos de Liquidez, com a linha **Investido: R$ ...** em cada cartão. O menu lateral do
investidor tem quatro itens: Visão geral, Blocos de Liquidez, Blocos Investidos e Relatório.

A barra de filtros tem:

- **Busca** pelo código do bloco ou pelo nome da etiqueta.
- **Etiqueta:** uma lista com as etiquetas em que o investidor tem blocos. Vindo do cubo da Visão geral, a tela
  abre com `?etiqueta=Safira` e esse filtro já marcado; a URL acompanha o filtro.
- **Ordenação:** mais recentes (a ordem de criação do bloco, a padrão), **maior investimento**,
  menor investimento, maior score e vencimento mais próximo.
- **Limpar filtros:** volta a busca, a etiqueta e a ordem ao padrão.

Acima dos cartões, uma linha mostra quantos blocos aparecem e quanto o investidor tem investido neles
("5 de 12 blocos · R$ 480.000,00 investidos").

!!! note "Não há data do investimento"
    A carteira é de demonstração e não guarda a data em que o investidor aplicou, então não dá para
    ordenar ou filtrar por ela. Os critérios de data disponíveis são o vencimento do bloco. Quando existir
    investimento real, a data do aporte entra na lista de ordenação.

O botão **Ver mais detalhes** abre o mesmo pop-up da tela de Blocos de Liquidez, mas com a visão de
quem já investiu. Ele mostra a etiqueta, a data de vencimento e o score do bloco, e acrescenta:

- **Capital total do bloco**;
- **Você investiu**: o valor que o investidor aplicou no bloco;
- **Sua participação no bloco**: o valor investido dividido pelo capital total.

A tabela de empresas ganha duas colunas além de nome, CNPJ, ramo, capital estimado e score de risco:
**% do bloco** (a fatia da empresa no bloco) e **Seu capital** (o valor investido vezes essa fatia,
isto é, quanto do dinheiro do investidor está em cada empresa; a coluna soma o valor investido). Nesse
pop-up não há botão de alocar dinheiro.

**Carteira de exemplo.** Como não existe aporte real, cada conta de investidor recebe uma carteira de
**demonstração**: cerca de 40% dos blocos, com um valor fictício em cada (múltiplo de R$ 5 mil, de
R$ 5 mil a R$ 500 mil). O sorteio é estável: a mesma conta vê sempre os mesmos blocos e valores, e
contas diferentes veem carteiras diferentes, o que permite que mais de um colega teste.

## O formulário de criação (gestora)

Só a gestora vê. Abre num **pop-up** a partir do botão **Criar novo bloco** da Gestão de
Blocos; ao criar, o pop-up fecha e a lista já mostra o bloco novo no topo, com o código dele
num aviso. O pop-up tem duas colunas: à esquerda, as empresas, que ocupam a maior parte; à
direita, os dados do bloco.

**Dados do bloco**

| Campo | Regra |
| --- | --- |
| Etiqueta | Uma das pedras da lista. |
| Capital total do bloco | Em R$, com até 2 casas. O campo já mostra o valor em BRL enquanto se digita (`1000000` vira `R$ 1.000.000,00`). |
| Data de vencimento | Tem de ser depois do dia da criação. |
| Nome do responsável técnico | Obrigatório, até 120 caracteres. |
| Observação | Opcional, até 500 caracteres. Serve para registrar qualquer nota sobre o bloco, útil em manutenções futuras. |

A **data de criação** não é um campo: o sistema preenche com o dia da criação, no
horário de Brasília.

**Empresas do bloco**

1. A gestora busca por **nome fantasia** ou **CNPJ**. A busca lista nome e CNPJ numa
   caixa de seleção, e ela marca uma ou várias empresas.
2. As empresas marcadas **continuam selecionadas** quando ela faz outra busca: aparecem como
   etiquetas acima dos resultados (cada uma com um × para desmarcar), e o botão mostra
   quantas há. Assim ela pode procurar e marcar empresas diferentes, uma busca após a outra.
3. Ao clicar em **Adicionar**, todas as marcadas entram de uma vez numa tabela com nome,
   CNPJ, ramo de atividade, **capital estimado para a empresa** e **porcentagem de
   liquidez aplicada**.
4. A gestora preenche a **porcentagem** de cada empresa (até 2 casas decimais). Essa
   porcentagem é a parte do capital total do bloco que a empresa recebe: 5% de
   R$ 1.000.000 dá R$ 50.000.
5. O **capital estimado** não é digitado: é calculado (capital total × porcentagem).

**Realocado e Disponível**

Dois campos se atualizam enquanto a gestora preenche a tabela: **Realocado** é a soma
das porcentagens já distribuídas, e **Disponível** é o que ainda falta distribuir. O
bloco só pode ser criado quando as porcentagens somam **exatamente 100%**, ou seja,
com Disponível em 0%. Isso impede criar um bloco sem ter dividido o capital entre as
empresas.

## Regras

- Uma empresa só pode estar em **um** bloco. A busca não lista empresas que já estão em
  algum bloco, e a gravação recusa a repetição (erro 409).
- Bloco e empresas são gravados juntos; se algo falhar, nada é gravado.
- Cada porcentagem fica entre 0 e 100, e uma empresa não pode aparecer duas vezes.

Os detalhes técnicos (tabelas, rotas e erros) estão em
[Blocos de Liquidez](../arquitetura/blocos.md), na seção de Arquitetura.

## Pendente de confirmação

- **Uma empresa em vários blocos.** Hoje vale "um só", como a gestora definiu para o
  momento, mas o grupo ainda vai confirmar. Se mudar, a busca deixa de filtrar e a
  gravação deixa de recusar.
- **Score real:** o modelo de machine learning (Random Forest, de 0 a 100, a partir do histórico) ainda não existe; hoje os scores são de demonstração (ver aviso acima).
- **Alocar dinheiro:** como o investidor aporta de verdade ainda não foi definido; hoje o botão só confirma, sem gravar.
- **Chatbot:** falta decidir a LLM, o endpoint e o que o assistente pode consultar. O ponto de ligação no frontend é a função `responder` em `src/js/paginas/investidor/chat.js`.
- **Outras visualizações da Visão geral:** além do cubo, dos totais e do ranking, o grupo ainda não definiu gráficos.
- **Filtros em Blocos Investidos:** outros filtros possíveis (faixa de valor investido, nota de risco mínima, vencimento até uma data) ainda não foram pedidos.
