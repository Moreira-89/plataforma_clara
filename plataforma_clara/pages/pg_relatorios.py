import reflex as rx

# from plataforma_clara.states.assistente_ia_state import AssistenteIAState # Estado para gerir o LLM

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
                color="#94A3B8", 
                p="2", 
                border_radius="md", 
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"}
            ),
            rx.link(
                rx.hstack(rx.icon("file-text", size=20), rx.text("Relatórios Nuclea", size="3"), align="center", spacing="2"), 
                href="/relatorios", 
                color="white", 
                p="2", 
                bg="#1E293B", # Item ativo
                border_radius="md", 
                width="100%",
                _hover={"text_decoration": "none"}
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



def pg_relatorios() -> rx.Component:
    """Página de Relatórios Insight AI para o Investidor."""
    
    from plataforma_clara.states.assistente_ia_state import AssistenteIAState
    
    return rx.flex(
        sidebar_investidor(),
        
        rx.flex(
            # Área Central: Geração de Relatório
            rx.vstack(
                rx.vstack(
                    rx.heading("Insight AI - Relatórios de Transparência", size="8", weight="bold", color="#111827"),
                    rx.text("Selecione um Bloco de Liquidez para gerar uma análise institucional aprofundada.", size="4", color="#4B5563"),
                    align_items="center",
                    text_align="center",
                    width="100%",
                    mb="8",
                ),
                
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("file-text", color="#8B5CF6", size=32),
                            rx.heading("Geração de Relatório Institucional PDF", size="6", color="#111827"),
                            align_items="center",
                            spacing="3",
                            mb="4"
                        ),
                        
                        rx.text("A nossa IA analisa o histórico completo do banco de dados, o risco setorial e o comportamento de pagamento para compor um PDF institucional assinado pela Insight AI.", color="#4B5563", mb="6"),
                        
                        rx.select(
                            ["Bloco Safira", "Bloco Rubi", "Bloco Esmeralda", "Bloco Diamante"],
                            placeholder="Selecione o Bloco de Liquidez...",
                            value=AssistenteIAState.bloco_selecionado,
                            on_change=AssistenteIAState.set_bloco_selecionado,
                            size="3",
                            width="100%",
                            mb="6",
                        ),
                        
                        rx.button(
                            rx.cond(
                                AssistenteIAState.is_loading,
                                rx.spinner(size="3"),
                                rx.hstack(
                                    rx.icon("download", size=20),
                                    rx.text("Gerar e Baixar Relatório PDF", size="4", weight="bold"),
                                    align_items="center",
                                    spacing="2"
                                )
                            ),
                            on_click=AssistenteIAState.gerar_e_baixar_relatorio,
                            size="4",
                            width="100%",
                            color_scheme="blue",
                            disabled=AssistenteIAState.is_loading,
                            cursor=rx.cond(AssistenteIAState.is_loading, "wait", "pointer"),
                        ),
                        
                        width="100%",
                        padding="3rem",
                        align_items="flex-start",
                    ),
                    variant="surface",
                    border="1px solid #E5E7EB",
                    width=["100%", "100%", "80%", "60%"],
                    margin="0 auto",
                    box_shadow="lg"
                ),
                width="100%",
                align_items="center",
                justify_content="center",
                height="100%",
                mt="10",
            ),
            
            direction="column",
            width="100%",
            padding=["2rem", "3rem"],
        ),
        
        direction=rx.breakpoints(initial="column", sm="row"),
        width="100vw",
        min_height="100vh",
        bg="#F9FAFB",
        spacing="0",
    )