"""
Contratos de dados do domínio (Pydantic v2).

Separados dos modelos de tabela em `domain/models.py` de propósito: modelo de
tabela descreve o que o banco guarda; contrato descreve o que atravessa a fronteira
do domínio. Misturar os dois é o que faz um campo interno (`senha_hash_usuario`)
vazar para uma resposta HTTP sem ninguém perceber.

Na Fase 2 estes modelos viram diretamente os `response_model` do FastAPI. Hoje eles
já são o que os repositórios devolvem e o que os serviços entregam aos states.

Os DTOs se dividem em duas famílias:
    - **Dados** (`MetricaBloco`, `KpisConsolidados`, ...) — números crus, sem formatação.
    - **Apresentação** (`LinhaTabelaGestora`, `CardBloco`, ...) — strings já formatadas
      para a tela atual. Estas são as que devem encolher na Fase 5, quando o frontend
      passar a formatar o que recebe.
"""

from pydantic import BaseModel, ConfigDict, Field

# -----------------------------------------------------------------------------
# USUÁRIO
# -----------------------------------------------------------------------------


class UsuarioCriacao(BaseModel):
    """Dados de entrada para cadastrar um usuário, já normalizados e validados."""

    tipo_usuario: str = Field(description="'gestora' ou 'investidor'")
    nome_usuario: str
    email_usuario: str
    identificador_usuario: str = Field(description="CPF/CNPJ somente com dígitos")
    senha: str = Field(description="Senha em texto plano — só existe em memória")


class UsuarioAutenticado(BaseModel):
    """
    Identidade devolvida após um login bem-sucedido.

    Deliberadamente NÃO carrega o hash da senha nem o e-mail: é o objeto que a
    camada de entrega pode manipular à vontade. Na Fase 2 vira o payload do JWT.
    """

    model_config = ConfigDict(frozen=True)

    tipo_usuario: str
    nome_usuario: str
    documento: str = Field(description="CPF/CNPJ somente com dígitos")


# -----------------------------------------------------------------------------
# MÉTRICAS DE BLOCO
# -----------------------------------------------------------------------------


class MetricaBloco(BaseModel):
    """Uma linha da agregação por Bloco de Liquidez — a unidade base do dashboard."""

    bloco_liquidez_setorial: str
    total_alocado: float
    score_medio_reputacao: float
    quantidade_aportes: int


class KpisConsolidados(BaseModel):
    """Os três números do topo do dashboard, consolidados a partir dos blocos."""

    model_config = ConfigDict(frozen=True)

    total_alocado: float = 0.0
    score_medio: float = 0.0
    quantidade_aportes: int = 0


# -----------------------------------------------------------------------------
# EMPRESAS SACADAS
# -----------------------------------------------------------------------------


class AgregadoEmpresa(BaseModel):
    """
    Agregação crua por empresa sacada, antes de qualquer formatação.

    Serve a duas consultas: a tabela da gestora (que não seleciona prazo) e a
    carteira de um bloco (que seleciona). Por isso `prazo_medio_dias` tem padrão
    zero em vez de ser obrigatório.
    """

    empresa_sacada_nome: str
    cnpj_sacado_limpo: str
    valor_total_alocado: float
    score_medio: float
    prazo_medio_dias: float = 0.0


class LinhaTabelaGestora(BaseModel):
    """Uma linha da tabela de empresas do dashboard da gestora, pronta para exibição."""

    empresa: str
    cnpj: str = Field(description="Já mascarado: XX.XXX.XXX/XXXX-XX")
    valor: str = Field(description="Já formatado: R$ 1.234,56")
    risco: str = Field(description="Nota de crédito — A+ a C-")
    status: str = Field(description="Adimplente, Atenção ou Inadimplente")


class AgregadoEmpresaBloco(BaseModel):
    """Agregação crua por par (empresa sacada, bloco) — base da tabela de transparência."""

    empresa_sacada_nome: str
    bloco_liquidez_setorial: str | None = None
    score_medio: float
    valor_total: float


class LinhaTransparencia(BaseModel):
    """Uma linha da tabela de transparência do investidor (empresa por bloco)."""

    empresa: str
    bloco: str
    score: float
    valor: str = Field(description="Já formatado: R$ 1.234,56")


# -----------------------------------------------------------------------------
# EXPLORAR E DETALHAR BLOCOS
# -----------------------------------------------------------------------------


class CardBloco(BaseModel):
    """Um card da página Explorar Blocos, com os filtros já aplicados."""

    id_bloco: str = Field(description="Nome do bloco em URL-encode, para a rota dinâmica")
    nome: str
    setor: str
    volume: str = Field(description="Já formatado: R$ 12,3M")
    score_literal: str
    rentabilidade: str


class EmpresaDoBloco(BaseModel):
    """Uma empresa financiada dentro de um Bloco de Liquidez."""

    nome: str
    cnpj: str
    peso: str = Field(description="Participação da empresa no volume do bloco")
    valor: str
    score: str


class DetalheBloco(BaseModel):
    """Os KPIs e a carteira de um Bloco de Liquidez específico."""

    volume_total: str = "R$ 0,00"
    score_medio: str = "N/A"
    prazo_medio: str = "N/A"
    rentabilidade_alvo: str = "N/A"
    empresas: list[EmpresaDoBloco] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# INGESTÃO
# -----------------------------------------------------------------------------


class ResultadoIngestao(BaseModel):
    """
    O que a ingestão de um CSV produziu.

    `registros_bigquery` sai daqui pronto para o `WRITE_APPEND` — na Fase 3 ele
    deixa de ser carregado na mão e passa a ser o payload do evento `AporteIngerido`.
    """

    quantidade_inserida: int
    registros_bigquery: list[dict] = Field(default_factory=list)
