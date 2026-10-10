"""
Cadastro de usuários: Firebase Auth, Firestore e claim de perfil.

COMO FUNCIONA:
    1. Reserva o documento em `documentos/{documento}` com `create()`, que falha se
       já existir — é isso que garante um CPF/CNPJ por conta.
    2. Cria o usuário no Firebase Auth.
    3. Grava `usuarios/{uid}` e aponta a reserva para o uid.
    4. Define a claim `perfil` no usuário.
    5. Se algo falhar depois da reserva, desfaz o que foi criado.

Args:
    Nenhum.

Returns:
    str: o uid, via `cadastrar_usuario()`.

Raises:
    DocumentoJaCadastradoError: Documento já reservado por outra conta.
    EmailJaCadastradoError: E-mail já existe no Firebase Auth.
"""

import logging

from firebase_admin import auth
from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore

from app.domain.erros import DocumentoJaCadastradoError, EmailJaCadastradoError
from app.domain.perfis import DadosCadastro, Perfil
from app.storage.firebase import cliente_firestore

logger = logging.getLogger(__name__)

_COLECAO_DOCUMENTOS = "documentos"
_COLECAO_USUARIOS = "usuarios"


def cadastrar_usuario(dados: DadosCadastro, senha: str, perfil: Perfil) -> str:
    """
    Cria a conta completa de um usuário. Bloqueante.

    Args:
        dados (DadosCadastro): Dados já validados pelo domínio.
        senha (str): Senha em texto, enviada só ao Firebase e nunca guardada.
        perfil (Perfil): Perfil gravado na claim.

    Returns:
        str: O uid do usuário criado.

    Raises:
        DocumentoJaCadastradoError: Documento já reservado por outra conta.
        EmailJaCadastradoError: E-mail já existe no Firebase Auth.
    """
    db = cliente_firestore()
    reserva = db.collection(_COLECAO_DOCUMENTOS).document(dados.documento)
    try:
        reserva.create({"criado_em": firestore.SERVER_TIMESTAMP})
    except AlreadyExists:
        raise DocumentoJaCadastradoError("Documento já cadastrado.") from None

    uid: str | None = None
    try:
        try:
            uid = auth.create_user(
                email=dados.email, password=senha, display_name=dados.nome
            ).uid
        except auth.EmailAlreadyExistsError:
            raise EmailJaCadastradoError("E-mail já cadastrado.") from None

        db.collection(_COLECAO_USUARIOS).document(uid).set(
            {
                "perfil": perfil.value,
                "documento": dados.documento,
                "tipo_documento": dados.tipo_documento,
                "nome": dados.nome,
                "criado_em": firestore.SERVER_TIMESTAMP,
            }
        )
        reserva.set({"uid": uid, "criado_em": firestore.SERVER_TIMESTAMP})
        auth.set_custom_user_claims(uid, {"perfil": perfil.value})
    except Exception:
        _desfazer(db, reserva, uid)
        raise

    return uid


def _desfazer(db, reserva, uid: str | None) -> None:
    """Remove o que o cadastro criou. Cada passo é tentado mesmo se o anterior falhar."""
    passos = [("reserva", reserva.delete)]
    if uid:
        passos += [
            ("usuário no Firestore", db.collection(_COLECAO_USUARIOS).document(uid).delete),
            ("usuário no Auth", lambda: auth.delete_user(uid)),
        ]
    for nome, passo in passos:
        try:
            passo()
        except Exception:
            logger.exception("Falha ao desfazer o cadastro (%s).", nome)
