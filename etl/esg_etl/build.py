"""Orquestração: dos CSVs da CVM ao esg-data.json que o app consome."""
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from esg_etl.companhias import ler_companhias_ativas
from esg_etl.contrato import Dataset, Empresa, TipoDimensao, serializar
from esg_etl.curadoria import carregar_marcas, dimensao_ambiental, resolver_selos
from esg_etl.indicadores import ValorBruto
from esg_etl.indicadores_governanca import extrair_governanca
from esg_etl.indicadores_sociais import extrair_sociais
from esg_etl.leitura import normalizar
from esg_etl.pontuacao import Comparacao, montar_dimensao

VERSAO_CONTRATO = 1
REFERENCIA_CVM = "FRE 2025"


def _comparacoes(
    brutos_por_cnpj: dict[str, list[ValorBruto]],
    setor_por_cnpj: dict[str, str],
) -> dict[str, dict[str, Comparacao]]:
    """Para cada setor e indicador, a lista de valores dos pares."""
    por_setor: dict[tuple[str, str], list[float]] = defaultdict(list)
    por_universo: dict[str, list[float]] = defaultdict(list)

    for cnpj, brutos in brutos_por_cnpj.items():
        setor = setor_por_cnpj.get(cnpj)
        if setor is None:
            continue
        for bruto in brutos:
            por_setor[(setor, bruto.id)].append(bruto.valor)
            por_universo[bruto.id].append(bruto.valor)

    resultado: dict[str, dict[str, Comparacao]] = {}
    for cnpj, brutos in brutos_por_cnpj.items():
        setor = setor_por_cnpj.get(cnpj)
        resultado[cnpj] = {
            bruto.id: Comparacao(
                valores_setor=por_setor.get((setor, bruto.id), []),
                valores_universo=por_universo.get(bruto.id, []),
            )
            for bruto in brutos
        }
    return resultado


def construir_dataset(
    diretorio_fre: Path,
    caminho_cadastro: Path,
    caminho_marcas: Path,
    caminho_ise: Path,
    gerado_em: str,
) -> tuple[Dataset, list[str]]:
    """Monta o dataset e devolve também os selos que não foram resolvidos."""
    companhias = ler_companhias_ativas(caminho_cadastro)
    marcas = carregar_marcas(caminho_marcas)
    selos, nao_resolvidos = resolver_selos(caminho_ise, companhias)

    sociais = extrair_sociais(diretorio_fre)
    governanca = extrair_governanca(diretorio_fre)
    setor_por_cnpj = {cnpj: c.setor for cnpj, c in companhias.items()}

    comp_sociais = _comparacoes(sociais, setor_por_cnpj)
    comp_governanca = _comparacoes(governanca, setor_por_cnpj)

    empresas = []
    for cnpj, marca in marcas.items():
        companhia = companhias.get(cnpj)
        if companhia is None:
            continue
        empresas.append(Empresa(
            cnpj=cnpj,
            razaoSocial=companhia.razao_social,
            nomeExibicao=marca.nomeExibicao,
            nomeNormalizado=normalizar(marca.nomeExibicao),
            aliases=marca.aliases,
            setor=companhia.setor,
            selos=selos.get(cnpj, []),
            dimensoes=[
                dimensao_ambiental(selos.get(cnpj, [])),
                montar_dimensao(TipoDimensao.SOCIAL, sociais.get(cnpj, []),
                                comp_sociais.get(cnpj, {})),
                montar_dimensao(TipoDimensao.GOVERNANCA, governanca.get(cnpj, []),
                                comp_governanca.get(cnpj, {})),
            ],
        ))

    empresas.sort(key=lambda empresa: empresa.nomeNormalizado)
    dataset = Dataset(
        versao=VERSAO_CONTRATO,
        geradoEm=gerado_em,
        referenciaCvm=REFERENCIA_CVM,
        empresas=empresas,
    )
    return dataset, nao_resolvidos


def main() -> None:
    raiz = Path(__file__).resolve().parents[1]
    dataset, nao_resolvidos = construir_dataset(
        diretorio_fre=raiz / "data" / "raw" / "fre",
        caminho_cadastro=raiz / "data" / "raw" / "cad_cia_aberta.csv",
        caminho_marcas=raiz / "data" / "curated" / "marcas.json",
        caminho_ise=raiz / "data" / "curated" / "ise_b3_2026.json",
        gerado_em=date.today().isoformat(),
    )

    saida = raiz.parent / "docs" / "data" / "esg-data.json"
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(serializar(dataset), encoding="utf-8")

    print(f"{len(dataset.empresas)} empresas escritas em {saida}")
    if nao_resolvidos:
        print("Selos sem CNPJ resolvido (preencha à mão em ise_b3_2026.json):",
              file=sys.stderr)
        for nome in nao_resolvidos:
            print(f"  - {nome}", file=sys.stderr)


if __name__ == "__main__":
    main()
