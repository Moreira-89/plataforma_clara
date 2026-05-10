"""
Página de Ingestão de Dados (Upload de CSV) para a Gestora.

Permite o upload de arquivos CSV com aportes de FIDCs, que são processados,
validados e persistidos no Supabase + BigQuery via IngestaoDadosState.
"""

import reflex as rx

from plataforma_clara.components.sidebar import sidebar_gestora
from plataforma_clara.states.ingestao_dados_state import IngestaoDadosState


# -----------------------------------------------------------------------------
# COMPONENTES INTERNOS
# -----------------------------------------------------------------------------


def criar_linha_historico(
    nome_ficheiro: str, data: str, registos: str, status: str
) -> rx.Component:
    """
    Renderiza uma linha do histórico de uploads com badge de status colorido.

    COMO FUNCIONA:
        A cor do badge é determinada por condicionais Python pois os dados são
        estáticos (não vêm do estado reativo Reflex) — neste caso, o condicional
        Python é corretamente avaliado em tempo de construção da página.

    Args:
        nome_ficheiro (str): Nome do arquivo CSV enviado.
        data (str): Data e hora do envio formatada.
        registos (str): Quantidade de registros processados.
        status (str): Status do processamento ("Concluído", "Processando", "Erro").

    Returns:
        rx.Component: Linha de tabela com ícone, metadados e badge de status.
    """
    # Para dados estáticos (não reativos), condicional Python é correto e eficiente.
    if status == "Concluído":
        cor_status = "green"
    elif status == "Processando":
        cor_status = "yellow"
    else:
        cor_status = "red"

    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.icon("file-text", size=16, color=rx.color("gray", 8)),
                rx.text(nome_ficheiro, weight="medium", color=rx.color("gray", 11)),
                align_items="center",
                spacing="2",
            )
        ),
        rx.table.cell(rx.text(data, color=rx.color("gray", 9))),
        rx.table.cell(rx.text(registos, color=rx.color("gray", 9))),
        rx.table.cell(rx.badge(status, color_scheme=cor_status, variant="soft")),
        rx.table.cell(
            rx.button(rx.icon("download", size=14), size="1", variant="ghost", color_scheme="gray")
        ),
    )


# -----------------------------------------------------------------------------
# PÁGINA PRINCIPAL
# -----------------------------------------------------------------------------


def ingestao_dados() -> rx.Component:
    """
    Página de Ingestão de Dados para o Portal da Gestora.

    COMO FUNCIONA:
        1. Upload — rx.upload captura o arquivo CSV selecionado pelo usuário.
        2. Processamento — IngestaoDadosState.lidar_com_upload_de_arquivo recebe
           os bytes via rx.upload_files e os encaminha para o pipeline de validação
           (csv_processor), inserção no Supabase e envio ao BigQuery.
        3. Feedback — rx.cond exibe o callout com a mensagem de status apenas
           quando IngestaoDadosState.mensagem_para_usuario está preenchida.
        4. Histórico Estático — Exibe uploads recentes fictícios como placeholder
           até a implementação do histórico dinâmico via banco de dados.
    """
    return rx.flex(
        # Sidebar com item "Ingestão de Dados" marcado como ativo
        sidebar_gestora(pagina_ativa="ingestao"),

        rx.vstack(
            # Cabeçalho
            rx.hstack(
                rx.vstack(
                    rx.heading(
                        "Ingestão de Dados",
                        size="8",
                        weight="bold",
                        color=rx.color("gray", 12),
                    ),
                    rx.text(
                        "Faça o upload dos arquivos CSV com as alocações e operações dos Blocos de Liquidez.",
                        size="3",
                        color=rx.color("gray", 10),
                    ),
                    align_items="flex-start",
                ),
                width="100%",
                align_items="center",
                mb="6",
            ),

            # Card de upload
            rx.card(
                rx.vstack(
                    rx.heading(
                        "Novo Upload", size="5", color=rx.color("gray", 12), mb="2"
                    ),
                    rx.upload(
                        rx.vstack(
                            rx.icon("cloud-upload", size=40, color=rx.color("gray", 7)),
                            rx.text(
                                "Arraste e solte o arquivo CSV aqui",
                                weight="bold",
                                color=rx.color("gray", 11),
                            ),
                            rx.text(
                                "Tamanho máximo: 50MB. Formato aceito: .csv",
                                size="2",
                                color=rx.color("gray", 9),
                            ),
                            align_items="center",
                            spacing="2",
                        ),
                        id="upload_csv_alocacoes",
                        multiple=False,
                        accept={"text/csv": [".csv"]},
                        padding="4rem",
                        width="100%",
                        border="2px dashed var(--gray-6)",
                        border_radius="lg",
                        bg=rx.color("gray", 2),
                        _hover={
                            "bg": rx.color("gray", 3),
                            "border_color": "#3B82F6",
                            "cursor": "pointer",
                        },
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
                            "Processar Arquivo",
                            color_scheme="blue",
                            size="3",
                            on_click=IngestaoDadosState.lidar_com_upload_de_arquivo(
                                files=rx.upload_files(upload_id="upload_csv_alocacoes")
                            ),
                        ),
                        width="100%",
                        mt="4",
                    ),
                    width="100%",
                    align_items="flex-start",
                ),
                # Callout de feedback — visível apenas quando há mensagem
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
                border="1px solid var(--gray-5)",
                mb="8",
            ),

            # Histórico de uploads (dados estáticos de exemplo)
            rx.card(
                rx.heading(
                    "Histórico de Processamento",
                    size="5",
                    color=rx.color("gray", 12),
                    mb="4",
                ),
                rx.text(
                    "Consulte o estado dos arquivos enviados recentemente e os relatórios de erros.",
                    size="2",
                    color=rx.color("gray", 9),
                    mb="4",
                ),
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            rx.table.column_header_cell(
                                rx.text("Nome do Arquivo", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Data de Envio", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Registros Processados", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Estado", color=rx.color("gray", 11))
                            ),
                            rx.table.column_header_cell(
                                rx.text("Log", color=rx.color("gray", 11))
                            ),
                        ),
                    ),
                    rx.table.body(
                        criar_linha_historico(
                            "alocacoes_bloco_safira_20250410.csv", "10 Abr 2025, 09:30", "1.240", "Concluído"
                        ),
                        criar_linha_historico(
                            "aportes_fidc_master_v2.csv", "09 Abr 2025, 16:45", "850", "Concluído"
                        ),
                        criar_linha_historico(
                            "dados_empresas_novas.csv", "09 Abr 2025, 11:20", "42", "Erro"
                        ),
                        criar_linha_historico(
                            "alocacoes_bloco_rubi.csv", "08 Abr 2025, 14:10", "3.100", "Concluído"
                        ),
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
