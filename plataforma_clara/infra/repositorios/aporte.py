"""
Repositório de acesso aos aportes (`tb_aporte`) no PostgreSQL.

Concentra todo o SQL que antes estava espalhado entre `dashboard_service`,
`dashboard_state` e `detalhes_bloco_state`. Cada método recebe a sessão pelo
construtor, devolve objetos de domínio e deixa as exceções subirem — quem decide
o que fazer com uma falha de banco é a camada de serviço, não esta.

As consultas de agregação usam SQL textual parametrizado. O documento do investidor
SEMPRE entra como parâmetro de bind, nunca concatenado: é a fronteira entre um dado
vindo da sessão do usuário e o banco.
"""

import logging

import sqlalchemy as sa
from sqlalchemy import func
from sqlmodel import Session

from plataforma_clara.domain.models import Aporte
from plataforma_clara.domain.schemas import (
    AgregadoEmpresa,
    AgregadoEmpresaBloco,
    MetricaBloco,
)

logger = logging.getLogger(__name__)

# Agregação por Bloco de Liquidez. O filtro por investidor é opcional e entra via
# formatação da cláusula, mas o VALOR do documento sempre vai como bind parameter.
_SQL_METRICAS_BLOCOS = """
    SELECT
        bloco_liquidez_setorial,
        SUM(valor_mercado_atual)      AS total_alocado,
        AVG(score_risco_interno)      AS score_medio_reputacao,
        COUNT(id_aporte_uuid)         AS quantidade_aportes
    FROM tb_aporte
    WHERE bloco_liquidez_setorial IS NOT NULL
      {filtro_investidor}
    GROUP BY bloco_liquidez_setorial
    ORDER BY total_alocado DESC
"""

# REGEXP_REPLACE normaliza o documento gravado antes de comparar, para que linhas
# com e sem máscara ('123.456.789-00' e '12345678900') sejam tratadas igual.
_FILTRO_INVESTIDOR = (
    "AND REGEXP_REPLACE(documento_investidor_cpf_cnpj, '[^0-9]', '', 'g') = :documento"
)

_SQL_EMPRESAS_GESTORA = """
    SELECT
        empresa_sacada_nome,
        cnpj_sacado_limpo,
        SUM(valor_mercado_atual)  AS valor_total_alocado,
        AVG(score_risco_interno)  AS score_medio
    FROM tb_aporte
    WHERE empresa_sacada_nome IS NOT NULL
    GROUP BY empresa_sacada_nome, cnpj_sacado_limpo
    ORDER BY valor_total_alocado DESC
    LIMIT :limite
"""

_SQL_EMPRESAS_DO_BLOCO = """
    SELECT
        empresa_sacada_nome,
        cnpj_sacado_limpo,
        SUM(valor_mercado_atual)                AS valor_total_alocado,
        AVG(score_risco_interno)                AS score_medio,
        COALESCE(AVG(prazo_vencimento_dias), 0) AS prazo_medio_dias
    FROM tb_aporte
    WHERE bloco_liquidez_setorial = :bloco
    GROUP BY empresa_sacada_nome, cnpj_sacado_limpo
    ORDER BY valor_total_alocado DESC
"""


class AporteRepositorio:
    """
    Acesso de leitura e escrita à tabela de aportes.

    Args:
        sessao (Session): Sessão aberta pelo chamador. O repositório não a fecha.
    """

    def __init__(self, sessao: Session) -> None:
        self.sessao = sessao

    # -------------------------------------------------------------------------
    # LEITURA — AGREGAÇÕES
    # -------------------------------------------------------------------------

    def metricas_por_bloco(self, *, documento_investidor: str | None = None) -> list[MetricaBloco]:
        """
        Agrega os aportes por Bloco de Liquidez.

        COMO FUNCIONA:
            1. Monta a consulta com ou sem o filtro por investidor — sem documento,
               é a visão consolidada da gestora; com documento, a carteira de um
               investidor. As duas visões compartilham a mesma agregação de propósito:
               é o que garante que gestora e investidor vejam o mesmo número.
            2. Executa com o documento como parâmetro de bind.
            3. Converte cada linha em `MetricaBloco`.

        Args:
            documento_investidor (str | None): CPF/CNPJ somente com dígitos. None
                                               devolve a visão consolidada.

        Returns:
            list[MetricaBloco]: Blocos ordenados por volume alocado decrescente.
        """
        # --- 1. MONTAGEM ---
        filtro = _FILTRO_INVESTIDOR if documento_investidor else ""
        consulta = sa.text(_SQL_METRICAS_BLOCOS.format(filtro_investidor=filtro))
        parametros = {"documento": documento_investidor} if documento_investidor else {}

        # --- 2. EXECUÇÃO ---
        linhas = self.sessao.execute(consulta, parametros).mappings().fetchall()

        # --- 3. CONVERSÃO ---
        return [MetricaBloco.model_validate(dict(linha)) for linha in linhas]

    def empresas_sacadas(self, *, limite: int = 50) -> list[AgregadoEmpresa]:
        """
        Agrega os aportes por empresa sacada, para a tabela da gestora.

        Args:
            limite (int): Máximo de empresas devolvidas. Padrão 50.

        Returns:
            list[AgregadoEmpresa]: Empresas ordenadas por volume alocado decrescente.
        """
        linhas = (
            self.sessao.execute(sa.text(_SQL_EMPRESAS_GESTORA), {"limite": limite})
            .mappings()
            .fetchall()
        )
        return [AgregadoEmpresa.model_validate(dict(linha)) for linha in linhas]

    def empresas_do_bloco(self, bloco: str) -> list[AgregadoEmpresa]:
        """
        Agrega os aportes de um Bloco de Liquidez por empresa sacada.

        Args:
            bloco (str): Nome exato do bloco, já decodificado da URL.

        Returns:
            list[AgregadoEmpresa]: Empresas do bloco, com prazo médio preenchido.
        """
        linhas = (
            self.sessao.execute(sa.text(_SQL_EMPRESAS_DO_BLOCO), {"bloco": bloco})
            .mappings()
            .fetchall()
        )
        return [AgregadoEmpresa.model_validate(dict(linha)) for linha in linhas]

    def empresas_por_bloco_do_investidor(self, documento: str) -> list[AgregadoEmpresaBloco]:
        """
        Agrega a carteira do investidor por par (empresa sacada, bloco).

        É a tabela de transparência: mostra em quais empresas o dinheiro do
        investidor foi efetivamente aplicado dentro de cada bloco.

        Args:
            documento (str): CPF/CNPJ do investidor, somente com dígitos.

        Returns:
            list[AgregadoEmpresaBloco]: Pares ordenados por score médio decrescente.
        """
        linhas = (
            self.sessao.query(
                Aporte.empresa_sacada_nome,
                Aporte.bloco_liquidez_setorial,
                func.avg(Aporte.score_risco_interno).label("score_medio"),
                func.sum(Aporte.valor_mercado_atual).label("valor_total"),
            )
            .filter(
                func.regexp_replace(Aporte.documento_investidor_cpf_cnpj, "[^0-9]", "", "g")
                == documento
            )
            .filter(Aporte.empresa_sacada_nome.isnot(None))
            .group_by(Aporte.empresa_sacada_nome, Aporte.bloco_liquidez_setorial)
            .order_by(func.avg(Aporte.score_risco_interno).desc())
            .all()
        )

        return [
            AgregadoEmpresaBloco(
                empresa_sacada_nome=linha.empresa_sacada_nome,
                bloco_liquidez_setorial=linha.bloco_liquidez_setorial,
                score_medio=float(linha.score_medio or 0.0),
                valor_total=float(linha.valor_total or 0.0),
            )
            for linha in linhas
        ]

    def patrimonio_total(self) -> float:
        """
        Soma o valor de mercado de todos os aportes da base.

        Returns:
            float: Patrimônio total sob gestão. Zero quando não há aportes.
        """
        total = self.sessao.query(func.sum(Aporte.valor_mercado_atual)).scalar()
        return float(total or 0.0)

    # -------------------------------------------------------------------------
    # ESCRITA
    # -------------------------------------------------------------------------

    def inserir_em_lote(self, registros: list[dict]) -> int:
        """
        Insere vários aportes numa única operação e confirma a transação.

        `bulk_insert_mappings` é usado por ser ordens de grandeza mais rápido que
        instanciar um objeto por linha — um CSV de ingestão traz milhares delas.
        O preço é não passar pelos validadores do modelo: por isso os registros
        precisam vir do `csv_processor`, que já validou e coagiu os tipos.

        ATENÇÃO: o commit acontece aqui e a escrita no BigQuery acontece depois,
        fora de qualquer transação. Uma falha no BigQuery deixa os dois lados
        divergentes em silêncio (D3 no roadmap) — o padrão outbox da Fase 3 existe
        para fechar exatamente esta janela.

        Args:
            registros (list[dict]): Aportes prontos, com as colunas de `tb_aporte`.

        Returns:
            int: Quantidade de registros inseridos.
        """
        if not registros:
            return 0

        self.sessao.bulk_insert_mappings(Aporte, registros)
        self.sessao.commit()
        logger.info("%d aportes inseridos no PostgreSQL.", len(registros))
        return len(registros)
