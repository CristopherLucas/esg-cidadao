"""Contrato de dados entre o ETL e o app Android.

Qualquer mudança aqui quebra a desserialização do app. Os testes de golden
file da Tarefa 9 existem para tornar essa quebra visível.
"""
import json
from dataclasses import asdict, dataclass, field
from enum import Enum


class TipoDimensao(str, Enum):
    AMBIENTAL = "AMBIENTAL"
    SOCIAL = "SOCIAL"
    GOVERNANCA = "GOVERNANCA"


class Semaforo(str, Enum):
    VERDE = "VERDE"
    AMARELO = "AMARELO"
    VERMELHO = "VERMELHO"
    SEM_DADOS = "SEM_DADOS"


class Direcao(str, Enum):
    MAIOR_MELHOR = "MAIOR_MELHOR"
    MENOR_MELHOR = "MENOR_MELHOR"


class Unidade(str, Enum):
    PERCENTUAL = "PERCENTUAL"
    RAZAO = "RAZAO"
    CONTAGEM = "CONTAGEM"
    BOOLEANO = "BOOLEANO"


@dataclass(frozen=True)
class Indicador:
    id: str
    rotulo: str
    valor: float
    unidade: Unidade
    percentilSetor: int | None
    medianaSetor: float | None
    comparacaoSetorial: bool
    direcao: Direcao
    fonte: str


@dataclass(frozen=True)
class Dimensao:
    tipo: TipoDimensao
    semaforo: Semaforo
    pontuacao: float | None
    indicadores: list[Indicador] = field(default_factory=list)


@dataclass(frozen=True)
class Empresa:
    cnpj: str
    razaoSocial: str
    nomeExibicao: str
    nomeNormalizado: str
    aliases: list[str]
    setor: str
    selos: list[str]
    dimensoes: list[Dimensao]


@dataclass(frozen=True)
class Dataset:
    versao: int
    geradoEm: str
    referenciaCvm: str
    empresas: list[Empresa]


def serializar(dataset: Dataset) -> str:
    """Serializa o dataset no formato que o app consome."""
    return json.dumps(asdict(dataset), ensure_ascii=False, indent=2)
