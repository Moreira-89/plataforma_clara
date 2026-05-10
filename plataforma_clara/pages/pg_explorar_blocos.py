"""
Página de exploração de Blocos de Liquidez disponíveis.

Permite ao investidor filtrar e descobrir novos blocos por nome, setor e
Score Nuclea, visualizando volume, rentabilidade alvo e nota de crédito.
"""

import reflex as rx

from plataforma_clara.components.sidebar import sidebar_investidor
from plataforma_clara.states.explorar_blocos_state import ExplorarBlocosState


# -----------------------------------------------------------------------------
# COMPONENTES INTERNOS
# -----------------------------------------------------------------------------


def criar_card_bloco_dinamico(bloco: dict) -> rx.Component:
    """
    Card de resumo de um Bloco de Liquidez para a listagem.

    COMO FUNCIONA:
        Usa rx.cond para determinar o color_scheme do badge de score de forma
        reativa — o badge muda de cor automaticamente conforme o score do bloco.

    Args:
        bloco (dict): Dict com chaves: setor, score_literal, nome, volume,
                      rentabilidade, id_bloco.

    Returns:
        rx.Component: Card interativo com informações do bloco.
    """
    # rx.cond encadeado: A → green, B → yellow, outros → red
    cor_score = rx.cond(
        bloco["score_literal"].to(str).contains("A"),
        "green",
        rx.cond(bloco["score_literal"].to(str).contains("B"), "yellow", "red"),
    )

    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.badge(bloco["setor"], color_scheme="blue", variant="soft"),
                rx.spacer(),
                rx.badge(
                    "Score: ", bloco["score_literal"],
                    color_scheme=cor_score,
                    variant="soft",
                ),
                width="100%",
            ),
            rx.heading(bloco["nome"], size="5", color=rx.color("gray", 12), mt="2"),
            rx.divider(margin_y="2"),
            rx.hstack(
                rx.vstack(
                    rx.text("Volume Total", size="1", color=rx.color("gray", 9)),
                    rx.text(
                        bloco["volume"],
                        size="3",
                        weight="bold",
                        color=rx.color("gray", 11),
                    ),
                    align_items="start",
                    spacing="0",
                ),
                rx.spacer(),
                rx.vstack(
                    rx.text("Rent. Alvo (a.a.)", size="1", color=rx.color("gray", 9)),
                    rx.text(
                        bloco["rentabilidade"],
                        size="3",
                        weight="bold",
                        color="#10B981",
                    ),
                    align_items="end",
                    spacing="0",
                ),
                width="100%",
            ),
            rx.button(
                "Ver Detalhes do Bloco",
                width="100%",
                mt="4",
                color_scheme="blue",
                variant="soft",
                on_click=rx.redirect(f"/detalhes-bloco/{bloco['id_bloco']}"),
            ),
            align_items="start",
            width="100%",
        ),
        width="100%",
        variant="surface",
        border="1px solid var(--gray-5)",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        _hover={
            "box_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
            "border_color": rx.color("gray", 7),
        },
    )


# -----------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# -----------------------------------------------------------------------------


def explorar_blocos() -> rx.Component:
    """
    Página de exploração de Blocos de Liquidez do Portal do Investidor.

    COMO FUNCIONA:
        Os filtros (busca, setor, score) atualizam variáveis no ExplorarBlocosState.
        O computed var `blocos_filtrados` recalcula automaticamente a lista de cards
        sem precisar de nova consulta ao banco — tudo em memória no estado.
    """
    return rx.flex(
        # Sidebar com item "Explorar Blocos" marcado como ativo
        sidebar_investidor(pagina_ativa="blocos"),

        rx.vstack(
            # Cabeçalho
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Explorar Blocos de Liquidez",
                        size="8",
                        weight="bold",
                        color=rx.color("gray", 12),
                    ),
                    rx.text(
                        "Descubra novas oportunidades com base no Score de Reputação Nuclea.",
                        size="3",
                        color=rx.color("gray", 10),
                    ),
                    align_items="flex-start",
                ),
                width="100%",
                align_items="center",
                mb="4",
            ),

            # Filtros
            rx.card(
                rx.hstack(
                    rx.input(
                        placeholder="Buscar por nome do bloco...",
                        width=["100%", "400px"],
                        size="3",
                        on_change=ExplorarBlocosState.set_termo_busca,
                    ),
                    rx.select(
                        ["Todos os Setores", "Tecnologia", "Varejo", "Agronegócio", "Indústria", "Saúde"],
                        placeholder="Setor",
                        size="3",
                        on_change=ExplorarBlocosState.set_filtro_setor,
                    ),
                    rx.select(
                        ["Qualquer Score", "A+ a A-", "B+ a B-", "C+ ou menor"],
                        placeholder="Score Mínimo",
                        size="3",
                        on_change=ExplorarBlocosState.set_filtro_score,
                    ),
                    rx.spacer(),
                    rx.button(rx.icon("filter", size=16), "Filtrar", size="3", variant="surface"),
                    width="100%",
                    wrap="wrap",
                    spacing="4",
                ),
                width="100%",
                variant="ghost",
                mb="6",
                padding="0",
            ),

            # Grade de cards de blocos
            rx.grid(
                rx.foreach(
                    ExplorarBlocosState.blocos_filtrados,
                    criar_card_bloco_dinamico,
                ),
                columns=rx.breakpoints(initial="1", sm="2", lg="3"),
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
        bg=rx.color("gray", 2),
        spacing="0",
    )
