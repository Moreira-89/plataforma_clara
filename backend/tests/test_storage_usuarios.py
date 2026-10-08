"""
Testes de `storage/usuarios.py` com Firebase e Firestore falsos.

Foco na compensação: se o cadastro falha no meio, não pode sobrar conta nem reserva.
"""

import pytest
from google.api_core.exceptions import AlreadyExists

from app.domain.erros import DocumentoJaCadastradoError
from app.domain.perfis import DadosCadastro, Perfil
from app.storage import usuarios

DADOS = DadosCadastro(
    nome="Ana", email="ana@exemplo.com", documento="12345678909", tipo_documento="CPF"
)


class DocFalso:
    def __init__(self, banco, caminho, falhar_no_set=False):
        self.banco, self.caminho, self.falhar_no_set = banco, caminho, falhar_no_set

    def create(self, dados):
        if self.caminho in self.banco:
            raise AlreadyExists("já existe")
        self.banco[self.caminho] = dados

    def set(self, dados):
        if self.falhar_no_set:
            raise RuntimeError("Firestore fora do ar")
        self.banco[self.caminho] = dados

    def delete(self):
        self.banco.pop(self.caminho, None)


class FirestoreFalso:
    def __init__(self, falhar_usuarios=False):
        self.banco: dict[tuple[str, str], dict] = {}
        self.falhar_usuarios = falhar_usuarios

    def collection(self, nome):
        falhar = self.falhar_usuarios and nome == "usuarios"
        return type(
            "Col", (), {"document": lambda _, id_: DocFalso(self.banco, (nome, id_), falhar)}
        )()


class AuthFalso:
    class EmailAlreadyExistsError(Exception):
        pass

    def __init__(self):
        self.contas: dict[str, dict] = {}
        self.claims: dict[str, dict] = {}

    def create_user(self, email, password, display_name):
        uid = f"uid-{len(self.contas) + 1}"
        self.contas[uid] = {"email": email}
        return type("U", (), {"uid": uid})()

    def set_custom_user_claims(self, uid, claims):
        self.claims[uid] = claims

    def delete_user(self, uid):
        self.contas.pop(uid, None)


@pytest.fixture
def firebase(monkeypatch):
    fs, auth = FirestoreFalso(), AuthFalso()
    monkeypatch.setattr(usuarios, "cliente_firestore", lambda: fs)
    monkeypatch.setattr(usuarios, "auth", auth)
    return fs, auth


def test_cadastro_completo_grava_tudo_e_define_a_claim(firebase):
    fs, auth = firebase

    uid = usuarios.cadastrar_usuario(DADOS, "senha-segura", Perfil.INVESTIDOR)

    assert auth.claims[uid] == {"perfil": "investidor"}
    assert fs.banco[("usuarios", uid)]["documento"] == "12345678909"
    assert fs.banco[("documentos", "12345678909")]["uid"] == uid


def test_documento_repetido_nao_cria_conta(firebase):
    fs, auth = firebase
    usuarios.cadastrar_usuario(DADOS, "senha-segura", Perfil.INVESTIDOR)

    with pytest.raises(DocumentoJaCadastradoError):
        usuarios.cadastrar_usuario(DADOS, "senha-segura", Perfil.INVESTIDOR)

    assert len(auth.contas) == 1


def test_falha_no_firestore_desfaz_conta_e_reserva(firebase):
    fs, auth = firebase
    fs.falhar_usuarios = True

    with pytest.raises(RuntimeError):
        usuarios.cadastrar_usuario(DADOS, "senha-segura", Perfil.INVESTIDOR)

    assert auth.contas == {}
    assert fs.banco == {}
