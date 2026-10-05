import streamlit as st

from src.analise import classificar_correlacao, correlacao, tabela_correlacoes
from src.dados import formatar_numero, formatar_pct, taxa_ponderada
from src.graficos import dispersao, matriz_correlacao, taxa_por_faixa
from src.ui import cabecalho, contexto, interpretacao, mostrar, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

cabecalho("Fatores associados", "Existe relação entre renda e evasão? Quais fatores parecem mais associados ao problema?")
resumo_filtro(len(df_filtrado), len(df))

if len(df_filtrado) < 30:
    st.warning("O recorte tem menos de 30 registros: amplie os filtros para uma análise de correlação confiável.")
    st.stop()

FATORES = {
    "Renda média familiar": ("renda_media_familiar", "faixa_renda"),
    "Índice de desempenho": ("indice_desempenho", "faixa_desempenho"),
    "Acesso à internet": ("acesso_internet", "faixa_internet"),
}
col_f, col_m = st.columns([2, 1])
fator = col_f.segmented_control("Fator analisado", list(FATORES), default="Renda média familiar", key="fator")
metodo = col_m.segmented_control("Correlação", ["Pearson", "Spearman"], default="Pearson", key="metodo",
                                 help="Pearson mede relação linear; Spearman mede relação monotônica (por postos).")
fator = fator or "Renda média familiar"
metodo = (metodo or "Pearson").lower()
coluna, faixa = FATORES[fator]

mostrar(dispersao(df_filtrado, coluna))

r = correlacao(df_filtrado[coluna], df_filtrado["taxa_evasao"], metodo)
quartis = taxa_ponderada(df_filtrado, faixa)
interpretacao(
    f"A correlação de {metodo.title()} entre **{fator.lower()}** e a taxa de evasão é "
    f"**{formatar_numero(r, 3)}** ({classificar_correlacao(r)}). Entre os quartis, a taxa varia de "
    f"{formatar_pct(quartis['taxa_evasao'].min())} a {formatar_pct(quartis['taxa_evasao'].max())}. "
    "As retas de cada rede são quase horizontais e separadas por um degrau: o que define o nível da evasão é a rede, "
    "não o fator socioeconômico."
)

st.subheader("Correlação entre todas as variáveis")
col_a, col_b = st.columns(2)
with col_a:
    mostrar(taxa_por_faixa(df_filtrado, faixa))
with col_b:
    mostrar(matriz_correlacao(df_filtrado, metodo))

tabela = tabela_correlacoes(df_filtrado, metodo)
st.markdown("**Correlação de cada fator com a taxa de evasão**")
st.dataframe(
    tabela, hide_index=True,
    column_config={
        "r (geral)": st.column_config.NumberColumn(format="%+.3f"),
        "p-valor": st.column_config.NumberColumn(format="%.4f", help="Teste t com aproximação normal. p < 0,05 = significativo."),
        "r (Pública)": st.column_config.NumberColumn(format="%+.3f"),
        "r (Privada)": st.column_config.NumberColumn(format="%+.3f"),
    },
)
st.caption(
    "Rede pública é uma variável binária (1 = pública, 0 = privada); sua correlação com a taxa é a correlação "
    "ponto-bisserial. As colunas por rede repetem o cálculo dentro de cada grupo (vazio = não se aplica)."
)

principal = tabela.iloc[tabela["r (geral)"].abs().idxmax()]
interpretacao(
    f"O fator mais associado à evasão é **{principal['Fator'].split(' (')[0].lower()}** "
    f"(r = {formatar_numero(principal['r (geral)'], 2)}, {classificar_correlacao(principal['r (geral)'])}). "
    "Na base completa, renda, desempenho e acesso à internet ficam abaixo de |0,1|, faixa considerada desprezível. "
    "O leve sinal negativo do desempenho no agregado não é consistente dentro das redes (o sinal muda entre pública "
    "e privada) e em boa parte reflete o desempenho médio um pouco maior da rede privada. Lembre-se: correlação não "
    "implica causalidade, e a base é simulada."
)
