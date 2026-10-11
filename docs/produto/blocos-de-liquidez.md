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
| Botão **Alocar dinheiro** no pop-up | não | sim, ainda desativado ("em breve") |
| Responsável técnico, data de criação e observação no pop-up | sim | não |

**Cartões.** Um cartão por bloco criado, sempre do mais recente para o mais antigo.
Cada cartão mostra a etiqueta (com a cor da pedra), o código do bloco (os 8 primeiros
caracteres do id), o score de risco, a quantidade de empresas, o vencimento e o botão
**Ver mais detalhes**.

**Busca e filtros.** A barra de busca procura pelo código do bloco (o id) ou pelo nome da
etiqueta. **Ver tudo** limpa a busca e volta à ordem padrão. O filtro de ordem tem
**Mais recentes** e **Maior score**; o segundo fica desativado até o score existir.

**Pop-up "Ver mais detalhes".** Mostra a etiqueta, a data de vencimento, o score do bloco e
a tabela de empresas, com nome, CNPJ, ramo, capital estimado e score de risco de cada uma.

!!! warning "Score de risco ainda não existe nos dados"
    Nenhuma tabela tem o score hoje (a `tb_empresas_fidc` não traz essa coluna), e a
    plataforma não inventa número. Os cartões e o pop-up mostram **—** e o aviso "score de
    risco indisponível". Quando a fonte do score for integrada, o score entra nos cartões, no
    pop-up e no filtro **Maior score**.

**Menu lateral.** Todas as telas de quem está logado (a Gestão de Blocos e os Blocos de
Liquidez) têm o mesmo menu à esquerda, fixo: o logo no topo, o item da área do perfil
(destacado quando é a tela atual) e, no rodapé, o e-mail de quem entrou e o botão **Sair**.
A home não tem esse menu. Telas novas entram na lista de itens do menu e passam a aparecer em
todas as páginas.

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
- **Score de risco** do bloco e de cada empresa: de onde vem e quando entra (ver aviso acima).
- **Alocar dinheiro:** como o investidor aporta ainda não foi definido; o botão está desativado.
