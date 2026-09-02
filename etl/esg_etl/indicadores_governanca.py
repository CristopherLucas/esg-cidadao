"""Indicadores da dimensão Governança, extraídos do FRE."""
from collections import defaultdict
from pathlib import Path

from esg_etl.contrato import Direcao, Unidade
from esg_etl.indicadores import FONTE_FRE, ValorBruto
from esg_etl.leitura import linhas_da_versao_mais_recente, normalizar

ARQ_REMUNERACAO = "fre_cia_aberta_remuneracao_maxima_minima_media_2025.csv"
ARQ_COMITE = "fre_cia_aberta_membro_comite_2025.csv"
ARQ_TRANSACAO = "fre_cia_aberta_transacao_parte_relacionada_2025.csv"
ARQ_FAMILIAR = "fre_cia_aberta_relacao_familiar_2025.csv"

DIRETORIA = "Diretoria Estatutária"
COMITE_AUDITORIA = "Comitê de Auditoria"
TERMOS_SUSTENTABILIDADE = ("sustentab", "esg", "socioambiental", "ambiental")


def _linhas(diretorio: Path, arquivo: str) -> list[dict[str, str]]:
    caminho = diretorio / arquivo
    if not caminho.exists():
        return []
    return linhas_da_versao_mais_recente(caminho)


def _decimal(texto: str) -> float:
    return float(texto.replace(",", ".")) if texto else 0.0


def _razao_remuneracao(diretorio: Path) -> dict[str, ValorBruto]:
    melhor_exercicio: dict[str, str] = {}
    valores: dict[str, tuple[float, float]] = {}

    for linha in _linhas(diretorio, ARQ_REMUNERACAO):
        if linha["Orgao_Administracao"] != DIRETORIA:
            continue
        cnpj = linha["CNPJ_Companhia"].strip()
        exercicio = linha["Data_Fim_Exercicio_Social"]
        if exercicio < melhor_exercicio.get(cnpj, ""):
            continue
        melhor_exercicio[cnpj] = exercicio
        valores[cnpj] = (
            _decimal(linha["Valor_Maior_Remuneracao"]),
            _decimal(linha["Valor_Menor_Remuneracao"]),
        )

    resultado: dict[str, ValorBruto] = {}
    for cnpj, (maior, menor) in valores.items():
        if menor <= 0 or maior <= 0:
            continue
        resultado[cnpj] = ValorBruto(
            id="razao_remuneracao",
            rotulo="Diferença entre a maior e a menor remuneração da diretoria",
            valor=maior / menor,
            unidade=Unidade.RAZAO,
            direcao=Direcao.MENOR_MELHOR,
            fonte=FONTE_FRE,
        )
    return resultado


def _comite_e_relevante(linha: dict[str, str]) -> bool:
    if linha["Tipo_Comite"] == COMITE_AUDITORIA:
        return True
    descricao = normalizar(linha.get("Descricao_Outros_Comites") or "")
    return any(termo in descricao for termo in TERMOS_SUSTENTABILIDADE)


def _comites(diretorio: Path) -> dict[str, ValorBruto]:
    presentes: dict[str, bool] = {}
    for linha in _linhas(diretorio, ARQ_COMITE):
        cnpj = linha["CNPJ_Companhia"].strip()
        presentes[cnpj] = presentes.get(cnpj, False) or _comite_e_relevante(linha)

    return {
        cnpj: ValorBruto(
            id="comites_relevantes",
            rotulo="Comitê de auditoria ou de sustentabilidade",
            valor=1.0 if tem else 0.0,
            unidade=Unidade.BOOLEANO,
            direcao=Direcao.MAIOR_MELHOR,
            fonte=FONTE_FRE,
        )
        for cnpj, tem in presentes.items()
    }


def _contagem(diretorio: Path, arquivo: str, id_indicador: str, rotulo: str) -> dict[str, ValorBruto]:
    contagens: dict[str, int] = defaultdict(int)
    for linha in _linhas(diretorio, arquivo):
        contagens[linha["CNPJ_Companhia"].strip()] += 1

    return {
        cnpj: ValorBruto(
            id=id_indicador,
            rotulo=rotulo,
            valor=float(total),
            unidade=Unidade.CONTAGEM,
            direcao=Direcao.MENOR_MELHOR,
            fonte=FONTE_FRE,
        )
        for cnpj, total in contagens.items()
    }


def extrair_governanca(diretorio: Path) -> dict[str, list[ValorBruto]]:
    """Indicadores de governança por CNPJ."""
    fontes = [
        _razao_remuneracao(diretorio),
        _comites(diretorio),
        _contagem(diretorio, ARQ_TRANSACAO, "transacoes_partes_relacionadas",
                  "Transações com partes relacionadas"),
        _contagem(diretorio, ARQ_FAMILIAR, "relacoes_familiares",
                  "Relações familiares na administração"),
    ]

    resultado: dict[str, list[ValorBruto]] = defaultdict(list)
    for fonte in fontes:
        for cnpj, indicador in fonte.items():
            resultado[cnpj].append(indicador)
    return dict(resultado)
