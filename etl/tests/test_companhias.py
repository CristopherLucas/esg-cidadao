from esg_etl.companhias import ler_companhias_ativas
from esg_etl.leitura import normalizar

CABECALHO = (
    "CNPJ_CIA;DENOM_SOCIAL;DENOM_COMERC;DT_REG;DT_CONST;DT_CANCEL;"
    "MOTIVO_CANCEL;SIT;DT_INI_SIT;CD_CVM;SETOR_ATIV"
)


def _linha(cnpj, nome, situacao, setor="Farmacêutico e Higiene"):
    return f"{cnpj};{nome};;;;;;{situacao};;;{setor}"


def _arquivo(tmp_path, linhas):
    caminho = tmp_path / "cad.csv"
    caminho.write_text(
        "\n".join([CABECALHO, *linhas]) + "\n", encoding="ISO-8859-1"
    )
    return caminho


def test_descarta_companhia_cancelada(tmp_path):
    caminho = _arquivo(tmp_path, [
        _linha("32.785.497/0001-97", "NATURA & CO HOLDING S.A.", "CANCELADA"),
        _linha("71.673.990/0001-77", "NATURA COSMETICOS SA", "ATIVO"),
    ])

    companhias = ler_companhias_ativas(caminho)

    assert list(companhias) == ["71.673.990/0001-77"]
    assert companhias["71.673.990/0001-77"].razao_social == "NATURA COSMETICOS SA"
    assert companhias["71.673.990/0001-77"].setor == "Farmacêutico e Higiene"


def test_ignora_companhia_sem_setor(tmp_path):
    caminho = _arquivo(tmp_path, [
        _linha("11.111.111/0001-11", "SEM SETOR SA", "ATIVO", setor=""),
    ])
    assert ler_companhias_ativas(caminho) == {}


def test_normalizar_remove_acento_e_caixa():
    assert normalizar("Farmacêutico e Higiene") == "farmaceutico e higiene"
    assert normalizar("  NATURÁ   COSMÉTICOS  ") == "natura cosmeticos"
