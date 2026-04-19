import reflex as rx
from plataforma_clara.states.dashboard_state import DashboardState


def card_kpi(titulo: str, valor: rx.Var, icone: str) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.icon(tag=icone, size=30, color=rx.color("blue", 9)),
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


@rx.page(route="/dashboard-gestora", on_load=DashboardState.carregar_dados_gestora)
def dashboard_gestora() -> rx.Component:
    return rx.container(
        rx.vstack(
            # ── Header com filtro ────────────────────────────────────────────
            rx.hstack(
                rx.heading("Painel da Gestora", size="8"),
                rx.spacer(),
                rx.button(
                    "Novo Upload",
                    on_click=rx.redirect("/ingestao-dados"),
                    color_scheme="blue",
                    variant="soft",
                ),
                rx.select(
                    DashboardState.lista_nomes_blocos,
                    value=DashboardState.bloco_selecionado_gestora,
                    on_change=DashboardState.set_bloco_selecionado_gestora,
                    placeholder="Filtrar por Bloco",
                    width="250px",
                ),
                width="100%",
                align_items="center",
                margin_bottom="4",
            ),

            # ── KPIs Globais ─────────────────────────────────────────────────
            rx.grid(
                card_kpi(
                    "AUM (Patrimônio Global)",
                    DashboardState.patrimonio_total_gestora_formatado,
                    "dollar-sign",
                ),
                card_kpi(
                    "Score Médio da Carteira",
                    DashboardState.score_medio_geral,
                    "shield-check",
                ),
                card_kpi(
                    "Aportes Rastreáveis",
                    DashboardState.quantidade_total_aportes,
                    "briefcase",
                ),
                columns="3",
                spacing="4",
                width="100%",
                margin_bottom="8",
            ),

            # ── Gráficos: Score por Bloco + Concentração ─────────────────────
            rx.grid(
                rx.card(
                    rx.heading(
                        "Saúde dos Blocos — Score Médio por Gema",
                        size="5",
                        margin_bottom="4",
                    ),
                    rx.recharts.bar_chart(
                        rx.recharts.bar(
                            data_key="score_medio",
                            fill=rx.color("blue", 7),
                        ),
                        rx.recharts.x_axis(data_key="bloco"),
                        rx.recharts.y_axis(),
                        rx.recharts.graphing_tooltip(),
                        data=DashboardState.score_medio_blocos,
                        width="100%",
                        height=300,
                    ),
                    width="100%",
                ),
                rx.card(
                    rx.heading(
                        "Concentração — Volume por Bloco",
                        size="5",
                        margin_bottom="4",
                    ),
                    rx.recharts.pie_chart(
                        rx.recharts.pie(
                            data=DashboardState.dados_grafico_pizza,
                            data_key="value",
                            name_key="name",
                            cx="50%",
                            cy="50%",
                            fill=rx.color("blue", 7),
                            label=True,
                        ),
                        rx.recharts.legend(),
                        rx.recharts.graphing_tooltip(),
                        width="100%",
                        height=300,
                    ),
                    width="100%",
                ),
                columns="2",
                spacing="4",
                width="100%",
                margin_bottom="8",
            ),

            # ── Insight IA ───────────────────────────────────────────────────
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
                margin_bottom="8",
            ),

            # ── Ranking de Reputação Geral ───────────────────────────────────
            rx.card(
                rx.heading(
                    "Ranking de Reputação — Todas as Empresas",
                    size="5",
                    margin_bottom="4",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Empresa Sacada"),
                            rx.table.column_header_cell("Bloco (Gema)"),
                            rx.table.column_header_cell("Score Médio ML"),
                            rx.table.column_header_cell("Volume Total"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(
                            DashboardState.ranking_empresas_gestora,
                            lambda item: rx.table.row(
                                rx.table.cell(item["empresa"]),
                                rx.table.cell(item["bloco"]),
                                rx.table.cell(item["score_medio"]),
                                rx.table.cell(item["volume"]),
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