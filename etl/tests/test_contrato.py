import json
from esg_etl.contrato import (
    Dataset, Dimensao, Direcao, Empresa, Indicador, Semaforo, TipoDimensao,
    Unidade, serializar,
)


def _dataset_exemplo():
    indicador = Indicador(
        id="mulheres_conselho",
        rotulo="Mulheres no Conselho de Administração",
        valor=25.0,
        unidade=Unidade.PERCENTUAL,
        percentilSetor=68,
        medianaSetor=18.0,
        comparacaoSetorial=True,
        direcao=Direcao.MAIOR_MELHOR,
        fonte="Formulário de Referência CVM, exercício 2025",
    )
    dimensao = Dimensao(
        tipo=TipoDimensao.SOCIAL,
        semaforo=Semaforo.VERDE,
        pontuacao=71.4,
        indicadores=[indicador],
    )
    empresa = Empresa(
        cnpj="71.673.990/0001-77",
        razaoSocial="NATURA COSMETICOS SA",
        nomeExibicao="Natura",
        nomeNormalizado="natura",
        aliases=["natura", "natura cosmeticos"],
        setor="Farmacêutico e Higiene",
        selos=["ISE_B3_2026"],
        dimensoes=[dimensao],
    )
    return Dataset(
        versao=1,
        geradoEm="2026-09-02",
        referenciaCvm="FRE 2025",
        empresas=[empresa],
    )


def test_serializa_com_as_chaves_do_contrato():
    resultado = json.loads(serializar(_dataset_exemplo()))

    assert resultado["versao"] == 1
    empresa = resultado["empresas"][0]
    assert empresa["nomeExibicao"] == "Natura"
    assert empresa["selos"] == ["ISE_B3_2026"]
    dimensao = empresa["dimensoes"][0]
    assert dimensao["tipo"] == "SOCIAL"
    assert dimensao["semaforo"] == "VERDE"
    assert dimensao["indicadores"][0]["direcao"] == "MAIOR_MELHOR"
    assert dimensao["indicadores"][0]["comparacaoSetorial"] is True


def test_serializa_enums_como_texto_e_nao_objeto():
    bruto = serializar(_dataset_exemplo())
    assert "TipoDimensao." not in bruto
    assert "Semaforo." not in bruto


def test_preserva_acentos_sem_escapar():
    bruto = serializar(_dataset_exemplo())
    assert "Farmacêutico" in bruto


def test_pontuacao_pode_ser_nula():
    dimensao = Dimensao(
        tipo=TipoDimensao.AMBIENTAL,
        semaforo=Semaforo.SEM_DADOS,
        pontuacao=None,
        indicadores=[],
    )
    assert dimensao.pontuacao is None
