import reflex as rx

from plataforma_clara.states.assistente_ia_state import AssistenteIAState
from plataforma_clara.states.autenticacao_state import AutenticacaoState


def sidebar_investidor() -> rx.Component:
    """Componente de menu lateral do investidor."""
    return rx.vstack(
        rx.vstack(
            rx.heading("Clara", size="7", weight="bold", color="white"),
            rx.text("Portal do Investidor", size="2", color="#94A3B8"),
            align_items="flex-start",
            mb="6",
            width="100%",
        ),
        rx.vstack(
            rx.link(
                rx.hstack(
                    rx.icon("pie-chart", size=20),
                    rx.text("Meu Portfólio", size="3"),
                    align="center",
                    spacing="2",
                ),
                href="/dashboard-investidor",
                color="#94A3B8",
                p="2",
                border_radius="md",
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"},
            ),
            rx.link(
                rx.hstack(
                    rx.icon("layers", size=20),
                    rx.text("Explorar Blocos", size="3"),
                    align="center",
                    spacing="2",
                ),
                href="/explorar-blocos",
                color="#94A3B8",
                p="2",
                border_radius="md",
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"},
            ),
            rx.link(
                rx.hstack(
                    rx.icon("file-text", size=20),
                    rx.text("Relatórios Nuclea", size="3"),
                    align="center",
                    spacing="2",
                ),
                href="/relatorios",
                color="white",
                p="2",
                bg="#1E293B",
                border_radius="md",
                width="100%",
                _hover={"text_decoration": "none"},
            ),
            spacing="2",
            width="100%",
        ),
        rx.spacer(),
        rx.button(
            rx.hstack(
                rx.icon("log-out", size=20),
                rx.text("Sair", size="3"),
                align="center",
                spacing="2",
            ),
            on_click=AutenticacaoState.fazer_logout,
            color="#EF4444",
            p="2",
            border_radius="md",
            width="100%",
            justify_content="flex-start",
            variant="ghost",
            _hover={"bg": "#FEF2F2"},
        ),
        bg="#0F172A",
        width=["100%", "250px"],
        height="100vh",
        padding="1.5rem",
        position=["relative", "sticky"],
        top="0",
    )


def pg_relatorios() -> rx.Component:
    """Página de geração do relatório consolidado de investimentos."""
    return rx.flex(
        sidebar_investidor(),
        rx.center(
            rx.vstack(
                rx.heading(
                    "Relatório Consolidado de Investimentos",
                    size="8",
                    weight="bold",
                    color="#111827",
                    text_align="center",
                ),
                rx.text(
                    "Selecione o relatório, gere a análise da IA e baixe o PDF.",
                    size="4",
                    color="#4B5563",
                    text_align="center",
                ),
                rx.card(
                    rx.vstack(
                        rx.text(
                            "1) Selecione o tipo de relatório",
                            size="2",
                            weight="bold",
                            color="#334155",
                        ),
                        rx.select(
                            AssistenteIAState.opcoes_relatorio,
                            placeholder="Selecione...",
                            value=AssistenteIAState.relatorio_selecionado,
                            on_change=AssistenteIAState.set_relatorio_selecionado,
                            width="100%",
                            size="3",
                        ),
                        rx.text(
                            "2) Clique em gerar para baixar o PDF consolidado com todos os blocos do investidor logado.",
                            size="2",
                            color="#475569",
                        ),
                        rx.button(
                            rx.cond(
                                AssistenteIAState.is_loading,
                                rx.hstack(
                                    rx.spinner(size="2"),
                                    rx.text("Gerando relatório..."),
                                    spacing="2",
                                    align="center",
                                ),
                                rx.hstack(
                                    rx.icon("download", size=18),
                                    rx.text("Gerar e Baixar PDF", weight="bold"),
                                    spacing="2",
                                    align="center",
                                ),
                            ),
                            on_click=AssistenteIAState.gerar_e_baixar_relatorio,
                            width="100%",
                            size="3",
                            color_scheme="blue",
                            disabled=AssistenteIAState.is_loading,
                            cursor=rx.cond(AssistenteIAState.is_loading, "wait", "pointer"),
                        ),
                        rx.cond(
                            AssistenteIAState.mensagem_para_usuario != "",
                            rx.callout(
                                AssistenteIAState.mensagem_para_usuario,
                                icon="info",
                                color_scheme=rx.cond(
                                    AssistenteIAState.mensagem_para_usuario.to(str).contains("sucesso"),
                                    "green",
                                    "blue",
                                ),
                                width="100%",
                            ),
                        ),
                        spacing="4",
                        width="100%",
                        align_items="flex-start",
                ),
                width=["100%", "100%", "80%", "65%"],
                max_width="840px",
                border="1px solid #E5E7EB",
                variant="surface",
                box_shadow="0 10px 15px -3px rgb(0 0 0 / 0.08)",
            ),
                spacing="6",
                width="100%",
                max_width="980px",
                align_items="center",
            ),
            width="100%",
            padding=["2rem", "3rem"],
            bg="#F9FAFB",
        ),
        direction=rx.breakpoints(initial="column", sm="row"),
        width="100vw",
        min_height="100vh",
        spacing="0",
    )
