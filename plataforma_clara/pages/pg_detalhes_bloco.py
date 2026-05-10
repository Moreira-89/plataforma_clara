"""
Página de detalhes de um Bloco de Liquidez específico.

Exibe KPIs do bloco (volume, rentabilidade, score, prazo), painel de insights
e a tabela com a composição das empresas sacadas financiadas pelo bloco.
"""

import reflex as rx

from plataforma_clara.components.sidebar import sidebar_investidor
from plataforma_clara.states.detalhes_bloco_state import DetalhesBlocoState


# -----------------------------------------------------------------------------
# COMPONENTES INTERNOS
# -----------------------------------------------------------------------------


def card_metrica_detalhe(titulo: str, valor: str, icone: str, cor_icone: str) -> rx.Component:
    """
    Cartão de KPI para a página de detalhes do bloco.

    Usa tokens de cor Radix para garantir contraste adequado em qualquer tema.

    Args:
        titulo (str): Rótulo do KPI (ex: "Volume do Bloco").
        valor (str): Valor formatado (ex: "R$ 2.345.678,00").
        icone (str): Nome do ícone Lucide.
        cor_icone (str): Cor hexadecimal do ícone decorativo.

    Returns:
        rx.Component: Card de KPI com ícone lateral.
    """
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(titulo, size="2", color=rx.color("gray", 10), weight="medium"),
                rx.heading(valor, size="6", color=rx.color("gray", 12), weight="bold"),
                align_items="start",
                spacing="1",
            ),
            rx.icon(icone, size=28, color=cor_icone),
            justify="between",
            width="100%",
        ),
        variant="surface",
        width="100%",
        border="1px solid var(--gray-5)",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    )


def criar_linha_empresa_dinamica(empresa: dict) -> rx.Component:
    """
    Renderiza uma linha da tabela de composição de empresas sacadas do bloco.

    Usa rx.cond encadeado para determinar o color_scheme do badge de score
    de forma reativa, avaliada no runtime do browser.

    Args:
        empresa (dict): Dict com chaves: nome, cnpj, peso, valor, score.

    Returns:
        rx.Component: Linha de tabela com células formatadas.
    """
    cor_score = rx.cond(
        empresa["score"].to(str).contains("A"),
        "green",
        rx.cond(empresa["score"].to(str).contains("B"), "yellow", "red"),
    )

    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(empresa["nome"], weight="bold", color=rx.color("gray", 12)),
                rx.text(empresa["cnpj"], size="1", color=rx.color("gray", 9)),
                align_items="start",
                spacing="0",
            )
        ),
        rx.table.cell(rx.text(empresa["peso"], weight="medium", color=rx.color("gray", 11))),
        rx.table.cell(rx.text(empresa["valor"], color=rx.color("gray", 10))),
        # variant="soft" em vez de "solid" garante legibilidade com texto escuro
        rx.table.cell(rx.badge(empresa["score"], color_scheme=cor_score, variant="soft")),
        rx.table.cell(
            rx.button(rx.icon("search", size=14), size="1", variant="ghost", color_scheme="gray")
        ),
    )


# -----------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# -----------------------------------------------------------------------------


def pg_detalhes_bloco() -> rx.Component:
    """
    Página de Detalhes de um Bloco de Liquidez específico.

    COMO FUNCIONA:
        1. on_load (em plataforma_clara.py) dispara DetalhesBlocoState.carregar_detalhes,
           que lê o parâmetro [bloco_id] da URL e busca os dados no banco.
        2. KPIs (volume_total, rentabilidade_alvo, score_medio, prazo_medio) ficam
           disponíveis via variáveis de estado e são exibidos nos cards.
        3. A tabela de empresas usa rx.foreach para renderização dinâmica das linhas.
    """


    return rx.flex(
        # Sidebar sem item ativo (bloco é subpágina de "Explorar Blocos")
        sidebar_investidor(pagina_ativa="blocos"),

        rx.vstack(
            # Botão de navegação "Voltar"
            rx.link(
                rx.hstack(
                    rx.icon("arrow-left", size=16),
                    rx.text("Voltar para Explorar Blocos"),
                    align="center",
                    spacing="2",
                ),
                href="/explorar-blocos",
                color=rx.color("gray", 9),
                mb="4",
                _hover={"color": rx.color("gray", 12)},
            ),

            # Cabeçalho do bloco
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.heading(
                            "Bloco ",
                            DetalhesBlocoState.nome_bloco,
                            size="8",
                            weight="bold",
                            color=rx.color("gray", 12),
                        ),
                        rx.badge("Ativo", color_scheme="green", variant="soft", size="2"),
                        align="center",
                        spacing="3",
                    ),
                    rx.text("ID: ", DetalhesBlocoState.nome_bloco, size="3", color=rx.color("gray", 10)),
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.button("Alocar Capital", color_scheme="blue", size="3"),
                width="100%",
                align_items="center",
                mb="6",
            ),

            # Grade de KPIs do bloco
            rx.grid(
                card_metrica_detalhe(
                    "Volume do Bloco",
                    DetalhesBlocoState.volume_total,
                    "database",
                    "#3B82F6",
                ),
                card_metrica_detalhe(
                    "Rentabilidade Alvo",
                    DetalhesBlocoState.rentabilidade_alvo,
                    "trending-up",
                    "#10B981",
                ),
                card_metrica_detalhe(
                    "Score Nuclea Médio",
                    DetalhesBlocoState.score_medio,
                    "shield-check",
                    "#8B5CF6",
                ),
                card_metrica_detalhe(
                    "Prazo Médio (Duration)",
                    DetalhesBlocoState.prazo_medio,
                    "clock",
                    "#F59E0B",
                ),
                columns=rx.breakpoints(initial="1", sm="2", lg="4"),
                spacing="4",
                width="100%",
                mb="6",
            ),

            # Painel de composição de risco e insight IA
            rx.flex(
                rx.card(
                    rx.heading(
                        "Composição de Risco",
                        size="4",
                        color=rx.color("gray", 12),
                        mb="4",
                    ),
                    rx.center(
                        rx.vstack(
                            rx.icon("pie-chart", size=48, color=rx.color("gray", 7)),
                            rx.text(
                                "Gráfico de Distribuição renderizado via Recharts",
                                color=rx.color("gray", 8),
                                size="2",
                            ),
                            align="center",
                        ),
                        height="200px",
                        bg=rx.color("gray", 3),
                        border_radius="md",
                        border="1px dashed var(--gray-6)",
                    ),
                    width=["100%", "100%", "50%"],
                    variant="surface",
                ),
                rx.card(
                    rx.hstack(
                        rx.icon("sparkles", color="#8B5CF6", size=20),
                        rx.heading(
                            "Insight AI - Resumo",
                            size="4",
                            color=rx.color("gray", 12),
                        ),
                        align="center",
                        mb="4",
                    ),
                    rx.text(
                        "O bloco possui excelente qualidade de crédito, concentrado no setor selecionado. "
                        "A Inadimplência projetada é baixa e a carteira apresenta estabilidade no prazo "
                        "médio das operações. Recomenda-se acompanhamento contínuo da alocação das "
                        "empresas principais.",
                        size="2",
                        color=rx.color("gray", 10),
                        line_height="1.6",
                    ),
                    rx.link(
                        "Ver relatório completo",
                        href="/relatorios",
                        color="#2563EB",
                        size="2",
                        mt="4",
                        weight="bold",
                    ),
                    width=["100%", "100%", "50%"],
                    variant="surface",
                    bg=rx.color("violet", 1),
                    border="1px solid var(--violet-4)",
                ),
                direction=rx.breakpoints(initial="column", md="row"),
                spacing="6",
                width="100%",
                mb="6",
            ),

            # Tabela de composição da carteira
            rx.card(
                rx.hstack(
                    rx.heading(
                        "Composição da Carteira (Empresas Financiadas)",
                        size="5",
                        color=rx.color("gray", 12),
                    ),
                    rx.spacer(),
                    rx.input(
                        placeholder="Buscar CNPJ ou Empresa...", size="2", width="250px"
                    ),
                    width="100%",
                    mb="4",
                    align_items="center",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Empresa Sacada", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Peso (%)", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Valor Alocado (R$)", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Score Nuclea (ML)", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Ações", color=rx.color("gray", 11))
                            ),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DetalhesBlocoState.empresas_bloco,
                            criar_linha_empresa_dinamica,
                        )
                    ),
                    width="100%",
                    variant="surface",
                ),
                width="100%",
                variant="surface",
                border="1px solid var(--gray-5)",
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
