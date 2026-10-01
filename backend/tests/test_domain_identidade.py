"""
Testes de `domain/identidade.py`: classificação e validação de CPF/CNPJ.

Os documentos válidos abaixo são sintéticos, com dígitos verificadores corretos.
Nenhum destes testes precisa de banco ou de rede.
"""

import pytest

from app.domain.identidade import DOCUMENTO_INVALIDO, identificar_documento


@pytest.mark.parametrize("bruto", ["529.982.247-25", "52998224725", " 529 982 247 25 "])
def test_cpf_valido_com_ou_sem_mascara(bruto):
    assert identificar_documento(bruto) == ("CPF", "52998224725")


@pytest.mark.parametrize("bruto", ["11.222.333/0001-81", "11222333000181"])
def test_cnpj_valido_com_ou_sem_mascara(bruto):
    assert identificar_documento(bruto) == ("CNPJ", "11222333000181")


@pytest.mark.parametrize(
    "bruto",
    [
        "529.982.247-26",  # CPF com dígito verificador errado
        "11.222.333/0001-82",  # CNPJ com dígito verificador errado
        "00000000000",  # CPF com dígitos repetidos
        "11111111111",
        "00000000000000",  # CNPJ com dígitos repetidos
        "123",  # tamanho errado
        "",
        "ABCDEFGHIJK",  # letras no tamanho de um CPF
        "12.ABC.345/01DE-35",  # CNPJ alfanumérico: recusado de propósito
    ],
)
def test_documento_invalido(bruto):
    assert identificar_documento(bruto)[0] == DOCUMENTO_INVALIDO
