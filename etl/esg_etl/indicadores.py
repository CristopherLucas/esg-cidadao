"""Valor bruto de um indicador, antes do cálculo de percentil."""
from dataclasses import dataclass

from esg_etl.contrato import Direcao, Unidade

FONTE_FRE = "Formulário de Referência CVM, exercício 2025"
FONTE_B3 = "Carteira ISE B3 2026"


@dataclass(frozen=True)
class ValorBruto:
    id: str
    rotulo: str
    valor: float
    unidade: Unidade
    direcao: Direcao
    fonte: str


def percentual(parte: float, total: float) -> float | None:
    """Percentual, ou None quando não há base para calcular."""
    if total <= 0:
        return None
    return parte / total * 100
