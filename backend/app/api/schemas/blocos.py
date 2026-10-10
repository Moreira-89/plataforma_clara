"""
Contratos do formulário de criação de bloco de liquidez.

COMO FUNCIONA:
    1. `NovoBlocoRequisicao` é o corpo de `POST /blocos`; o formato é validado aqui e as
       regras de negócio em `domain/blocos.py`.
    2. `BlocoCriado` devolve o código gerado e o capital estimado de cada empresa.
    3. `EtiquetaResposta` e `EmpresaBusca` alimentam o seletor e a busca do formulário.
    4. `BlocoListagem` e `BlocoDetalhe` devolvem os blocos já criados; a cor vem da etiqueta.

Args:
    Nenhum.

Returns:
    Nenhum.

Raises:
    Nenhum.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class EtiquetaResposta(BaseModel):
    """Uma pedra e a sua cor."""

    nome: str
    cor: str = Field(description="Cor em hexadecimal, ex.: #0F52BA")


class EmpresaBusca(BaseModel):
    """Uma empresa do cadastro, devolvida pela busca."""

    id_empresa: str
    nome_fantasia: str
    razao_social: str
    cnpj: str = Field(description="Somente dígitos")
    ramo_atividade: str


class EmpresaDoBlocoEntrada(BaseModel):
    """Empresa escolhida e a porcentagem do capital do bloco que ela recebe."""

    id_empresa: str = Field(min_length=1)
    percentual_liquidez: Decimal = Field(gt=0, le=100, decimal_places=2)


class NovoBlocoRequisicao(BaseModel):
    """Corpo do formulário de criação de bloco."""

    etiqueta: str
    capital_total: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    data_vencimento: date
    responsavel_tecnico: str = Field(min_length=1)
    observacao: str = ""
    empresas: list[EmpresaDoBlocoEntrada] = Field(min_length=1)


class EmpresaAlocadaResposta(BaseModel):
    """Empresa do bloco criado, com o capital estimado."""

    id_empresa: str
    percentual_liquidez: Decimal
    capital_estimado: Decimal


class BlocoCriado(BaseModel):
    """Bloco gravado."""

    id_bloco: str
    codigo_identificacao: str
    etiqueta: str
    capital_total: Decimal
    data_criacao: date
    data_vencimento: date
    empresas: list[EmpresaAlocadaResposta]


class BlocoListagem(BaseModel):
    """Um bloco já criado, na lista."""

    id_bloco: str
    codigo_identificacao: str
    etiqueta: str
    cor: str | None = Field(description="Cor da pedra; vazia se a etiqueta saiu da lista")
    capital_total: Decimal
    data_criacao: date
    data_vencimento: date
    responsavel_tecnico: str
    observacao: str | None
    quantidade_empresas: int


class EmpresaDoBlocoDetalhe(BaseModel):
    """Empresa de um bloco já criado."""

    id_empresa: str
    cnpj: str = Field(description="Somente dígitos")
    nome_fantasia: str | None = Field(
        description="Vazio se o cadastro de empresas estiver fora do ar"
    )
    ramo_atividade: str | None
    capital_estimado: Decimal
    percentual_liquidez: Decimal


class BlocoDetalhe(BlocoListagem):
    """Um bloco já criado, com as suas empresas."""

    empresas: list[EmpresaDoBlocoDetalhe]
