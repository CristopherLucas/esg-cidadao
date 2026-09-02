import pytest
from esg_etl.contrato import Direcao, Unidade
from esg_etl.indicadores_governanca import extrair_governanca

CNPJ = "71.673.990/0001-77"

REMUNERACAO = (
    "CNPJ_Companhia;Versao;Nome_Companhia;Data_Fim_Exercicio_Social;"
    "Orgao_Administracao;Valor_Maior_Remuneracao;Valor_Menor_Remuneracao"
)
COMITE = (
    "CNPJ_Companhia;Versao;Nome_Companhia;Tipo_Comite;Descricao_Outros_Comites"
)
TRANSACAO = "CNPJ_Companhia;Versao;Nome_Companhia;Parte_Relacionada"
FAMILIAR = "CNPJ_Companhia;Versao;Nome_Companhia;Tipo_Parentesco"


def _escrever(tmp_path, nome, cabecalho, linhas):
    caminho = tmp_path / nome
    caminho.write_text(
        "\n".join([cabecalho, *linhas]) + "\n", encoding="ISO-8859-1"
    )


def _por_id(valores):
    return {valor.id: valor for valor in valores}


def test_razao_de_remuneracao_da_diretoria(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_remuneracao_maxima_minima_media_2025.csv", REMUNERACAO, [
        f"{CNPJ};13;NATURA;2023-12-31;Diretoria Estatutária;33576.20;2202.98",
        f"{CNPJ};13;NATURA;2023-12-31;Conselho Fiscal;205.20;205.20",
    ])

    indicador = _por_id(extrair_governanca(tmp_path)[CNPJ])["razao_remuneracao"]

    assert indicador.valor == pytest.approx(33576.20 / 2202.98)
    assert indicador.unidade is Unidade.RAZAO
    assert indicador.direcao is Direcao.MENOR_MELHOR


def test_usa_o_exercicio_mais_recente(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_remuneracao_maxima_minima_media_2025.csv", REMUNERACAO, [
        f"{CNPJ};13;NATURA;2022-12-31;Diretoria Estatutária;15814.00;2187.00",
        f"{CNPJ};13;NATURA;2023-12-31;Diretoria Estatutária;33576.20;2202.98",
    ])

    indicador = _por_id(extrair_governanca(tmp_path)[CNPJ])["razao_remuneracao"]

    assert indicador.valor == pytest.approx(33576.20 / 2202.98)


def test_omite_razao_quando_menor_remuneracao_e_zero(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_remuneracao_maxima_minima_media_2025.csv", REMUNERACAO, [
        f"{CNPJ};13;NATURA;2023-12-31;Diretoria Estatutária;33576.20;0.00",
    ])

    assert extrair_governanca(tmp_path).get(CNPJ, []) == []


def test_comite_de_auditoria_conta_como_presente(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_membro_comite_2025.csv", COMITE, [
        f"{CNPJ};13;NATURA;Comitê de Auditoria;",
    ])

    indicador = _por_id(extrair_governanca(tmp_path)[CNPJ])["comites_relevantes"]

    assert indicador.valor == 1.0
    assert indicador.unidade is Unidade.BOOLEANO


def test_sustentabilidade_e_reconhecida_em_outros_comites(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_membro_comite_2025.csv", COMITE, [
        f"{CNPJ};13;NATURA;Outros Comitês;Comitê de Sustentabilidade e ESG",
    ])

    assert _por_id(extrair_governanca(tmp_path)[CNPJ])["comites_relevantes"].valor == 1.0


def test_comite_irrelevante_nao_conta(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_membro_comite_2025.csv", COMITE, [
        f"{CNPJ};13;NATURA;Outros Comitês;Comitê de Marketing",
    ])

    assert _por_id(extrair_governanca(tmp_path)[CNPJ])["comites_relevantes"].valor == 0.0


def test_conta_transacoes_com_partes_relacionadas(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_transacao_parte_relacionada_2025.csv", TRANSACAO, [
        f"{CNPJ};13;NATURA;Controlada A",
        f"{CNPJ};13;NATURA;Controlada B",
    ])

    indicador = _por_id(extrair_governanca(tmp_path)[CNPJ])["transacoes_partes_relacionadas"]

    assert indicador.valor == 2.0
    assert indicador.unidade is Unidade.CONTAGEM
    assert indicador.direcao is Direcao.MENOR_MELHOR


def test_conta_relacoes_familiares_no_conselho(tmp_path):
    _escrever(tmp_path, "fre_cia_aberta_relacao_familiar_2025.csv", FAMILIAR, [
        f"{CNPJ};13;NATURA;Irmão ou Irmã",
    ])

    assert _por_id(extrair_governanca(tmp_path)[CNPJ])["relacoes_familiares"].valor == 1.0
