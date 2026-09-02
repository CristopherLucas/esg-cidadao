import json
from pathlib import Path

from esg_etl.build import construir_dataset
from esg_etl.contrato import Semaforo, serializar

GOLDEN = Path(__file__).parent / "golden" / "esg-data-esperado.json"
CNPJ = "71.673.990/0001-77"

CADASTRO = (
    "CNPJ_CIA;DENOM_SOCIAL;DENOM_COMERC;DT_REG;DT_CONST;DT_CANCEL;"
    "MOTIVO_CANCEL;SIT;DT_INI_SIT;CD_CVM;SETOR_ATIV"
)
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


def _montar_entrada(tmp_path):
    (tmp_path / "cad.csv").write_text(
        "\n".join([
            CADASTRO,
            f"{CNPJ};NATURA COSMETICOS SA;;;;;;ATIVO;;;Farmacêutico e Higiene",
            "32.785.497/0001-97;NATURA & CO HOLDING S.A.;;;;;;CANCELADA;;;Farmacêutico e Higiene",
        ]) + "\n",
        encoding="ISO-8859-1",
    )
    fre = tmp_path / "fre"
    fre.mkdir()
    (fre / "fre_cia_aberta_administrador_declaracao_genero_2025.csv").write_text(
        "\n".join([GENERO, f"{CNPJ};13;NATURA;Conselho de Administração - Efetivos;2;6;0;0;0"]) + "\n",
        encoding="ISO-8859-1",
    )
    (fre / "fre_cia_aberta_empregado_posicao_declaracao_raca_2025.csv").write_text(
        "\n".join([
            RACA,
            f"{CNPJ};13;NATURA;Liderança;13;503;23;60;1;0;3",
            f"{CNPJ};13;NATURA;Não-liderança;131;2574;394;1093;8;0;29",
        ]) + "\n",
        encoding="ISO-8859-1",
    )
    (tmp_path / "marcas.json").write_text(json.dumps([
        {"cnpj": CNPJ, "nomeExibicao": "Natura", "aliases": ["natura", "natura cosmeticos"]}
    ], ensure_ascii=False), encoding="utf-8")
    (tmp_path / "ise.json").write_text(json.dumps({
        "carteira": "ISE_B3_2026",
        "empresas": [{"nome": "Natura", "cnpj": CNPJ}],
    }, ensure_ascii=False), encoding="utf-8")
    return fre, tmp_path / "cad.csv", tmp_path / "marcas.json", tmp_path / "ise.json"


def test_gera_apenas_empresas_com_marca_curada(tmp_path):
    dataset, _ = construir_dataset(*_montar_entrada(tmp_path), gerado_em="2026-09-02")

    assert [e.cnpj for e in dataset.empresas] == [CNPJ]
    assert dataset.empresas[0].nomeExibicao == "Natura"
    assert dataset.empresas[0].nomeNormalizado == "natura"


def test_empresa_tem_as_tres_dimensoes(tmp_path):
    dataset, _ = construir_dataset(*_montar_entrada(tmp_path), gerado_em="2026-09-02")

    tipos = [d.tipo.value for d in dataset.empresas[0].dimensoes]
    assert tipos == ["AMBIENTAL", "SOCIAL", "GOVERNANCA"]


def test_governanca_sem_dados_quando_nao_ha_csv(tmp_path):
    dataset, _ = construir_dataset(*_montar_entrada(tmp_path), gerado_em="2026-09-02")

    governanca = next(d for d in dataset.empresas[0].dimensoes if d.tipo.value == "GOVERNANCA")
    assert governanca.semaforo is Semaforo.SEM_DADOS


def test_ambiental_verde_pelo_selo_da_b3(tmp_path):
    dataset, _ = construir_dataset(*_montar_entrada(tmp_path), gerado_em="2026-09-02")

    ambiental = next(d for d in dataset.empresas[0].dimensoes if d.tipo.value == "AMBIENTAL")
    assert ambiental.semaforo is Semaforo.VERDE


def test_json_bate_com_o_golden_file(tmp_path):
    """Trava o contrato com o app. Se este teste quebrar, o app quebra junto:
    atualize o golden file E os DTOs do Android na mesma mudança."""
    dataset, _ = construir_dataset(*_montar_entrada(tmp_path), gerado_em="2026-09-02")

    assert json.loads(serializar(dataset)) == json.loads(GOLDEN.read_text(encoding="utf-8"))
