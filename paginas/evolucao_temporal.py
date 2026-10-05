import streamlit as st

from src.analise import periodos_criticos, tendencia_anual
from src.dados import formatar_numero, formatar_pct, taxa_ponderada
from src.graficos import heatmap_semestral, linha_interativa_regioes, linha_temporal
from src.ui import cabecalho, contexto, interpretacao, mostrar, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Evolução temporal", "A evasão aumentou ou diminuiu ao longo do tempo? Quais foram os períodos críticos?")
resumo_filtro(len(df_filtrado), len(df))

if df_filtrado["ano"].nunique() < 2:
    st.warning("Selecione pelo menos dois anos para analisar a evolução temporal.")
    st.stop()

t = tendencia_anual(df_filtrado)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Variação no período", f"{formatar_numero(t['variacao_total'], 2)} p.p.", border=True,
          help="Diferença entre a taxa do último e do primeiro ano selecionados.")
c2.metric("Tendência (p.p. por ano)", formatar_numero(t["inclinacao"], 3), border=True,
          help="Inclinação da reta de mínimos quadrados (numpy.polyfit) ajustada à série anual.")
c3.metric("Ano de pico", t["ano_pico"], delta=formatar_pct(t["taxa_pico"]), delta_color="off", delta_arrow="off", border=True)
c4.metric("Ano de menor evasão", t["ano_minimo"], delta=formatar_pct(t["taxa_minima"]), delta_color="off",
          delta_arrow="off", border=True)

por_rede = st.toggle("Separar por rede de ensino", value=True)
mostrar(linha_temporal(df_filtrado, por_rede=por_rede))

sentido = "recuou" if t["inclinacao"] < 0 else "avançou"
texto = (
    f"No recorte selecionado, a evasão {sentido} em média {formatar_numero(abs(t['inclinacao']), 3)} p.p. por ano. "
    "A variação é pequena diante do nível da taxa: a evasão permaneceu num patamar alto e estável durante o "
    "período, sem uma melhora consistente."
)
redes_ano = taxa_ponderada(df_filtrado, ["ano", "rede_ensino"]).pivot(index="ano", columns="rede_ensino", values="taxa_evasao")
if {"Pública", "Privada"} <= set(redes_ano.columns):
    gap = (redes_ano["Pública"] - redes_ano["Privada"]).dropna()
    texto += (
        f" Em todos os anos a rede pública ficou acima da privada, com diferença entre "
        f"{formatar_numero(gap.min(), 1)} e {formatar_numero(gap.max(), 1)} p.p."
        if (gap > 0).all() else ""
    )
interpretacao(texto)

st.subheader("Mapa de calor semestral")
agrupar = st.segmented_control("Agrupar linhas por", ["Região", "Estado"], default="Região", key="agrupar_heatmap")
mostrar(heatmap_semestral(df_filtrado, "uf" if agrupar == "Estado" else "regiao"))

criticos = periodos_criticos(df_filtrado)
lista = ", ".join(f"**{p}** ({formatar_pct(v)})" for p, v in zip(criticos["periodo"], criticos["taxa_evasao"]))
interpretacao(
    f"Cada célula mostra a taxa ponderada do semestre. Tons mais escuros indicam evasão mais alta. "
    f"Os semestres mais críticos do recorte foram {lista}. As células oscilam de um semestre para outro "
    "sem um padrão sazonal fixo, sinal de que choques locais pesam mais que o calendário."
)

st.subheader("Série semestral por região (interativa)")
st.plotly_chart(linha_interativa_regioes(df_filtrado), config={"displaylogo": False})
st.caption("Passe o mouse para comparar as regiões no mesmo semestre; clique na legenda para ocultar séries.")

st.subheader("Tabela anual")
tabela = t["tabela"][["ano", "matriculados", "evasoes", "taxa_evasao", "variacao_pp", "media_movel_3a"]]
st.dataframe(
    tabela, hide_index=True,
    column_config={
        "ano": st.column_config.NumberColumn("Ano", format="%d"),
        "matriculados": st.column_config.NumberColumn("Matriculados", format="localized"),
        "evasoes": st.column_config.NumberColumn("Evasões", format="localized"),
        "taxa_evasao": st.column_config.NumberColumn("Taxa (%)", format="%.2f"),
        "variacao_pp": st.column_config.NumberColumn("Variação (p.p.)", format="%+.2f"),
        "media_movel_3a": st.column_config.NumberColumn("Média móvel 3 anos (%)", format="%.2f"),
    },
)
