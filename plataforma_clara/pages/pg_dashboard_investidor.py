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
                href="/explorar-blocos", # Rota a definir
                color="#94A3B8", 
                p="2", 
                border_radius="md", 
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"}
            ),
            rx.link(
                rx.hstack(rx.icon("file-text", size=20), rx.text("Relatórios Nuclea", size="3"), align="center", spacing="2"), 
                href="/relatorios", # Rota a definir
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
                rx.text(subtitulo, size="1", color="#10B981" if "+" in subtitulo else "#64748B"), # Verde se for rendimento
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

@rx.page(route="/dashboard-investidor", on_load=DashboardState.carregar_dados_dashboard)
def dashboard_investidor() -> rx.Component:
    """Página principal do Dashboard do Investidor."""
    
    return rx.flex(
        # 1. Menu Lateral
        sidebar_investidor(),
        
        # 2. Área Principal de Conteúdo
        rx.vstack(
            # Cabeçalho da Página
            rx.hstack(
                rx.vstack(
                    rx.heading("Meu Portfólio FIDC", size="8", weight="bold", color="#111827"),
                    rx.text("Acompanhe o rendimento e a transparência das suas alocações.", size="3", color="#4B5563"),
                    align_items="flex-start",
                ),
                rx.spacer(),
                # Investidor não cria bloco, talvez aqui fique um botão de "Baixar Relatório"
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
                card_metrica_investidor("Capital Investido", "R$ 1.500.000", "Referência: Hoje", "wallet", "#3B82F6"), # Azul
                card_metrica_investidor("Rendimento Projetado", "R$ 142.000", "+9.4% a.a.", "trending-up", "#10B981"), # Verde
                card_metrica_investidor("Blocos Alocados", "3 Blocos", "Diversificação OK", "pie-chart", "#8B5CF6"), # Roxo
                card_metrica_investidor("Score Médio de Reputação", "Alto (AA)", "Risco Nuclea", "shield-check", "#F59E0B"), # Âmbar
                columns=rx.breakpoints(initial="1", sm="2", lg="4"), 
                spacing="4",
                width="100%",
                mb="8",
            ),
            
            # Secção de Blocos (Placeholder por enquanto)
            rx.card(
                rx.heading("Meus Blocos de Liquidez", size="5", color="#111827", mb="4"),
                rx.text("Abaixo estarão os blocos onde seu capital foi alocado, com o Score Nuclea de cada um.", size="2", color="#64748B", mb="4"),
                
                rx.center(
                    rx.text("Lista de Blocos renderizada pelo Reflex (Baseado nos dados do Backend).", color="#9CA3AF"),
                    height="200px",
                    width="100%",
                    bg="#F3F4F6",
                    border_radius="md",
                    border="1px dashed #D1D5DB",
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