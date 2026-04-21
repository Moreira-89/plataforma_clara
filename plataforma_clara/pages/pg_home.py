import reflex as rx

def navbar_home() -> rx.Component:
    """Barra de navegação da Landing Page."""
    return rx.hstack(
        rx.hstack(
            rx.image(src="/logo_para_usar_fundo_escuro.png", height="80px", alt="Logo Clara"),
            align_items="center",
            spacing="2"
        ),
        rx.spacer(),
        rx.hstack(
            rx.link("Entrar", href="/login-usuario", color="#CBD5E1", weight="medium", _hover={"color": "white"}), 
            rx.button(
                "Criar Conta", 
                on_click=rx.redirect("/cadastro"), 
                color_scheme="blue", 
                variant="solid",
                size="3"
            ),
            spacing="6",
            align_items="center"
        ),
        width="100%",
        padding_y="1.5rem",
        padding_x=["2rem", "4rem", "8rem"],
        bg="#0F172A",
        border_bottom="1px solid #1E293B"
    )

def feature_card(icone: str, titulo: str, descricao: str) -> rx.Component:
    """Cartão de destaque para as funcionalidades principais."""
    return rx.card(
        rx.vstack(
            rx.icon(icone, size=36, color="#3B82F6", mb="3"),
            rx.heading(titulo, size="5", color="#111827", weight="bold"),
            rx.text(descricao, size="3", color="#4B5563", line_height="1.6"),
            align_items="start",
            spacing="2"
        ),
        variant="surface",
        padding="2rem",
        height="100%",
        border="1px solid #E5E7EB",
        box_shadow="0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        _hover={"transform": "translateY(-4px)", "transition": "transform 0.2s ease-in-out"}
    )

def home_page() -> rx.Component:
    """Página Inicial (Landing Page) da Plataforma Clara."""
    return rx.box(
        navbar_home(),
        
        rx.center(
            rx.vstack(
                rx.badge("MVP Acadêmico - FIAP + Nuclea", color_scheme="blue", variant="soft", size="2", mb="4"),
                rx.heading(
                    "O Novo Padrão de Transparência para FIDCs", 
                    size="9", 
                    weight="bold", 
                    color="white", 
                    text_align="center", 
                    line_height="1.1",
                    mb="4"
                ),
                rx.text(
                    "Elimine a assimetria de informação. Conecte Gestoras e Investidores através de rastreabilidade de ativos, "
                    "Score Nuclea preditivo e relatórios gerados por Inteligência Artificial.",
                    size="5", 
                    color="#94A3B8", 
                    text_align="center", 
                    max_width="800px", 
                    mb="8",
                    line_height="1.5"
                ),
                rx.hstack(
                    rx.button(
                        "Acessar Plataforma", 
                        on_click=rx.redirect("/login-usuario"), 
                        size="4", 
                        color_scheme="blue"
                    ),
                    rx.button(
                        "Saiba Mais", 
                        on_click=rx.redirect("/cadastro"), 
                        variant="outline", 
                        color_scheme="gray", 
                        size="4", 
                        color="white",
                        border_color="#475569",
                        _hover={"bg": "#1E293B"}
                    ),
                    spacing="4",
                    wrap="wrap",
                    justify="center"
                ),
                align_items="center",
                width="100%",
            ),
            width="100%",
            min_height="70vh",
            bg="#0F172A",
            background_image="radial-gradient(circle at 50% 0%, #1E293B 0%, #0F172A 70%)",
            padding_y="5rem",
            padding_x=["2rem", "4rem"],
        ),
        
        rx.box(
            rx.vstack(
                rx.heading("Inteligência e Segurança em Três Pilares", size="7", color="#111827", text_align="center", mb="8"),
                rx.grid(
                    feature_card(
                        "shield-check", 
                        "Rastreabilidade de Ativos", 
                        "Acompanhe o fluxo do capital. Saiba exatamente para quais empresas o seu aporte foi alocado e em qual proporção."
                    ),
                    feature_card(
                        "bar-chart-2", 
                        "Score de Reputação Nuclea", 
                        "Motor de Machine Learning que cruza dados internos e de mercado para avaliar o risco real das empresas sacadas."
                    ),
                    feature_card(
                        "sparkles", 
                        "Insight AI", 
                        "Relatórios de risco descritivos gerados automaticamente pelo Google Gemini, transformando dados brutos em decisões claras."
                    ),
                    columns=rx.breakpoints(initial="1", md="3"),
                    spacing="6",
                    width="100%",
                ),
                width="100%",
                max_width="1200px",
                margin="0 auto",
            ),
            width="100%",
            padding_y="6rem",
            padding_x=["2rem", "4rem"],
            bg="#F8FAFC",
        ),
        
        rx.center(
            rx.vstack(
                rx.divider(border_color="#E2E8F0", mb="4"),
                rx.text(
                    "© 2025 Plataforma Clara. Desenvolvido por Alliance Team (1TSCO) para o FIAP + Nuclea Challenge.", 
                    size="2", 
                    color="#64748B",
                    text_align="center"
                ),
                width="100%",
                max_width="1200px",
            ),
            width="100%",
            bg="#F8FAFC",
            padding_bottom="2rem",
            padding_x=["2rem", "4rem"],
        ),
        
        width="100vw",
        min_height="100vh",
        margin="0",
        spacing="0",
    )
