import sqlalchemy as sa
import datetime
from typing import Optional
import sqlmodel
import reflex as rx


class tb_usuario(rx.Model, table=True):
    """Tabela de usuários da plataforma (gestoras e investidores)."""

    tipo_usuario: str  # Esperado: "gestora" ou "investidor"
    nome_usuario: str
    email_usuario: str = sa.Column(  # type: ignore[assignment]
        sa.String, unique=True, index=True, nullable=False
    )
    identificador_usuario: str
    senha_hash_usuario: str


class tb_aporte(rx.Model, table=True):
    """Modelo para registro de aportes e alocações (Tabela Principal)."""
    id_aporte_uuid: str = sqlmodel.Field(index=True)
    documento_investidor_cpf_cnpj: str = sqlmodel.Field(index=True) # FK para Cadastro Fantasma
    fundo_origem_id: str
    nome_fundo_investidor: str
    empresa_sacada_nome: str
    cnpj_sacado_limpo: str
    valor_aporte_compra: float
    valor_mercado_atual: float
    quantidade_papeis_adquiridos: float
    data_vencimento: str
    data_referencia_competencia: str
    prazo_vencimento_dias: int
    status_prazo_vencimento: str
    taxa_retorno_pre_fixada: float
    bloco_liquidez_setorial: str
    categoria_tecnica_ativo: str
    codigo_identificacao_isin: Optional[str] = None
    codigo_identificacao_selic: Optional[str] = None
    score_risco_interno: float
    flag_outlier_valor: str

    # Metadados de sistema
    data_criacao: datetime.datetime = sqlmodel.Field(
        default_factory=datetime.datetime.utcnow,
        sa_column=sa.Column(sa.DateTime(timezone=True))
    )
