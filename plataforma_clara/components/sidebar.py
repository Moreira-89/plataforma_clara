"""
Componentes de menu lateral (Sidebar) reutilizáveis da Plataforma Clara.

Centraliza os dois menus laterais da plataforma — Portal do Investidor e Portal
da Gestora — que eram anteriormente duplicados em cada página. Usar um único módulo
garante consistência visual e facilita futuras alterações (basta editar aqui).
"""

import reflex as rx

from plataforma_clara.states.autenticacao_state import AutenticacaoState


# -----------------------------------------------------------------------------
# COMPONENTE INTERNO: ITEM DE NAVEGAÇÃO
# -----------------------------------------------------------------------------


def _nav_link(
    icone: str,
    label: str,
    href: str,
    ativo: bool = False,
) -> rx.Component:
    """
    Renderiza um item de link de navegação na sidebar.

    Args:
        icone (str): Nome do ícone Lucide (ex: 'pie-chart', 'layers').
        label (str): Texto do link exibido ao lado do ícone.
        href (str): URL de destino ao clicar.
        ativo (bool): Se True, aplica o estilo de item selecionado (fundo destacado).

    Returns:
        rx.Component: Link estilizado com ícone e label.
    """
    # O item ativo recebe fundo #1E293B (cinza-azulado) e texto branco.
    # Os inativos usam #94A3B8 com hover para branco, proporcionando feedback visual claro.
    cor_texto = "white" if ativo else "#94A3B8"
    bg_ativo = {"bg": "#1E293B"} if ativo else {}

    return rx.link(
        rx.hstack(
            rx.icon(icone, size=20),
            rx.text(label, size="3"),
            align="center",
            spacing="2",
        ),
        href=href,
        color=cor_texto,
        p="2",
        border_radius="md",
        width="100%",
        _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"},
        **bg_ativo,
    )


# -----------------------------------------------------------------------------
# SIDEBARS PÚBLICAS
# -----------------------------------------------------------------------------


def sidebar_investidor(pagina_ativa: str = "") -> rx.Component:
    """
    Menu lateral do Portal do Investidor.

    COMO FUNCIONA:
        1. Logo e Subtítulo — Exibe o logo da plataforma com transform scale
           para ocupar o espaço visual correto sem alterar o layout.
        2. Links de Navegação — Três links principais; o ativo é identificado
           pelo parâmetro pagina_ativa e recebe estilo diferenciado.
        3. Botão Sair — Fixado no rodapé da sidebar com cor de alerta (vermelho)
           e hover branco para indicar ação destrutiva.

    Args:
        pagina_ativa (str): Slug da página atual — 'portfolio', 'blocos' ou 'relatorios'.

    Returns:
        rx.Component: Sidebar completa do Portal do Investidor.
    """
    return rx.vstack(
        # --- 1. LOGO E SUBTÍTULO ---
        rx.vstack(
            rx.image(
                src="/logo_para_usar_fundo_escuro.png",
                height="40px",
                alt="Logo Clara",
                transform="scale(2.5)",
                transform_origin="left center",
            ),
            rx.text("Portal do Investidor", size="2", color="#94A3B8", mt="2"),
            align_items="flex-start",
            mb="6",
            width="100%",
        ),

        # --- 2. LINKS DE NAVEGAÇÃO ---
        rx.vstack(
            _nav_link(
                "pie-chart",
                "Meu Portfólio",
                "/dashboard-investidor",
                ativo=(pagina_ativa == "portfolio"),
            ),
            _nav_link(
                "layers",
                "Explorar Blocos",
                "/explorar-blocos",
                ativo=(pagina_ativa == "blocos"),
            ),
            _nav_link(
                "file-text",
                "Relatórios Nuclea",
                "/relatorios",
                ativo=(pagina_ativa == "relatorios"),
            ),
            spacing="2",
            width="100%",
        ),

        rx.spacer(),

        # --- 3. BOTÃO SAIR ---
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
            # Hover com fundo levemente avermelhado — mantido claro para contrastar
            # com a sidebar escura, indicando ação destrutiva sem ser agressivo.
            _hover={"bg": "rgba(239, 68, 68, 0.1)", "color": "#DC2626"},
        ),

        bg="#0F172A",
        width=["100%", "250px"],
        height="100vh",
        padding="1.5rem",
        position=["relative", "sticky"],
        top="0",
    )


def sidebar_gestora(pagina_ativa: str = "") -> rx.Component:
    """
    Menu lateral do Portal da Gestora.

    COMO FUNCIONA:
        Mesma estrutura de sidebar_investidor, mas com os links do portal da gestora.
        Aceita pagina_ativa para marcar o item de navegação correto.

    Args:
        pagina_ativa (str): Slug da página atual — 'visao_geral' ou 'ingestao'.

    Returns:
        rx.Component: Sidebar completa do Portal da Gestora.
    """
    return rx.vstack(
        # Logo e subtítulo
        rx.vstack(
            rx.image(
                src="/logo_para_usar_fundo_escuro.png",
                height="40px",
                alt="Logo Clara",
                transform="scale(2.5)",
                transform_origin="left center",
            ),
            rx.text("Portal da Gestora", size="2", color="#94A3B8", mt="2"),
            align_items="flex-start",
            mb="6",
            width="100%",
        ),

        # Links de navegação
        rx.vstack(
            _nav_link(
                "layout-dashboard",
                "Visão Geral",
                "/dashboard-gestora",
                ativo=(pagina_ativa == "visao_geral"),
            ),
            _nav_link(
                "upload",
                "Ingestão de Dados",
                "/ingestao-dados",
                ativo=(pagina_ativa == "ingestao"),
            ),
            spacing="2",
            width="100%",
        ),

        rx.spacer(),

        # Botão Sair
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
            _hover={"bg": "rgba(239, 68, 68, 0.1)", "color": "#DC2626"},
        ),

        bg="#0F172A",
        width=["100%", "250px"],
        height="100vh",
        padding="1.5rem",
        position=["relative", "sticky"],
        top="0",
    )
