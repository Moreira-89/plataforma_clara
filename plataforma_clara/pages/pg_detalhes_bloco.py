import reflex as rx
from plataforma_clara.states.detalhes_bloco_state import DetalhesBlocoState
from plataforma_clara.states.autenticacao_state import AutenticacaoState

def sidebar_investidor() -> rx.Component:
    """Componente de Menu Lateral (Reutilizado para manter a navegação visual)."""
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
                bg="#1E293B", # Deixando 'Explorar' ativo como contexto
                p="2", 
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
        rx.button(
            rx.hstack(rx.icon("log-out", size=20), rx.text("Sair", size="3"), align="center", spacing="2"), 
            on_click=AutenticacaoState.fazer_logout,
            color="#EF4444",
            p="2", 
            border_radius="md", 
            width="100%",
            justify_content="flex-start",
            variant="ghost",
            _hover={"bg": "#FEF2F2"}
        ),
        bg="#0F172A",
        width=["100%", "250px"],
        height="100vh",
        padding="1.5rem",
        position=["relative", "sticky"],
        top="0",
    )

def card_metrica_detalhe(titulo: str, valor: str, icone: str, cor_icone: str) -> rx.Component:
    """Componente para os cartões de KPIs do Bloco."""
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.text(titulo, size="2", color="#64748B", weight="medium"),
                rx.heading(valor, size="6", color="#111827", weight="bold"),
                align_items="start",
                spacing="1",
            ),
            rx.icon(icone, size=28, color=cor_icone),
            justify="between",
            width="100%",
        ),
        variant="surface",
        width="100%",
        border="1px solid #E5E7EB",
        box_shadow="0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    )

def criar_linha_empresa_dinamica(empresa: dict) -> rx.Component:
    """Renderiza uma empresa (sacada) dinamicamente dentro da tabela do bloco."""
    cor_score = rx.cond(
        empresa["score"].to(str).contains("A"), "green",
        rx.cond(empresa["score"].to(str).contains("B"), "yellow", "red")
    )

    return rx.table.row(
        rx.table.cell(
            rx.vstack(
                rx.text(empresa["nome"], weight="bold", color="#111827"),
                rx.text(empresa["cnpj"], size="1", color="#6B7280"),
                align_items="start",
                spacing="0"
            )
        ),
        rx.table.cell(rx.text(empresa["peso"], weight="medium")),
        rx.table.cell(rx.text(empresa["valor"], color="#4B5563")),
        rx.table.cell(rx.badge(empresa["score"], color_scheme=cor_score, variant="solid")),
        rx.table.cell(
            rx.button(rx.icon("search", size=14), size="1", variant="ghost", color_scheme="gray")
        ),
    )

def pg_detalhes_bloco() -> rx.Component:
    """Página de Detalhes de um Bloco de Liquidez Específico."""
    
    bloco_id = DetalhesBlocoState.router.page.params.get("bloco_id", "")
    
    return rx.flex(
        sidebar_investidor(),
        
        rx.vstack(
            # Navegação (Voltar)
            rx.link(
                rx.hstack(rx.icon("arrow-left", size=16), rx.text("Voltar para Explorar Blocos"), align="center", spacing="2"),
                href="/explorar-blocos",
                color="#64748B",
                mb="4",
                _hover={"color": "#111827"}
            ),

            # Cabeçalho do Bloco
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        rx.heading("Bloco ", DetalhesBlocoState.nome_bloco, size="8", weight="bold", color="#111827"),
                        rx.badge("Ativo", color_scheme="green", variant="soft", size="2"),
                        align="center",
                        spacing="3"
                    ),
                    rx.text("ID: ", bloco_id, size="3", color="#4B5563"),
                    align_items="flex-start",
                ),
                rx.spacer(),
                rx.button(
                    "Alocar Capital",
                    color_scheme="blue",
                    size="3",
                ),
                width="100%",
                align_items="center",
                mb="6",
            ),
            
            # Grid de KPIs do Bloco
            rx.grid(
                card_metrica_detalhe("Volume do Bloco", DetalhesBlocoState.volume_total, "database", "#3B82F6"),
                card_metrica_detalhe("Rentabilidade Alvo", DetalhesBlocoState.rentabilidade_alvo, "trending-up", "#10B981"),
                card_metrica_detalhe("Score Nuclea Médio", DetalhesBlocoState.score_medio, "shield-check", "#8B5CF6"),
                card_metrica_detalhe("Prazo Médio (Duration)", DetalhesBlocoState.prazo_medio, "clock", "#F59E0B"),
                columns=rx.breakpoints(initial="1", sm="2", lg="4"), 
                spacing="4",
                width="100%",
                mb="6",
            ),

            # Secção Intermediária: Distribuição e Insights
            rx.flex(
                # Gráfico (Placeholder)
                rx.card(
                    rx.heading("Composição de Risco", size="4", color="#111827", mb="4"),
                    rx.center(
                        rx.vstack(
                            rx.icon("pie-chart", size=48, color="#94A3B8"),
                            rx.text("Gráfico de Distribuição renderizado via Plotly/Recharts", color="#94A3B8", size="2"),
                            align="center"
                        ),
                        height="200px",
                        bg="#F8FAFC",
                        border_radius="md",
                        border="1px dashed #CBD5E1",
                    ),
                    width=["100%", "100%", "50%"],
                    variant="surface",
                ),
                
                # Resumo Insight AI
                rx.card(
                    rx.hstack(
                        rx.icon("sparkles", color="#8B5CF6", size=20),
                        rx.heading("Insight AI - Resumo", size="4", color="#111827"),
                        align="center",
                        mb="4"
                    ),
                    rx.text(
                        "O bloco possui excelente qualidade de crédito, concentrado no setor selecionado. "
                        "A Inadimplência projetada é baixa e a carteira apresenta estabilidade no prazo médio das operações. "
                        "Recomenda-se acompanhamento contínuo da alocação das empresas principais.",
                        size="2",
                        color="#4B5563",
                        line_height="1.6"
                    ),
                    rx.link("Ver relatório completo", href="/relatorios", color="#2563EB", size="2", mt="4", weight="bold"),
                    width=["100%", "100%", "50%"],
                    variant="surface",
                    bg="#F8FAFF",
                    border="1px solid #BFDBFE"
                ),
                direction=rx.breakpoints(initial="column", md="row"),
                spacing="6",
                width="100%",
                mb="6",
            ),
            
            # Tabela de Composição da Carteira (Empresas)
            rx.card(
                rx.hstack(
                    rx.heading("Composição da Carteira (Empresas Financiadas)", size="5", color="#111827"),
                    rx.spacer(),
                    rx.input(placeholder="Buscar CNPJ ou Empresa...", size="2", width="250px"),
                    width="100%",
                    mb="4",
                    align_items="center"
                ),
                
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(rx.text("Empresa Sacada", color="#111827")),
                            rx.table.column_header_cell(rx.text("Peso (%)", color="#111827")),
                            rx.table.column_header_cell(rx.text("Valor Alocado (R$)", color="#111827")),
                            rx.table.column_header_cell(rx.text("Score Nuclea (ML)", color="#111827")),
                            rx.table.column_header_cell(rx.text("Ações", color="#111827")),
                        ),
                    ),
                    rx.table.body(
                        rx.foreach(
                            DetalhesBlocoState.empresas_bloco,
                            criar_linha_empresa_dinamica
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
