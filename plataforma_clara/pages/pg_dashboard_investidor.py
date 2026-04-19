import reflex as rx
from plataforma_clara.states.dashboard_state import DashboardState


def card_kpi_investidor(titulo: str, valor: rx.Var, icone: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.icon(tag=icone, size=30, color=rx.color("green", 9)),
            rx.vstack(
                rx.text(titulo, size="3", weight="bold", color="gray"),
                rx.heading(valor, size="6"),
                align_items="start",
            ),
            spacing="4",
        ),
        width="100%",
        box_shadow="sm",
    )


@rx.page(route="/dashboard-investidor", on_load=DashboardState.carregar_dados_dashboard)
def dashboard_investidor() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Painel do Investidor", size="8", margin_bottom="4"),

            # ── KPIs Pessoais ────────────────────────────────────────────────
            rx.grid(
                card_kpi_investidor(
                    "Meu Patrimônio Total",
                    DashboardState.patrimonio_total_investidor,
                    "dollar-sign",
                ),
                card_kpi_investidor(
                    "Score Médio da Carteira",
                    DashboardState.score_medio_geral,
                    "shield-check",
                ),
                card_kpi_investidor(
                    "Aportes Rastreáveis",
                    DashboardState.quantidade_total_aportes,
                    "briefcase",
                ),
                columns="3",
                spacing="4",
                width="100%",
                margin_bottom="8",
            ),

            # ── Gráfico de Alocação + Insight IA ────────────────────────────
            rx.grid(
                rx.card(
                    rx.heading(
                        "Alocação por Bloco de Liquidez",
                        size="5",
                        margin_bottom="4",
                    ),
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=DashboardState.alocacao_blocos_investidor,
                            data_key="value",
                            name_key="name",
                            cx="50%",
                            cy="50%",
                            fill="#8884d8",
                            label=True,
                        ),
                        rx.recharts.legend(),
                        rx.recharts.graphing_tooltip(),
                        width="100%",
                        height=300,
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.heading(
                        "Clara Assistant — Insight AI",
                        size="5",
                        margin_bottom="4",
                    ),
                    rx.text(
                        DashboardState.insight_ia,
                        color="gray",
                        font_style="italic",
                    ),
                    width="100%",
                ),
                columns="2",
                spacing="4",
                width="100%",
                margin_bottom="8",
            ),

            # ── Tabela de Transparência (Rastreabilidade) ────────────────────
            rx.card(
                rx.heading(
                    "Rastreabilidade — Destino do Seu Dinheiro",
                    size="5",
                    margin_bottom="4",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Empresa Sacada"),
                            rx.table.column_header_cell("Bloco (Gema)"),
                            rx.table.column_header_cell("Score ML"),
                            rx.table.column_header_cell("Valor Alocado"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            DashboardState.tabela_transparencia_investidor,
                            lambda item: rx.table.row(
                                rx.table.cell(item["empresa"]),
                                rx.table.cell(item["bloco"]),
                                rx.table.cell(item["score"]),
                                rx.table.cell(item["valor"]),
                            ),
                        )
                    ),
                ),
                width="100%",
            ),

            width="100%",
            padding_y="8",
        ),
        size="4",
    )