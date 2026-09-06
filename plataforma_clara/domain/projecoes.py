"""
Séries temporais SIMULADAS exibidas nos gráficos do dashboard.

ATENÇÃO — NENHUM DADO DESTE MÓDULO É REAL.

A plataforma não guarda histórico: `tb_aporte` tem `data_criacao`, mas nenhuma
consulta a utiliza para reconstruir a evolução do patrimônio. As duas séries abaixo
são derivadas do valor ATUAL por fatores fixos, e aparecem na tela ao lado de
números verdadeiros, sem rótulo que as distinga.

Este módulo existe para tornar isso visível: enquanto as funções estavam dentro de
computed vars do `DashboardState`, a natureza simulada só era perceptível lendo o
código. Reunidas aqui, a decisão fica explícita — calcular a série de verdade a
partir do histórico, ou marcá-las como projeção ilustrativa na UI. Nenhuma das duas
é decisão de refatoração, por isso o comportamento segue idêntico ao atual.
"""

from plataforma_clara.domain import formatacao

# Meses exibidos no gráfico de evolução (fixos, não derivados da data atual).
_MESES_HISTORICO = ("Jan", "Fev", "Mar", "Abr", "Mai", "Jun")

# Fatores que simulam crescimento progressivo até o valor atual (100% no último mês).
_FATORES_HISTORICO = (0.83, 0.87, 0.91, 0.95, 0.98, 1.0)

# Meses exibidos na projeção de rendimento.
_MESES_PROJECAO = ("Jul", "Ago", "Set", "Out", "Nov", "Dez")

# Taxa mensal composta aplicada na projeção de rendimento.
_TAXA_MENSAL = 1.01


def evolucao_aum_simulada(patrimonio_atual: float) -> list[dict]:
    """
    Monta a série SIMULADA de evolução do patrimônio sob gestão.

    Aplica fatores fixos sobre o patrimônio atual para desenhar uma curva ascendente
    de seis meses. Não consulta histórico nenhum.

    Args:
        patrimonio_atual (float): Patrimônio total sob gestão, em reais.

    Returns:
        list[dict]: Pontos com 'name' (mês) e 'volume' (em milhões de reais).
    """
    return [
        {"name": mes, "volume": formatacao.para_milhoes(patrimonio_atual * fator)}
        for mes, fator in zip(_MESES_HISTORICO, _FATORES_HISTORICO, strict=True)
    ]


def rendimento_projetado_simulado(total_alocado: float) -> list[dict]:
    """
    Monta a série SIMULADA de rendimento acumulado dos próximos seis meses.

    Aplica 1% ao mês de forma composta sobre o total alocado e devolve o ganho
    acumulado em relação ao valor de hoje. A taxa é arbitrária: não vem da
    `taxa_retorno_pre_fixada` dos aportes nem de qualquer outra coluna.

    Args:
        total_alocado (float): Valor total alocado hoje, em reais.

    Returns:
        list[dict]: Pontos com 'name' (mês) e 'rendimento' (ganho em milhões).
    """
    acumulado = total_alocado
    serie: list[dict] = []
    for mes in _MESES_PROJECAO:
        acumulado *= _TAXA_MENSAL
        serie.append(
            {"name": mes, "rendimento": formatacao.para_milhoes(acumulado - total_alocado)}
        )
    return serie
