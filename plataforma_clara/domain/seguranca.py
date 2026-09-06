"""
Hash e verificação de senha com bcrypt.

Extraído de `CadastroUsuarioState._gerar_hash_senha` e do trecho de verificação em
`AutenticacaoState.fazer_login`. Este é o único lugar da plataforma autorizado a
criar ou conferir hash de senha.

O cost factor NÃO pode ser reduzido na migração: os hashes já gravados continuariam
válidos, mas as senhas novas ficariam mais fáceis de quebrar — uma regressão de
segurança que nenhum teste de fluxo perceberia. `bcrypt.gensalt()` usa 12 rounds
por padrão, e é esse padrão que está no banco hoje (`$2b$12$...`).
"""

import logging

import bcrypt

logger = logging.getLogger(__name__)


def gerar_hash_senha(senha_texto_plano: str) -> str:
    """
    Gera o hash bcrypt de uma senha, com salt aleatório por chamada.

    O salt aleatório faz com que duas contas com a mesma senha produzam hashes
    diferentes — sem ele, um vazamento do banco revelaria quais usuários
    compartilham senha.

    Args:
        senha_texto_plano (str): Senha digitada pelo usuário.

    Returns:
        str: Hash em string UTF-8, pronto para gravar em `tb_usuario`.
    """
    hash_gerado = bcrypt.hashpw(senha_texto_plano.encode("utf-8"), bcrypt.gensalt())
    return hash_gerado.decode("utf-8")


def senha_confere(senha_texto_plano: str, hash_armazenado: str) -> bool:
    """
    Verifica uma senha contra o hash gravado no banco.

    Um hash corrompido ou em formato inesperado devolve False em vez de propagar a
    exceção: para quem está tentando entrar, o resultado é o mesmo de senha errada,
    e o incidente fica registrado no log para investigação.

    Args:
        senha_texto_plano (str): Senha digitada na tela de login.
        hash_armazenado (str): Hash bcrypt vindo de `tb_usuario.senha_hash_usuario`.

    Returns:
        bool: True apenas se a senha corresponder ao hash.
    """
    try:
        return bcrypt.checkpw(
            senha_texto_plano.encode("utf-8"), (hash_armazenado or "").encode("utf-8")
        )
    except (TypeError, ValueError):
        logger.warning("Hash de senha em formato inválido encontrado no banco.")
        return False
