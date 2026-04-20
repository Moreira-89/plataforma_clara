import reflex as rx
import asyncio
import os
from markdown_pdf import MarkdownPdf, Section

from plataforma_clara.states.autenticacao_state import AutenticacaoState
from codigo_llm import criar_app, ClienteNuclea

class AssistenteIAState(rx.State):
    """Estado para gerir a geração e download do Relatório de Inteligência Artificial."""
    
    bloco_selecionado: str = ""
    is_loading: bool = False
    
    @rx.event
    async def gerar_e_baixar_relatorio(self):
        """Dispara a geração do relatório LLM em thread e retorna o PDF para download."""
        if not self.bloco_selecionado:
            yield rx.window_alert("Por favor, selecione um bloco de liquidez primeiro.")
            return
            
        self.is_loading = True
        yield
        
        # Recupera o documento do estado de autenticação (usamos isso para criar o cliente)
        auth_state = await self.get_state(AutenticacaoState)
        doc = auth_state.documento_usuario_logado or "Investidor Genérico"
        
        # Função síncrona que executa o LangGraph e gera o PDF
        def _executar_llm():
            # Cria o cliente com base na seleção
            investidor_logado = ClienteNuclea(
                nome=f"Investidor {doc}",
                descricao_cliente=f"Foco na análise do Bloco de Liquidez: {self.bloco_selecionado}"
            )
            
            estado_inicial = {"cliente": investidor_logado}
            app_clara = criar_app()
            
            # Invoca o grafo bloqueante
            resultado = app_clara.invoke(estado_inicial)
            
            # Lógica de PDF exata que o colega programou
            css_estilo = """
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                border: 1px solid black;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            """
            
            pdf = MarkdownPdf(toc_level=2)
            pdf.add_section(Section(resultado["relatorio_gerado"]), user_css=css_estilo)
            
            # Gera nome do arquivo seguro
            nome_arquivo = f"Relatorio_Insight_{self.bloco_selecionado.replace(' ', '_')}.pdf"
            
            # Caminho de download dentro da pasta do Reflex (para que seja acessível)
            caminho_arquivo = os.path.join(rx.get_upload_dir(), nome_arquivo)
            pdf.save(caminho_arquivo)
            
            return caminho_arquivo, nome_arquivo
            
        try:
            caminho_pdf, nome_pdf = await asyncio.to_thread(_executar_llm)
            
            # Retorna a instrução para o navegador fazer o download
            # Usando o endpoint do upload_dir que o reflex disponibiliza
            with open(caminho_pdf, "rb") as file_data:
                pdf_bytes = file_data.read()
                
            yield rx.download(data=pdf_bytes, filename=nome_pdf)
            
        except Exception as e:
            print(f"Erro na geração do relatório: {e}")
            yield rx.window_alert("Ocorreu um erro ao gerar o relatório. Tente novamente mais tarde.")
        finally:
            self.is_loading = False
            yield
