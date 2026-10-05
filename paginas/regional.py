import streamlit as st

from src.dados import formatar_numero, formatar_pct, taxa_ponderada
from src.graficos import barras_estado, barras_regiao, mapa_ufs
from src.ui import cabecalho, contexto, interpretacao, mostrar, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Regiões e estados", "Quais estados apresentam maior evasão? Existem regiões mais vulneráveis?")
resumo_filtro(len(df_filtrado), len(df))

ranking = (
    taxa_ponderada(df_filtrado, ["uf", "nome_uf", "regiao"])
    .sort_values("taxa_evasao", ascending=False)
    .reset_index(drop=True)
)
por_regiao = taxa_ponderada(df_filtrado, "regiao").sort_values("taxa_evasao", ascending=False)

st.subheader("Mapa interativo")
st.plotly_chart(mapa_ufs(df_filtrado, ctx["malha"]), config={"displaylogo": False, "scrollZoom": False})
st.caption(
    f"Contorno dos estados obtido da API de malhas do IBGE ({ctx['origens']['malha']}). "
    "Estados em cinza não fazem parte da base ou do recorte filtrado."
)

col_a, col_b = st.columns([1.05, 1])
with col_a:
    mostrar(barras_estado(df_filtrado))
with col_b:
    st.markdown("**Ranking estadual**")
    st.dataframe(
        ranking[["uf", "nome_uf", "regiao", "taxa_evasao", "evasoes"]],
        hide_index=True, height=min(38 * (len(ranking) + 1), 640),
        column_config={
            "uf": "UF",
            "nome_uf": "Estado",
            "regiao": "Região",
            "taxa_evasao": st.column_config.ProgressColumn(
                "Taxa de evasão", format="%.2f%%", min_value=0, max_value=float(ranking["taxa_evasao"].max()) * 1.1
            ),
            "evasoes": st.column_config.NumberColumn("Evasões", format="localized"),
        },
    )

if len(ranking) >= 2:
    topo, base = ranking.iloc[0], ranking.iloc[-1]
    amplitude = topo["taxa_evasao"] - base["taxa_evasao"]
    interpretacao(
        f"**{topo['nome_uf']} ({topo['uf']})** tem a maior taxa do recorte ({formatar_pct(topo['taxa_evasao'])}) e "
        f"**{base['nome_uf']} ({base['uf']})** a menor ({formatar_pct(base['taxa_evasao'])}): uma amplitude de "
        f"{formatar_numero(amplitude, 2)} p.p. A linha tracejada marca a média do recorte; as cores identificam a "
        "região de cada estado, o que mostra que estados da mesma região aparecem espalhados pelo ranking."
    )

st.subheader("Comparação entre regiões")
mostrar(barras_regiao(df_filtrado))

if len(por_regiao) >= 2:
    mais, menos = por_regiao.iloc[0], por_regiao.iloc[-1]
    interpretacao(
        f"**{mais['regiao']}** é a região mais vulnerável ({formatar_pct(mais['taxa_evasao'])}) e **{menos['regiao']}** "
        f"a menos afetada ({formatar_pct(menos['taxa_evasao'])}). A diferença entre regiões "
        f"({formatar_numero(mais['taxa_evasao'] - menos['taxa_evasao'], 2)} p.p.) é bem menor que a diferença entre "
        "redes dentro de qualquer região: a desigualdade regional existe, mas pesa menos do que o tipo de escola."
    )
