"""
Conexão com o PostgreSQL, independente de framework.

Substitui o `rx.session()` do Reflex, que era o último fio prendendo a camada de
dados ao framework de UI. A engine é criada uma única vez, sob demanda, a partir da
`DATABASE_URL` — a mesma variável que o `rxconfig.py` já usa, então os dois caminhos
apontam para o mesmo banco enquanto o Reflex continuar de pé.

DUAS FORMAS DE OBTER UMA SESSÃO:
    - `sessao()` — gerenciador de contexto, para código síncrono chamado de dentro
      de `asyncio.to_thread`. É o que os serviços usam hoje.
    - `obter_sessao()` — gerador, no formato que o `Depends` do FastAPI espera.
      Já existe para que a Fase 2 não precise mexer nesta camada de novo.

AVISO SOBRE MIGRAÇÕES: o histórico em `alembic/versions/` NÃO reproduz o schema que
o código espera. A migração que cria `tb_usuario` declara as colunas `nome`, `email`
e `senha_hash`, enquanto o modelo usa `nome_usuario`, `email_usuario` e
`senha_hash_usuario`, e nenhuma migração posterior faz o rename. Um `alembic upgrade
head` num banco vazio produz um `tb_usuario` que a aplicação não consegue usar. O
banco em uso hoje foi ajustado por fora do histórico. Corrigir isso exige decidir
o que fazer com o estado real do Supabase, e por isso não é feito aqui.
"""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy.engine import Engine
from sqlmodel import Session, create_engine

logger = logging.getLogger(__name__)

# A engine mantém um pool de conexões e é cara de criar — uma por processo.
_engine: Engine | None = None


def obter_engine() -> Engine:
    """
    Devolve a engine do banco, criando-a na primeira chamada.

    COMO FUNCIONA:
        1. Reaproveitamento — Uma engine já criada é devolvida direto; o pool de
           conexões precisa ser único no processo.
        2. Leitura da configuração — Carrega o `.env` e lê `DATABASE_URL`.
        3. Criação — `pool_pre_ping=True` testa a conexão antes de entregá-la. O
           Supabase encerra conexões ociosas, e sem isso a primeira query após um
           período parado falha com "server closed the connection unexpectedly".

    Returns:
        Engine: Engine SQLAlchemy conectada ao PostgreSQL.

    Raises:
        RuntimeError: Se `DATABASE_URL` não estiver configurada.
    """
    # --- 1. REAPROVEITAMENTO ---
    global _engine
    if _engine is not None:
        return _engine

    # --- 2. LEITURA DA CONFIGURAÇÃO ---
    load_dotenv()
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL não configurada. Preencha o .env antes de acessar o banco."
        )

    # --- 3. CRIAÇÃO ---
    _engine = create_engine(url, pool_pre_ping=True)
    logger.info("Engine do PostgreSQL inicializada.")
    return _engine


@contextmanager
def sessao() -> Iterator[Session]:
    """
    Abre uma sessão de banco como gerenciador de contexto.

    A sessão é fechada ao sair do bloco, com ou sem exceção. O commit é
    responsabilidade de quem escreve — leituras não precisam de nenhum.

    Yields:
        Session: Sessão SQLModel pronta para uso.
    """
    with Session(obter_engine()) as sessao_ativa:
        yield sessao_ativa


def obter_sessao() -> Iterator[Session]:
    """
    Fornece uma sessão no formato de dependência do FastAPI.

    Preparado para a Fase 2: `def rota(sessao: Session = Depends(obter_sessao))`.

    Yields:
        Session: Sessão SQLModel, fechada ao fim da requisição.
    """
    with sessao() as sessao_ativa:
        yield sessao_ativa


def redefinir_engine() -> None:
    """
    Descarta a engine atual, forçando a recriação na próxima chamada.

    Existe para os testes, que trocam a `DATABASE_URL` entre casos. Em produção
    não deve ser chamada: descartar a engine descarta o pool de conexões junto.
    """
    global _engine
    if _engine is not None:
        _engine.dispose()
    _engine = None
