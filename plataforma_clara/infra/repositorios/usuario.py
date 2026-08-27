"""
Repositório de acesso aos usuários (`tb_usuario`) no PostgreSQL.

Concentra as consultas que estavam dentro de `AutenticacaoState`,
`CadastroUsuarioState` e `relatorio_ia_service`. Nenhum método aqui conhece senha
em texto plano: quem gera e confere hash é `domain/seguranca.py`.
"""

import logging

from sqlalchemy import func
from sqlmodel import Session

from plataforma_clara.domain.models import Usuario

logger = logging.getLogger(__name__)


class UsuarioRepositorio:
    """
    Acesso de leitura e escrita à tabela de usuários.

    Args:
        sessao (Session): Sessão aberta pelo chamador. O repositório não a fecha.
    """

    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    def buscar_por_email(self, email: str) -> Usuario | None:
        """
        Busca um usuário pelo e-mail de login.

        Args:
            email (str): E-mail já normalizado (minúsculo, sem espaços).

        Returns:
            Usuario | None: O usuário, ou None se não existir.
        """
        return self.sessao.query(Usuario).filter_by(email_usuario=email).first()

    def buscar_por_documento(self, documento: str) -> Usuario | None:
        """
        Busca um usuário pelo CPF/CNPJ, ignorando a formatação gravada.

        O documento é normalizado no cadastro, mas registros antigos podem ter
        sido gravados com máscara — daí o REGEXP_REPLACE também na consulta.

        Args:
            documento (str): CPF/CNPJ somente com dígitos.

        Returns:
            Usuario | None: O usuário, ou None se não existir.
        """
        return (
            self.sessao.query(Usuario)
            .filter(
                func.regexp_replace(Usuario.identificador_usuario, "[^0-9]", "", "g") == documento
            )
            .first()
        )

    def email_ja_cadastrado(self, email: str) -> bool:
        """
        Verifica se o e-mail já pertence a algum usuário.

        A verificação prévia existe para produzir uma mensagem clara na tela. Ela
        NÃO substitui a constraint de unicidade: entre a consulta e o INSERT há uma
        janela em que outro cadastro pode gravar o mesmo e-mail.

        Args:
            email (str): E-mail já normalizado.

        Returns:
            bool: True se o e-mail já está em uso.
        """
        return self.buscar_por_email(email) is not None

    def criar(self, usuario: Usuario) -> Usuario:
        """
        Persiste um novo usuário e confirma a transação.

        Args:
            usuario (Usuario): Instância já preenchida, com a senha em hash.

        Returns:
            Usuario: O mesmo usuário, agora com o `id` atribuído pelo banco.
        """
        self.sessao.add(usuario)
        self.sessao.commit()
        self.sessao.refresh(usuario)
        logger.info("Novo usuário cadastrado: %s (%s)", usuario.email_usuario, usuario.tipo_usuario)
        return usuario
