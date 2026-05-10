"""
Modelos de dados da Plataforma Clara (SQLModel + Reflex).

Define as tabelas do banco de dados via classes que herdam de rx.Model,
que internamente usa SQLModel sobre SQLAlchemy. O Reflex gerencia a criação
das tabelas e a sessão de banco automaticamente.
"""

import datetime
from typing import Optional

import sqlalchemy as sa
import sqlmodel
import reflex as rx


# -----------------------------------------------------------------------------
# MODELOS DE BANCO DE DADOS
# -----------------------------------------------------------------------------


class tb_usuario(rx.Model, table=True):
    """
    Representa um usuário cadastrado na plataforma.

    Pode ser do tipo 'gestora' (acesso administrativo ao dashboard de gestão)
    ou 'investidor' (acesso ao dashboard pessoal de portfólio).

    Campos:
        tipo_usuario (str): Perfil de acesso — 'gestora' ou 'investidor'.
        nome_usuario (str): Nome completo para exibição na interface.
        email_usuario (str): E-mail único, usado como login. Indexado para buscas.
        identificador_usuario (str): CPF (11 dígitos) ou CNPJ (14 dígitos), sem formatação.
        senha_hash_usuario (str): Hash bcrypt da senha. Nunca armazenar texto plano.
    """

    tipo_usuario: str
    nome_usuario: str
    # sa.Column com unique=True garante que não haverá dois usuários com o mesmo e-mail
    # a nível de banco — uma camada extra de segurança além da validação na aplicação.
    email_usuario: str = sa.Column(  # type: ignore[assignment]
        sa.String, unique=True, index=True, nullable=False
    )
    identificador_usuario: str
    senha_hash_usuario: str


class tb_aporte(rx.Model, table=True):
    """
    Representa um registro de aporte/alocação de capital em um FIDC.

    Esta é a tabela principal da plataforma — contém todos os aportes realizados
    pelos investidores, organizados por Bloco de Liquidez e empresa sacada.
    É espelhada no BigQuery para consultas analíticas de alto volume.

    Campos:
        id_aporte_uuid (str): UUID v4 gerado na ingestão. Indexado para buscas rápidas.
        documento_investidor_cpf_cnpj (str): Documento do investidor (somente dígitos).
        fundo_origem_id (str): Identificador do fundo FIDC de origem.
        nome_fundo_investidor (str): Nome legível do fundo.
        empresa_sacada_nome (str): Nome da empresa que recebe o crédito (sacada).
        cnpj_sacado_limpo (str): CNPJ da empresa sacada (somente dígitos).
        valor_aporte_compra (float): Valor original do aporte no momento da compra (R$).
        valor_mercado_atual (float): Valor de mercado atualizado do aporte (R$).
        quantidade_papeis_adquiridos (float): Quantidade de cotas/papéis adquiridos.
        data_vencimento (datetime.date): Data de vencimento do direito creditório.
        data_referencia_competencia (datetime.date): Data de competência do registro.
        prazo_vencimento_dias (int): Dias restantes até o vencimento.
        status_prazo_vencimento (str): Status textual — ex: 'Vigente', 'Vencido'.
        taxa_retorno_pre_fixada (float): Taxa de retorno contratada (% a.a.).
        bloco_liquidez_setorial (str): Nome do Bloco de Liquidez (ex: 'Safira').
        categoria_tecnica_ativo (str): Categoria do ativo (ex: 'Recebível Comercial').
        codigo_identificacao_isin (Optional[str]): Código ISIN, quando disponível.
        score_risco_interno (float): Score de risco ML (0–100), maior = menor risco.
        flag_outlier_valor (str): Indica se o valor é estatisticamente atípico.
        data_criacao (datetime.datetime): Timestamp UTC de inserção do registro.
    """

    id_aporte_uuid: str = sqlmodel.Field(index=True)
    documento_investidor_cpf_cnpj: str = sqlmodel.Field(index=True)
    fundo_origem_id: str
    nome_fundo_investidor: str
    empresa_sacada_nome: str
    cnpj_sacado_limpo: str
    valor_aporte_compra: float
    valor_mercado_atual: float
    quantidade_papeis_adquiridos: float
    data_vencimento: datetime.date
    data_referencia_competencia: datetime.date
    prazo_vencimento_dias: int
    status_prazo_vencimento: str
    taxa_retorno_pre_fixada: float
    bloco_liquidez_setorial: str
    categoria_tecnica_ativo: str
    # Optional — nem todos os ativos possuem código ISIN atribuído.
    codigo_identificacao_isin: Optional[str] = None
    score_risco_interno: float
    flag_outlier_valor: str

    # sa.Column com timezone=True garante que o timestamp seja armazenado em UTC,
    # evitando problemas de fuso horário ao fazer queries comparativas.
    data_criacao: datetime.datetime = sqlmodel.Field(
        default_factory=datetime.datetime.utcnow,
        sa_column=sa.Column(sa.DateTime(timezone=True)),
    )
