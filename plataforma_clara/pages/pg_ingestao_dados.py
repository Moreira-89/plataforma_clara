import reflex as rx
from plataforma_clara.states.ingestao_dados_state import IngestaoDadosState


def ingestao_dados() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Ingestão de Dados", size="1"),#type: ignore
            rx.text("Envie o arquivo CSV com os dados dos aportes", size="2"),#type: ignore
            rx.upload(
                rx.text("Arraste e solte o CSV aqui ou clique para selecionar"),
                id="upload-csv",
                accept={".csv": ["text/csv"]}
            ),
            rx.button(
                "Processar e Salvar",
                on_click=lambda: IngestaoDadosState.lidar_com_upload_de_arquivo(rx.upload_files(upload_id="upload-csv")) #type: ignore
            ),
            rx.text(IngestaoDadosState.mensagem_para_usuario)
        )
    )
