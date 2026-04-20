import reflex as rx
from plataforma_clara.states.dashboard_state import DashboardState


def sidebar_investidor() -> rx.Component:
    """Componente de Menu Lateral para o Investidor."""
    return rx.vstack(
        # Logótipo / Branding
        rx.vstack(
            rx.heading("Clara", size="7", weight="bold", color="white"),
            rx.text("Portal do Investidor", size="2", color="#94A3B8"),
            align_items="flex-start",
            mb="6",
            width="100%",
        ),
        
        # Links de Navegação
        rx.vstack(
            rx.link(
                rx.hstack(rx.icon("pie-chart", size=20), rx.text("Meu Portfólio", size="3"), align="center", spacing="2"), 
                href="/dashboard-investidor", 
                color="white", 
                p="2", 
                bg="#1E293B", # Item ativo
                border_radius="md", 
                width="100%",
                _hover={"text_decoration": "none"}
            ),
            rx.link(
                rx.hstack(rx.icon("layers", size=20), rx.text("Explorar Blocos", size="3"), align="center", spacing="2"), 
                href="/explorar-blocos", 
                color="#94A3B8", 
                p="2", 
                border_radius="md", 
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"}
            ),
            rx.link(
                rx.hstack(rx.icon("file-text", size=20), rx.text("Relatórios Nuclea", size="3"), align="center", spacing="2"), 
                href="/relatorios", 
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
        
        # Botão de Logout
        rx.link(
            rx.hstack(rx.icon("log-out", size=20), rx.text("Sair", size="3"), align="center", spacing="2"), 
            href="/", 
            color="#EF4444",
            p="2", 
            border_radius="md", 
            width="100%",
            _hover={"bg": "#FEF2F2", "text_decoration": "none"}
        ),
        
        bg="#0F172A",
        width=["100%", "250px"],
        height="100vh",
        padding="1.5rem",
        position=["relative", "sticky"],
        top="0",
    )

def card_metrica_investidor(titulo: str, valor: str, subtitulo: str, icone: str, cor_icone: str) -> rx.Component:
    """Componente reutilizável para os cartões de KPIs do Investidor."""
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(titulo, size="2", color="#64748B", weight="medium"),
                rx.heading(valor, size="6", color="#111827", weight="bold"),
                rx.text(subtitulo, size="1", color="#10B981" if "+" in subtitulo else "#64748B"), 
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

def criar_linha_transparencia_investidor(item: dict) -> rx.Component:
    """Função auxiliar para renderizar cada linha de transparência (empresa) do investidor."""
    # A variável 'score' é um número no backend, precisamos converter para string e usar lógica simples para cor
    score_val = item["score"].to(float)
    cor_score = rx.cond(score_val >= 80, "green", rx.cond(score_val >= 50, "yellow", "red"))
    score_txt = rx.cond(score_val >= 80, "A+", rx.cond(score_val >= 50, "B+", "C-"))

    return rx.table.row(
        rx.table.cell(rx.text(item["empresa"], weight="bold", color="#111827")),
        rx.table.cell(rx.badge(item["bloco"], color_scheme="blue", variant="soft")),
        rx.table.cell(rx.text(item["valor"], weight="medium", color="#111827")),
        rx.table.cell(rx.text("+10.0% a.a.", color="#10B981", weight="bold")), # Simulando rentabilidade
        rx.table.cell(rx.badge(score_txt, color_scheme=cor_score, variant="solid")),
        rx.table.cell(rx.badge("Ativo", color_scheme="green", variant="soft")),
        rx.table.cell(
            rx.button("Análise Completa", size="1", variant="outline", color_scheme="gray", color="#111827",
                      on_click=rx.redirect("/relatorios"))
        ),
    )


@rx.page(route="/dashboard-investidor", on_load=DashboardState.carregar_dados_dashboard)
def dashboard_investidor() -> rx.Component:
    """Página principal do Dashboard do Investidor."""
    
    return rx.flex(
        sidebar_investidor(),
        
        rx.vstack(
            # Cabeçalho da Página
            rx.hstack(
                rx.vstack(
                    rx.heading("Meu Portfólio FIDC", size="8", weight="bold", color="#111827"),
                    rx.text("Acompanhe o rendimento e a transparência das suas alocações.", size="3", color="#4B5563"),
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
            
            # Grid de Métricas (KPIs)
            rx.grid(
                card_metrica_investidor("Capital Investido", DashboardState.patrimonio_total_investidor, "Referência: Hoje", "wallet", "#3B82F6"),
                card_metrica_investidor("Total Aportes", DashboardState.quantidade_total_aportes.to_string(), "Histórico Ativo", "layers", "#10B981"),
                card_metrica_investidor("Blocos Alocados", DashboardState.dados_blocos.length().to_string(), "Diversificação OK", "pie-chart", "#8B5CF6"),
                card_metrica_investidor("Score Médio", DashboardState.score_medio_geral.to_string(), "Risco Nuclea", "shield-check", "#F59E0B"),
                columns=rx.breakpoints(initial="1", sm="2", lg="4"), 
                spacing="4",
                width="100%",
                mb="8",
            ),
            
            # Gráficos Analíticos (Recharts)
            rx.grid(
                rx.card(
                    rx.heading("Rendimento Projetado (em Milhões de R$)", size="4", mb="4", color="#111827"),
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
                    rx.heading("Diversificação do Portfólio (em Milhões de R$)", size="4", mb="4", color="#111827"),
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
            
            # Tabela de Portfólio Substituindo o Placeholder
            rx.card(
                rx.hstack(
                    rx.heading("Transparência do Portfólio (Empresas Sacadas)", size="5", color="#111827"),
                    rx.spacer(),
                    rx.input(placeholder="Buscar empresa...", size="2", width="250px"),
                    width="100%",
                    mb="4",
                    align_items="center"
                ),
                rx.text("Acompanhe a alocação do seu capital e o Score Nuclea em tempo real.", size="2", color="#64748B", mb="4"),
                
                # Tabela Reflex Customizada
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Empresa Sacada", color="#111827"),
                            rx.table.column_header_cell("Bloco / Setor", color="#111827"),
                            rx.table.column_header_cell("Capital Alocado (R$)", color="#111827"),
                            rx.table.column_header_cell("Rentabilidade", color="#111827"),
                            rx.table.column_header_cell("Score Nuclea (ML)", color="#111827"),
                            rx.table.column_header_cell("Status", color="#111827"),
                            rx.table.column_header_cell("Ações", color="#111827"),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DashboardState.tabela_transparencia_investidor,
                            criar_linha_transparencia_investidor
                        )
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