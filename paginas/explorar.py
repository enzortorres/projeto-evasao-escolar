import pandas as pd
import streamlit as st

from src.banco import CONSULTAS, executar_consulta
from src.graficos import CMAP_SEQUENCIAL
from src.ui import cabecalho, contexto, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Explorar dados e SQL", "Tabela dinâmica, consultas SQL no banco SQLite e a base filtrada para download.")
resumo_filtro(len(df_filtrado), len(df))

aba_pivot, aba_sql, aba_base = st.tabs(["Tabela dinâmica", "Consulta SQL", "Base filtrada"])

# ---------------------------------------------------------------- Tabela dinâmica
DIMENSOES = {
    "Ano": "ano", "Semestre": "semestre", "Período": "periodo", "Região": "regiao", "Estado": "uf",
    "Município": "municipio", "Rede de ensino": "rede_ensino", "Série": "serie", "Nível de risco": "nivel_risco",
    "Quartil de renda": "faixa_renda", "Quartil de desempenho": "faixa_desempenho",
}
METRICAS = {
    "Taxa de evasão ponderada (%)": None,
    "Total de evasões": ("evasoes", "sum"),
    "Total de matriculados": ("matriculados", "sum"),
    "Renda média familiar (R$)": ("renda_media_familiar", "mean"),
    "Índice de desempenho médio": ("indice_desempenho", "mean"),
    "Acesso à internet médio (%)": ("acesso_internet", "mean"),
    "Número de registros": ("evasoes", "size"),
}

with aba_pivot:
    c1, c2, c3 = st.columns(3)
    linhas = c1.selectbox("Linhas", list(DIMENSOES), index=3)
    colunas = c2.selectbox("Colunas", ["(nenhuma)"] + list(DIMENSOES), index=7)
    metrica = c3.selectbox("Métrica", list(METRICAS))

    indices = [DIMENSOES[linhas]]
    if colunas != "(nenhuma)" and DIMENSOES[colunas] != DIMENSOES[linhas]:
        indices.append(DIMENSOES[colunas])

    if METRICAS[metrica] is None:
        agg = df_filtrado.groupby(indices, observed=True)[["evasoes", "matriculados"]].sum()
        valores = agg["evasoes"] / agg["matriculados"] * 100
    else:
        coluna, funcao = METRICAS[metrica]
        valores = df_filtrado.groupby(indices, observed=True)[coluna].agg(funcao)

    pivot = valores.unstack() if len(indices) == 2 else valores.to_frame(metrica)
    pivot.index = pivot.index.astype(str)
    pivot.columns = pivot.columns.astype(str)
    casas = 0 if metrica.startswith(("Total", "Número")) else 2
    st.dataframe(
        pivot.style.format(lambda v: "" if pd.isna(v) else f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", "."))
        .background_gradient(cmap=CMAP_SEQUENCIAL, axis=None),
        height=min(38 * (len(pivot) + 1), 600),
    )
    st.caption(
        "Taxas são sempre ponderadas pelas matrículas (soma de evasões ÷ soma de matriculados). "
        "Tons mais escuros indicam valores maiores na tabela."
    )
    st.download_button("Baixar tabela dinâmica (CSV)", pivot.to_csv(sep=";", decimal=",").encode("utf-8-sig"),
                       file_name="tabela_dinamica_evasao.csv", mime="text/csv", icon=":material/download:")

# ---------------------------------------------------------------- SQL
with aba_sql:
    st.markdown(
        """
O tratamento gera um banco **SQLite** normalizado com **SQLAlchemy ORM** (`database/evasao_escolar.sqlite`),
combinando o CSV com a tabela de estados obtida da API do IBGE:

`regioes (1) ── (N) estados (1) ── (N) municipios (1) ── (N) indicadores_evasao`

O banco contém a **base completa tratada** (os filtros da barra lateral não se aplicam aqui) e é aberto em
modo somente leitura: experimente editar a consulta.
"""
    )
    escolha = st.selectbox("Consulta pronta", list(CONSULTAS))
    sql = st.text_area("SQL", CONSULTAS[escolha].strip(), height=230, key=f"sql_{escolha}")
    try:
        resultado = executar_consulta(ctx["engine"], sql)
        st.dataframe(resultado, hide_index=True)
        st.caption(f"{len(resultado)} linha(s) retornada(s).")
    except Exception as erro:  # erro de sintaxe ou tentativa de escrita no banco somente leitura
        st.error(f"Não foi possível executar a consulta: {erro.__class__.__name__}. {str(erro).splitlines()[0]}")

# ---------------------------------------------------------------- Base filtrada
with aba_base:
    colunas_base = [
        "ano", "semestre", "regiao", "uf", "municipio", "rede_ensino", "serie", "matriculados", "evasoes",
        "taxa_evasao", "renda_media_familiar", "indice_desempenho", "acesso_internet", "nivel_risco",
    ]
    st.dataframe(
        df_filtrado[colunas_base], hide_index=True, height=520,
        column_config={
            "ano": st.column_config.NumberColumn("Ano", format="%d"),
            "taxa_evasao": st.column_config.NumberColumn("Taxa (%)", format="%.2f"),
            "renda_media_familiar": st.column_config.NumberColumn("Renda (R$)", format="%.2f"),
            "matriculados": st.column_config.NumberColumn("Matriculados", format="localized"),
            "evasoes": st.column_config.NumberColumn("Evasões", format="localized"),
        },
    )
    st.download_button(
        "Baixar base filtrada (CSV)", df_filtrado[colunas_base].to_csv(index=False).encode("utf-8-sig"),
        file_name="evasao_escolar_filtrada.csv", mime="text/csv", icon=":material/download:",
    )
