"""Leitura, limpeza, engenharia de atributos e agregações da base de evasão escolar."""

from __future__ import annotations

import pandas as pd

from src.config import ORDEM_REDES, ORDEM_REGIOES, ORDEM_RISCO, ORDEM_SERIES

COLUNAS_OBRIGATORIAS = [
    "ano", "semestre", "data", "regiao", "uf", "municipio", "rede_ensino", "serie",
    "matriculados", "evasoes", "taxa_evasao", "renda_media_familiar",
    "indice_desempenho", "acesso_internet", "nivel_risco",
]
COLUNAS_NUMERICAS = [
    "ano", "semestre", "matriculados", "evasoes", "taxa_evasao",
    "renda_media_familiar", "indice_desempenho", "acesso_internet",
]
COLUNAS_TEXTO = ["regiao", "uf", "municipio", "rede_ensino", "serie", "nivel_risco"]


def ler_csv(origem) -> pd.DataFrame:
    """Lê o CSV (caminho ou arquivo enviado) tratando o BOM do UTF-8."""
    df = pd.read_csv(origem, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.lower()
    return df


def validar_colunas(df: pd.DataFrame) -> list[str]:
    """Retorna as colunas obrigatórias ausentes (lista vazia = base válida)."""
    return [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]


def limpar(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica a limpeza e devolve a base tratada junto com um relatório de cada etapa."""
    df = df.copy()
    relatorio = {"linhas_originais": len(df)}

    for col in COLUNAS_TEXTO:
        df[col] = df[col].astype("string").str.strip()
    df["uf"] = df["uf"].str.upper()
    for col in COLUNAS_NUMERICAS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    relatorio["valores_nulos"] = int(df[COLUNAS_OBRIGATORIAS].isna().sum().sum())
    df = df.dropna(subset=["ano", "semestre", "uf", "rede_ensino", "serie", "matriculados", "evasoes"])

    relatorio["duplicados_removidos"] = int(df.duplicated().sum())
    df = df.drop_duplicates()

    # Registros impossíveis: sem matrículas ou com mais evasões do que alunos.
    invalidos = (df["matriculados"] <= 0) | (df["evasoes"] < 0) | (df["evasoes"] > df["matriculados"])
    relatorio["registros_invalidos"] = int(invalidos.sum())
    df = df[~invalidos]

    # A taxa informada deve ser coerente com evasões / matriculados; recalculamos a partir da fonte primária.
    taxa_calculada = (df["evasoes"] / df["matriculados"] * 100).round(2)
    relatorio["taxas_corrigidas"] = int(((taxa_calculada - df["taxa_evasao"]).abs() > 0.05).sum())
    df["taxa_evasao"] = taxa_calculada

    # Índices percentuais não podem sair do intervalo 0–100.
    fora_intervalo = 0
    for col in ["indice_desempenho", "acesso_internet"]:
        fora_intervalo += int(((df[col] < 0) | (df[col] > 100)).sum())
        df[col] = df[col].clip(0, 100)
    relatorio["indices_ajustados"] = fora_intervalo

    df["ano"] = df["ano"].astype(int)
    df["semestre"] = df["semestre"].astype(int)
    df["matriculados"] = df["matriculados"].astype(int)
    df["evasoes"] = df["evasoes"].astype(int)

    relatorio["linhas_finais"] = len(df)
    return df.reset_index(drop=True), relatorio


def criar_atributos(df: pd.DataFrame, estados: pd.DataFrame | None = None) -> pd.DataFrame:
    """Engenharia de atributos: período, faixas de quartil, permanência e dados do IBGE."""
    df = df.copy()

    df["periodo"] = df["ano"].astype(str) + "-S" + df["semestre"].astype(str)
    df["permanencias"] = df["matriculados"] - df["evasoes"]

    for col in ["regiao", "rede_ensino", "serie", "nivel_risco"]:
        df[col] = df[col].astype(str)
    df["regiao"] = pd.Categorical(df["regiao"], categories=ORDEM_REGIOES, ordered=True)
    df["serie"] = pd.Categorical(df["serie"], categories=ORDEM_SERIES, ordered=True)
    df["rede_ensino"] = pd.Categorical(df["rede_ensino"], categories=ORDEM_REDES, ordered=True)
    df["nivel_risco"] = pd.Categorical(df["nivel_risco"], categories=ORDEM_RISCO, ordered=True)

    rotulos = ["Q1 (mais baixo)", "Q2", "Q3", "Q4 (mais alto)"]
    df["faixa_renda"] = pd.qcut(df["renda_media_familiar"], 4, labels=rotulos)
    df["faixa_desempenho"] = pd.qcut(df["indice_desempenho"], 4, labels=rotulos)
    df["faixa_internet"] = pd.qcut(df["acesso_internet"], 4, labels=rotulos)

    # Integração com a tabela de estados do IBGE (nome oficial e código para o mapa).
    if estados is not None:
        df = df.merge(estados[["uf", "nome", "codigo_ibge"]].rename(columns={"nome": "nome_uf"}), on="uf", how="left")

    return df


def taxa_ponderada(df: pd.DataFrame, por=None) -> pd.DataFrame | float:
    """Taxa de evasão ponderada pelas matrículas (soma de evasões / soma de matriculados).

    É a forma correta de agregar taxas: a média simples daria o mesmo peso a uma
    escola com 400 alunos e a outra com 40 mil.
    """
    if por is None:
        matriculados = df["matriculados"].sum()
        return float(df["evasoes"].sum() / matriculados * 100) if matriculados else float("nan")

    agg = (
        df.groupby(por, observed=True)
        .agg(evasoes=("evasoes", "sum"), matriculados=("matriculados", "sum"), registros=("evasoes", "size"))
        .reset_index()
    )
    agg["taxa_evasao"] = agg["evasoes"] / agg["matriculados"] * 100
    return agg


def aplicar_filtros(df: pd.DataFrame, filtros: dict) -> pd.DataFrame:
    """Aplica os filtros escolhidos na barra lateral."""
    ano_ini, ano_fim = filtros["anos"]
    mascara = (
        df["ano"].between(ano_ini, ano_fim)
        & df["semestre"].isin(filtros["semestres"])
        & df["regiao"].isin(filtros["regioes"])
        & df["uf"].isin(filtros["ufs"])
        & df["rede_ensino"].isin(filtros["redes"])
        & df["serie"].isin(filtros["series"])
        & df["nivel_risco"].isin(filtros["riscos"])
    )
    return df[mascara]


def formatar_numero(valor: float, casas: int = 0) -> str:
    """Formata números no padrão brasileiro (1.234,5)."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_pct(valor: float, casas: int = 2) -> str:
    return f"{formatar_numero(valor, casas)}%"
