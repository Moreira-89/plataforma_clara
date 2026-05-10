"""
Página do Dashboard do Investidor.

Exibe KPIs pessoais (capital investido, total de aportes, blocos alocados, score médio),
gráficos de rendimento projetado e diversificação, e a tabela de transparência
com as empresas sacadas e o Score Nuclea de cada alocação.
"""

import reflex as rx

from plataforma_clara.components.sidebar import sidebar_investidor
from plataforma_clara.states.dashboard_state import DashboardState


# -----------------------------------------------------------------------------
# COMPONENTES INTERNOS
# -----------------------------------------------------------------------------


def card_metrica_investidor(
    titulo: str,
    valor: str,
    subtitulo: str,
    icone: str,
    cor_icone: str,
    subtitulo_positivo: bool = True,
) -> rx.Component:
    """
    Cartão de KPI do Portal do Investidor.

    Usa tokens de cor do Radix para garantir contraste. O parâmetro
    `subtitulo_positivo` controla a cor do subtítulo (verde = positivo,
    cinza = neutro). Diferente da versão anterior, não usa condicionais
    Python (que são avaliadas em compile time) — usa o parâmetro bool
    passado de forma determinística na construção da página.

    Args:
        titulo (str): Rótulo do KPI (ex: "Capital Investido").
        valor (str): Valor formatado (ex: "R$ 1.234.567,89").
        subtitulo (str): Contexto adicional (ex: "Referência: Hoje").
        icone (str): Nome do ícone Lucide.
        cor_icone (str): Cor hexadecimal do ícone decorativo.
        subtitulo_positivo (bool): Se True, subtítulo aparece em verde; caso contrário, cinza.

    Returns:
        rx.Component: Card com KPI e subtítulo colorido.
    """
    cor_subtitulo = "#10B981" if subtitulo_positivo else rx.color("gray", 9)

    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(titulo, size="2", color=rx.color("gray", 10), weight="medium"),
                rx.heading(valor, size="6", color=rx.color("gray", 12), weight="bold"),
                rx.text(subtitulo, size="1", color=cor_subtitulo),
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


def criar_linha_transparencia_investidor(item: dict) -> rx.Component:
    """
    Renderiza uma linha da tabela de transparência do investidor.

    Usa rx.cond para determinar cores e textos de forma reativa (avaliação
    no runtime do browser). O score é convertido para float via .to(float)
    antes de comparações numéricas.

    Args:
        item (dict): Dict com chaves: empresa, bloco, valor, score.

    Returns:
        rx.Component: Linha de tabela formatada com badges reativos.
    """
    # .to(float) é necessário porque o valor vem como Any do estado Reflex
    score_val = item["score"].to(float)
    cor_score = rx.cond(
        score_val >= 80,
        "green",
        rx.cond(score_val >= 50, "yellow", "red"),
    )
    score_txt = rx.cond(
        score_val >= 80,
        "A+",
        rx.cond(score_val >= 50, "B+", "C-"),
    )

    return rx.table.row(
        rx.table.cell(
            rx.text(item["empresa"], weight="bold", color=rx.color("gray", 12))
        ),
        rx.table.cell(
            rx.badge(item["bloco"], color_scheme="blue", variant="soft")
        ),
        rx.table.cell(
            rx.text(item["valor"], weight="medium", color=rx.color("gray", 11))
        ),
        rx.table.cell(
            rx.text("+10.0% a.a.", color="#10B981", weight="bold")
        ),
        rx.table.cell(
            # variant="soft" garante legibilidade em qualquer fundo (tema claro/escuro)
            rx.badge(score_txt, color_scheme=cor_score, variant="soft")
        ),
        rx.table.cell(
            rx.badge("Ativo", color_scheme="green", variant="soft")
        ),
        rx.table.cell(
            rx.button(
                "Análise Completa",
                size="1",
                variant="outline",
                color_scheme="gray",
                on_click=rx.redirect("/relatorios"),
            )
        ),
    )


# -----------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# -----------------------------------------------------------------------------


@rx.page(route="/dashboard-investidor", on_load=DashboardState.carregar_dados_dashboard)
def dashboard_investidor() -> rx.Component:
    """
    Página principal do Dashboard do Investidor da Plataforma Clara.

    COMO FUNCIONA:
        1. on_load dispara DashboardState.carregar_dados_dashboard ao montar a página.
           O evento busca dados filtrados pelo CPF/CNPJ do investidor logado.
        2. KPIs derivados via computed vars (@rx.var) no DashboardState — recalculados
           automaticamente quando os dados brutos mudam.
        3. Tabela de transparência usa rx.foreach + criar_linha_transparencia_investidor;
           as cores dos badges são determinadas por rx.cond (reativo, não Python).
    """
    return rx.flex(
        # Sidebar com item "Meu Portfólio" marcado como ativo
        sidebar_investidor(pagina_ativa="portfolio"),

        rx.vstack(
            # Cabeçalho
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Meu Portfólio FIDC",
                        size="8",
                        weight="bold",
                        color=rx.color("gray", 12),
                    ),
                    rx.text(
                        "Acompanhe o rendimento e a transparência das suas alocações.",
                        size="3",
                        color=rx.color("gray", 10),
                    ),
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("download", size=18),
                    "Exportar Dados",
                    color_scheme="gray",
                    variant="surface",
                    size="3",
                ),
                width="100%",
                align_items="center",
                mb="6",
            ),

            # Grade de KPIs
            rx.grid(
                card_metrica_investidor(
                    "Capital Investido",
                    DashboardState.patrimonio_total_investidor,
                    "Referência: Hoje",
                    "wallet",
                    "#3B82F6",
                    subtitulo_positivo=False,
                ),
                card_metrica_investidor(
                    "Total Aportes",
                    DashboardState.quantidade_total_aportes.to_string(),
                    "Histórico Ativo",
                    "layers",
                    "#10B981",
                    subtitulo_positivo=True,
                ),
                card_metrica_investidor(
                    "Blocos Alocados",
                    DashboardState.dados_blocos.length().to_string(),
                    "Diversificação OK",
                    "pie-chart",
                    "#8B5CF6",
                    subtitulo_positivo=True,
                ),
                card_metrica_investidor(
                    "Score Médio",
                    DashboardState.score_medio_geral.to_string(),
                    "Risco Nuclea",
                    "shield-check",
                    "#F59E0B",
                    subtitulo_positivo=False,
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
                        "Rendimento Projetado (em Milhões de R$)",
                        size="4",
                        mb="4",
                        color=rx.color("gray", 12),
                    ),
                    rx.recharts.line_chart(
                        rx.recharts.line(
                            data_key="rendimento", stroke="#10B981", type_="monotone"
                        ),
                        rx.recharts.x_axis(data_key="name"),
                        rx.recharts.y_axis(),
                        rx.recharts.cartesian_grid(stroke_dasharray="3 3"),
                        rx.recharts.graphing_tooltip(),
                        data=DashboardState.dados_rendimento_projetado,
                        height=250,
                    ),
                    width="100%",
                    variant="surface",
                ),
                rx.card(
                    rx.heading(
                        "Diversificação do Portfólio (em Milhões de R$)",
                        size="4",
                        mb="4",
                        color=rx.color("gray", 12),
                    ),
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=DashboardState.alocacao_blocos_investidor,
                            data_key="value",
                            name_key="name",
                            cx="50%",
                            cy="50%",
                            inner_radius="0%",
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
                columns=rx.breakpoints(initial="1", md="2"),
                spacing="4",
                width="100%",
                mb="8",
            ),

            # Tabela de transparência
            rx.card(
                rx.hstack(
                    rx.heading(
                        "Transparência do Portfólio (Empresas Sacadas)",
                        size="5",
                        color=rx.color("gray", 12),
                    ),
                    rx.spacer(),
                    rx.input(placeholder="Buscar empresa...", size="2", width="250px"),
                    width="100%",
                    mb="4",
                    align_items="center",
                ),
                rx.text(
                    "Acompanhe a alocação do seu capital e o Score Nuclea em tempo real.",
                    size="2",
                    color=rx.color("gray", 10),
                    mb="4",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Empresa Sacada", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Bloco / Setor", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Capital Alocado (R$)", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Rentabilidade", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Score Nuclea (ML)", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Status", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Ações", color=rx.color("gray", 11))
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DashboardState.tabela_transparencia_investidor,
                            criar_linha_transparencia_investidor,
                        )
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
