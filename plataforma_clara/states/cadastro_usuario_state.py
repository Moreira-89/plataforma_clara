import logging
import re

import bcrypt
import reflex as rx

from plataforma_clara.model.schemas import tb_usuario

logger = logging.getLogger(__name__)

# Regex simples para validação de formato de e-mail
_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Regras de identificação de documentos brasileiros
_REGRAS_DOCUMENTOS: dict[str, dict] = {
    "CPF": {"tamanho": 11, "permite_letras": False},
    "CNPJ": {"tamanho": 14, "permite_letras": True},
}


class CadastroUsuarioState(rx.State):
    """Estado responsável por gerenciar o fluxo de cadastro de novos usuários."""

    tipo_usuario: str = ""
    nome_usuario: str = ""
    email_usuario: str = ""
    identificador_usuario: str = ""
    senha_hash_usuario: str = ""
    mensagem_para_usuario: str = ""

    def _limpar_estado(self) -> None:
        """Reseta todos os campos de formulário para o valor padrão."""
        self.tipo_usuario = ""
        self.nome_usuario = ""
        self.email_usuario = ""
        self.identificador_usuario = ""
        self.senha_hash_usuario = ""
        self.mensagem_para_usuario = ""

    @rx.event
    async def identificar_tipo_usuario(self, tipo_pagina: str):
        """
        Valida os dados do formulário, identifica o tipo de documento e inicia o salvamento.

        Args:
            tipo_pagina: String indicando a origem do cadastro ('gestora' ou 'investidor').
        """
        # Limpa mensagem anterior antes de nova validação.
        self.mensagem_para_usuario = ""
        self.email_usuario = (self.email_usuario or "").strip().lower()
        self.nome_usuario = (self.nome_usuario or "").strip()

        # Valida o tipo de usuário
        if tipo_pagina not in ("gestora", "investidor"):
            self.mensagem_para_usuario = "Tipo de usuário inválido"
            return

        self.tipo_usuario = tipo_pagina

        # Validação mínima para evitar persistência de dados vazios
        if not all([self.nome_usuario, self.email_usuario, self.identificador_usuario, self.senha_hash_usuario]):
            self.mensagem_para_usuario = "Preencha todos os campos obrigatórios."
            return

        # Validação de formato de e-mail
        if not _EMAIL_REGEX.match(self.email_usuario):
            self.mensagem_para_usuario = "Formato de e-mail inválido."
            return

        # Normaliza o documento e descobre se é CPF ou CNPJ
        tipo_doc, doc_limpo = self._identificar_e_limpar_documento(self.identificador_usuario)

        if tipo_doc == "INVALIDO":
            self.mensagem_para_usuario = "Documento inválido. Verifique os números digitados."
            return

        # Persiste só caracteres alfanuméricos normalizados (sem pontos/traços).
        self.identificador_usuario = doc_limpo
        self.mensagem_para_usuario = f"{tipo_doc} validado com sucesso!"

        # Prossegue para a persistência dos dados.
        self._salvar_informacao_banco()

        # Quando houver erro de persistência, interrompe o fluxo sem redirecionar.
        if self.mensagem_para_usuario != "Usuário cadastrado com sucesso!":
            return

        self._limpar_estado()
        return rx.redirect("/login-usuario")

    @staticmethod
    def _identificar_e_limpar_documento(doc_bruto: str) -> tuple[str, str]:
        """
        Remove formatação e valida se a string corresponde a um CPF ou CNPJ.

        Args:
            doc_bruto: A string digitada pelo usuário no campo de identificador.

        Returns:
            Tupla (tipo, doc_limpo): O tipo identificado ('CPF', 'CNPJ' ou 'INVALIDO')
            e a string limpa.
        """
        # Remove tudo que não for letra ou número; padroniza em maiúsculas.
        doc_limpo = re.sub(r"[^a-zA-Z0-9]", "", str(doc_bruto)).upper()
        tamanho_atual = len(doc_limpo)

        for tipo, regras in _REGRAS_DOCUMENTOS.items():
            if tamanho_atual != regras["tamanho"]:
                continue
            # CPF: se não pode letras e há letra no meio, ignora e tenta o outro.
            if not regras["permite_letras"] and not doc_limpo.isdigit():
                continue
            return tipo, doc_limpo

        return "INVALIDO", doc_limpo

    @staticmethod
    def _gerar_hash_senha(senha_texto_plano: str) -> str:
        """
        Criptografa a senha utilizando o algoritmo bcrypt.

        Args:
            senha_texto_plano: A senha digitada pelo usuário.

        Returns:
            O hash da senha decodificado em string para armazenamento.
        """
        senha_bytes = senha_texto_plano.encode("utf-8")
        hash_gerado = bcrypt.hashpw(senha_bytes, bcrypt.gensalt())
        return hash_gerado.decode("utf-8")

    def _salvar_informacao_banco(self) -> None:
        """Gera o hash da senha e persiste o novo usuário no banco de dados."""
        senha_hash = self._gerar_hash_senha(self.senha_hash_usuario)

        try:
            with rx.session() as session:
                # Verifica se e-mail já está cadastrado
                usuario_existente = (
                    session.query(tb_usuario)
                    .filter_by(email_usuario=self.email_usuario)
                    .first()
                )
                if usuario_existente:
                    self.mensagem_para_usuario = "Este e-mail já está cadastrado."
                    logger.warning("Tentativa de cadastro duplicado: %s", self.email_usuario)
                    return

                novo_usuario = tb_usuario(
                    tipo_usuario=self.tipo_usuario,
                    nome_usuario=self.nome_usuario,
                    email_usuario=self.email_usuario,
                    identificador_usuario=self.identificador_usuario,
                    senha_hash_usuario=senha_hash,
                )
                session.add(novo_usuario)
                session.commit()

        except Exception:
            logger.exception("Falha ao salvar usuário no banco de dados.")
            self.mensagem_para_usuario = "Não foi possível concluir o cadastro. Tente novamente."
            return

        logger.info("Novo usuário cadastrado: %s (%s)", self.email_usuario, self.tipo_usuario)
        self.mensagem_para_usuario = "Usuário cadastrado com sucesso!"
