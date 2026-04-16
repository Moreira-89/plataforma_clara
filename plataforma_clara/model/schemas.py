import datetime
from typing import Optional

import reflex as rx
import sqlalchemy as sa


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
    id_aporte_uuid: str
    investidor_id: Optional[str] = None
    nome_investidor: Optional[str] = None
    documento_investidor_cpf_cnpj: Optional[str] = None
    email_investidor: Optional[str] = None
    fundo_origem_id: Optional[str] = None
    nome_fundo_investidor: Optional[str] = None
    empresa_sacada_nome: Optional[str] = None
    cnpj_sacado_limpo: Optional[str] = None
    valor_aporte_compra: Optional[float] = None
    valor_mercado_atual: Optional[float] = None
    taxa_retorno_pre_fixada: Optional[float] = None
    prazo_vencimento_dias: Optional[int] = None
    quantidade_papeis_adquiridos: Optional[int] = None
    score_risco_interno: Optional[float] = None
    status_prazo_vencimento: Optional[str] = None
    bloco_liquidez_setorial: Optional[str] = None
    categoria_tecnica_ativo: Optional[str] = None
    codigo_identificacao_isin: Optional[str] = None
    codigo_identificacao_selic: Optional[str] = None
    data_referencia_competencia: Optional[datetime.date] = None
