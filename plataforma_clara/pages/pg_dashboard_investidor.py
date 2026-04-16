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
            
            # KPIs usando as variáveis que já existem no State por enquanto
            rx.grid(
                card_kpi_investidor("Meu Patrimônio Total", DashboardState.total_alocado_geral, "dollar-sign"),
                card_kpi_investidor("Score da Minha Carteira", DashboardState.score_medio_geral, "shield-check"),
                card_kpi_investidor("Aportes Rastreáveis", DashboardState.quantidade_total_aportes, "briefcase"),
                columns="3",
                spacing="4",
                width="100%",
                margin_bottom="8",
            ),

            rx.grid(
                rx.card(
                    rx.heading("Ranking de Reputação (Empresas)", size="5", margin_bottom="4"),
                    # Tabela consumindo o Mock do State
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("Empresa"),
                                rx.table.column_header_cell("Score"),
                                rx.table.column_header_cell("Status"),
                            )
                        ),
                        rx.table.body(
                            rx.foreach(
                                DashboardState.ranking_empresas_mock,
                                lambda item: rx.table.row(
                                    rx.table.cell(item["empresa"]),
                                    rx.table.cell(item["score"]),
                                    rx.table.cell(item["status"]),
                                )
                            )
                        )
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.heading("Clara Assistant - Insight AI", size="5", margin_bottom="4"),
                    rx.text(
                        DashboardState.insight_ia, 
                        color="gray",
                        font_style="italic"
                    ),
                    width="100%",
                ),
                columns="2",
                spacing="4",
                width="100%",
            ),
            
            width="100%",
            padding_y="8",
        ),
        size="4",
    )