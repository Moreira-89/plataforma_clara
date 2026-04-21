import reflex as rx
from plataforma_clara.states.dashboard_state import DashboardState
from plataforma_clara.states.autenticacao_state import AutenticacaoState


def sidebar_gestora() -> rx.Component:
    """Componente de Menu Lateral para a Gestora."""
    return rx.vstack(
        rx.vstack(
            rx.image(src="/logo_para_usar_fundo_escuro.png", height="80px", alt="Logo Clara"),
            rx.text("Portal da Gestora", size="2", color="#94A3B8", mt="2"),
            align_items="flex-start",
            mb="6",
            width="100%",
        ),
        
        rx.vstack(
            rx.link(
                rx.hstack(rx.icon("layout-dashboard", size=20), rx.text("Visão Geral", size="3"), align="center", spacing="2"), 
                href="/dashboard-gestora", 
                color="white", 
                p="2", 
                bg="#1E293B",
                border_radius="md", 
                width="100%",
                _hover={"text_decoration": "none"}
            ),
            rx.link(
                rx.hstack(rx.icon("upload", size=20), rx.text("Ingestão de Dados", size="3"), align="center", spacing="2"), 
                href="/ingestao-dados", 
                color="#94A3B8", 
                p="2", 
                border_radius="md", 
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"}
            ),
            spacing="2",
            width="100%",
        ),
        
        rx.spacer(),
        
        rx.button(
            rx.hstack(rx.icon("log-out", size=20), rx.text("Sair", size="3"), align="center", spacing="2"), 
            on_click=AutenticacaoState.fazer_logout,
            color="#EF4444",
            p="2", 
            border_radius="md", 
            width="100%",
            justify_content="flex-start",
            variant="ghost",
            _hover={"bg": "#FEF2F2"}
        ),
        
        bg="#0F172A",
        width=["100%", "250px"],
        height="100vh",
        padding="1.5rem",
        position=["relative", "sticky"],
        top="0",
    )

def card_metrica(titulo: str, valor: str, icone: str, cor_icone: str) -> rx.Component:
    """Componente reutilizável para os cartões de KPIs."""
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(titulo, size="2", color="#64748B", weight="medium"),
                rx.heading(valor, size="6", color="#0F172A", weight="bold"),
                align_items="start",
                spacing="1",
            ),
            rx.icon(icone, size=32, color=cor_icone),
            justify="between",
            width="100%",
        ),
        variant="surface",
        width="100%",
        border="1px solid #E5E7EB",
        box_shadow="0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    )


@rx.page(route="/dashboard-gestora", on_load=DashboardState.carregar_dados_gestora)
def dashboard_gestora() -> rx.Component:
    """Página principal do Dashboard da Gestora."""
    
    return rx.flex(
        sidebar_gestora(),
        
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Visão Geral do FIDC", size="8", weight="bold", color="#111827"),
                    rx.text("Acompanhe a liquidez, alocações e o risco da sua carteira.", size="3", color="#4B5563"),
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.button(
                    rx.icon("plus", size=18),
                    "Novo Bloco",
                    color_scheme="blue",
                    size="3",
                ),
                width="100%",
                align_items="center",
                mb="6",
            ),
            
            rx.grid(
                card_metrica("Total sob Gestão (AUM)", DashboardState.patrimonio_total_gestora_formatado, "dollar-sign", "#10B981"),
                card_metrica("Blocos de Liquidez Ativos", DashboardState.qtd_blocos_ativos, "layers", "#3B82F6"),
                card_metrica("Risco Médio da Carteira", DashboardState.classificacao_risco_medio, "shield-check", "#8B5CF6"),
                card_metrica("Inadimplência Projetada", DashboardState.inadimplencia_projetada, "trending-down", "#EF4444"),
                columns=rx.breakpoints(initial="1", sm="2", lg="4"),
                spacing="4",
                width="100%",
                mb="8",
            ),
            
            rx.grid(
                rx.card(
                    rx.heading("Evolução do Volume Total (em Milhões de R$)", size="4", mb="4", color="#111827"),
                    rx.recharts.line_chart(
                        rx.recharts.line(
                            data_key="volume", stroke="#10B981", type_="monotone"
                        ),
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
                    rx.heading("Distribuição de Aportes (em Milhões de R$)", size="4", mb="4", color="#111827"),
                    rx.recharts.bar_chart(
                        rx.recharts.bar(
                            data_key="alocado", fill="#3B82F6"
                        ),
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
                    rx.heading("Alocação por Bloco (em Milhões de R$)", size="4", mb="4", color="#111827"),
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
            
            rx.card(
                rx.hstack(
                    rx.heading("Distribuição de Aportes Recentes", size="5", color="#111827"),
                    rx.spacer(),
                    rx.input(placeholder="Buscar empresa ou CNPJ...", size="2", width="250px"),
                    width="100%",
                    mb="4",
                    align_items="center"
                ),
                
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Empresa Sacada", color="#111827"),
                            rx.table.column_header_cell("Valor Alocado (R$)", color="#111827"),
                            rx.table.column_header_cell("Score Nuclea (ML)", color="#111827"),
                            rx.table.column_header_cell("Status Atual", color="#111827"),
                            rx.table.column_header_cell("Ações", color="#111827"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DashboardState.tabela_aportes_gestora,
                            lambda item: rx.table.row(
                                rx.table.cell(
                                    rx.vstack(
                                        rx.text(item["empresa"], weight="bold", color="#111827"),
                                        rx.text(item["cnpj"], size="1", color="#6B7280"),
                                        align_items="start",
                                        spacing="0",
                                    )
                                ),
                                rx.table.cell(rx.text(item["valor"], weight="medium", color="#111827")),
                                rx.table.cell(rx.badge(item["risco"], variant="soft")),
                                rx.table.cell(rx.badge(item["status"], variant="solid")),
                                rx.table.cell(
                                    rx.button("Detalhes", size="1", variant="outline", color_scheme="gray", color="#111827")
                                ),
                            ),
                        ),
                    ),
                    width="100%",
                    variant="surface",
                ),
                
                width="100%",
                variant="surface",
                border="1px solid #E5E7EB",
            ),
            
            width="100%",
            padding=["2rem", "3rem"],
            align_items="flex-start",
        ),
        
        direction=rx.breakpoints(initial="column", sm="row"),
        width="100vw",
        min_height="100vh",
        bg="#F9FAFB",
        spacing="0",
    )
