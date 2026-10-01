"""
Cria a conta de uma gestora pela linha de comando.

Existe porque a primeira gestora (a Núclea) não tem como chamar
`POST /auth/register/gestora`, que exige um token de gestora.

COMO FUNCIONA:
    1. Lê nome, e-mail e CNPJ dos argumentos e a senha de `getpass`.
    2. Valida no domínio e cria a conta com o mesmo `cadastrar_usuario` da API.
    3. Precisa da credencial de service account no ambiente (`backend/.env`).

Uso:
    python -m app.jobs.criar_gestora --nome "Núclea" --email gestora@exemplo.com --cnpj 12.345.678/0001-90

Args:
    --nome (str): Nome da gestora.
    --email (str): E-mail de login.
    --cnpj (str): CNPJ, com ou sem máscara.

Returns:
    int: Código de saída do processo (0 em sucesso).

Raises:
    ErroDeNegocio: Dados inválidos ou conta já existente; a mensagem sai no log.
"""

import argparse
import getpass
import logging
import sys

from app.config.logging import configurar_logging
from app.domain.erros import ErroDeNegocio
from app.domain.perfis import Perfil, validar_cadastro
from app.storage.firebase import inicializar_firebase
from app.storage.usuarios import cadastrar_usuario

logger = logging.getLogger(__name__)

_TAMANHO_MINIMO_SENHA = 8


def main(argv: list[str] | None = None) -> int:
    """
    Executa o cadastro da gestora.

    Args:
        argv (list[str] | None): Argumentos; None usa os da linha de comando.

    Returns:
        int: 0 em sucesso, 1 em erro.
    """
    parser = argparse.ArgumentParser(description="Cria uma conta de gestora.")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--cnpj", required=True)
    args = parser.parse_args(argv)

    configurar_logging()

    senha = getpass.getpass("Senha: ")
    if len(senha) < _TAMANHO_MINIMO_SENHA or senha != getpass.getpass("Repita a senha: "):
        logger.error("Senha curta (mínimo %d) ou diferente da repetição.", _TAMANHO_MINIMO_SENHA)
        return 1

    try:
        dados = validar_cadastro(args.nome, args.email, args.cnpj, Perfil.GESTORA)
        inicializar_firebase()
        uid = cadastrar_usuario(dados, senha, Perfil.GESTORA)
    except ErroDeNegocio as e:
        logger.error("%s", e)
        return 1

    logger.info("Gestora criada: uid=%s", uid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
