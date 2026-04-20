import reflex as rx
import asyncio
from typing import Any
import pandas as pd
import sqlalchemy as sa
from plataforma_clara.states.dashboard_state import DashboardState
import urllib.parse
import hashlib

class DetalhesBlocoState(DashboardState):
    """Estado para a página de detalhes de um bloco de liquidez específico."""
    
    nome_bloco: str = ""
    volume_total: str = ""
    rentabilidade_alvo: str = ""
    score_medio: str = ""
    prazo_medio: str = ""
    
    empresas_bloco: list[dict[str, Any]] = []

    async def carregar_detalhes(self):
        """Busca os detalhes do bloco no BigQuery de forma assíncrona."""
        
        # Lê o parâmetro de rota diretamente da sessão
        bloco_id_raw = self.router.page.params.get("bloco_id", "")
        bloco_id = bloco_id_raw[0] if isinstance(bloco_id_raw, list) and bloco_id_raw else bloco_id_raw
        
        if not bloco_id:
            return
            
        bloco_decodificado = urllib.parse.unquote(str(bloco_id))
        self.nome_bloco = bloco_decodificado
        
        try:
            resultados = await asyncio.to_thread(self._buscar_dados_bloco_bq, bloco_decodificado)
            self.empresas_bloco = resultados.get("empresas", [])
            self.volume_total = resultados.get("volume_total", "R$ 0,00")
            self.score_medio = resultados.get("score_medio", "N/A")
            self.rentabilidade_alvo = resultados.get("rentabilidade_alvo", "N/A")
            self.prazo_medio = resultados.get("prazo_medio", "N/A")
            
        except Exception as e:
            print(f"Erro ao carregar bloco {bloco_decodificado}: {e}")
            
    def _buscar_dados_bloco_bq(self, bloco: str) -> dict:
        """Query bloqueante isolada em thread para não travar a UI (usando Supabase)."""
        query = sa.text("""
            SELECT 
                empresa_sacada_nome,
                cnpj_sacado_limpo,
                SUM(valor_mercado_atual) as valor_alocado,
                AVG(score_risco_interno) as score,
                COALESCE(AVG(prazo_vencimento_dias), 0) as prazo_medio
            FROM tb_aporte
            WHERE bloco_liquidez_setorial = :bloco
            GROUP BY empresa_sacada_nome, cnpj_sacado_limpo
            ORDER BY valor_alocado DESC
        """)
        
        with rx.session() as session:
            result = session.execute(query, {"bloco": bloco}).mappings().fetchall()
            
        dados_db = [dict(row) for row in result]
        
        if not dados_db:
            return {}
            
        total_vol = sum((float(r["valor_alocado"]) if r["valor_alocado"] else 0.0) for r in dados_db)
        score_med = sum((float(r["score"]) if r["score"] else 0.0) for r in dados_db) / len(dados_db) if len(dados_db) > 0 else 0
        prazo_med = sum((float(r["prazo_medio"]) if r["prazo_medio"] else 0.0) for r in dados_db) / len(dados_db) if len(dados_db) > 0 else 0
        
        empresas = []
        for row in dados_db:
            val = float(row["valor_alocado"]) if row["valor_alocado"] else 0.0
            peso = val / total_vol if total_vol > 0 else 0
            sc = float(row["score"]) if row["score"] else 0.0
            nota = "C-"
            if sc >= 80: nota = "A+"
            elif sc >= 70: nota = "A"
            elif sc >= 60: nota = "A-"
            elif sc >= 50: nota = "B+"
            elif sc >= 40: nota = "B"
            
            v_str = f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            empresas.append({
                "nome": str(row["empresa_sacada_nome"]),
                "cnpj": str(row["cnpj_sacado_limpo"]),
                "peso": f"{peso * 100:.1f}%",
                "valor": f"R$ {v_str}",
                "score": nota
            })
            
        # Calcula nota geral e rentabilidade simulada
        nota_geral = "C-"
        if score_med >= 80: nota_geral = "A+ (Baixo Risco)"
        elif score_med >= 70: nota_geral = "A (Baixo Risco)"
        elif score_med >= 60: nota_geral = "A- (Baixo Risco)"
        elif score_med >= 50: nota_geral = "B+ (Médio Risco)"
        elif score_med >= 40: nota_geral = "B (Médio Risco)"
        
        hash_rent = int(hashlib.sha1(bloco.encode('utf-8')).hexdigest(), 16) % 8 + 10
        total_str = f"{total_vol:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        return {
            "volume_total": f"R$ {total_str}",
            "score_medio": nota_geral,
            "prazo_medio": f"{int(prazo_med)} Dias",
            "rentabilidade_alvo": f"{hash_rent}.5% a.a.",
            "empresas": empresas
        }
