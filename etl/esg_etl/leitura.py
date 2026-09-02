"""Leitura dos CSVs da CVM e normalização de texto."""
import csv
import unicodedata
from pathlib import Path
from typing import Iterator

ENCODING = "ISO-8859-1"
DELIMITADOR = ";"


def normalizar(texto: str) -> str:
    """Minúsculo, sem acento e com espaços colapsados."""
    sem_acento = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return " ".join(sem_acento.lower().split())


def ler_csv(caminho: Path) -> Iterator[dict[str, str]]:
    """Percorre um CSV da CVM linha a linha, já decodificado."""
    with caminho.open(encoding=ENCODING, newline="") as arquivo:
        yield from csv.DictReader(arquivo, delimiter=DELIMITADOR)


def linhas_da_versao_mais_recente(caminho: Path) -> list[dict[str, str]]:
    """Filtra o CSV para a maior `Versao` de cada `CNPJ_Companhia`.

    A comparação é numérica: a versão 13 vence a 9, o que a ordenação
    textual erraria.
    """
    por_cnpj: dict[str, list[dict[str, str]]] = {}
    maior_versao: dict[str, int] = {}

    for linha in ler_csv(caminho):
        cnpj = linha["CNPJ_Companhia"].strip()
        versao = int(linha["Versao"])
        if versao > maior_versao.get(cnpj, -1):
            maior_versao[cnpj] = versao
            por_cnpj[cnpj] = [linha]
        elif versao == maior_versao[cnpj]:
            por_cnpj[cnpj].append(linha)

    return [linha for linhas in por_cnpj.values() for linha in linhas]
