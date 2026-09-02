import pytest
from esg_etl.contrato import Direcao, Unidade
from esg_etl.indicadores_sociais import extrair_sociais

CNPJ = "71.673.990/0001-77"

GENERO = (
    "CNPJ_Companhia;Versao;Nome_Companhia;Orgao_Administracao;"
    "Quantidade_Feminino;Quantidade_Masculino;Quantidade_Nao_Binario;"
    "Quantidade_Outros;Quantidade_Sem_Resposta"
)
RACA = (
    "CNPJ_Companhia;Versao;Nome_Companhia;Posicao;Quantidade_Amarelo;"
    "Quantidade_Branco;Quantidade_Preto;Quantidade_Pardo;"
    "Quantidade_Indigena;Quantidade_Outros;Quantidade_Sem_Resposta"
)
PCD = (
    "CNPJ_Companhia;Versao;Nome_Companhia;Posicao;Quantidade_PCD;"
    "Quantidade_Nao_PCD;Quantidade_Sem_Resposta"
)


@pytest.fixture
def diretorio(tmp_path):
    def escrever(nome, cabecalho, linhas):
        caminho = tmp_path / nome
        caminho.write_text(
            "\n".join([cabecalho, *linhas]) + "\n", encoding="ISO-8859-1"
        )

    escrever(
        "fre_cia_aberta_administrador_declaracao_genero_2025.csv", GENERO,
        [f"{CNPJ};13;NATURA;Conselho de Administração - Efetivos;2;6;0;0;0",
         f"{CNPJ};13;NATURA;Diretoria;3;3;0;0;0"],
    )
    escrever(
        "fre_cia_aberta_empregado_posicao_declaracao_raca_2025.csv", RACA,
        [f"{CNPJ};13;NATURA;Liderança;13;503;23;60;1;0;3",
         f"{CNPJ};13;NATURA;Não-liderança;131;2574;394;1093;8;0;29"],
    )
    escrever(
        "fre_cia_aberta_empregado_PCD_2025.csv", PCD,
        [f"{CNPJ};13;NATURA;Liderança;5;598;0",
         f"{CNPJ};13;NATURA;Não-liderança;288;3941;0"],
    )
    return tmp_path


def _por_id(valores):
    return {valor.id: valor for valor in valores}


def test_percentual_de_mulheres_no_conselho(diretorio):
    indicador = _por_id(extrair_sociais(diretorio)[CNPJ])["mulheres_conselho"]

    assert indicador.valor == pytest.approx(25.0)
    assert indicador.unidade is Unidade.PERCENTUAL
    assert indicador.direcao is Direcao.MAIOR_MELHOR


def test_usa_o_conselho_efetivo_e_nao_a_diretoria(diretorio):
    """A diretoria do fixture tem 50% de mulheres; o conselho, 25%."""
    indicador = _por_id(extrair_sociais(diretorio)[CNPJ])["mulheres_conselho"]
    assert indicador.valor != pytest.approx(50.0)


def test_percentual_de_negros_na_lideranca(diretorio):
    indicador = _por_id(extrair_sociais(diretorio)[CNPJ])["negros_lideranca"]
    # (23 + 60) de 603 pessoas na liderança
    assert indicador.valor == pytest.approx(83 / 603 * 100)


def test_gap_racial_em_pontos_percentuais(diretorio):
    indicador = _por_id(extrair_sociais(diretorio)[CNPJ])["gap_racial"]
    nao_lideranca = (394 + 1093) / 4229 * 100
    lideranca = 83 / 603 * 100

    assert indicador.valor == pytest.approx(nao_lideranca - lideranca)
    assert indicador.direcao is Direcao.MENOR_MELHOR


def test_percentual_de_pcd_soma_lideranca_e_nao_lideranca(diretorio):
    indicador = _por_id(extrair_sociais(diretorio)[CNPJ])["pcd_empregados"]
    assert indicador.valor == pytest.approx(293 / 4832 * 100)


def test_omite_indicador_quando_o_total_e_zero(tmp_path):
    caminho = tmp_path / "fre_cia_aberta_administrador_declaracao_genero_2025.csv"
    caminho.write_text(
        "\n".join([GENERO, f"{CNPJ};13;NATURA;Conselho de Administração - Efetivos;0;0;0;0;0"]) + "\n",
        encoding="ISO-8859-1",
    )

    assert extrair_sociais(tmp_path).get(CNPJ, []) == []
