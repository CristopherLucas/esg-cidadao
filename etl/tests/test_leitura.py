from esg_etl.leitura import linhas_da_versao_mais_recente

CABECALHO = "CNPJ_Companhia;Versao;Nome_Companhia;Valor"


def _arquivo(tmp_path, linhas):
    caminho = tmp_path / "fre.csv"
    caminho.write_text(
        "\n".join([CABECALHO, *linhas]) + "\n", encoding="ISO-8859-1"
    )
    return caminho


def test_mantem_apenas_a_maior_versao_por_cnpj(tmp_path):
    caminho = _arquivo(tmp_path, [
        "71.673.990/0001-77;2;NATURA;antigo",
        "71.673.990/0001-77;13;NATURA;novo",
        "00.000.000/0001-00;1;OUTRA;unico",
    ])

    linhas = linhas_da_versao_mais_recente(caminho)

    valores = {linha["CNPJ_Companhia"]: linha["Valor"] for linha in linhas}
    assert valores == {
        "71.673.990/0001-77": "novo",
        "00.000.000/0001-00": "unico",
    }


def test_mantem_todas_as_linhas_da_versao_vencedora(tmp_path):
    caminho = _arquivo(tmp_path, [
        "71.673.990/0001-77;13;NATURA;lideranca",
        "71.673.990/0001-77;13;NATURA;nao-lideranca",
        "71.673.990/0001-77;2;NATURA;velho",
    ])

    linhas = linhas_da_versao_mais_recente(caminho)

    assert sorted(linha["Valor"] for linha in linhas) == ["lideranca", "nao-lideranca"]


def test_versao_e_comparada_como_numero_e_nao_como_texto(tmp_path):
    caminho = _arquivo(tmp_path, [
        "71.673.990/0001-77;9;NATURA;nove",
        "71.673.990/0001-77;13;NATURA;treze",
    ])

    linhas = linhas_da_versao_mais_recente(caminho)

    assert [linha["Valor"] for linha in linhas] == ["treze"]
