"""KPIs, estatísticas e textos interpretativos gerados a partir do recorte filtrado."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.dados import formatar_numero, formatar_pct, taxa_ponderada


def _maior(df: pd.DataFrame, por: str) -> tuple[str, float]:
    agg = taxa_ponderada(df, por).sort_values("taxa_evasao", ascending=False)
    linha = agg.iloc[0]
    return str(linha[por]), float(linha["taxa_evasao"])


def calcular_kpis(df: pd.DataFrame) -> dict:
    """Os seis KPIs exigidos pelo tema + indicadores de apoio."""
    redes = taxa_ponderada(df, "rede_ensino").set_index("rede_ensino")["taxa_evasao"]
    kpis = {
        "taxa_media": taxa_ponderada(df),
        "taxa_media_simples": float(df["taxa_evasao"].mean()),
        "total_evasoes": int(df["evasoes"].sum()),
        "total_matriculados": int(df["matriculados"].sum()),
        "estado": _maior(df, "uf"),
        "regiao": _maior(df, "regiao"),
        "rede": _maior(df, "rede_ensino"),
        "serie": _maior(df, "serie"),
        "pct_critico": float((df["nivel_risco"] == "Crítico").mean() * 100),
        "taxa_publica": float(redes.get("Pública", np.nan)),
        "taxa_privada": float(redes.get("Privada", np.nan)),
    }
    if kpis["taxa_privada"] and not math.isnan(kpis["taxa_privada"]) and not math.isnan(kpis["taxa_publica"]):
        kpis["razao_redes"] = kpis["taxa_publica"] / kpis["taxa_privada"]
    else:
        kpis["razao_redes"] = np.nan
    return kpis


def tendencia_anual(df: pd.DataFrame) -> dict:
    """Série anual com variação, média móvel e inclinação da reta de tendência (mínimos quadrados)."""
    anual = taxa_ponderada(df, "ano").sort_values("ano")
    anual["variacao_pp"] = anual["taxa_evasao"].diff()
    anual["media_movel_3a"] = anual["taxa_evasao"].rolling(3, min_periods=1).mean()
    inclinacao = float(np.polyfit(anual["ano"], anual["taxa_evasao"], 1)[0]) if len(anual) >= 2 else 0.0
    return {
        "tabela": anual,
        "inclinacao": inclinacao,
        "variacao_total": float(anual["taxa_evasao"].iloc[-1] - anual["taxa_evasao"].iloc[0]),
        "ano_pico": int(anual.loc[anual["taxa_evasao"].idxmax(), "ano"]),
        "taxa_pico": float(anual["taxa_evasao"].max()),
        "ano_minimo": int(anual.loc[anual["taxa_evasao"].idxmin(), "ano"]),
        "taxa_minima": float(anual["taxa_evasao"].min()),
    }


def periodos_criticos(df: pd.DataFrame, n: int = 3) -> pd.DataFrame:
    return taxa_ponderada(df, "periodo").sort_values("taxa_evasao", ascending=False).head(n)


def correlacao(x: pd.Series, y: pd.Series, metodo: str = "pearson") -> float:
    """Pearson ou Spearman. Spearman = Pearson sobre os postos, o que dispensa a dependência do SciPy."""
    if metodo == "spearman":
        x, y = x.rank(), y.rank()
    return float(x.corr(y))


def correlacao_com_significancia(x: pd.Series, y: pd.Series, metodo: str = "pearson") -> tuple[float, float]:
    """Coeficiente de correlação e p-valor aproximado (teste t; aproximação normal, adequada para n >= 30)."""
    r = correlacao(x, y, metodo)
    n = int(pd.concat([x, y], axis=1).dropna().shape[0])
    if n < 30 or math.isnan(r) or abs(r) >= 1:
        return r, float("nan")
    t = r * math.sqrt((n - 2) / (1 - r**2))
    return r, math.erfc(abs(t) / math.sqrt(2))


def tabela_correlacoes(df: pd.DataFrame, metodo: str = "pearson") -> pd.DataFrame:
    """Correlação de cada fator com a taxa de evasão, no total e dentro de cada rede."""
    fatores = {
        "Rede pública (1 = sim)": (df["rede_ensino"] == "Pública").astype(int),
        "Renda média familiar": df["renda_media_familiar"],
        "Índice de desempenho": df["indice_desempenho"],
        "Acesso à internet": df["acesso_internet"],
    }
    linhas = []
    for nome, serie in fatores.items():
        r, p = correlacao_com_significancia(serie, df["taxa_evasao"], metodo)
        linha = {"Fator": nome, "r (geral)": r, "p-valor": p}
        for rede in ["Pública", "Privada"]:
            mascara = df["rede_ensino"] == rede
            linha[f"r ({rede})"] = np.nan if nome.startswith("Rede") or mascara.sum() < 3 else correlacao(
                serie[mascara], df.loc[mascara, "taxa_evasao"], metodo)
        linhas.append(linha)
    return pd.DataFrame(linhas)


def classificar_correlacao(r: float) -> str:
    if math.isnan(r):
        return "indefinida"
    forca = abs(r)
    if forca < 0.1:
        return "desprezível"
    if forca < 0.3:
        return "fraca"
    if forca < 0.5:
        return "moderada"
    return "forte"


def destaques(df: pd.DataFrame) -> list[str]:
    """Frases interpretativas que se ajustam ao recorte selecionado."""
    k = calcular_kpis(df)
    frases = [
        f"A taxa de evasão ponderada do recorte é **{formatar_pct(k['taxa_media'])}**, o equivalente a "
        f"**{formatar_numero(k['total_evasoes'])}** estudantes que abandonaram a escola de "
        f"{formatar_numero(k['total_matriculados'])} matriculados.",
        f"**{k['estado'][0]}** lidera o ranking estadual ({formatar_pct(k['estado'][1])}) e **{k['regiao'][0]}** é a "
        f"região mais vulnerável ({formatar_pct(k['regiao'][1])}).",
    ]
    if not math.isnan(k["razao_redes"]):
        frases.append(
            f"A rede **pública** perde {formatar_pct(k['taxa_publica'])} dos alunos contra "
            f"{formatar_pct(k['taxa_privada'])} na privada: uma taxa **{formatar_numero(k['razao_redes'], 1)} vezes maior**."
        )
    if df["ano"].nunique() >= 2:
        t = tendencia_anual(df)
        sentido = "queda" if t["inclinacao"] < 0 else "alta"
        frases.append(
            f"A tendência linear indica **{sentido} de {formatar_numero(abs(t['inclinacao']), 3)} p.p. por ano**; "
            f"o pico foi em {t['ano_pico']} ({formatar_pct(t['taxa_pico'])}) e o menor valor em "
            f"{t['ano_minimo']} ({formatar_pct(t['taxa_minima'])})."
        )
    frases.append(
        f"A série com maior taxa é o **{k['serie'][0]}** ({formatar_pct(k['serie'][1])}) e "
        f"{formatar_pct(k['pct_critico'], 1)} dos registros estão em nível de risco **Crítico**."
    )
    return frases
