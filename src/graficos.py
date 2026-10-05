"""Gráficos do projeto: Matplotlib/Seaborn para as análises e Plotly para o mapa e a série interativa."""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap

from src.config import (
    COR_DESTAQUE, COR_NEUTRA, CORES_REDE, CORES_REGIAO, CORES_RISCO, ESCALA_SEQUENCIAL, GRADE,
    ORDEM_REDES, ORDEM_RISCO, SUPERFICIE, TINTA_PRIMARIA, TINTA_SECUNDARIA, TINTA_SUAVE,
)
from src.dados import taxa_ponderada

CMAP_SEQUENCIAL = LinearSegmentedColormap.from_list("azul", ESCALA_SEQUENCIAL)
CMAP_DIVERGENTE = LinearSegmentedColormap.from_list("divergente", ["#d03b3b", "#f0efec", "#2a78d6"])
FORMATO_PCT = mtick.FuncFormatter(lambda v, _: f"{v:.0f}%".replace(".", ","))


def aplicar_estilo() -> None:
    """Estilo único para todos os gráficos: grade discreta, tinta neutra e sem bordas supérfluas."""
    sns.set_theme(style="whitegrid")
    plt.rcParams.update({
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "axes.edgecolor": COR_NEUTRA,
        "axes.labelcolor": TINTA_SECUNDARIA,
        "axes.titlecolor": TINTA_PRIMARIA,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 12,
        "axes.labelsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": GRADE,
        "grid.linewidth": 0.8,
        "xtick.color": TINTA_SUAVE,
        "ytick.color": TINTA_SUAVE,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "legend.title_fontsize": 9,
        "text.color": TINTA_PRIMARIA,
        "font.family": "sans-serif",
    })


def _rotulo_pct(v: float, casas: int = 1) -> str:
    return f"{v:.{casas}f}%".replace(".", ",")


# ---------------------------------------------------------------- Temporal
def linha_temporal(df: pd.DataFrame, por_rede: bool = True) -> plt.Figure:
    """Taxa de evasão ponderada por ano: geral + uma linha por rede de ensino."""
    fig, ax = plt.subplots(figsize=(11, 4.6))
    geral = taxa_ponderada(df, "ano")
    ax.plot(geral["ano"], geral["taxa_evasao"], color=TINTA_SECUNDARIA, lw=2, ls="--", marker="o", ms=5, label="Geral")
    ax.annotate(f"Geral {_rotulo_pct(geral['taxa_evasao'].iloc[-1])}", (geral["ano"].iloc[-1], geral["taxa_evasao"].iloc[-1]),
                xytext=(8, 0), textcoords="offset points", va="center", fontsize=9, color=TINTA_SECUNDARIA)

    if por_rede:
        por = taxa_ponderada(df, ["ano", "rede_ensino"])
        for rede in ORDEM_REDES:
            serie = por[por["rede_ensino"] == rede]
            if serie.empty:
                continue
            ax.plot(serie["ano"], serie["taxa_evasao"], color=CORES_REDE[rede], lw=2, marker="o", ms=6, label=rede)
            ax.annotate(f"{rede} {_rotulo_pct(serie['taxa_evasao'].iloc[-1])}",
                        (serie["ano"].iloc[-1], serie["taxa_evasao"].iloc[-1]),
                        xytext=(8, 0), textcoords="offset points", va="center", fontsize=9, color=TINTA_PRIMARIA)

    ax.set_title("Evolução anual da taxa de evasão")
    ax.set_xlabel("Ano letivo")
    ax.set_ylabel("Taxa de evasão (ponderada)")
    ax.yaxis.set_major_formatter(FORMATO_PCT)
    ax.set_xticks(sorted(df["ano"].unique()))
    ax.set_ylim(bottom=0)
    ax.set_xlim(right=ax.get_xlim()[1] + 0.9)
    ax.legend(loc="lower left", ncol=3)
    fig.tight_layout()
    return fig


def heatmap_semestral(df: pd.DataFrame, linhas: str = "regiao") -> plt.Figure:
    """Mapa de calor da taxa por período semestral (colunas) e região/UF (linhas)."""
    agg = taxa_ponderada(df, [linhas, "periodo"])
    tabela = agg.pivot(index=linhas, columns="periodo", values="taxa_evasao")
    if linhas == "uf":
        ordem = taxa_ponderada(df, linhas).sort_values("taxa_evasao", ascending=False)[linhas]
        tabela = tabela.loc[ordem]

    altura = max(3.8, 0.42 * len(tabela) + 2)
    fig, ax = plt.subplots(figsize=(13, altura))
    sns.heatmap(
        tabela, cmap=CMAP_SEQUENCIAL, annot=len(tabela.columns) <= 20, fmt=".1f",
        annot_kws={"fontsize": 8}, linewidths=1.5, linecolor=SUPERFICIE,
        cbar_kws={"label": "Taxa de evasão (%)", "shrink": 0.8}, ax=ax,
    )
    ax.set_title("Taxa de evasão por semestre (%)")
    ax.grid(False)
    ax.set_xlabel("Período (ano-semestre)")
    ax.set_ylabel("Região" if linhas == "regiao" else "UF")
    ax.tick_params(axis="x", rotation=45)
    ax.tick_params(axis="y", rotation=0)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- Geografia
def barras_estado(df: pd.DataFrame) -> plt.Figure:
    """Ranking de UFs pela taxa ponderada, coloridas pela região, com a média do recorte como referência."""
    agg = taxa_ponderada(df, ["uf", "regiao"]).sort_values("taxa_evasao", ascending=True)
    media = taxa_ponderada(df)

    fig, ax = plt.subplots(figsize=(7, max(3.5, 0.3 * len(agg) + 1.2)))
    cores = [CORES_REGIAO[str(r)] for r in agg["regiao"]]
    ax.barh(agg["uf"], agg["taxa_evasao"], color=cores, height=0.68, edgecolor=SUPERFICIE, linewidth=1)
    for y, v in enumerate(agg["taxa_evasao"]):
        ax.text(v + 0.08, y, _rotulo_pct(v, 2), va="center", fontsize=8.5, color=TINTA_SECUNDARIA)
    ax.axvline(media, color=TINTA_PRIMARIA, lw=1.2, ls="--")
    ax.text(media, -0.75, f" média {_rotulo_pct(media, 2)}", fontsize=8.5, color=TINTA_PRIMARIA, va="center")
    ax.set_ylim(-1.1, len(agg) - 0.4)

    regioes = [r for r in CORES_REGIAO if r in set(agg["regiao"].astype(str))]
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=CORES_REGIAO[r]) for r in regioes], labels=regioes,
              loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=len(regioes), title=None)
    ax.set_title("Taxa de evasão por estado")
    ax.set_xlabel("Taxa de evasão (ponderada)")
    ax.set_ylabel("")
    ax.xaxis.set_major_formatter(FORMATO_PCT)
    ax.set_xlim(0, agg["taxa_evasao"].max() * 1.15)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def barras_regiao(df: pd.DataFrame) -> plt.Figure:
    """Taxa por região, separada por rede: mostra se a desigualdade regional existe dentro de cada rede."""
    agg = taxa_ponderada(df, ["regiao", "rede_ensino"])
    fig, ax = plt.subplots(figsize=(10, 4.4))
    sns.barplot(data=agg, x="regiao", y="taxa_evasao", hue="rede_ensino", palette=CORES_REDE,
                hue_order=[r for r in ORDEM_REDES if r in set(agg["rede_ensino"].astype(str))],
                width=0.7, saturation=1, edgecolor=SUPERFICIE, linewidth=2, ax=ax)
    for container in ax.containers:
        ax.bar_label(container, labels=[_rotulo_pct(v) for v in container.datavalues], fontsize=8.5,
                     color=TINTA_SECUNDARIA, padding=2)
    ax.set_title("Taxa de evasão por região e rede de ensino")
    ax.set_xlabel("")
    ax.set_ylabel("Taxa de evasão (ponderada)")
    ax.yaxis.set_major_formatter(FORMATO_PCT)
    ax.legend(title="Rede", loc="upper right")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def mapa_ufs(df: pd.DataFrame, malha: dict):
    """Mapa coroplético interativo (Plotly) com a taxa ponderada de cada UF."""
    agg = taxa_ponderada(df, ["codigo_ibge", "uf", "nome_uf", "regiao"])
    agg["codarea"] = agg["codigo_ibge"].astype(str)
    agg["taxa_fmt"] = agg["taxa_evasao"].map(lambda v: _rotulo_pct(v, 2))
    agg["evasoes_fmt"] = agg["evasoes"].map(lambda v: f"{v:,.0f}".replace(",", "."))
    fig = px.choropleth(
        agg, geojson=malha, locations="codarea", featureidkey="properties.codarea",
        color="taxa_evasao", color_continuous_scale=ESCALA_SEQUENCIAL,
        custom_data=["nome_uf", "uf", "regiao", "taxa_fmt", "evasoes_fmt"],
    )
    fig.update_traces(
        marker_line_color="#ffffff", marker_line_width=0.8,
        hovertemplate="<b>%{customdata[0]} (%{customdata[1]})</b><br>Região: %{customdata[2]}"
                      "<br>Taxa de evasão: %{customdata[3]}<br>Evasões: %{customdata[4]}<extra></extra>",
    )
    # Estados fora da base/recorte ficam em cinza para o contorno do país continuar completo.
    com_dados = set(agg["codarea"])
    sem_dados = [f["properties"]["codarea"] for f in malha["features"] if f["properties"]["codarea"] not in com_dados]
    if sem_dados:
        fig.add_trace(go.Choropleth(
            geojson=malha, locations=sem_dados, featureidkey="properties.codarea", z=[0] * len(sem_dados),
            colorscale=[[0, GRADE], [1, GRADE]], showscale=False, marker_line_color="#ffffff",
            marker_line_width=0.8, hovertemplate="Sem dados no recorte<extra></extra>",
        ))
    fig.update_geos(fitbounds="geojson", visible=False)
    fig.update_layout(
        height=520, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor=SUPERFICIE, geo_bgcolor=SUPERFICIE,
        coloraxis_colorbar=dict(title="Taxa (%)", ticksuffix="%"),
    )
    return fig


def linha_interativa_regioes(df: pd.DataFrame):
    """Série semestral por região com tooltip unificado (Plotly)."""
    agg = taxa_ponderada(df, ["periodo", "regiao"]).sort_values("periodo")
    agg["regiao"] = agg["regiao"].astype(str)
    fig = px.line(agg, x="periodo", y="taxa_evasao", color="regiao", markers=True,
                  color_discrete_map=CORES_REGIAO,
                  category_orders={"regiao": [r for r in CORES_REGIAO if r in set(agg["regiao"])]},
                  labels={"periodo": "Período", "taxa_evasao": "Taxa de evasão (%)", "regiao": "Região"})
    fig.update_traces(line_width=2, marker_size=7, hovertemplate="%{y:.2f}%")
    fig.update_layout(
        height=420, hovermode="x unified", paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE,
        margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.08, x=0, title=None),
        yaxis=dict(gridcolor=GRADE, ticksuffix="%", rangemode="tozero"), xaxis=dict(gridcolor=GRADE),
    )
    return fig


# ---------------------------------------------------------------- Rede e série
def barras_serie(df: pd.DataFrame) -> plt.Figure:
    """Taxa por série do ensino médio, separada por rede."""
    agg = taxa_ponderada(df, ["serie", "rede_ensino"])
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    sns.barplot(data=agg, x="serie", y="taxa_evasao", hue="rede_ensino", palette=CORES_REDE,
                hue_order=[r for r in ORDEM_REDES if r in set(agg["rede_ensino"].astype(str))],
                width=0.65, saturation=1, edgecolor=SUPERFICIE, linewidth=2, ax=ax)
    for container in ax.containers:
        ax.bar_label(container, labels=[_rotulo_pct(v, 2) for v in container.datavalues], fontsize=8.5,
                     color=TINTA_SECUNDARIA, padding=2)
    ax.set_title("Taxa de evasão por série e rede")
    ax.set_xlabel("")
    ax.set_ylabel("Taxa de evasão (ponderada)")
    ax.yaxis.set_major_formatter(FORMATO_PCT)
    ax.legend(title="Rede", loc="upper right")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def boxplot_rede(df: pd.DataFrame) -> plt.Figure:
    """Distribuição das taxas por registro em cada rede: mostra que a diferença não é efeito de outliers."""
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    redes = [r for r in ORDEM_REDES if r in set(df["rede_ensino"].astype(str))]
    sns.boxplot(data=df, x="rede_ensino", y="taxa_evasao", hue="rede_ensino", order=redes, hue_order=redes,
                palette=CORES_REDE, saturation=1, width=0.5, fliersize=3, linewidth=1.2, legend=False, ax=ax)
    ax.set_title("Distribuição da taxa de evasão por rede")
    ax.set_xlabel("")
    ax.set_ylabel("Taxa de evasão por registro")
    ax.yaxis.set_major_formatter(FORMATO_PCT)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def risco_por_rede(df: pd.DataFrame) -> plt.Figure:
    """Composição percentual dos níveis de risco em cada rede (barras 100% empilhadas)."""
    tabela = pd.crosstab(df["rede_ensino"], df["nivel_risco"], normalize="index") * 100
    tabela = tabela.reindex(columns=[r for r in ORDEM_RISCO if r in tabela.columns])
    tabela = tabela.loc[[r for r in ORDEM_REDES if r in tabela.index]]

    fig, ax = plt.subplots(figsize=(10, 2.8))
    esquerda = np.zeros(len(tabela))
    for nivel in tabela.columns:
        valores = tabela[nivel].to_numpy()
        ax.barh(tabela.index.astype(str), valores, left=esquerda, color=CORES_RISCO[nivel], label=nivel,
                height=0.55, edgecolor=SUPERFICIE, linewidth=2)
        for y, (v, x0) in enumerate(zip(valores, esquerda)):
            if v >= 6:
                ax.text(x0 + v / 2, y, f"{nivel}\n{v:.0f}%", ha="center", va="center", fontsize=8, color=TINTA_PRIMARIA)
        esquerda += valores
    ax.set_title("Composição dos níveis de risco por rede")
    ax.set_xlim(0, 100)
    ax.xaxis.set_major_formatter(FORMATO_PCT)
    ax.invert_yaxis()
    ax.legend(title="Nível de risco", ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------- Fatores
ROTULOS_FATORES = {
    "renda_media_familiar": "Renda média familiar (R$)",
    "indice_desempenho": "Índice de desempenho",
    "acesso_internet": "Acesso à internet (%)",
    "taxa_evasao": "Taxa de evasão (%)",
}


def dispersao(df: pd.DataFrame, x: str = "renda_media_familiar") -> plt.Figure:
    """Dispersão fator x taxa de evasão com reta de tendência por rede."""
    fig, ax = plt.subplots(figsize=(11, 4.8))
    redes = [r for r in ORDEM_REDES if r in set(df["rede_ensino"].astype(str))]
    for rede in redes:
        sub = df[df["rede_ensino"] == rede]
        sns.regplot(data=sub, x=x, y="taxa_evasao", ax=ax, color=CORES_REDE[rede], ci=None,
                    scatter_kws={"s": 18, "alpha": 0.45, "edgecolor": "none"},
                    line_kws={"lw": 2}, label=f"{rede} (r = {sub[x].corr(sub['taxa_evasao']):+.2f})".replace(".", ","))
    r_geral = df[x].corr(df["taxa_evasao"])
    ax.set_title(f"{ROTULOS_FATORES[x].split(' (')[0]} x taxa de evasão  —  r geral = {r_geral:+.2f}".replace(".", ","))
    ax.set_xlabel(ROTULOS_FATORES[x])
    ax.set_ylabel("Taxa de evasão por registro")
    ax.yaxis.set_major_formatter(FORMATO_PCT)
    if x == "renda_media_familiar":
        ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"R$ {v:,.0f}".replace(",", ".")))
    ax.legend(title="Rede (correlação de Pearson)", loc="upper right")
    fig.tight_layout()
    return fig


def taxa_por_faixa(df: pd.DataFrame, faixa: str = "faixa_renda") -> plt.Figure:
    """Taxa ponderada por quartil do fator: complementa a correlação com uma leitura não linear."""
    agg = taxa_ponderada(df, faixa)
    fig, ax = plt.subplots(figsize=(7, 5.6))
    ax.bar(agg[faixa].astype(str), agg["taxa_evasao"], color=COR_DESTAQUE, width=0.6, edgecolor=SUPERFICIE)
    for i, v in enumerate(agg["taxa_evasao"]):
        ax.text(i, v + 0.1, _rotulo_pct(v, 2), ha="center", fontsize=9, color=TINTA_SECUNDARIA)
    nome = {"faixa_renda": "renda", "faixa_desempenho": "desempenho", "faixa_internet": "acesso à internet"}[faixa]
    ax.set_title(f"Taxa de evasão por quartil de {nome}")
    ax.set_xlabel(f"Quartil de {nome}")
    ax.set_ylabel("Taxa de evasão (ponderada)")
    ax.yaxis.set_major_formatter(FORMATO_PCT)
    ax.set_ylim(0, agg["taxa_evasao"].max() * 1.2)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def matriz_correlacao(df: pd.DataFrame, metodo: str = "pearson") -> plt.Figure:
    """Matriz de correlação entre a taxa de evasão e os fatores socioeducacionais."""
    base = df[list(ROTULOS_FATORES)].copy()
    base["rede_publica"] = (df["rede_ensino"] == "Pública").astype(int)
    corr = base.corr(method=metodo)
    rotulos = [ROTULOS_FATORES.get(c, "Rede pública (1 = sim)").split(" (")[0] if c != "rede_publica" else "Rede pública"
               for c in corr.columns]
    mascara = np.triu(np.ones_like(corr, dtype=bool), k=1)

    fig, ax = plt.subplots(figsize=(7, 5.6))
    sns.heatmap(corr, mask=mascara, cmap=CMAP_DIVERGENTE, vmin=-1, vmax=1, center=0, annot=True, fmt=".2f",
                linewidths=2, linecolor=SUPERFICIE, square=True, xticklabels=rotulos, yticklabels=rotulos,
                cbar_kws={"label": f"Correlação ({metodo.title()})", "shrink": 0.75}, ax=ax)
    ax.set_title("Matriz de correlação")
    ax.grid(False)
    ax.tick_params(axis="x", rotation=35)
    plt.setp(ax.get_xticklabels(), ha="right")
    fig.tight_layout()
    return fig
