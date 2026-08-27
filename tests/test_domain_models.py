"""
Testes do contrato dos modelos de tabela.

Cobre `domain/models.py`, que na Fase 1 deixou de herdar de `rx.Model` e passou a
ser SQLModel puro. A troca é invisível para o banco — e é exatamente isso que estes
testes verificam: nome de tabela, colunas e índices precisam continuar iguais, senão
a aplicação para de enxergar os dados que já existem no Supabase.

O segundo contrato travado aqui é entre PostgreSQL, BigQuery e o CSV de ingestão:
as três pontas compartilham as mesmas 19 colunas de negócio e não há migração
automática entre elas. Uma coluna nova em `Aporte` que não chegue ao BigQuery causa
divergência silenciosa entre o dashboard e o relatório.
"""

from __future__ import annotations

import pytest

pytest.importorskip("sqlmodel", reason="requer o stack de banco instalado")

from plataforma_clara.domain.models import Aporte, Usuario  # noqa: E402
from plataforma_clara.services.csv_processor import COLUNAS_OBRIGATORIAS  # noqa: E402

# Colunas que a plataforma adiciona e que não vêm do CSV.
_COLUNAS_INTERNAS = {"id", "data_criacao"}


def test_nomes_fisicos_das_tabelas_nao_mudaram():
    """
    `rx.Model` derivava o nome da tabela do nome da classe. Com as classes renomeadas
    para `Usuario` e `Aporte`, o padrão do SQLModel seria 'usuario'/'aporte' — que
    NÃO é o que está no banco. O nome fixado à mão é o que mantém a aplicação de pé.
    """
    assert Usuario.__tablename__ == "tb_usuario"
    assert Aporte.__tablename__ == "tb_aporte"


def test_aporte_cobre_exatamente_as_colunas_do_csv():
    """As 19 colunas do contrato de ingestão, mais as duas internas. Nem mais, nem menos."""
    colunas = {coluna.name for coluna in Aporte.__table__.columns}

    assert colunas == set(COLUNAS_OBRIGATORIAS) | _COLUNAS_INTERNAS


def test_apenas_o_isin_e_opcional():
    """
    Toda coluna de negócio é obrigatória, menos o ISIN — nem todo ativo tem um. Se
    outra coluna virar nula, o `csv_processor` precisa parar de descartar aquelas
    linhas, e as duas mudanças têm que andar juntas.
    """
    opcionais = {
        coluna.name
        for coluna in Aporte.__table__.columns
        if coluna.nullable and coluna.name not in _COLUNAS_INTERNAS
    }

    assert opcionais == {"codigo_identificacao_isin"}


def test_colunas_de_busca_continuam_indexadas():
    """
    Os dois índices que sustentam as consultas do dashboard: o documento filtra a
    carteira do investidor e o UUID é a chave de deduplicação prevista para a Fase 3.
    """
    indexadas = {
        coluna.name for coluna in Aporte.__table__.columns if coluna.index or coluna.primary_key
    }

    assert {"id", "id_aporte_uuid", "documento_investidor_cpf_cnpj"} <= indexadas


def test_usuario_tem_email_unico_no_modelo():
    """
    ATENÇÃO — esta unicidade existe apenas nos metadados do modelo. Nenhuma migração
    em `alembic/versions/` cria o índice, e a versão anterior do modelo (com
    `rx.Model`) nem sequer o declarava: o `sa.Column(...)` passado como valor padrão
    era descartado pelo SQLModel, e o índice nunca chegou a existir em lugar nenhum.

    O teste trava a intenção declarada no código. A proteção de verdade no banco
    depende de uma migração — e de resolver antes o descompasso do histórico do
    Alembic descrito em `infra/db.py`.
    """
    coluna = Usuario.__table__.columns["email_usuario"]

    assert coluna.unique is True
    assert coluna.index is True
    assert coluna.nullable is False
