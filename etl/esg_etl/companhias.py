"""Cadastro de companhias abertas ativas."""
from dataclasses import dataclass
from pathlib import Path

from esg_etl.leitura import ler_csv


@dataclass(frozen=True)
class Companhia:
    cnpj: str
    razao_social: str
    setor: str


def ler_companhias_ativas(caminho: Path) -> dict[str, Companhia]:
    """Companhias com registro ATIVO, chaveadas por CNPJ.

    Entidades canceladas são descartadas: uma mesma marca pode ter holding
    cancelada e operadora ativa, e só a ativa representa a empresa hoje.
    """
    companhias: dict[str, Companhia] = {}
    for linha in ler_csv(caminho):
        if linha["SIT"] != "ATIVO":
            continue
        setor = linha["SETOR_ATIV"].strip()
        if not setor:
            continue
        cnpj = linha["CNPJ_CIA"].strip()
        companhias[cnpj] = Companhia(
            cnpj=cnpj,
            razao_social=linha["DENOM_SOCIAL"].strip(),
            setor=setor,
        )
    return companhias
