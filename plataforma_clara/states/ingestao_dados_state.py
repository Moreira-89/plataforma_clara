import os

import pandas as pd
import reflex as rx

from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.csv_processor import processar_arquivo_csv


class IngestaoDadosState(rx.State):
    mensagem_para_usuario: str = (
        ""  # Texto exibido na tela: sucesso ou mensagem de erro de validação
    )
    processamento_ativo: bool = False

    async def lidar_com_upload_de_arquivo(self, arquivos: list[rx.UploadFile]):
        # Evento assíncrono: o componente de upload entrega uma lista de UploadFile do Starlette/FastAPI
        self.mensagem_para_usuario = (
            ""  # Limpa mensagem anterior antes de tentar de novo
        )
        caminho_temporario = None

        try:
            if not arquivos:
                self.mensagem_para_usuario = "Nenhum arquivo foi enviado."
                return

            dados_arquivos = await arquivos[
                0
            ].read()  # Lê o conteúdo binário do primeiro arquivo enviado

            # Pasta de upload do Reflex + nome original; Path evita path manual incorreto
            caminho_temporario = rx.get_upload_dir() / arquivos[0].filename  # type: ignore

            with open(
                caminho_temporario, "wb"
            ) as f:  # Grava em disco para processar_arquivo_csv abrir por caminho
                f.write(dados_arquivos)

            self.processamento_ativo = True

            yield

            dataframe = processar_arquivo_csv(
                caminho_temporario
            )  # Converte o arquivo em tabela em memória (pandas DataFrame)

            with (
                rx.session() as session
            ):  # Abre transação com o banco configurado no Reflex
                for (
                    _,
                    dados_da_linha,
                ) in (
                    dataframe.iterrows()
                ):  # Cada linha do CSV vira uma série nomeada pelas colunas
                    aporte = tb_aporte(  # Insta um registro ORM com os campos esperados pelo modelo
                        cnpj=dados_da_linha["cnpj"],
                        nome_empresa=dados_da_linha["nome_empresa"],
                        valor_aporte=dados_da_linha["valor_aporte"],
                        categoria=dados_da_linha["categoria"],
                        prazo=dados_da_linha["prazo"],
                        taxa=dados_da_linha["taxa"],
                        status_pagamento=dados_da_linha["status_pagamento"],
                    )
                    session.add(
                        aporte
                    )  # Enfileira o INSERT na sessão (ainda não grava no disco)

                session.commit()  # Persiste todas as linhas de uma vez; em erro, nada é salvo parcialmente (transação)

            if caminho_temporario and os.path.exists(caminho_temporario):
                os.remove(caminho_temporario)

            self.processamento_ativo = False

            self.mensagem_para_usuario = (
                "Sucesso! CSV validado e pronto."  # Feedback positivo para o usuário
            )

            dados_para_envio = dataframe.to_dict(orient="records")

            yield IngestaoDadosState.enviar_dados_bigquery(dados_para_envio)

        except (
            ValueError
        ) as e:  # processar_arquivo_csv levanta ValueError quando o CSV é inválido
            self.mensagem_para_usuario = str(
                e
            )  # Mostra a mensagem de validação sem quebrar a página
        except Exception:
            # Captura falhas inesperadas (tipagem, banco, I/O) e evita quebra de tela para o usuário.
            self.mensagem_para_usuario = (
                "Erro ao processar o arquivo. Revise o CSV e tente novamente."
            )

    @rx.event(
        background=True
    )  # Decorador para rodar em background e não travar a interface
    async def enviar_dados_bigquery(self, dados: list[dict]):

        dataframe_bigquery = pd.DataFrame(dados)
        pass
