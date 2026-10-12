"""
Testes de `storage/scores.py`: leitura do CSV de scores, sem rede.

Cada teste aponta o leitor para um arquivo temporário e limpa o cache antes e depois.
"""

import pytest

from app.storage import scores


@pytest.fixture(autouse=True)
def limpar_cache():
    scores.carregar_scores.cache_clear()
    yield
    scores.carregar_scores.cache_clear()


def usar_arquivo(monkeypatch, tmp_path, conteudo):
    arquivo = tmp_path / "scores_empresas.csv"
    arquivo.write_text(conteudo, encoding="utf-8")
    monkeypatch.setattr(scores, "CAMINHO_SCORES", arquivo)


def test_le_o_score_de_cada_empresa(monkeypatch, tmp_path):
    usar_arquivo(monkeypatch, tmp_path, "id_empresa,score\n1,15\n2,40.5\n")

    assert scores.carregar_scores() == {"1": 15.0, "2": 40.5}


def test_ignora_linhas_malformadas_e_scores_fora_da_faixa(monkeypatch, tmp_path):
    usar_arquivo(monkeypatch, tmp_path, "id_empresa,score\n1,abc\n2,101\n3,-1\n,50\n4,0\n5,100\n")

    assert scores.carregar_scores() == {"4": 0.0, "5": 100.0}


def test_sem_o_arquivo_devolve_vazio(monkeypatch, tmp_path):
    monkeypatch.setattr(scores, "CAMINHO_SCORES", tmp_path / "nao-existe.csv")

    assert scores.carregar_scores() == {}


def test_o_arquivo_do_projeto_cobre_scores_validos():
    todos = scores.carregar_scores()

    assert len(todos) > 0
    assert all(0 <= v <= 100 for v in todos.values())
