import reflex as rx
from plataforma_clara.states.ingestao_dados_state import IngestaoDadosState
from plataforma_clara.states.autenticacao_state import AutenticacaoState

def sidebar_gestora() -> rx.Component:
    """Componente de Menu Lateral para a Gestora (Reutilizado)."""
    return rx.vstack(
        rx.vstack(
            rx.image(src="/logo_para_usar_fundo_escuro.png", height="80px", alt="Logo Clara"),
            rx.text("Portal da Gestora", size="2", color="#94A3B8", mt="2"),
            align_items="flex-start",
            mb="6",
            width="100%",
        ),
        
        rx.vstack(
            rx.link(
                rx.hstack(rx.icon("layout-dashboard", size=20), rx.text("Visão Geral", size="3"), align="center", spacing="2"), 
                href="/dashboard-gestora", 
                color="#94A3B8", 
                p="2", 
                border_radius="md", 
                width="100%",
                _hover={"bg": "#1E293B", "color": "white", "text_decoration": "none"}
            ),
            rx.link(
                rx.hstack(rx.icon("upload", size=20), rx.text("Ingestão de Dados", size="3"), align="center", spacing="2"), 
                href="/ingestao-dados", 
                color="white", 
                p="2", 
                bg="#1E293B",
                border_radius="md", 
                width="100%",
                _hover={"text_decoration": "none"}
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

def criar_linha_historico(nome_ficheiro: str, data: str, registos: str, status: str) -> rx.Component:
    """Função auxiliar para renderizar o histórico de uploads."""
    cor_status = "green" if status == "Concluído" else ("yellow" if status == "Processando" else "red")
    
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.icon("file-text", size=16, color="#6B7280"),
                rx.text(nome_ficheiro, weight="medium", color="#111827"),
                align_items="center",
                spacing="2"
            )
        ),
        rx.table.cell(rx.text(data, color="#6B7280")),
        rx.table.cell(rx.text(registos, color="#6B7280")),
        rx.table.cell(rx.badge(status, color_scheme=cor_status, variant="soft")),
        rx.table.cell(
            rx.button(rx.icon("download", size=14), size="1", variant="ghost", color_scheme="gray")
        ),
    )


def ingestao_dados() -> rx.Component:
    """Página de Ingestão de Dados (Upload de CSV) para a Gestora."""
    
    return rx.flex(
        sidebar_gestora(),
        
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.heading("Ingestão de Dados", size="8", weight="bold", color="#111827"),
                    rx.text("Faça o upload dos ficheiros CSV com as alocações e operações dos Blocos de Liquidez.", size="3", color="#4B5563"),
                    align_items="flex-start",
                ),
                width="100%",
                align_items="center",
                mb="6",
            ),
            
            rx.card(
                rx.vstack(
                    rx.heading("Novo Upload", size="5", color="#111827", mb="2"),
                    
                    rx.upload(
                        rx.vstack(
                            rx.icon("cloud-upload", size=40, color="#94A3B8"),
                            rx.text("Arraste e solte o seu ficheiro CSV aqui", weight="bold", color="#374151"),
                            rx.text("Tamanho máximo: 50MB. Formato aceite: .csv", size="2", color="#6B7280"),
                            align_items="center",
                            spacing="2",
                        ),
                        id="upload_csv_alocacoes",
                        multiple=False,
                        accept={"text/csv": [".csv"]},
                        padding="4rem",
                        width="100%",
                        border="2px dashed #CBD5E1",
                        border_radius="lg",
                        bg="#F8FAFC",
                        _hover={"bg": "#F1F5F9", "border_color": "#3B82F6", "cursor": "pointer"},
                    ),
                    
                    rx.hstack(
                        rx.button(
                            "Limpar",
                            color_scheme="gray",
                            variant="surface",
                            size="3",
                            on_click=rx.clear_selected_files("upload_csv_alocacoes"),
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.icon("play", size=18),
                            "Processar Ficheiro",
                            color_scheme="blue",
                            size="3",
                            on_click=IngestaoDadosState.lidar_com_upload_de_arquivo(files=rx.upload_files(upload_id="upload_csv_alocacoes")),
                        ),
                        width="100%",
                        mt="4",
                    ),
                    width="100%",
                    align_items="flex-start",
                ),
                rx.cond(
                    IngestaoDadosState.mensagem_para_usuario != "",
                    rx.callout(
                        IngestaoDadosState.mensagem_para_usuario,
                        icon="info",
                        width="100%",
                        color_scheme="blue",
                        mt="4",
                    ),
                ),
                width="100%",
                variant="surface",
                border="1px solid #E5E7EB",
                mb="8",
            ),
            
            rx.card(
                rx.heading("Histórico de Processamento", size="5", color="#111827", mb="4"),
                rx.text("Consulte o estado dos ficheiros enviados recentemente e os relatórios de erros, caso existam.", size="2", color="#6B7280", mb="4"),
                
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell("Nome do Ficheiro"),
                            rx.table.column_header_cell("Data de Envio"),
                            rx.table.column_header_cell("Registos Processados"),
                            rx.table.column_header_cell("Estado"),
                            rx.table.column_header_cell("Log"),
                        ),
                    ),
                    rx.table.body(
                        criar_linha_historico("alocacoes_bloco_safira_20250410.csv", "10 Abr 2025, 09:30", "1.240", "Concluído"),
                        criar_linha_historico("aportes_fidc_master_v2.csv", "09 Abr 2025, 16:45", "850", "Concluído"),
                        criar_linha_historico("dados_empresas_novas.csv", "09 Abr 2025, 11:20", "42", "Erro"),
                        criar_linha_historico("alocacoes_bloco_rubi.csv", "08 Abr 2025, 14:10", "3.100", "Concluído"),
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
