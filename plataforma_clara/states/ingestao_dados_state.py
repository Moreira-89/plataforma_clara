import reflex as rx 
import os
from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.csv_processor import processar_arquivo_csv


class IngestaoDadosState(rx.State):
    mensagem_para_usuario: str = ""  # Texto exibido na tela: sucesso ou mensagem de erro de validação

    async def lidar_com_upload_de_arquivo(self, arquivos: list[rx.UploadFile]):
        # Evento assíncrono: o componente de upload entrega uma lista de UploadFile do Starlette/FastAPI
        self.mensagem_para_usuario = ""  # Limpa mensagem anterior antes de tentar de novo

        try:
            dados_arquivos = await arquivos[0].read()  # Lê o conteúdo binário do primeiro arquivo enviado

            # Pasta de upload do Reflex + nome original; Path evita path manual incorreto
            caminho_temporario = rx.get_upload_dir() / arquivos[0].filename #type: ignore

            with open(caminho_temporario, "wb") as f:  # Grava em disco para processar_arquivo_csv abrir por caminho
                f.write(dados_arquivos)

            dataframe = processar_arquivo_csv(caminho_temporario)  # Converte o arquivo em tabela em memória (pandas DataFrame)

            with rx.session() as session:  # Abre transação com o banco configurado no Reflex

                for _, dados_da_linha in dataframe.iterrows():  # Cada linha do CSV vira uma série nomeada pelas colunas

                    aporte = tb_aporte(  # Insta um registro ORM com os campos esperados pelo modelo
                        cnpj=dados_da_linha["cnpj"],
                        nome_empresa=dados_da_linha["nome_empresa"],
                        valor_aporte=dados_da_linha["valor_aporte"],
                        categoria=dados_da_linha["categoria"],
                        prazo=dados_da_linha["prazo"],
                        taxa=dados_da_linha["taxa"],
                        status_pagamento=dados_da_linha["status_pagamento"]
                    )
                    session.add(aporte)  # Enfileira o INSERT na sessão (ainda não grava no disco)

                session.commit()  # Persiste todas as linhas de uma vez; em erro, nada é salvo parcialmente (transação)
                os.remove(caminho_temporario)  # Remove o CSV temporário para não encher a pasta de uploads

            self.mensagem_para_usuario = "Sucesso! CSV validado e pronto."  # Feedback positivo para o usuário

        except ValueError as e:  # processar_arquivo_csv levanta ValueError quando o CSV é inválido
            self.mensagem_para_usuario = str(e)  # Mostra a mensagem de validação sem quebrar a página
