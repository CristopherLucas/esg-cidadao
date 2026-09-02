"""Baixa os datasets abertos da CVM, com cache em disco."""
from pathlib import Path
from typing import Callable

BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA"

FONTES = {
    "cadastro": f"{BASE}/CAD/DADOS/cad_cia_aberta.csv",
    "fre": f"{BASE}/DOC/FRE/DADOS/fre_cia_aberta_2025.zip",
}


def _buscar_http(url: str) -> bytes:
    import requests

    resposta = requests.get(url, timeout=120)
    resposta.raise_for_status()
    return resposta.content


def baixar(url: str, destino: Path, buscar: Callable[[str], bytes] = _buscar_http) -> Path:
    """Baixa `url` para `destino`. Se o arquivo já existe, não baixa de novo."""
    if destino.exists():
        return destino
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(buscar(url))
    return destino
