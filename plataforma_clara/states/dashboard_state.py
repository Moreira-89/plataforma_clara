import asyncio
import logging
from typing import Any

import reflex as rx
from sqlalchemy import func

from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.dashboard_service import (
    buscar_metricas_blocos_liquidez,
    buscar_metricas_gerais_gestora,
    buscar_tabela_aportes_gestora,
)

logger = logging.getLogger(__name__)


class DashboardState(rx.State):
    """Estado compartilhado pelos dashboards de investidor e gestora."""

    dados_blocos_gestora: list[dict[str, Any]] = []
    patrimonio_total_gestora: float = 0.0
    tabela_aportes_gestora: list[dict[str, Any]] = []

    tabela_transparencia_investidor: list[dict[str, Any]] = []
    dados_blocos: list[dict[str, Any]] = []

    total_alocado_geral: float = 0.0
    score_medio_geral: float = 0.0
    quantidade_total_aportes: int = 0
    mensagem_erro: str = ""

    @staticmethod
    def _to_float(valor: Any) -> float:
        try:
            return float(valor or 0)
        except (TypeError, ValueError):
            return 0.0

    def _calcular_metricas(self, dados: list[dict[str, Any]]) -> None:
        """Atualiza KPIs consolidados a partir das métricas por bloco."""
        if not dados:
            self.total_alocado_geral = 0.0
            self.score_medio_geral = 0.0
            self.quantidade_total_aportes = 0
            return

        self.total_alocado_geral = sum(self._to_float(item.get("total_alocado")) for item in dados)
        total_scores = sum(self._to_float(item.get("score_medio_reputacao")) for item in dados)
        self.score_medio_geral = round(total_scores / len(dados), 2)
        self.quantidade_total_aportes = sum(int(self._to_float(item.get("quantidade_aportes"))) for item in dados)

    @rx.event
    async def carregar_dados_dashboard(self):
        """Carrega visão do investidor filtrada pelo documento logado."""
        self.mensagem_erro = ""
        self.dados_blocos = []
        self.tabela_transparencia_investidor = []
        self._calcular_metricas([])

        auth = await self.get_state(
            __import__(
                "plataforma_clara.states.autenticacao_state",
                fromlist=["AutenticacaoState"],
            ).AutenticacaoState
        )
        cpf_logado = auth.documento_usuario_logado
        if not cpf_logado:
            return rx.redirect("/")

        self.dados_blocos = await asyncio.to_thread(
            buscar_metricas_blocos_liquidez, cpf_investidor=cpf_logado
        )
        if not self.dados_blocos:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard investidor carregado sem dados.")
            return

        self._calcular_metricas(self.dados_blocos)

        # Query separada para tabela de transparência por empresa/bloco.
        def fetch_transparencia():
            with rx.session() as session:
                return (
                    session.query(
                        tb_aporte.empresa_sacada_nome,
                        tb_aporte.bloco_liquidez_setorial,
                        func.avg(tb_aporte.score_risco_interno).label("score_medio"),
                        func.sum(tb_aporte.valor_mercado_atual).label("valor_total"),
                    )
                    .filter(
                        func.regexp_replace(
                            tb_aporte.documento_investidor_cpf_cnpj,
                            "[^0-9]",
                            "",
                            "g",
                        )
                        == cpf_logado
                    )
                    .filter(tb_aporte.empresa_sacada_nome.isnot(None))
                    .group_by(tb_aporte.empresa_sacada_nome, tb_aporte.bloco_liquidez_setorial)
                    .order_by(func.avg(tb_aporte.score_risco_interno).desc())
                    .all()
                )

        try:
            registros = await asyncio.to_thread(fetch_transparencia)
            for r in registros:
                valor = self._to_float(r.valor_total)
                valor_str = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                self.tabela_transparencia_investidor.append(
                    {
                        "empresa": r.empresa_sacada_nome,
                        "bloco": r.bloco_liquidez_setorial or "N/A",
                        "score": round(self._to_float(r.score_medio), 2),
                        "valor": f"R$ {valor_str}",
                    }
                )
        except Exception:
            logger.exception("Erro ao buscar tabela de transparência do investidor.")

    @rx.event
    async def carregar_dados_gestora(self):
        """Carrega visão global da carteira para a gestora."""
        self.mensagem_erro = ""
        self.dados_blocos_gestora = []
        self.dados_blocos = []
        self.tabela_aportes_gestora = []
        self.patrimonio_total_gestora = 0.0
        self._calcular_metricas([])

        self.dados_blocos_gestora = await asyncio.to_thread(buscar_metricas_gerais_gestora)
        if not self.dados_blocos_gestora:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard gestora carregado sem dados.")
            return

        self.tabela_aportes_gestora = await asyncio.to_thread(buscar_tabela_aportes_gestora)
        self.dados_blocos = self.dados_blocos_gestora
        self._calcular_metricas(self.dados_blocos_gestora)

        def fetch_patrimonio():
            with rx.session() as session:
                return session.query(func.sum(tb_aporte.valor_mercado_atual)).scalar()

        try:
            total = await asyncio.to_thread(fetch_patrimonio)
            self.patrimonio_total_gestora = self._to_float(total)
        except Exception:
            logger.exception("Erro ao buscar patrimônio total da gestora.")

    @rx.var
    def dados_grafico_pizza(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.get("bloco_liquidez_setorial", "N/A"),
                "value": round(self._to_float(item.get("total_alocado")) / 1_000_000, 2),
            }
            for item in self.dados_blocos
        ]

    @rx.var
    def patrimonio_total_investidor(self) -> str:
        texto = f"{self.total_alocado_geral:,.2f}"
        return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def alocacao_blocos_investidor(self) -> list[dict[str, Any]]:
        return [
            {
                "name": item.get("bloco_liquidez_setorial", "N/A"),
                "value": round(self._to_float(item.get("total_alocado")) / 1_000_000, 2),
            }
            for item in self.dados_blocos
        ]

    @rx.var
    def patrimonio_total_gestora_formatado(self) -> str:
        texto = f"{self.patrimonio_total_gestora:,.2f}"
        return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")

    @rx.var
    def qtd_blocos_ativos(self) -> str:
        qtd = len(self.dados_blocos_gestora)
        return f"{qtd} Blocos" if qtd != 1 else "1 Bloco"

    @rx.var
    def classificacao_risco_medio(self) -> str:
        if not self.score_medio_geral:
            return "N/A"
        s = self.score_medio_geral
        if s >= 80:
            return "Baixo (A+)"
        if s >= 70:
            return "Baixo (A)"
        if s >= 60:
            return "Moderado (A-)"
        if s >= 50:
            return "Médio (B+)"
        if s >= 40:
            return "Alto (B)"
        return "Crítico (C-)"

    @rx.var
    def inadimplencia_projetada(self) -> str:
        if not self.dados_blocos_gestora:
            return "0.0%"
        total = len(self.dados_blocos_gestora)
        baixos = sum(1 for b in self.dados_blocos_gestora if self._to_float(b.get("score_medio_reputacao")) < 50)
        return f"{round((baixos / total) * 100, 1)}%"

    @rx.var
    def dados_evolucao_aum(self) -> list[dict[str, Any]]:
        meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun"]
        fatores = [0.83, 0.87, 0.91, 0.95, 0.98, 1.0]
        total = self.patrimonio_total_gestora
        return [
            {"name": mes, "volume": round((total * fator) / 1_000_000, 2)}
            for mes, fator in zip(meses, fatores, strict=False)
        ]

    @rx.var
    def dados_distribuicao_aportes(self) -> list[dict[str, Any]]:
        return [
            {
                "name": b.get("bloco_liquidez_setorial", "N/A"),
                "alocado": round(self._to_float(b.get("total_alocado")) / 1_000_000, 2),
            }
            for b in self.dados_blocos_gestora[:5]
        ]

    @rx.var
    def dados_rendimento_projetado(self) -> list[dict[str, Any]]:
        meses = ["Jul", "Ago", "Set", "Out", "Nov", "Dez"]
        base = self.total_alocado_geral
        dados: list[dict[str, Any]] = []
        for mes in meses:
            base *= 1.01
            dados.append({"name": mes, "rendimento": round((base - self.total_alocado_geral) / 1_000_000, 2)})
        return dados
