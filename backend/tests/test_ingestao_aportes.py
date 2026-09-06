"""
Testes do serviço de ingestão de CSV.

Cobre `app/ingestion/aportes`. É a fronteira onde um arquivo enviado por uma
gestora vira registro persistível, e onde nasce o payload que segue para o BigQuery.

O `csv_processor` continua com seus próprios testes; aqui o foco é o que acontece
DEPOIS dele: geração de UUID e o formato das datas em cada destino.
"""

from __future__ import annotations

import datetime

import pytest

pytest.importorskip("pandas", reason="requer pandas instalado")

from app.ingestion.aportes import ingerir_csv  # noqa: E402


def test_ingestao_insere_as_linhas_validas(escrever_csv, linha_aporte_valida):
    """Caminho feliz: duas linhas boas viram dois registros nos dois formatos."""
    caminho = escrever_csv([linha_aporte_valida, linha_aporte_valida])

    resultado = ingerir_csv(caminho)

    assert resultado.quantidade_inserida == 2
    assert len(resultado.registros) == 2
    assert len(resultado.registros_bigquery) == 2


def test_uuid_do_csv_nunca_e_reaproveitado(escrever_csv, linha_aporte_valida):
    """
    Cada linha recebe um UUID novo, mesmo que o CSV traga um. É o que permite
    reenviar o mesmo arquivo sem colidir com os registros anteriores — e é também o
    motivo de a plataforma não conseguir detectar um reenvio acidental hoje.
    """
    caminho = escrever_csv([linha_aporte_valida, linha_aporte_valida])

    resultado = ingerir_csv(caminho)

    uuids = [registro["id_aporte_uuid"] for registro in resultado.registros]
    assert linha_aporte_valida["id_aporte_uuid"] not in uuids
    assert len(set(uuids)) == 2


def test_datas_saem_como_date_no_registro_e_iso_no_bigquery(escrever_csv, linha_aporte_valida):
    """
    Os dois destinos querem formatos diferentes da mesma data: a persistência
    operacional guarda `datetime.date` e o schema do BigQuery declara STRING. A
    conversão acontece só na cópia do BigQuery, sem contaminar o outro registro.
    """
    caminho = escrever_csv([linha_aporte_valida])

    resultado = ingerir_csv(caminho)

    assert resultado.registros[0]["data_vencimento"] == datetime.date(2026, 12, 31)
    assert resultado.registros_bigquery[0]["data_vencimento"] == "2026-12-31"


def test_csv_sem_linhas_validas_nao_produz_registro(escrever_csv, linha_aporte_valida):
    """Nada a inserir não é erro: devolve resultado vazio, sem levantar."""
    caminho = escrever_csv([dict(linha_aporte_valida, documento_investidor_cpf_cnpj="")])

    resultado = ingerir_csv(caminho)

    assert resultado.quantidade_inserida == 0
    assert resultado.registros == []


def test_csv_fora_do_padrao_falha_no_contrato(escrever_csv, linha_aporte_valida):
    """Coluna obrigatória ausente derruba o arquivo inteiro, sem resultado parcial."""
    sem_score = {k: v for k, v in linha_aporte_valida.items() if k != "score_risco_interno"}
    caminho = escrever_csv([sem_score])

    with pytest.raises(ValueError, match="score_risco_interno"):
        ingerir_csv(caminho)


def test_registro_do_bigquery_tem_as_mesmas_chaves_do_registro(escrever_csv, linha_aporte_valida):
    """
    Os dois lados precisam ficar sincronizados manualmente. Uma divergência de
    chaves aqui vira uma coluna faltando no BigQuery — e um relatório de IA que
    ignora um dado que o dashboard mostra.
    """
    caminho = escrever_csv([linha_aporte_valida])

    resultado = ingerir_csv(caminho)

    assert set(resultado.registros_bigquery[0]) == set(resultado.registros[0])
