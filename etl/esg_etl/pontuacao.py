"""Percentil setorial e tradução para semáforo.

O percentil é comparativo, não absoluto: verde significa "melhor que os
pares do setor", não "bom em termos absolutos".
"""
import statistics
from dataclasses import dataclass

from esg_etl.contrato import (
    Dimensao, Direcao, Indicador, Semaforo, TipoDimensao, Unidade,
)
from esg_etl.indicadores import ValorBruto

MINIMO_SETORIAL = 8
MINIMO_INDICADORES = 2
# Abaixo disso não há com quem comparar: a empresa seria medida contra si
# mesma, o que devolveria percentil 0 e um vermelho sem significado.
MINIMO_PARES = 3
LIMITE_VERDE = 66.0
LIMITE_AMARELO = 33.0


@dataclass(frozen=True)
class Comparacao:
    """Valores do mesmo indicador entre pares, para posicionar uma empresa."""
    valores_setor: list[float]
    valores_universo: list[float]


def percentil(valor: float, pares: list[float], direcao: Direcao) -> int:
    """Fração dos pares que estão em situação pior que `valor`, de 0 a 100."""
    if not pares:
        return 0
    if direcao is Direcao.MAIOR_MELHOR:
        piores = sum(1 for par in pares if par < valor)
    else:
        piores = sum(1 for par in pares if par > valor)
    return round(piores / len(pares) * 100)


def classificar(pontuacao: float | None) -> Semaforo:
    if pontuacao is None:
        return Semaforo.SEM_DADOS
    if pontuacao >= LIMITE_VERDE:
        return Semaforo.VERDE
    if pontuacao >= LIMITE_AMARELO:
        return Semaforo.AMARELO
    return Semaforo.VERMELHO


def _base_de_comparacao(comparacao: Comparacao) -> tuple[list[float], bool]:
    """Pares do setor quando há massa crítica; senão, o universo inteiro."""
    if len(comparacao.valores_setor) >= MINIMO_SETORIAL:
        return comparacao.valores_setor, True
    return comparacao.valores_universo, False


def montar_dimensao(
    tipo: TipoDimensao,
    brutos: list[ValorBruto],
    comparacoes: dict[str, Comparacao],
) -> Dimensao:
    """Monta a dimensão com percentis calculados e o semáforo resultante."""
    indicadores: list[Indicador] = []
    for bruto in brutos:
        comparacao = comparacoes.get(bruto.id, Comparacao([], []))
        pares, setorial = _base_de_comparacao(comparacao)

        if bruto.unidade is Unidade.BOOLEANO:
            # Booleano é fato absoluto, não posição relativa. Ter comitê de
            # auditoria vale 100 mesmo que todas as concorrentes também tenham:
            # o percentil relativo daria 16 a quem tem e puniria quem faz certo.
            pontos = 100 if bruto.valor >= 1.0 else 0
            mediana = None
        elif len(pares) >= MINIMO_PARES:
            pontos = percentil(bruto.valor, pares, bruto.direcao)
            mediana = round(statistics.median(pares), 2)
        else:
            pontos = None
            mediana = None

        indicadores.append(Indicador(
            id=bruto.id,
            rotulo=bruto.rotulo,
            valor=round(bruto.valor, 2),
            unidade=bruto.unidade,
            percentilSetor=pontos,
            medianaSetor=mediana,
            comparacaoSetorial=setorial and bruto.unidade is not Unidade.BOOLEANO,
            direcao=bruto.direcao,
            fonte=bruto.fonte,
        ))

    # O indicador continua visível mesmo sem percentil: o valor e a fonte
    # informam o cidadão, só a posição relativa é que não existe.
    posicionados = [i.percentilSetor for i in indicadores if i.percentilSetor is not None]
    if len(posicionados) < MINIMO_INDICADORES:
        return Dimensao(tipo=tipo, semaforo=Semaforo.SEM_DADOS,
                        pontuacao=None, indicadores=indicadores)

    pontuacao = sum(posicionados) / len(posicionados)
    return Dimensao(tipo=tipo, semaforo=classificar(pontuacao),
                    pontuacao=round(pontuacao, 1), indicadores=indicadores)
