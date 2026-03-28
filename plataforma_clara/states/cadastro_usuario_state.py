import reflex as rx
import bcrypt
import re
from plataforma_clara.model.schemas import tb_usuario

class CadastroUsuarioState(rx.State):
    """Estado responsável por gerenciar o fluxo de cadastro de novos usuários."""
    
    # Define as variáveis de estado que serão vinculadas aos componentes da UI
    tipo_usuario: str = ""  # Armazena se é 'gestora' ou 'investidor'
    nome_usuario: str = ""  # Nome completo do usuário
    email_usuario: str = ""  # E-mail para contato e login
    identificador_usuario: str = ""  # CPF ou CNPJ (bruto ou limpo)
    senha_hash_usuario: str = ""  # Senha em texto plano (antes do hash)
    mensagem_para_usuario: str = ""  # Feedback visual para o front-end


    async def identificar_tipo_usuario(self, tipo_pagina: str):
        """
        Valida os dados do formulário, identifica o tipo de documento e inicia o salvamento.
        
        Args:
            tipo_pagina: String indicando a origem do cadastro ('gestora' ou 'investidor').
        """
        # Limpa mensagem anterior antes de nova validação.
        self.mensagem_para_usuario = ""

        # Se a página indica cadastro de gestora, fixa o tipo no estado.
        if tipo_pagina == "gestora":
            self.tipo_usuario = "gestora"
        # Se indica investidor, fixa o tipo correspondente.
        elif tipo_pagina == "investidor":
            self.tipo_usuario = "investidor"
        # Qualquer outro valor de rota não é aceito.
        else:
            self.mensagem_para_usuario = "Tipo de usuário inválido"
            return

        # Normaliza o documento e descobre se é CPF ou CNPJ pelas regras abaixo.
        tipo_doc, doc_limpo = self.identificar_e_limpar_documento(self.identificador_usuario)

        # Tamanho/conteúdo não bate com CPF nem CNPJ válidos segundo as regras.
        if tipo_doc == "INVALIDO":
            self.mensagem_para_usuario = "Documento inválido. Verifique os números digitados."
        else:
            # Persiste só caracteres alfanuméricos normalizados (sem pontos/traços).
            self.identificador_usuario = doc_limpo
            # Informa qual documento foi reconhecido (CPF ou CNPJ).
            self.mensagem_para_usuario = f"{tipo_doc} validado com sucesso!"
            # Prossegue para a persistência dos dados.
            self.salvar_informacao_banco()

        

    def identificar_e_limpar_documento(self, doc_bruto):
        """
        Remove formatação e valida se a string corresponde a um CPF ou CNPJ.
        
        Args:
            doc_bruto: A string digitada pelo usuário no campo de identificador.
            
        Returns:
            Tuple[str, str]: O tipo identificado ('CPF', 'CNPJ' ou 'INVALIDO') e a string limpa.
        """

        # Regras: CPF tem 11 dígitos e não pode ter letras; CNPJ tem 14 e pode ter letras (ex. filial).
        REGRAS_DOCUMENTOS = {
            'CPF': {'tamanho': 11, 'permite_letras': False},
            'CNPJ': {'tamanho': 14, 'permite_letras': True}
        }
        # Remove tudo que não for letra ou número; padroniza em maiúsculas.
        doc_limpo = re.sub(r'[^a-zA-Z0-9]', '', str(doc_bruto)).upper()
        # Conta caracteres após a limpeza para comparar com CPF (11) ou CNPJ (14).
        tamanho_atual = len(doc_limpo)

        # Testa cada tipo de documento: primeiro bate o tamanho, depois a regra de letras.
        for tipo, regras in REGRAS_DOCUMENTOS.items():
            # Só considera este tipo se o comprimento for exatamente o esperado.
            if tamanho_atual == regras['tamanho']:
                # CPF: se não pode letras e há letra no meio, ignora este tipo e tenta o outro.
                if not regras['permite_letras'] and not doc_limpo.isdigit():
                    continue
                
                # Bateu tamanho e regra de letras: documento identificado.
                return tipo, doc_limpo

        # Nenhuma regra satisfeita: devolve INVALIDO mas ainda retorna o texto limpo (para debug/UI).
        return "INVALIDO", doc_limpo
    

    def gerar_hash_senha(self, senha_texto_plano: str) -> str:
        """
        Criptografa a senha utilizando o algoritmo bcrypt.
        
        Args:
            senha_texto_plano: A senha digitada pelo usuário.
            
        Returns:
            str: O hash da senha decodificado em string para armazenamento.
        """
        # O bcrypt exige que a senha seja convertida de texto (str) para bytes
        senha_bytes = senha_texto_plano.encode('utf-8')
        
        # Gera o hash de forma segura
        hash_gerado = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())
        
        # Devolve como texto novamente para podermos salvar na coluna do banco
        return hash_gerado.decode('utf-8')
    

    def salvar_informacao_banco(self):
        """Gera o hash da senha e persiste o novo usuário no banco de dados."""
        # Transforma a senha digitada em um hash seguro antes de salvar
        senha_hash = self.gerar_hash_senha(self.senha_hash_usuario)

        # Abre uma sessão com o banco de dados (SQLAlchemy/Reflex)
        with rx.session() as session:
            # Instancia o modelo da tabela de usuários com os dados do estado
            novo_usuario = tb_usuario(
                tipo_usuario=self.tipo_usuario,
                nome_usuario=self.nome_usuario,
                email_usuario=self.email_usuario,
                identificador_usuario=self.identificador_usuario,
                senha_hash_usuario=senha_hash
            )
            # Adiciona o objeto à sessão
            session.add(novo_usuario)
            # Confirma a transação no banco de dados
            session.commit()
            # Atualiza a interface com mensagem de sucesso
            self.mensagem_para_usuario = "Usuário cadastrado com sucesso!"