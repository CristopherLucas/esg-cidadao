import pytest
from esg_etl.contrato import Direcao, Semaforo, TipoDimensao, Unidade
from esg_etl.indicadores import ValorBruto
from esg_etl.pontuacao import (
    Comparacao, classificar, montar_dimensao, percentil,
)


def _bruto(id_indicador, valor, direcao=Direcao.MAIOR_MELHOR):
    return ValorBruto(
        id=id_indicador,
        rotulo=id_indicador,
        valor=valor,
        unidade=Unidade.PERCENTUAL,
        direcao=direcao,
        fonte="fonte",
    )


def test_percentil_conta_quantos_pares_sao_piores():
    assert percentil(25.0, [10.0, 20.0, 25.0, 30.0], Direcao.MAIOR_MELHOR) == 50


def test_percentil_inverte_quando_menor_e_melhor():
    assert percentil(25.0, [10.0, 20.0, 25.0, 30.0], Direcao.MENOR_MELHOR) == 25


def test_percentil_do_melhor_de_todos_e_quase_cem():
    assert percentil(99.0, [1.0, 2.0, 99.0], Direcao.MAIOR_MELHOR) == 67


def test_percentil_sem_pares_e_zero():
    assert percentil(25.0, [], Direcao.MAIOR_MELHOR) == 0


@pytest.mark.parametrize("pontuacao,esperado", [
    (100.0, Semaforo.VERDE),
    (66.0, Semaforo.VERDE),
    (65.9, Semaforo.AMARELO),
    (33.0, Semaforo.AMARELO),
    (32.9, Semaforo.VERMELHO),
    (0.0, Semaforo.VERMELHO),
    (None, Semaforo.SEM_DADOS),
])
def test_faixas_do_semaforo(pontuacao, esperado):
    assert classificar(pontuacao) is esperado


def test_dimensao_com_um_indicador_fica_sem_dados():
    """Dois indicadores é o mínimo para haver veredito em SOCIAL."""
    comparacoes = {"a": Comparacao(valores_setor=[1.0] * 10, valores_universo=[1.0] * 50)}

    dimensao = montar_dimensao(TipoDimensao.SOCIAL, [_bruto("a", 1.0)], comparacoes)

    assert dimensao.semaforo is Semaforo.SEM_DADOS
    assert dimensao.pontuacao is None
    assert len(dimensao.indicadores) == 1


def test_pontuacao_e_a_media_dos_percentis():
    comparacoes = {
        "a": Comparacao(valores_setor=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0],
                        valores_universo=[]),
        "b": Comparacao(valores_setor=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 10.0],
                        valores_universo=[]),
    }

    dimensao = montar_dimensao(
        TipoDimensao.SOCIAL, [_bruto("a", 10.0), _bruto("b", 0.0)], comparacoes
    )

    # 'a' é o melhor dos 10 (percentil 90), 'b' é o pior (percentil 0)
    assert dimensao.pontuacao == pytest.approx(45.0)
    assert dimensao.semaforo is Semaforo.AMARELO


def test_cai_para_o_universo_quando_o_setor_e_pequeno():
    comparacoes = {
        "a": Comparacao(valores_setor=[1.0, 2.0, 3.0], valores_universo=[0.0] * 20),
        "b": Comparacao(valores_setor=[1.0, 2.0, 3.0], valores_universo=[0.0] * 20),
    }

    dimensao = montar_dimensao(
        TipoDimensao.SOCIAL, [_bruto("a", 5.0), _bruto("b", 5.0)], comparacoes
    )

    for indicador in dimensao.indicadores:
        assert indicador.comparacaoSetorial is False
        assert indicador.percentilSetor == 100


def test_marca_comparacao_setorial_quando_ha_pares_suficientes():
    comparacoes = {
        "a": Comparacao(valores_setor=[1.0] * 8, valores_universo=[0.0] * 20),
        "b": Comparacao(valores_setor=[1.0] * 8, valores_universo=[0.0] * 20),
    }

    dimensao = montar_dimensao(
        TipoDimensao.SOCIAL, [_bruto("a", 1.0), _bruto("b", 1.0)], comparacoes
    )

    assert all(indicador.comparacaoSetorial for indicador in dimensao.indicadores)


def test_dimensao_sem_indicador_algum():
    dimensao = montar_dimensao(TipoDimensao.GOVERNANCA, [], {})

    assert dimensao.semaforo is Semaforo.SEM_DADOS
    assert dimensao.indicadores == []


def test_indicador_sem_pares_suficientes_nao_recebe_percentil():
    """Comparar a empresa consigo mesma daria percentil 0 e um vermelho falso."""
    comparacoes = {
        "a": Comparacao(valores_setor=[5.0], valores_universo=[5.0]),
        "b": Comparacao(valores_setor=[1.0] * 10, valores_universo=[]),
    }

    dimensao = montar_dimensao(
        TipoDimensao.SOCIAL, [_bruto("a", 5.0), _bruto("b", 1.0)], comparacoes
    )

    posicionados = {i.id: i.percentilSetor for i in dimensao.indicadores}
    assert posicionados["a"] is None
    assert posicionados["b"] == 0


def test_indicador_sem_percentil_fica_fora_da_media():
    comparacoes = {
        "a": Comparacao(valores_setor=[5.0], valores_universo=[5.0]),
        "b": Comparacao(valores_setor=[0.0] * 10, valores_universo=[]),
        "c": Comparacao(valores_setor=[0.0] * 10, valores_universo=[]),
    }

    dimensao = montar_dimensao(
        TipoDimensao.SOCIAL,
        [_bruto("a", 5.0), _bruto("b", 9.0), _bruto("c", 9.0)],
        comparacoes,
    )

    # 'b' e 'c' estão acima de todos os 10 pares; 'a' não conta
    assert dimensao.pontuacao == pytest.approx(100.0)
    assert dimensao.semaforo is Semaforo.VERDE


def test_dimensao_sem_indicadores_posicionados_fica_sem_dados():
    comparacoes = {
        "a": Comparacao(valores_setor=[5.0], valores_universo=[5.0]),
        "b": Comparacao(valores_setor=[1.0], valores_universo=[1.0]),
    }

    dimensao = montar_dimensao(
        TipoDimensao.SOCIAL, [_bruto("a", 5.0), _bruto("b", 1.0)], comparacoes
    )

    assert dimensao.semaforo is Semaforo.SEM_DADOS
    assert dimensao.pontuacao is None
    assert len(dimensao.indicadores) == 2


def test_mediana_some_quando_nao_ha_com_quem_comparar():
    comparacoes = {"a": Comparacao(valores_setor=[5.0], valores_universo=[5.0])}

    dimensao = montar_dimensao(TipoDimensao.SOCIAL, [_bruto("a", 5.0)], comparacoes)

    assert dimensao.indicadores[0].medianaSetor is None


def _booleano(id_indicador, valor):
    return ValorBruto(
        id=id_indicador, rotulo=id_indicador, valor=valor,
        unidade=Unidade.BOOLEANO, direcao=Direcao.MAIOR_MELHOR, fonte="fonte",
    )


def test_booleano_verdadeiro_vale_cem_independente_dos_pares():
    """Ter o comitê é um fato absoluto. Se 84% das empresas também têm, o
    percentil relativo daria 16 a quem tem — punindo quem faz o certo."""
    comparacoes = {
        "tem": Comparacao(valores_setor=[1.0] * 20, valores_universo=[]),
        "outro": Comparacao(valores_setor=[1.0] * 20, valores_universo=[]),
    }

    dimensao = montar_dimensao(
        TipoDimensao.GOVERNANCA,
        [_booleano("tem", 1.0), _booleano("outro", 1.0)],
        comparacoes,
    )

    assert [i.percentilSetor for i in dimensao.indicadores] == [100, 100]
    assert dimensao.semaforo is Semaforo.VERDE


def test_booleano_falso_vale_zero():
    comparacoes = {
        "nao_tem": Comparacao(valores_setor=[0.0] * 20, valores_universo=[]),
        "outro": Comparacao(valores_setor=[0.0] * 20, valores_universo=[]),
    }

    dimensao = montar_dimensao(
        TipoDimensao.GOVERNANCA,
        [_booleano("nao_tem", 0.0), _booleano("outro", 0.0)],
        comparacoes,
    )

    assert [i.percentilSetor for i in dimensao.indicadores] == [0, 0]
    assert dimensao.semaforo is Semaforo.VERMELHO


def test_booleano_dispensa_pares_para_ser_pontuado():
    comparacoes = {
        "tem": Comparacao(valores_setor=[1.0], valores_universo=[1.0]),
        "outro": Comparacao(valores_setor=[1.0], valores_universo=[1.0]),
    }

    dimensao = montar_dimensao(
        TipoDimensao.GOVERNANCA,
        [_booleano("tem", 1.0), _booleano("outro", 1.0)],
        comparacoes,
    )

    assert dimensao.pontuacao == pytest.approx(100.0)
