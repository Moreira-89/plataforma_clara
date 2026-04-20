import logging
from typing import Any

import reflex as rx
from sqlalchemy import func

from plataforma_clara.model.schemas import tb_aporte
from plataforma_clara.services.assistente_ia import gerar_insight_relatorio_langchain
from plataforma_clara.services.dashboard_service import (
    buscar_metricas_blocos_liquidez,
    buscar_metricas_gerais_gestora,
    buscar_tabela_aportes_gestora,
)

logger = logging.getLogger(__name__)


class DashboardState(rx.State):
    """Estado compartilhado pelos dashboards de gestora e investidor."""

    # ── Gestora: dados globais e filtro por bloco ────────────────────────────
    dados_blocos_gestora: list[dict[str, Any]] = []
    bloco_selecionado_gestora: str = "Todos"
    lista_nomes_blocos: list[str] = ["Todos"]
    patrimonio_total_gestora: float = 0.0
    score_medio_blocos: list[dict[str, Any]] = []
    ranking_empresas_gestora: list[dict[str, Any]] = []
    tabela_aportes_gestora: list[dict[str, Any]] = []

    # ── Investidor: tabela de transparência ───────────────────────────────────
    tabela_transparencia_investidor: list[dict[str, Any]] = []

    # ── Dados de exibição (compartilhados pelos KPIs/gráficos) ───────────────
    dados_blocos: list[dict[str, Any]] = []

    # Insights gerados pela IA (Mocks por enquanto)
    insight_ia: str = ""

    # Métricas consolidadas para os Cards de topo
    total_alocado_geral: float = 0.0
    score_medio_geral: float = 0.0
    quantidade_total_aportes: int = 0

    # Mensagem de erro para feedback ao usuário
    mensagem_erro: str = ""

    # ── Helpers internos ─────────────────────────────────────────────────────

    def _calcular_metricas(self, dados: list[dict[str, Any]]) -> None:
        """Recalcula KPIs a partir de uma lista de blocos."""
        if not dados:
            self.total_alocado_geral = 0.0
            self.score_medio_geral = 0.0
            self.quantidade_total_aportes = 0
            return

        self.total_alocado_geral = sum(
            item.get("total_alocado", 0) for item in dados
        )
        total_scores = sum(
            item.get("score_medio_reputacao", 0) for item in dados
        )
        self.score_medio_geral = round(total_scores / len(dados), 2)
        self.quantidade_total_aportes = sum(
            item.get("quantidade_aportes", 0) for item in dados
        )

    # ── Investidor ───────────────────────────────────────────────────────────

    @rx.event
    async def carregar_dados_dashboard(self):
        """
        Evento disparado ao carregar o dashboard do investidor.
        Busca dados filtrados pelo documento do investidor logado.
        """
        # Reset completo para evitar dados residuais de outras sessões/páginas
        self.mensagem_erro = ""
        self.dados_blocos = []
        self.total_alocado_geral = 0.0
        self.score_medio_geral = 0.0
        self.quantidade_total_aportes = 0
        self.insight_ia = ""

        # Acessa o sub-state de autenticação de forma segura via get_state()
        auth = await self.get_state(
            # import inline para evitar circular import no module-level
            __import__(
                "plataforma_clara.states.autenticacao_state",
                fromlist=["AutenticacaoState"],
            ).AutenticacaoState
        )
        cpf_logado = auth.documento_usuario_logado

        if not cpf_logado:
            return rx.redirect("/")

        self.dados_blocos = buscar_metricas_blocos_liquidez(cpf_investidor=cpf_logado)

        if not self.dados_blocos:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard investidor carregado sem dados.")
            return

        self._calcular_metricas(self.dados_blocos)

        # Gera o insight inicial (usando o Mock do LangChain)
        self.insight_ia = gerar_insight_relatorio_langchain(self.dados_blocos[0])

        # ── Tabela de Transparência via Supabase ─────────────────────────────
        try:
            with rx.session() as session:
                registros = (
                    session.query(
                        tb_aporte.empresa_sacada_nome,
                        tb_aporte.bloco_liquidez_setorial,
                        func.avg(tb_aporte.score_risco_interno).label("score_medio"),
                        func.sum(tb_aporte.valor_mercado_atual).label("valor_total"),
                    )
                    .filter(
                        func.regexp_replace(
                            tb_aporte.documento_investidor_cpf_cnpj,
                            "[^0-9]", "", "g",
                        ) == cpf_logado
                    )
                    .filter(tb_aporte.empresa_sacada_nome.isnot(None))
                    .group_by(
                        tb_aporte.empresa_sacada_nome,
                        tb_aporte.bloco_liquidez_setorial,
                    )
                    .order_by(func.avg(tb_aporte.score_risco_interno).desc())
                    .all()
                )
                self.tabela_transparencia_investidor = [
                    {
                        "empresa": r.empresa_sacada_nome,
                        "bloco": r.bloco_liquidez_setorial or "N/A",
                        "score": round(float(r.score_medio or 0), 2),
                        "valor": f"R$ {float(r.valor_total or 0):,.2f}",
                    }
                    for r in registros
                ]
        except Exception:
            logger.exception("Erro ao buscar tabela de transparência do investidor.")

        logger.info(
            "Dashboard investidor carregado: %d blocos, R$ %.2f alocados.",
            len(self.dados_blocos),
            self.total_alocado_geral,
        )

    # ── Gestora ──────────────────────────────────────────────────────────────

    @rx.event
    def carregar_dados_gestora(self):
        """Busca a visão global do FIDC para a Gestora (BigQuery + Supabase)."""
        self.mensagem_erro = ""

        # ── 1. Dados via BigQuery (gráficos e filtro por bloco) ──────────────
        self.dados_blocos_gestora = buscar_metricas_gerais_gestora()

        if not self.dados_blocos_gestora:
            self.mensagem_erro = "Nenhum dado encontrado para exibir."
            logger.warning("Dashboard gestora carregado sem dados.")
            return

        # ── 1b. Tabela de aportes por empresa (BigQuery) ──────────────────────
        self.tabela_aportes_gestora = buscar_tabela_aportes_gestora()

        # Cria a lista de opções do menu dinamicamente
        nomes = [item["bloco_liquidez_setorial"] for item in self.dados_blocos_gestora]
        self.lista_nomes_blocos = ["Todos"] + nomes

        # Calcula os KPIs com todos os blocos e gera insight
        self._aplicar_filtro_bloco("Todos")

        self.insight_ia = gerar_insight_relatorio_langchain(self.dados_blocos_gestora[0])

        # ── 2. Dados via Supabase (patrimônio + score + ranking) ──────────────
        try:
            with rx.session() as session:
                # Soma TUDO (sem filtro de CPF)
                total = session.query(
                    func.sum(tb_aporte.valor_mercado_atual)
                ).scalar()
                self.patrimonio_total_gestora = float(total) if total else 0.0

                # Média de Score por Bloco
                resultados = session.query(
                    tb_aporte.bloco_liquidez_setorial,
                    func.avg(tb_aporte.score_risco_interno),
                ).group_by(
                    tb_aporte.bloco_liquidez_setorial
                ).all()

                self.score_medio_blocos = [
                    {"bloco": bloco, "score_medio": round(float(score), 2)}
                    for bloco, score in resultados
                    if bloco is not None
                ]

                # Ranking de reputação geral (todas as empresas)
                registros_ranking = (
                    session.query(
                        tb_aporte.empresa_sacada_nome,
                        tb_aporte.bloco_liquidez_setorial,
                        func.avg(tb_aporte.score_risco_interno).label("score_medio"),
                        func.sum(tb_aporte.valor_mercado_atual).label("volume_total"),
                    )
                    .filter(tb_aporte.empresa_sacada_nome.isnot(None))
                    .group_by(
                        tb_aporte.empresa_sacada_nome,
                        tb_aporte.bloco_liquidez_setorial,
                    )
                    .order_by(func.avg(tb_aporte.score_risco_interno).desc())
                    .limit(50)
                    .all()
                )
                self.ranking_empresas_gestora = [
                    {
                        "empresa": r.empresa_sacada_nome,
                        "bloco": r.bloco_liquidez_setorial or "N/A",
                        "score_medio": round(float(r.score_medio or 0), 2),
                        "volume": f"R$ {float(r.volume_total or 0):,.2f}",
                    }
                    for r in registros_ranking
                ]
        except Exception:
            logger.exception("Erro ao buscar métricas da gestora no Supabase.")

        logger.info(
            "Dashboard gestora carregado: %d blocos, patrimônio R$ %.2f.",
            len(self.dados_blocos_gestora),
            self.patrimonio_total_gestora,
        )

    @rx.event
    def set_bloco_selecionado_gestora(self, novo_bloco: str):
        """Atualiza KPIs quando a gestora escolhe um bloco diferente no menu."""
        self._aplicar_filtro_bloco(novo_bloco)

    def _aplicar_filtro_bloco(self, bloco: str) -> None:
        """Filtra dados da gestora por bloco e recalcula KPIs."""
        self.bloco_selecionado_gestora = bloco

        if bloco == "Todos":
            dados_filtrados = self.dados_blocos_gestora
        else:
            dados_filtrados = [
                b for b in self.dados_blocos_gestora
                if b.get("bloco_liquidez_setorial") == bloco
            ]

        self._calcular_metricas(dados_filtrados)
        # Atualiza o gráfico de pizza com os dados filtrados
        self.dados_blocos = dados_filtrados

    # ── Computed vars ────────────────────────────────────────────────────────

    @rx.var
    def dados_grafico_pizza(self) -> list[dict[str, Any]]:
        """Propriedade computada que formata os dados para o gráfico de pizza."""
        return [
            {"name": item["bloco_liquidez_setorial"], "value": item["total_alocado"]}
            for item in self.dados_blocos
        ]

    @rx.var
    def patrimonio_total_investidor(self) -> str:
        """Patrimônio total do investidor logado, formatado em R$."""
        return f"R$ {self.total_alocado_geral:,.2f}"

    @rx.var
    def alocacao_blocos_investidor(self) -> list[dict[str, Any]]:
        """Dados de alocação por bloco formatados para gráfico de pizza do investidor."""
        return [
            {"name": item["bloco_liquidez_setorial"], "value": item["total_alocado"]}
            for item in self.dados_blocos
        ]

    @rx.var
    def patrimonio_total_gestora_formatado(self) -> str:
        """Patrimônio total do FIDC formatado em R$."""
        return f"R$ {self.patrimonio_total_gestora:,.2f}"

    @rx.var
    def qtd_blocos_ativos(self) -> str:
        """Quantidade de blocos de liquidez ativos."""
        qtd = len(self.dados_blocos_gestora)
        return f"{qtd} Blocos" if qtd != 1 else "1 Bloco"

    @rx.var
    def classificacao_risco_medio(self) -> str:
        """Classificação de risco média da carteira baseada no score médio."""
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
        """Percentual estimado de inadimplência baseado nos scores baixos."""
        if not self.dados_blocos_gestora:
            return "0.0%"
        total = len(self.dados_blocos_gestora)
        baixos = sum(1 for b in self.dados_blocos_gestora if b.get("score_medio_reputacao", 0) < 50)
        pct = round((baixos / total) * 100, 1) if total else 0
        return f"{pct}%"
