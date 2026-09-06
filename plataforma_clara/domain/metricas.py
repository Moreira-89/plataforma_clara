"""
Regras de negócio dos dashboards: consolidação, filtros e montagem de visões.

Este módulo concentra o que antes vivia dentro de `rx.State` — `_calcular_metricas`,
o corpo do computed var `blocos_filtrados` e a formatação feita dentro de
`_buscar_dados_bloco_bq`. São funções puras: recebem dados, devolvem dados, não
tocam banco nem sessão. É o que permite que a mesma regra sirva ao Reflex hoje e a
um endpoint FastAPI na Fase 2, sem duplicação.
"""

import hashlib
import urllib.parse

from plataforma_clara.domain import formatacao, risco
from plataforma_clara.domain.schemas import (
    AgregadoEmpresa,
    AgregadoEmpresaBloco,
    CardBloco,
    DetalheBloco,
    EmpresaDoBloco,
    KpisConsolidados,
    LinhaTabelaGestora,
    LinhaTransparencia,
    MetricaBloco,
)

# Rótulos das opções de filtro da página Explorar Blocos que significam "não filtrar".
_SETOR_TODOS = "Todos os Setores"
_SCORE_QUALQUER = "Qualquer Score"


# -----------------------------------------------------------------------------
# CONSOLIDAÇÃO DE KPIs
# -----------------------------------------------------------------------------


def consolidar_kpis(blocos: list[MetricaBloco]) -> KpisConsolidados:
    """
    Consolida a lista de blocos nos três KPIs do topo do dashboard.

    COMO FUNCIONA:
        1. Lista vazia devolve os KPIs zerados, nunca uma divisão por zero.
        2. O total alocado é a soma dos totais de cada bloco.
        3. O score médio é a MÉDIA SIMPLES das médias por bloco — não é ponderado
           pelo volume. Um bloco de R$ 1 mil pesa igual a um de R$ 10 milhões.
           O comportamento é o que está na tela hoje e foi preservado; se a banca
           questionar o número, esta é a linha a mudar.
        4. A quantidade de aportes é a soma das contagens por bloco.

    Args:
        blocos (list[MetricaBloco]): Métricas agregadas por Bloco de Liquidez.

    Returns:
        KpisConsolidados: Total alocado, score médio (2 casas) e quantidade de aportes.
    """
    if not blocos:
        return KpisConsolidados()

    total_alocado = sum(bloco.total_alocado for bloco in blocos)
    soma_scores = sum(bloco.score_medio_reputacao for bloco in blocos)

    return KpisConsolidados(
        total_alocado=total_alocado,
        score_medio=round(soma_scores / len(blocos), 2),
        quantidade_aportes=sum(int(bloco.quantidade_aportes) for bloco in blocos),
    )


def percentual_blocos_em_risco(blocos: list[MetricaBloco]) -> str:
    """
    Calcula a fatia de blocos com score abaixo do corte de inadimplência.

    Args:
        blocos (list[MetricaBloco]): Métricas agregadas por bloco.

    Returns:
        str: Percentual formatado — ex: '12.5%'. Devolve '0.0%' sem blocos.
    """
    if not blocos:
        return "0.0%"

    em_risco = sum(
        1 for bloco in blocos if risco.esta_em_risco_de_inadimplencia(bloco.score_medio_reputacao)
    )
    return formatacao.formatar_percentual(em_risco / len(blocos))


def descrever_quantidade_blocos(blocos: list[MetricaBloco]) -> str:
    """
    Descreve a quantidade de blocos ativos com concordância de número.

    Args:
        blocos (list[MetricaBloco]): Métricas agregadas por bloco.

    Returns:
        str: '1 Bloco' ou 'N Blocos'.
    """
    quantidade = len(blocos)
    return f"{quantidade} Blocos" if quantidade != 1 else "1 Bloco"


def serie_alocacao_por_bloco(blocos: list[MetricaBloco]) -> list[dict]:
    """
    Monta a série de alocação por bloco para os gráficos, em milhões de reais.

    O formato de saída (chaves 'name' e 'value') é ditado pelo componente de
    gráfico do Reflex, por isso continua sendo dict e não um DTO.

    Args:
        blocos (list[MetricaBloco]): Métricas agregadas por bloco.

    Returns:
        list[dict]: Pontos com 'name' (nome do bloco) e 'value' (volume em milhões).
    """
    return [
        {
            "name": bloco.bloco_liquidez_setorial or "N/A",
            "value": formatacao.para_milhoes(bloco.total_alocado),
        }
        for bloco in blocos
    ]


def serie_distribuicao_aportes(blocos: list[MetricaBloco], limite: int = 5) -> list[dict]:
    """
    Monta a série dos maiores blocos por volume alocado.

    Args:
        blocos (list[MetricaBloco]): Métricas já ordenadas por volume decrescente.
        limite (int): Quantos blocos exibir. Padrão 5.

    Returns:
        list[dict]: Pontos com 'name' e 'alocado' (volume em milhões).
    """
    return [
        {
            "name": bloco.bloco_liquidez_setorial or "N/A",
            "alocado": formatacao.para_milhoes(bloco.total_alocado),
        }
        for bloco in blocos[:limite]
    ]


# -----------------------------------------------------------------------------
# TABELA DA GESTORA
# -----------------------------------------------------------------------------


def montar_tabela_gestora(empresas: list[AgregadoEmpresa]) -> list[LinhaTabelaGestora]:
    """
    Formata a agregação por empresa sacada para a tabela do dashboard da gestora.

    COMO FUNCIONA:
        A classificação de risco e o status de adimplência eram calculados por um
        `CASE WHEN` dentro da query SQL. Passaram para cá porque são política de
        risco, não consulta: mantê-los no SQL obrigaria a reescrever a regra em cada
        banco que a plataforma passar a consultar (Postgres hoje, BigQuery na Fase 3).
        A escada de faixas é a mesma — `domain/risco.py`.

    Args:
        empresas (list[AgregadoEmpresa]): Agregação crua por empresa sacada.

    Returns:
        list[LinhaTabelaGestora]: Linhas com CNPJ mascarado, valor em R$ e nota.
    """
    return [
        LinhaTabelaGestora(
            empresa=empresa.empresa_sacada_nome,
            cnpj=formatacao.formatar_cnpj(empresa.cnpj_sacado_limpo),
            valor=formatacao.formatar_moeda(empresa.valor_total_alocado),
            risco=risco.classificar_nota(empresa.score_medio),
            status=risco.classificar_adimplencia(empresa.score_medio),
        )
        for empresa in empresas
    ]


def montar_tabela_transparencia(
    agregados: list[AgregadoEmpresaBloco],
) -> list[LinhaTransparencia]:
    """
    Formata a carteira do investidor para a tabela de transparência.

    É a tela que dá nome ao produto: mostra ao investidor em quais empresas o
    dinheiro dele foi efetivamente aplicado dentro de cada Bloco de Liquidez.

    Args:
        agregados (list[AgregadoEmpresaBloco]): Agregação por empresa e bloco.

    Returns:
        list[LinhaTransparencia]: Linhas com score arredondado e valor em R$.
    """
    return [
        LinhaTransparencia(
            empresa=item.empresa_sacada_nome,
            bloco=item.bloco_liquidez_setorial or "N/A",
            score=round(item.score_medio, 2),
            valor=formatacao.formatar_moeda(item.valor_total),
        )
        for item in agregados
    ]


# -----------------------------------------------------------------------------
# EXPLORAR BLOCOS
# -----------------------------------------------------------------------------


def rentabilidade_estavel(nome_bloco: str) -> float:
    """
    Deriva um percentual de rentabilidade estável a partir do nome do bloco.

    ATENÇÃO — ESTE NÚMERO É SIMULADO. O dataset atual não traz rentabilidade
    realizada nem alvo; o valor exibido é um hash SHA-1 do nome do bloco reduzido à
    faixa de 10,5% a 17,5%. O hash existe para que o mesmo bloco mostre sempre o
    mesmo número entre renderizações (um `random()` mudaria a cada recálculo), não
    porque tenha qualquer significado financeiro.

    Enquanto a origem real não existir, a tela apresenta um dado inventado como se
    fosse informação de investimento. Vale decidir explicitamente — junto da Fase 5
    — entre trazer o dado de verdade ou rotular o campo como estimativa na UI.

    Args:
        nome_bloco (str): Nome do Bloco de Liquidez.

    Returns:
        float: Percentual entre 10.5 e 17.5, sempre o mesmo para o mesmo nome.
    """
    digest = hashlib.sha1(nome_bloco.encode("utf-8")).hexdigest()
    return int(digest, 16) % 8 + 10 + 0.5


def _passa_no_filtro_de_score(score: float, filtro: str) -> bool:
    """Aplica a faixa de score selecionada no seletor da página Explorar Blocos."""
    if not filtro or filtro == _SCORE_QUALQUER:
        return True
    if filtro == "A+ a A-":
        return score >= 60
    if filtro == "B+ a B-":
        return 40 <= score < 60
    if filtro == "C+ ou menor":
        return score < 40
    # Rótulo desconhecido não filtra nada — o mesmo que a versão anterior fazia.
    return True


def filtrar_blocos(
    blocos: list[MetricaBloco],
    *,
    termo_busca: str = "",
    filtro_setor: str = "",
    filtro_score: str = "",
) -> list[CardBloco]:
    """
    Aplica os filtros da página Explorar Blocos e monta os cards de exibição.

    COMO FUNCIONA:
        1. Filtro por texto — busca case-insensitive no nome do bloco.
        2. Filtro por setor — o dataset atual não tem coluna de setor, então o setor
           É o nome do bloco. O filtro fica funcional para quando a coluna existir.
        3. Filtro por score — traduz a faixa literal escolhida em corte numérico.
        4. Montagem — formata volume, nota e rentabilidade, e codifica o nome do
           bloco para uso como parâmetro da rota dinâmica `/bloco/[bloco_id]`.

    CARACTERIZAÇÃO DE LIMITAÇÃO CONHECIDA: o termo de busca é testado por `.strip()`
    mas comparado sem strip. Digitar "safira " (com espaço) não encontra nada. O
    comportamento é o atual e foi preservado — corrigir muda o que o usuário vê.

    Args:
        blocos (list[MetricaBloco]): Métricas agregadas por bloco.
        termo_busca (str): Texto digitado na busca.
        filtro_setor (str): Setor selecionado, ou 'Todos os Setores'.
        filtro_score (str): Faixa de score selecionada, ou 'Qualquer Score'.

    Returns:
        list[CardBloco]: Cards dos blocos que passaram por todos os filtros.
    """
    cards: list[CardBloco] = []

    for bloco in blocos:
        nome = bloco.bloco_liquidez_setorial or "N/A"
        setor = nome
        score = bloco.score_medio_reputacao

        # --- 1. FILTRO POR TEXTO ---
        if termo_busca.strip() and termo_busca.lower() not in nome.lower():
            continue

        # --- 2. FILTRO POR SETOR ---
        if filtro_setor and filtro_setor != _SETOR_TODOS:
            if filtro_setor.lower() not in setor.lower():
                continue

        # --- 3. FILTRO POR SCORE ---
        if not _passa_no_filtro_de_score(score, filtro_score):
            continue

        # --- 4. MONTAGEM ---
        cards.append(
            CardBloco(
                id_bloco=urllib.parse.quote(nome),
                nome=nome,
                setor=setor,
                volume=formatacao.formatar_milhoes(bloco.total_alocado),
                score_literal=risco.classificar_nota(score),
                rentabilidade=f"{rentabilidade_estavel(nome)}%",
            )
        )

    return cards


# -----------------------------------------------------------------------------
# DETALHES DE UM BLOCO
# -----------------------------------------------------------------------------


def montar_detalhe_bloco(nome_bloco: str, empresas: list[AgregadoEmpresa]) -> DetalheBloco:
    """
    Consolida a carteira de um bloco nos KPIs e na lista de empresas da página.

    COMO FUNCIONA:
        1. Bloco sem empresas devolve o DetalheBloco vazio (volume zerado, KPIs 'N/A').
        2. Os agregados são médias SIMPLES entre empresas, não ponderadas pelo volume —
           mesma escolha de `consolidar_kpis`, preservada como está.
        3. Cada empresa recebe seu peso percentual no volume total do bloco.
        4. O score médio vira nota com nível; a rentabilidade é o valor simulado
           de `rentabilidade_estavel` (ver o aviso naquela função).

    Args:
        nome_bloco (str): Nome do bloco, já decodificado da URL.
        empresas (list[AgregadoEmpresa]): Agregação por empresa sacada do bloco.

    Returns:
        DetalheBloco: KPIs formatados e a lista de empresas financiadas.
    """
    if not empresas:
        return DetalheBloco()

    volume_total = sum(empresa.valor_total_alocado for empresa in empresas)
    quantidade = len(empresas)
    score_medio = sum(empresa.score_medio for empresa in empresas) / quantidade
    prazo_medio = sum(empresa.prazo_medio_dias for empresa in empresas) / quantidade

    linhas = [
        EmpresaDoBloco(
            nome=empresa.empresa_sacada_nome,
            cnpj=empresa.cnpj_sacado_limpo,
            peso=formatacao.formatar_percentual(
                empresa.valor_total_alocado / volume_total if volume_total > 0 else 0.0
            ),
            valor=formatacao.formatar_moeda(empresa.valor_total_alocado),
            score=risco.classificar_nota(empresa.score_medio),
        )
        for empresa in empresas
    ]

    return DetalheBloco(
        volume_total=formatacao.formatar_moeda(volume_total),
        score_medio=risco.classificar_nota_com_nivel(score_medio),
        prazo_medio=f"{int(prazo_medio)} Dias",
        rentabilidade_alvo=f"{rentabilidade_estavel(nome_bloco)}% a.a.",
        empresas=linhas,
    )
