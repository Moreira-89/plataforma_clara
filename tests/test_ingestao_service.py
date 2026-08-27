"""
Testes do serviço de ingestão de CSV.

Cobre `services/ingestao_service`, extraído na Fase 1 de dentro de uma closure do
`IngestaoDadosState`. É a fronteira onde um arquivo enviado por uma gestora vira
registro de banco, e onde nasce o payload que segue para o BigQuery.

O `csv_processor` continua com seus próprios testes; aqui o foco é o que acontece
DEPOIS dele: geração de UUID, formato das datas e o que chega ao banco.
"""

from __future__ import annotations

import datetime

import pytest

pytest.importorskip("sqlmodel", reason="requer o stack de banco instalado")

from plataforma_clara.services.ingestao_service import ingerir_csv  # noqa: E402


def test_ingestao_insere_as_linhas_validas(escrever_csv, linha_aporte_valida, fabricar_sessao_fake):
    """Caminho feliz: duas linhas boas viram dois registros e um commit só."""
    fabrica = fabricar_sessao_fake()
    caminho = escrever_csv([linha_aporte_valida, linha_aporte_valida])

    resultado = ingerir_csv(caminho, sessao_factory=fabrica)

    assert resultado.quantidade_inserida == 2
    assert len(fabrica().inseridos) == 2
    assert fabrica().commits == 1


def test_uuid_do_csv_nunca_e_reaproveitado(escrever_csv, linha_aporte_valida, fabricar_sessao_fake):
    """
    Cada linha recebe um UUID novo, mesmo que o CSV traga um. É o que permite
    reenviar o mesmo arquivo sem colidir com os registros anteriores — e é também o
    motivo de a plataforma não conseguir detectar um reenvio acidental hoje.
    """
    fabrica = fabricar_sessao_fake()
    caminho = escrever_csv([linha_aporte_valida, linha_aporte_valida])

    ingerir_csv(caminho, sessao_factory=fabrica)

    uuids = [registro["id_aporte_uuid"] for registro in fabrica().inseridos]
    assert linha_aporte_valida["id_aporte_uuid"] not in uuids
    assert len(set(uuids)) == 2


def test_datas_vao_como_date_para_o_postgres_e_iso_para_o_bigquery(
    escrever_csv, linha_aporte_valida, fabricar_sessao_fake
):
    """
    Os dois destinos querem formatos diferentes da mesma data: o SQLModel espera
    `datetime.date` e o schema do BigQuery declara STRING. A conversão acontece só
    na cópia do BigQuery, sem contaminar o registro do banco.
    """
    fabrica = fabricar_sessao_fake()
    caminho = escrever_csv([linha_aporte_valida])

    resultado = ingerir_csv(caminho, sessao_factory=fabrica)

    assert fabrica().inseridos[0]["data_vencimento"] == datetime.date(2026, 12, 31)
    assert resultado.registros_bigquery[0]["data_vencimento"] == "2026-12-31"


def test_csv_sem_linhas_validas_nao_abre_transacao(
    escrever_csv, linha_aporte_valida, fabricar_sessao_fake
):
    """Nada a inserir não é erro — e também não deve gastar uma conexão de banco."""
    fabrica = fabricar_sessao_fake()
    caminho = escrever_csv([dict(linha_aporte_valida, documento_investidor_cpf_cnpj="")])

    resultado = ingerir_csv(caminho, sessao_factory=fabrica)

    assert resultado.quantidade_inserida == 0
    assert fabrica().commits == 0


def test_csv_fora_do_padrao_falha_antes_de_tocar_o_banco(
    escrever_csv, linha_aporte_valida, fabricar_sessao_fake
):
    """Coluna obrigatória ausente derruba o arquivo inteiro, sem inserção parcial."""
    fabrica = fabricar_sessao_fake()
    sem_score = {k: v for k, v in linha_aporte_valida.items() if k != "score_risco_interno"}
    caminho = escrever_csv([sem_score])

    with pytest.raises(ValueError, match="score_risco_interno"):
        ingerir_csv(caminho, sessao_factory=fabrica)

    assert fabrica().inseridos == []


def test_registro_do_bigquery_tem_as_mesmas_chaves_do_postgres(
    escrever_csv, linha_aporte_valida, fabricar_sessao_fake
):
    """
    Os dois lados precisam ficar sincronizados manualmente. Uma divergência de
    chaves aqui vira uma coluna faltando no BigQuery — e um relatório de IA que
    ignora um dado que o dashboard mostra.
    """
    fabrica = fabricar_sessao_fake()
    caminho = escrever_csv([linha_aporte_valida])

    resultado = ingerir_csv(caminho, sessao_factory=fabrica)

    assert set(resultado.registros_bigquery[0]) == set(fabrica().inseridos[0])
