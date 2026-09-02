import json

from esg_etl.companhias import Companhia
from esg_etl.contrato import Semaforo, TipoDimensao, Unidade
from esg_etl.curadoria import carregar_marcas, dimensao_ambiental, resolver_selos

CNPJ_NATURA = "71.673.990/0001-77"
CNPJ_RENNER = "92.754.738/0001-62"


def _escrever(tmp_path, nome, conteudo):
    caminho = tmp_path / nome
    caminho.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    return caminho


def test_carrega_marcas_com_aliases(tmp_path):
    caminho = _escrever(tmp_path, "marcas.json", [
        {"cnpj": CNPJ_NATURA, "nomeExibicao": "Natura",
         "aliases": ["natura", "natura cosmeticos"]},
    ])

    marcas = carregar_marcas(caminho)

    assert marcas[CNPJ_NATURA].nomeExibicao == "Natura"
    assert marcas[CNPJ_NATURA].aliases == ["natura", "natura cosmeticos"]


def test_selo_com_cnpj_explicito_dispensa_busca_por_nome(tmp_path):
    caminho = _escrever(tmp_path, "ise.json", {
        "carteira": "ISE_B3_2026",
        "empresas": [{"nome": "Natura", "cnpj": CNPJ_NATURA}],
    })

    selos, nao_resolvidos = resolver_selos(caminho, {})

    assert selos == {CNPJ_NATURA: ["ISE_B3_2026"]}
    assert nao_resolvidos == []


def test_selo_sem_cnpj_e_resolvido_pela_razao_social(tmp_path):
    caminho = _escrever(tmp_path, "ise.json", {
        "carteira": "ISE_B3_2026",
        "empresas": [{"nome": "Lojas Renner", "cnpj": None}],
    })
    companhias = {
        CNPJ_RENNER: Companhia(CNPJ_RENNER, "LOJAS RENNER S.A.", "Têxtil e Vestuário"),
    }

    selos, nao_resolvidos = resolver_selos(caminho, companhias)

    assert selos == {CNPJ_RENNER: ["ISE_B3_2026"]}
    assert nao_resolvidos == []


def test_nome_que_nao_casa_e_reportado_para_curadoria_manual(tmp_path):
    caminho = _escrever(tmp_path, "ise.json", {
        "carteira": "ISE_B3_2026",
        "empresas": [{"nome": "Empresa Inexistente", "cnpj": None}],
    })

    selos, nao_resolvidos = resolver_selos(caminho, {})

    assert selos == {}
    assert nao_resolvidos == ["Empresa Inexistente"]


def test_dimensao_ambiental_verde_quando_tem_selo():
    dimensao = dimensao_ambiental(["ISE_B3_2026"])

    assert dimensao.tipo is TipoDimensao.AMBIENTAL
    assert dimensao.semaforo is Semaforo.VERDE
    assert dimensao.indicadores[0].unidade is Unidade.BOOLEANO
    assert dimensao.indicadores[0].valor == 1.0


def test_dimensao_ambiental_sem_selo_e_sem_dados_e_nao_vermelho():
    """Ausência de selo não é evidência de mau desempenho ambiental."""
    dimensao = dimensao_ambiental([])

    assert dimensao.semaforo is Semaforo.SEM_DADOS
    assert dimensao.pontuacao is None
    assert dimensao.indicadores == []


def test_nome_ambiguo_nao_escolhe_um_candidato_ao_acaso(tmp_path):
    """Bradesco casa com o banco e com a leasing. Escolher em silêncio daria
    o selo à empresa errada, então o caso vira curadoria manual."""
    caminho = _escrever(tmp_path, "ise.json", {
        "carteira": "ISE_B3_2026",
        "empresas": [{"nome": "Bradesco", "cnpj": None}],
    })
    companhias = {
        "60.746.948/0001-12": Companhia("60.746.948/0001-12", "BANCO BRADESCO S.A.", "Bancos"),
        "47.509.120/0001-82": Companhia("47.509.120/0001-82", "BRADESCO LEASING S.A.", "Bancos"),
    }

    selos, nao_resolvidos = resolver_selos(caminho, companhias)

    assert selos == {}
    assert nao_resolvidos == ["Bradesco"]


def test_nome_exato_vence_mesmo_havendo_outros_com_o_mesmo_prefixo(tmp_path):
    caminho = _escrever(tmp_path, "ise.json", {
        "carteira": "ISE_B3_2026",
        "empresas": [{"nome": "Klabin S.A.", "cnpj": None}],
    })
    companhias = {
        "1": Companhia("1", "KLABIN S.A.", "Papel e Celulose"),
        "2": Companhia("2", "KLABIN S.A. IRMAOS E CIA", "Papel e Celulose"),
    }

    selos, nao_resolvidos = resolver_selos(caminho, companhias)

    assert selos == {"1": ["ISE_B3_2026"]}
    assert nao_resolvidos == []
