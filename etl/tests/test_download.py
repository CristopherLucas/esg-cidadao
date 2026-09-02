from pathlib import Path
import pytest
from esg_etl.download import baixar, FONTES


def test_baixa_quando_arquivo_nao_existe(tmp_path):
    chamadas = []

    def buscar_falso(url):
        chamadas.append(url)
        return b"conteudo"

    destino = tmp_path / "arquivo.csv"
    resultado = baixar("http://exemplo/arquivo.csv", destino, buscar_falso)

    assert resultado == destino
    assert destino.read_bytes() == b"conteudo"
    assert chamadas == ["http://exemplo/arquivo.csv"]


def test_nao_baixa_de_novo_quando_ja_existe(tmp_path):
    destino = tmp_path / "arquivo.csv"
    destino.write_bytes(b"cache")

    def buscar_falso(url):
        raise AssertionError("nao deveria baixar de novo")

    assert baixar("http://exemplo/arquivo.csv", destino, buscar_falso) == destino
    assert destino.read_bytes() == b"cache"


def test_fontes_declara_apenas_o_que_o_etl_processa():
    assert set(FONTES) == {"cadastro", "fre"}
