import reflex as rx
import datetime
from typing import Optional


class tb_usuario(rx.Model, table=True):
    tipo_usuario: str  # Esperado: "gestora" ou "investidor"
    nome_usuario: str
    email_usuario: str
    identificador_usuario: str
    senha_hash_usuario: str


class tb_aporte(rx.Model, table=True):
    id_aporte_uuid: str
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
