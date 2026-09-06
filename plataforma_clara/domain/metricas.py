"""
Regras de negócio dos dashboards: consolidação, filtros e montagem de visões.

Este módulo concentra o que antes vivia dentro de `rx.State` — `_calcular_metricas`,
o corpo do computed var `blocos_filtrados` e a formatação feita dentro de
`_buscar_dados_bloco_bq`. São funções puras: recebem dados, devolvem dados, não
tocam banco nem sessão. É o que permite que a mesma regra sirva ao Reflex hoje e a
um endpoint FastAPI na Fase 2, sem duplicação.
"""


from plataforma_clara.domain import formatacao, risco
from plataforma_clara.domain.schemas import (
    AgregadoEmpresa,
    AgregadoEmpresaBloco,
    DetalheBloco,
    EmpresaDoBloco,
    KpisConsolidados,
    LinhaTabelaGestora,
    LinhaTransparencia,
    MetricaBloco,
)

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
        4. O score médio vira nota com nível. O campo de rentabilidade saiu: era um
           hash do nome do bloco apresentado como percentual ao ano.

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
        empresas=linhas,
    )
