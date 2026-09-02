"""Indicadores da dimensão Social, extraídos do FRE."""
from collections import defaultdict
from pathlib import Path

from esg_etl.contrato import Direcao, Unidade
from esg_etl.indicadores import FONTE_FRE, ValorBruto, percentual
from esg_etl.leitura import linhas_da_versao_mais_recente

ARQ_GENERO = "fre_cia_aberta_administrador_declaracao_genero_2025.csv"
ARQ_RACA = "fre_cia_aberta_empregado_posicao_declaracao_raca_2025.csv"
ARQ_PCD = "fre_cia_aberta_empregado_PCD_2025.csv"

CONSELHO_EFETIVO = "Conselho de Administração - Efetivos"
LIDERANCA = "Liderança"
NAO_LIDERANCA = "Não-liderança"

COLUNAS_GENERO = (
    "Quantidade_Feminino", "Quantidade_Masculino", "Quantidade_Nao_Binario",
    "Quantidade_Outros", "Quantidade_Sem_Resposta",
)
COLUNAS_RACA = (
    "Quantidade_Amarelo", "Quantidade_Branco", "Quantidade_Preto",
    "Quantidade_Pardo", "Quantidade_Indigena", "Quantidade_Outros",
    "Quantidade_Sem_Resposta",
)


def _inteiro(linha: dict[str, str], coluna: str) -> int:
    return int(linha.get(coluna) or 0)


def _soma(linha: dict[str, str], colunas: tuple[str, ...]) -> int:
    return sum(_inteiro(linha, coluna) for coluna in colunas)


def _linhas(diretorio: Path, arquivo: str) -> list[dict[str, str]]:
    caminho = diretorio / arquivo
    if not caminho.exists():
        return []
    return linhas_da_versao_mais_recente(caminho)


def _mulheres_conselho(diretorio: Path) -> dict[str, ValorBruto]:
    resultado: dict[str, ValorBruto] = {}
    for linha in _linhas(diretorio, ARQ_GENERO):
        if linha["Orgao_Administracao"] != CONSELHO_EFETIVO:
            continue
        valor = percentual(
            _inteiro(linha, "Quantidade_Feminino"), _soma(linha, COLUNAS_GENERO)
        )
        if valor is None:
            continue
        resultado[linha["CNPJ_Companhia"].strip()] = ValorBruto(
            id="mulheres_conselho",
            rotulo="Mulheres no Conselho de Administração",
            valor=valor,
            unidade=Unidade.PERCENTUAL,
            direcao=Direcao.MAIOR_MELHOR,
            fonte=FONTE_FRE,
        )
    return resultado


def _percentuais_negros(diretorio: Path) -> dict[str, dict[str, float]]:
    """Percentual de pessoas negras por CNPJ e por posição hierárquica."""
    bruto: dict[str, dict[str, float]] = defaultdict(dict)
    for linha in _linhas(diretorio, ARQ_RACA):
        posicao = linha["Posicao"]
        if posicao not in (LIDERANCA, NAO_LIDERANCA):
            continue
        negros = _inteiro(linha, "Quantidade_Preto") + _inteiro(linha, "Quantidade_Pardo")
        valor = percentual(negros, _soma(linha, COLUNAS_RACA))
        if valor is None:
            continue
        bruto[linha["CNPJ_Companhia"].strip()][posicao] = valor
    return bruto


def _pcd(diretorio: Path) -> dict[str, ValorBruto]:
    somas: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for linha in _linhas(diretorio, ARQ_PCD):
        cnpj = linha["CNPJ_Companhia"].strip()
        somas[cnpj][0] += _inteiro(linha, "Quantidade_PCD")
        somas[cnpj][1] += _soma(
            linha,
            ("Quantidade_PCD", "Quantidade_Nao_PCD", "Quantidade_Sem_Resposta"),
        )

    resultado: dict[str, ValorBruto] = {}
    for cnpj, (com_deficiencia, total) in somas.items():
        valor = percentual(com_deficiencia, total)
        if valor is None:
            continue
        resultado[cnpj] = ValorBruto(
            id="pcd_empregados",
            rotulo="Empregados com deficiência",
            valor=valor,
            unidade=Unidade.PERCENTUAL,
            direcao=Direcao.MAIOR_MELHOR,
            fonte=FONTE_FRE,
        )
    return resultado


def extrair_sociais(diretorio: Path) -> dict[str, list[ValorBruto]]:
    """Indicadores sociais por CNPJ. Indicadores sem base são omitidos."""
    resultado: dict[str, list[ValorBruto]] = defaultdict(list)

    for cnpj, indicador in _mulheres_conselho(diretorio).items():
        resultado[cnpj].append(indicador)

    for cnpj, por_posicao in _percentuais_negros(diretorio).items():
        if LIDERANCA in por_posicao:
            resultado[cnpj].append(ValorBruto(
                id="negros_lideranca",
                rotulo="Pessoas negras na liderança",
                valor=por_posicao[LIDERANCA],
                unidade=Unidade.PERCENTUAL,
                direcao=Direcao.MAIOR_MELHOR,
                fonte=FONTE_FRE,
            ))
        if LIDERANCA in por_posicao and NAO_LIDERANCA in por_posicao:
            resultado[cnpj].append(ValorBruto(
                id="gap_racial",
                rotulo="Queda da diversidade racial na liderança",
                valor=por_posicao[NAO_LIDERANCA] - por_posicao[LIDERANCA],
                unidade=Unidade.PERCENTUAL,
                direcao=Direcao.MENOR_MELHOR,
                fonte=FONTE_FRE,
            ))

    for cnpj, indicador in _pcd(diretorio).items():
        resultado[cnpj].append(indicador)

    return dict(resultado)
