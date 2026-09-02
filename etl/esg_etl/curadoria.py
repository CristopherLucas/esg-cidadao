"""Dados mantidos à mão: selos da B3 e mapa de marcas do consumidor."""
import json
import re
from dataclasses import dataclass
from pathlib import Path

from esg_etl.companhias import Companhia
from esg_etl.contrato import (
    Dimensao, Direcao, Indicador, Semaforo, TipoDimensao, Unidade,
)
from esg_etl.indicadores import FONTE_B3
from esg_etl.leitura import normalizar


@dataclass(frozen=True)
class Marca:
    cnpj: str
    nomeExibicao: str
    aliases: list[str]


def carregar_marcas(caminho: Path) -> dict[str, Marca]:
    """Mapa CNPJ -> marca reconhecível pelo consumidor."""
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    return {
        item["cnpj"]: Marca(
            cnpj=item["cnpj"],
            nomeExibicao=item["nomeExibicao"],
            aliases=item["aliases"],
        )
        for item in dados
    }


def resolver_selos(
    caminho: Path, companhias: dict[str, Companhia]
) -> tuple[dict[str, list[str]], list[str]]:
    """Selos por CNPJ e a lista de nomes que não casaram com nenhuma companhia.

    Nomes não resolvidos são devolvidos em vez de silenciados: quem mantém a
    curadoria precisa saber o que preencher à mão.
    """
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    carteira = dados["carteira"]

    por_nome = {
        normalizar(companhia.razao_social): cnpj
        for cnpj, companhia in companhias.items()
    }

    selos: dict[str, list[str]] = {}
    nao_resolvidos: list[str] = []

    for entrada in dados["empresas"]:
        cnpj = entrada.get("cnpj") or _resolver_por_nome(entrada["nome"], por_nome)
        if cnpj is None:
            nao_resolvidos.append(entrada["nome"])
            continue
        selos.setdefault(cnpj, []).append(carteira)

    return selos, nao_resolvidos


def _resolver_por_nome(nome: str, por_nome: dict[str, str]) -> str | None:
    """CNPJ da companhia cuja razão social corresponde ao nome, ou None.

    Nome ambíguo devolve None de propósito. "Bradesco" casa com o banco e com
    a leasing; escolher em silêncio daria o selo à empresa errada. Sem certeza,
    o caso volta para a curadoria manual.
    """
    alvo = normalizar(nome)
    if alvo in por_nome:
        return por_nome[alvo]

    # Busca por palavra inteira, não por prefixo: "Bradesco" precisa encontrar
    # tanto "BANCO BRADESCO" quanto "BRADESCO LEASING" para que a ambiguidade
    # apareça. Prefixo acharia só a leasing e resolveria para a empresa errada.
    padrao = re.compile(rf"\b{re.escape(alvo)}\b")
    candidatos = [valor for chave, valor in por_nome.items() if padrao.search(chave)]
    return candidatos[0] if len(candidatos) == 1 else None


def dimensao_ambiental(selos: list[str]) -> Dimensao:
    """Dimensão Ambiental — exceção à regra dos dois indicadores.

    A CVM não publica dados ambientais quantitativos estruturados, então a
    dimensão se apoia num único sinal: estar num índice de sustentabilidade
    da B3. A ausência do selo vira SEM_DADOS, nunca VERMELHO, porque não
    estar num índice não é evidência de mau desempenho ambiental.
    """
    if not selos:
        return Dimensao(
            tipo=TipoDimensao.AMBIENTAL,
            semaforo=Semaforo.SEM_DADOS,
            pontuacao=None,
            indicadores=[],
        )

    return Dimensao(
        tipo=TipoDimensao.AMBIENTAL,
        semaforo=Semaforo.VERDE,
        pontuacao=100.0,
        indicadores=[Indicador(
            id="indice_sustentabilidade_b3",
            rotulo="Integra índice de sustentabilidade da B3",
            valor=1.0,
            unidade=Unidade.BOOLEANO,
            percentilSetor=None,
            medianaSetor=None,
            comparacaoSetorial=False,
            direcao=Direcao.MAIOR_MELHOR,
            fonte=FONTE_B3,
        )],
    )
