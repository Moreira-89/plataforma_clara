"""
Página do Dashboard da Gestora.

Exibe KPIs consolidados (AUM, blocos ativos, risco médio, inadimplência),
gráficos de evolução e distribuição, e a tabela de aportes recentes com
score Nuclea por empresa sacada.
"""

import reflex as rx

from plataforma_clara.components.sidebar import sidebar_gestora
from plataforma_clara.states.dashboard_state import DashboardState


# -----------------------------------------------------------------------------
# COMPONENTES INTERNOS
# -----------------------------------------------------------------------------


def card_metrica(titulo: str, valor: str, icone: str, cor_icone: str) -> rx.Component:
    """
    Cartão de KPI reutilizável para o dashboard da gestora.

    Usa tokens de cor do Radix em vez de hexadecimais hardcoded para garantir
    contraste adequado em qualquer tema. rx.color("gray", 12) equivale ao tom
    mais escuro do cinza disponível no Radix — garante legibilidade máxima.

    Args:
        titulo (str): Rótulo do KPI (ex: "Total sob Gestão").
        valor (str): Valor formatado a exibir (ex: "R$ 1.234.567,89").
        icone (str): Nome do ícone Lucide (ex: "dollar-sign").
        cor_icone (str): Cor hexadecimal do ícone decorativo.

    Returns:
        rx.Component: Card com título, valor destacado e ícone lateral.
    """
    return rx.card(
        rx.hstack(
            rx.vstack(
                # Subtítulo do KPI — usa tom médio do cinza Radix para legibilidade suave
                rx.text(titulo, size="2", color=rx.color("gray", 10), weight="medium"),
                # Valor principal — tom máximo do cinza para contraste absoluto com o fundo
                rx.heading(valor, size="6", color=rx.color("gray", 12), weight="bold"),
                align_items="start",
                spacing="1",
            ),
            rx.icon(icone, size=32, color=cor_icone),
            justify="between",
            width="100%",
        ),
        variant="surface",
        width="100%",
        border="1px solid var(--gray-5)",
        box_shadow="0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    )


# -----------------------------------------------------------------------------
# MAPEAMENTO DE CORES DE RISCO E STATUS
# -----------------------------------------------------------------------------


def _cor_risco(risco: str) -> str:
    """
    Mapeia o risco literal para um color_scheme do Radix.

    Usado no badge de risco da tabela de aportes. Retorna 'green' para A+/A/A-,
    'yellow' para B+/B e 'red' para C- (alto risco).

    Args:
        risco (str): Classificação literal (ex: "A+", "B", "C-").

    Returns:
        str: Nome do color_scheme do Radix UI.
    """
    if risco in ("A+", "A", "A-"):
        return "green"
    if risco in ("B+", "B"):
        return "yellow"
    return "red"


def criar_linha_tabela_gestora(item: dict) -> rx.Component:
    """
    Renderiza uma linha da tabela de aportes da gestora de forma dinâmica.

    Usa rx.cond para determinar as cores dos badges de forma reativa —
    diferente de condicionais Python que são avaliadas em tempo de compilação,
    rx.cond garante que a cor mude conforme o valor real do item no estado.

    Args:
        item (dict): Dict com chaves: empresa, cnpj, valor, risco, status.

    Returns:
        rx.Component: Linha de tabela com células formatadas.
    """
    # rx.cond é avaliado no runtime do browser, não em Python —
    # por isso funciona corretamente com dados dinâmicos do estado.
    cor_risco = rx.cond(
        item["risco"].to(str).contains("A"),
        "green",
        rx.cond(item["risco"].to(str).contains("B"), "yellow", "red"),
    )
    cor_status = rx.cond(
        item["status"].to(str) == "Adimplente",
        "green",
        rx.cond(item["status"].to(str) == "Atenção", "yellow", "red"),
    )

    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(item["empresa"], weight="bold", color=rx.color("gray", 12)),
                rx.text(item["cnpj"], size="1", color=rx.color("gray", 9)),
                align_items="start",
                spacing="0",
            )
        ),
        rx.table.cell(
            rx.text(item["valor"], weight="medium", color=rx.color("gray", 11))
        ),
        # variant="soft" garante legibilidade do badge em qualquer fundo
        rx.table.cell(rx.badge(item["risco"], color_scheme=cor_risco, variant="soft")),
        rx.table.cell(rx.badge(item["status"], color_scheme=cor_status, variant="soft")),
        rx.table.cell(
            rx.button("Detalhes", size="1", variant="outline", color_scheme="gray")
        ),
    )


# -----------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# -----------------------------------------------------------------------------


@rx.page(route="/dashboard-gestora", on_load=DashboardState.carregar_dados_gestora)
def dashboard_gestora() -> rx.Component:
    """
    Página principal do Dashboard da Gestora da Plataforma Clara.

    COMO FUNCIONA:
        1. on_load dispara DashboardState.carregar_dados_gestora ao montar a página.
        2. Gráficos de recharts consomem computed vars (@rx.var) do DashboardState,
           que são recalculados automaticamente quando os dados brutos mudam.
        3. A tabela usa rx.foreach + lambda para renderizar linhas dinamicamente;
           as cores dos badges são determinadas por rx.cond (reativo, não Python).
    """
    return rx.flex(
        # Sidebar com item "Visão Geral" marcado como ativo
        sidebar_gestora(pagina_ativa="visao_geral"),

        rx.vstack(
            # Cabeçalho da página
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Visão Geral do FIDC",
                        size="8",
                        weight="bold",
                        color=rx.color("gray", 12),
                    ),
                    rx.text(
                        "Acompanhe a liquidez, alocações e o risco da sua carteira.",
                        size="3",
                        color=rx.color("gray", 10),
                    ),
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.button(rx.icon("plus", size=18), "Novo Bloco", color_scheme="blue", size="3"),
                width="100%",
                align_items="center",
                mb="6",
            ),

            # Grade de KPIs
            rx.grid(
                card_metrica(
                    "Total sob Gestão (AUM)",
                    DashboardState.patrimonio_total_gestora_formatado,
                    "dollar-sign",
                    "#10B981",
                ),
                card_metrica(
                    "Blocos de Liquidez Ativos",
                    DashboardState.qtd_blocos_ativos,
                    "layers",
                    "#3B82F6",
                ),
                card_metrica(
                    "Risco Médio da Carteira",
                    DashboardState.classificacao_risco_medio,
                    "shield-check",
                    "#8B5CF6",
                ),
                card_metrica(
                    "Inadimplência Projetada",
                    DashboardState.inadimplencia_projetada,
                    "trending-down",
                    "#EF4444",
                ),
                columns=rx.breakpoints(initial="1", sm="2", lg="4"),
                spacing="4",
                width="100%",
                mb="8",
            ),

            # Gráficos
            rx.grid(
                rx.card(
                    rx.heading(
                        "Evolução do Volume Total (em Milhões de R$)",
                        size="4",
                        mb="4",
                        color=rx.color("gray", 12),
                    ),
                    rx.recharts.line_chart(
                        rx.recharts.line(data_key="volume", stroke="#10B981", type_="monotone"),
                        rx.recharts.x_axis(data_key="name"),
                        rx.recharts.y_axis(),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.graphing_tooltip(),
                        data=DashboardState.dados_evolucao_aum,
                        height=250,
                    ),
                    width="100%",
                    variant="surface",
                ),
                rx.card(
                    rx.heading(
                        "Distribuição de Aportes (em Milhões de R$)",
                        size="4",
                        mb="4",
                        color=rx.color("gray", 12),
                    ),
                    rx.recharts.bar_chart(
                        rx.recharts.bar(data_key="alocado", fill="#3B82F6"),
                        rx.recharts.x_axis(data_key="name"),
                        rx.recharts.y_axis(),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.graphing_tooltip(),
                        data=DashboardState.dados_distribuicao_aportes,
                        height=250,
                    ),
                    width="100%",
                    variant="surface",
                ),
                rx.card(
                    rx.heading(
                        "Alocação por Bloco (em Milhões de R$)",
                        size="4",
                        mb="4",
                        color=rx.color("gray", 12),
                    ),
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=DashboardState.dados_grafico_pizza,
                            data_key="value",
                            name_key="name",
                            cx="50%",
                            cy="50%",
                            inner_radius="60%",
                            outer_radius="80%",
                            fill="#8B5CF6",
                            label=True,
                        ),
                        rx.recharts.graphing_tooltip(),
                        height=250,
                    ),
                    width="100%",
                    variant="surface",
                ),
                columns=rx.breakpoints(initial="1", lg="3"),
                spacing="4",
                width="100%",
                mb="8",
            ),

            # Tabela de aportes
            rx.card(
                rx.hstack(
                    rx.heading(
                        "Distribuição de Aportes Recentes",
                        size="5",
                        color=rx.color("gray", 12),
                    ),
                    rx.spacer(),
                    rx.input(
                        placeholder="Buscar empresa ou CNPJ...", size="2", width="250px"
                    ),
                    width="100%",
                    mb="4",
                    align_items="center",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            # color=rx.color("gray", 11) garante legibilidade do cabeçalho
                            # independente do fundo do Radix Table (variant="surface")
                            rx.table.column_header_cell(
                                rx.text("Empresa Sacada", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Valor Alocado (R$)", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Score Nuclea (ML)", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Status Atual", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Ações", color=rx.color("gray", 11))
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DashboardState.tabela_aportes_gestora,
                            criar_linha_tabela_gestora,
                        ),
                    ),
                    width="100%",
                    variant="surface",
                ),
                width="100%",
                variant="surface",
                border="1px solid var(--gray-5)",
            ),

            width="100%",
            padding=["2rem", "3rem"],
            align_items="flex-start",
        ),

        direction=rx.breakpoints(initial="column", sm="row"),
        width="100vw",
        min_height="100vh",
        bg=rx.color("gray", 2),
        spacing="0",
    )
