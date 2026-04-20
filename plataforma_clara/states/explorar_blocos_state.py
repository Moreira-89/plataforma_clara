import reflex as rx
from typing import Any
from plataforma_clara.states.dashboard_state import DashboardState
import hashlib

class ExplorarBlocosState(DashboardState):
    """Estado responsável pelos filtros da página de Explorar Blocos."""
    
    termo_busca: str = ""
    filtro_setor: str = ""
    filtro_score: str = ""

    @rx.var
    def blocos_filtrados(self) -> list[dict[str, Any]]:
        """Aplica os filtros na lista de blocos da gestora e retorna os dados formatados para o card."""
        
        blocos = self.dados_blocos_gestora
        resultado = []
        
        for b in blocos:
            nome_bloco = str(b.get("bloco_liquidez_setorial", "N/A"))
            setor = nome_bloco # Simplificação para o MVP
            score = float(b.get("score_medio_reputacao", 0))
            
            # 1. Filtro por Busca Textual
            if self.termo_busca.strip():
                if self.termo_busca.lower() not in nome_bloco.lower():
                    continue
                    
            # 2. Filtro por Setor
            if self.filtro_setor and self.filtro_setor != "Todos os Setores":
                if self.filtro_setor.lower() not in setor.lower():
                    continue
                    
            # 3. Filtro por Score
            if self.filtro_score and self.filtro_score != "Qualquer Score":
                if self.filtro_score == "A+ a A-" and score < 60:
                    continue
                if self.filtro_score == "B+ a B-" and (score >= 60 or score < 40):
                    continue
                if self.filtro_score == "C+ ou menor" and score >= 40:
                    continue
            
            # Formatação do Volume para Milhões (M)
            v = float(b.get("total_alocado", 0))
            v_str = f"{v / 1_000_000:,.1f}".replace(".", ",")
            
            # Rentabilidade Simulada determinística baseada no nome
            hash_rent = int(hashlib.sha1(nome_bloco.encode('utf-8')).hexdigest(), 16) % 8 + 10 # 10 a 18
            
            # Tradução Numérico -> Literal
            nota = "C-"
            if score >= 80: nota = "A+"
            elif score >= 70: nota = "A"
            elif score >= 60: nota = "A-"
            elif score >= 50: nota = "B+"
            elif score >= 40: nota = "B"
            
            # O ID para navegação será o nome sem espaços (em base64 ou url encode)
            # Para simplificar a URL:
            import urllib.parse
            id_bloco = urllib.parse.quote(nome_bloco)
            
            resultado.append({
                "id_bloco": id_bloco,
                "nome": nome_bloco,
                "setor": setor,
                "volume": f"R$ {v_str}M",
                "score_literal": nota,
                "rentabilidade": f"{hash_rent}.5%"
            })
            
        return resultado
