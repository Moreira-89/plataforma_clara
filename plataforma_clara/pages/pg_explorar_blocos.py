import reflex as rx
from plataforma_clara.states.dashboard_state import DashboardState # Para ligar aos dados reais no futuro

def sidebar_investidor() -> rx.Component:
    """Componente de Menu Lateral para o Investidor (Reutilizado)."""
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
                color="#94A3B8", 
                p="2", 
                border_radius="md", 
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"}
            ),
            rx.link(
                rx.hstack(rx.icon("layers", size=20), rx.text("Explorar Blocos", size="3"), align="center", spacing="2"), 
                href="/explorar-blocos", 
                color="white", 
                p="2", 
                bg="#1E293B", # Item ativo
                border_radius="md", 
                width="100%",
                _hover={"text_decoration": "none"}
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

def criar_card_bloco(nome: str, setor: str, volume: str, score_medio: str, rentabilidade: str) -> rx.Component:
    """Componente para renderizar o resumo de um Bloco de Liquidez."""
    
    # Lógica simples de cores baseada no score
    cor_score = "green" if "A" in score_medio else ("yellow" if "B" in score_medio else "red")
    
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(setor, color_scheme="blue", variant="soft"),
                rx.spacer(),
                rx.badge(f"Score: {score_medio}", color_scheme=cor_score, variant="solid"),
                width="100%",
            ),
            rx.heading(nome, size="5", color="#111827", mt="2"),
            rx.divider(margin_y="2"),
            
            rx.hstack(
                rx.vstack(
                    rx.text("Volume Total", size="1", color="#6B7280"),
                    rx.text(volume, size="3", weight="bold", color="#374151"),
                    align_items="start",
                    spacing="0"
                ),
                rx.spacer(),
                rx.vstack(
                    rx.text("Rent. Alvo (a.a.)", size="1", color="#6B7280"),
                    rx.text(rentabilidade, size="3", weight="bold", color="#10B981"),
                    align_items="end",
                    spacing="0"
                ),
                width="100%",
            ),
            
            rx.button(
                "Ver Detalhes do Bloco", 
                width="100%", 
                mt="4", 
                variant="outline", 
                color_scheme="gray",
                # on_click=lambda: rx.redirect(f"/detalhes-bloco/{id_bloco}") # Para navegação futura
            ),
            align_items="start",
            width="100%",
        ),
        width="100%",
        variant="surface",
        border="1px solid #E5E7EB",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        _hover={"box_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)", "border_color": "#CBD5E1"}, # Efeito de hover
    )

def explorar_blocos() -> rx.Component:
    """Página para o Investidor explorar os Blocos de Liquidez."""
    
    return rx.flex(
        sidebar_investidor(),
        
        rx.vstack(
            # Cabeçalho da Página
            rx.hstack(
                rx.vstack(
                    rx.heading("Explorar Blocos de Liquidez", size="8", weight="bold", color="#111827"),
                    rx.text("Descubra novas oportunidades com base no Score de Reputação Nuclea.", size="3", color="#4B5563"),
                    align_items="flex-start",
                ),
                width="100%",
                align_items="center",
                mb="4",
            ),
            
            # Barra de Pesquisa e Filtros
            rx.card(
                rx.hstack(
                    rx.input(
                        placeholder="Buscar por nome do bloco ou setor...", 
                        width=["100%", "400px"],
                        size="3",
                        # on_change=DashboardState.set_termo_busca
                    ),
                    rx.select(
                        ["Todos os Setores", "Tecnologia", "Varejo", "Agronegócio", "Indústria"],
                        placeholder="Setor",
                        size="3",
                        # on_change=DashboardState.set_filtro_setor
                    ),
                    rx.select(
                        ["Qualquer Score", "A+ a A-", "B+ a B-", "C+ ou menor"],
                        placeholder="Score Mínimo",
                        size="3",
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("filter", size=16), "Filtrar", size="3", variant="surface"),
                    width="100%",
                    wrap="wrap", # Permite que os elementos quebrem a linha em telas menores
                    spacing="4",
                ),
                width="100%",
                variant="ghost", # Sem borda, apenas agrupa os filtros
                mb="6",
                padding="0"
            ),
            
            # Grid de Blocos
            rx.grid(
                # Dados Mockados para visualização do design.
                criar_card_bloco("Bloco Safira - Tech", "Tecnologia", "R$ 12.5M", "A+", "14.5%"),
                criar_card_bloco("FIDC Master Varejo", "Varejo", "R$ 35.0M", "A-", "15.2%"),
                criar_card_bloco("Agro Exportação Q3", "Agronegócio", "R$ 8.2M", "B+", "16.0%"),
                criar_card_bloco("Indústria Pesada Sul", "Indústria", "R$ 22.1M", "B-", "17.5%"),
                criar_card_bloco("Serviços Logísticos Ex", "Logística", "R$ 5.5M", "A", "14.8%"),
                criar_card_bloco("Saúde & Pharma BR", "Saúde", "R$ 18.0M", "A+", "13.9%"),
                columns=rx.breakpoints(initial="1", sm="2", lg="3"), # 1 coluna (mobile), 2 (tablet), 3 (desktop)
                spacing="6",
                width="100%",
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