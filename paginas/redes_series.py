import streamlit as st

from src.analise import calcular_kpis
from src.dados import formatar_numero, formatar_pct, taxa_ponderada
from src.graficos import barras_serie, boxplot_rede, risco_por_rede
from src.ui import cabecalho, contexto, interpretacao, mostrar, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Redes de ensino e séries", "Há diferenças entre escolas públicas e privadas? Quais séries apresentam maior abandono?")
resumo_filtro(len(df_filtrado), len(df))

k = calcular_kpis(df_filtrado)
ambas_redes = k["razao_redes"] == k["razao_redes"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Taxa na rede pública", formatar_pct(k["taxa_publica"]) if k["taxa_publica"] == k["taxa_publica"] else "—", border=True)
c2.metric("Taxa na rede privada", formatar_pct(k["taxa_privada"]) if k["taxa_privada"] == k["taxa_privada"] else "—", border=True)
c3.metric("Diferença", f"{formatar_numero(k['taxa_publica'] - k['taxa_privada'], 2)} p.p." if ambas_redes else "—", border=True)
c4.metric("Pública ÷ privada", f"{formatar_numero(k['razao_redes'], 1)}x" if ambas_redes else "—", border=True)

col_a, col_b = st.columns(2)
with col_a:
    mostrar(boxplot_rede(df_filtrado))
with col_b:
    mostrar(barras_serie(df_filtrado))

if ambas_redes:
    interpretacao(
        f"A rede pública perde **{formatar_numero(k['razao_redes'], 1)} vezes mais** alunos que a privada. O boxplot "
        "mostra que as duas distribuições quase não se sobrepõem: a diferença não vem de poucos casos extremos, "
        "atinge praticamente todos os municípios e semestres."
    )

st.subheader("Qual série é mais crítica?")
geral = taxa_ponderada(df_filtrado, "serie").sort_values("taxa_evasao", ascending=False)
st.dataframe(
    geral[["serie", "taxa_evasao", "evasoes", "matriculados"]], hide_index=True,
    column_config={
        "serie": "Série",
        "taxa_evasao": st.column_config.NumberColumn("Taxa geral (%)", format="%.2f"),
        "evasoes": st.column_config.NumberColumn("Evasões", format="localized"),
        "matriculados": st.column_config.NumberColumn("Matriculados", format="localized"),
    },
)

por_serie_rede = taxa_ponderada(df_filtrado, ["serie", "rede_ensino"])
texto = (
    f"No agregado, o **{geral.iloc[0]['serie']}** tem a maior taxa ({formatar_pct(geral.iloc[0]['taxa_evasao'])}), "
    f"mas a diferença entre séries é de apenas {formatar_numero(geral['taxa_evasao'].max() - geral['taxa_evasao'].min(), 2)} p.p."
)
if ambas_redes:
    publica = por_serie_rede[por_serie_rede["rede_ensino"] == "Pública"].sort_values("taxa_evasao", ascending=False)
    privada = por_serie_rede[por_serie_rede["rede_ensino"] == "Privada"].sort_values("taxa_evasao", ascending=False)
    texto += (
        f" Dentro de cada rede o quadro muda: na pública a série mais crítica é o **{publica.iloc[0]['serie']}**, "
        f"na privada é o **{privada.iloc[0]['serie']}**. Ou seja, a série mais crítica depende da rede, e as diferenças entre "
        "séries são pequenas perto da diferença entre redes: a comparação por rede é a leitura mais informativa."
    )
interpretacao(texto)

st.subheader("Níveis de risco")
mostrar(risco_por_rede(df_filtrado))
interpretacao(
    "O nível de risco classifica cada registro pela taxa (Baixo < 4%, Médio 4–8%, Alto 8–13%, Crítico ≥ 13%). "
    "Todos os registros críticos estão na rede pública, e quase nenhum registro público chega ao nível Baixo: "
    "o risco elevado é praticamente exclusivo da rede pública."
)
