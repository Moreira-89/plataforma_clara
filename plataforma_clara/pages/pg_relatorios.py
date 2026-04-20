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

def qa_message(mensagem: str, is_user: bool) -> rx.Component:
    """Componente para renderizar uma mensagem do chat com a Assistente."""
    bg_color = "#E0F2FE" if is_user else "#F3F4F6"
    align_self = "flex-end" if is_user else "flex-start"
    
    return rx.box(
        rx.markdown(mensagem),
        bg=bg_color,
        padding="3",
        border_radius="lg",
        max_width="80%",
        align_self=align_self,
        box_shadow="sm",
    )

def pg_relatorios() -> rx.Component:
    """Página de Relatórios Insight AI para o Investidor."""
    
    # Texto estático simulando o retorno do Gemini (Markdown)
    relatorio_mock = """
### Síntese de Risco: Bloco Safira - Tech

**Visão Geral:**
O Bloco Safira apresenta um **Score de Reputação Nuclea A+**, indicando um risco de crédito extremamente baixo. As alocações recentes estão concentradas no setor de tecnologia, em empresas com histórico de pagamento superior a 98% de pontualidade nos últimos 24 meses.

**Pontos Fortes Identificados:**
* **Baixa Inadimplência:** A inadimplência projetada do bloco encontra-se em 0.8%, bem abaixo da média do setor (2.5%).
* **Diversificação:** O capital está distribuído entre 42 empresas diferentes, mitigando o risco de concentração.
* **Sinais Positivos (Dados Externos):** A análise de dados BACEN não apontou novos protestos ou execuções fiscais para as 5 maiores tomadoras do bloco nos últimos 30 dias.

**Pontos de Atenção:**
* **Exposição Cambial:** Algumas empresas (representando 12% do bloco) possuem receitas atreladas a contratos em dólar. Flutuações bruscas de câmbio exigem monitoramento.

**Conclusão da IA:**
Com base no modelo preditivo, a probabilidade de o Bloco Safira atingir a rentabilidade alvo (14.5% a.a.) no próximo trimestre é de **87%**.
    """

    return rx.flex(
        sidebar_investidor(),
        
        rx.flex(
            # Coluna Principal: Relatório
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Insight AI - Relatórios de Transparência", size="8", weight="bold", color="#111827"),
                        rx.text("Análises geradas por Inteligência Artificial sobre a saúde dos Blocos de Liquidez.", size="3", color="#4B5563"),
                        align_items="flex-start",
                    ),
                    rx.spacer(),
                    rx.select(
                        ["Bloco Safira - Tech", "FIDC Master Varejo", "Agro Exportação Q3"],
                        placeholder="Selecione um Bloco...",
                        size="3",
                        width="250px",
                    ),
                    width="100%",
                    align_items="center",
                    mb="6",
                ),
                
                # Card do Relatório Markdown
                rx.card(
                    rx.hstack(
                        rx.icon("sparkles", color="#8B5CF6", size=24),
                        rx.heading("Análise Nuclea Gerada", size="5", color="#111827"),
                        align_items="center",
                        spacing="2",
                        mb="4"
                    ),
                    rx.markdown(
                        relatorio_mock,
                        # Para personalização de estilos do markdown no futuro
                        # component_map={"h3": lambda text: rx.heading(text, size="4", mt="4", mb="2")} 
                    ),
                    width="100%",
                    variant="surface",
                    border="1px solid #E5E7EB",
                    padding="2rem",
                ),
                width=["100%", "100%", "60%", "65%"], # Ocupa a maior parte da tela em desktops
                align_items="flex-start",
                height="100%",
            ),

            # Coluna Lateral: Chat Assistente Clara
            rx.vstack(
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.avatar(fallback="C", color_scheme="blue", size="3"),
                            rx.heading("Assistente Clara", size="4", color="#111827"),
                            align_items="center",
                            spacing="2",
                        ),
                        rx.divider(margin_y="2"),
                        
                        # Área de Mensagens
                        rx.vstack(
                            qa_message("Olá! Sou a Clara. Posso ajudar a interpretar os dados do Bloco Safira?", False),
                            qa_message("Qual é a principal empresa desse bloco?", True),
                            qa_message("A empresa com maior alocação (15%) é a Tech Solutions S.A., que possui um score impecável.", False),
                            # rx.foreach(AssistenteIAState.chat_history, lambda msg: qa_message(msg[0], msg[1])) # Conexão futura
                            height="400px",
                            overflow_y="auto",
                            width="100%",
                            spacing="3",
                            padding_y="2",
                        ),
                        
                        # Input de Pergunta
                        rx.hstack(
                            rx.input(placeholder="Pergunte sobre o relatório...", width="100%"),
                            rx.button(rx.icon("send", size=16), color_scheme="blue"),
                            width="100%",
                            mt="4"
                        ),
                        
                        width="100%",
                        height="100%",
                        justify_content="space-between"
                    ),
                    width="100%",
                    height="100%",
                    variant="surface",
                    border="1px solid #E5E7EB",
                ),
                width=["100%", "100%", "40%", "35%"], # Largura fixa para o chat lateral
                height="100%",
                mt=["6", "6", "0", "0"], # Margem superior apenas no mobile, quando empilha
            ),
            
            direction=rx.breakpoints(initial="column", md="row"),
            spacing="6",
            width="100%",
            padding=["2rem", "3rem"],
        ),
        
        direction=rx.breakpoints(initial="column", sm="row"),
        width="100vw",
        min_height="100vh",
        bg="#F9FAFB",
        spacing="0",
    )