"""
Página de geração de Relatório Consolidado de Investimentos.

Permite ao investidor selecionar o tipo de relatório, acionar a geração via IA
(ChatGroq) e fazer download do PDF com análise consolidada de todos os seus blocos.
"""

import reflex as rx

from plataforma_clara.components.sidebar import sidebar_investidor
from plataforma_clara.states.assistente_ia_state import AssistenteIAState


# -----------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# -----------------------------------------------------------------------------


def pg_relatorios() -> rx.Component:
    """
    Página de relatórios do Portal do Investidor.

    COMO FUNCIONA:
        1. Seleção — O investidor escolhe o tipo de relatório via rx.select.
        2. Geração — Ao clicar em "Gerar", AssistenteIAState.gerar_e_baixar_relatorio
           é acionado. Ele executa a geração em thread separada (evitando travamento da UI)
           e, ao concluir, dispara rx.download para o browser.
        3. Feedback — rx.cond alterna entre o spinner de carregamento e o botão normal,
           e exibe o callout de mensagem apenas quando há conteúdo (mensagem != "").
    """
    return rx.flex(
        # Sidebar com item "Relatórios Nuclea" marcado como ativo
        sidebar_investidor(pagina_ativa="relatorios"),

        rx.center(
            rx.vstack(
                rx.heading(
                    "Relatório Consolidado de Investimentos",
                    size="8",
                    weight="bold",
                    color=rx.color("gray", 12),
                    text_align="center",
                ),
                rx.text(
                    "Selecione o relatório, gere a análise da IA e baixe o PDF.",
                    size="4",
                    color=rx.color("gray", 10),
                    text_align="center",
                ),
                rx.card(
                    rx.vstack(
                        rx.text(
                            "1) Selecione o tipo de relatório",
                            size="2",
                            weight="bold",
                            color=rx.color("gray", 11),
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
                            color=rx.color("gray", 10),
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
                        # Exibe callout apenas quando há mensagem — rx.cond avalia no browser
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
                    border="1px solid var(--gray-5)",
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
            bg=rx.color("gray", 2),
        ),

        direction=rx.breakpoints(initial="column", sm="row"),
        width="100vw",
        min_height="100vh",
        spacing="0",
    )
