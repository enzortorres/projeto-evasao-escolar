"""Dashboard Streamlit — Evasão Escolar no Ensino Médio Brasileiro (2015–2024).

Ponto de entrada do app multipágina: carrega e trata os dados, integra a API do IBGE,
grava o banco SQLite, monta os filtros globais e entrega o recorte para as páginas.

Execução local:  streamlit run app.py
"""

import io

import streamlit as st

from src import banco, dados, ibge
from src.config import CAMINHO_CSV, ORDEM_REDES, ORDEM_REGIOES, ORDEM_RISCO, ORDEM_SERIES, TITULO
from src.graficos import aplicar_estilo
from src.ui import credito_sidebar

st.set_page_config(page_title="Evasão Escolar no Ensino Médio", page_icon=":material/school:", layout="wide")
aplicar_estilo()


# ---------------------------------------------------------------- Dados
@st.cache_data(show_spinner="Consultando a API do IBGE...", ttl=24 * 3600)
def carregar_ibge():
    estados, origem_estados = ibge.buscar_estados()
    malha, origem_malha = ibge.buscar_malha_ufs()
    return estados, malha, {"estados": origem_estados, "malha": origem_malha}


@st.cache_data(show_spinner="Tratando a base de dados...")
def carregar_dados(conteudo: bytes | None, estados):
    bruto = dados.ler_csv(io.BytesIO(conteudo) if conteudo else CAMINHO_CSV)
    limpo, relatorio = dados.limpar(bruto)
    return dados.criar_atributos(limpo, estados), relatorio


@st.cache_resource(show_spinner="Gravando o banco SQLite...")
def preparar_banco(_df, _estados, chave: str):
    """Recria o SQLite quando a base muda (a `chave` identifica a base carregada)."""
    banco.construir_banco(_df, _estados)
    return banco.conectar_somente_leitura()


estados, malha, origens = carregar_ibge()

st.sidebar.header("Fonte de dados")
with st.sidebar.expander("Enviar outro CSV (opcional)", icon=":material/upload_file:"):
    arquivo = st.file_uploader("CSV com o mesmo layout da base original", type="csv", label_visibility="collapsed")

conteudo, fonte = None, "Base original (simulacao_evasao_escolar_brasil.csv)"
if arquivo is not None:
    candidato = arquivo.getvalue()
    faltando = dados.validar_colunas(dados.ler_csv(io.BytesIO(candidato)))
    if faltando:
        st.sidebar.error(f"Arquivo ignorado. Colunas ausentes: {', '.join(faltando)}")
    else:
        conteudo, fonte = candidato, f"Arquivo enviado ({arquivo.name})"

df, relatorio = carregar_dados(conteudo, estados)
engine = preparar_banco(df, estados, chave=f"{fonte}-{len(df)}-{int(df['evasoes'].sum())}")


# ---------------------------------------------------------------- Filtros globais
CHAVES_FILTRO = ["f_anos", "f_semestres", "f_regioes", "f_ufs", "f_redes", "f_series", "f_riscos"]


def limpar_filtros():
    for chave in CHAVES_FILTRO:
        st.session_state.pop(chave, None)


st.sidebar.header("Filtros")
ano_min, ano_max = int(df["ano"].min()), int(df["ano"].max())
anos = st.sidebar.slider("Ano letivo", ano_min, ano_max, (ano_min, ano_max), key="f_anos")
semestres = st.sidebar.pills("Semestre", [1, 2], default=[1, 2], selection_mode="multi",
                             format_func=lambda s: f"{s}º semestre", key="f_semestres")
regioes = st.sidebar.multiselect("Região", ORDEM_REGIOES, default=ORDEM_REGIOES, key="f_regioes")

ufs_disponiveis = sorted(df.loc[df["regiao"].isin(regioes), "uf"].unique())
ufs = st.sidebar.multiselect("Estado (vazio = todos da região)", ufs_disponiveis, key="f_ufs",
                             placeholder="Todos os estados")
redes = st.sidebar.pills("Rede de ensino", ORDEM_REDES, default=ORDEM_REDES, selection_mode="multi", key="f_redes")
series = st.sidebar.pills("Série", ORDEM_SERIES, default=ORDEM_SERIES, selection_mode="multi", key="f_series")
riscos = st.sidebar.pills("Nível de risco", ORDEM_RISCO, default=ORDEM_RISCO, selection_mode="multi", key="f_riscos")
st.sidebar.button("Limpar filtros", icon=":material/filter_alt_off:", on_click=limpar_filtros, width="stretch")

filtros = {
    "anos": anos,
    "semestres": semestres,
    "regioes": regioes,
    "ufs": [u for u in ufs if u in ufs_disponiveis] or ufs_disponiveis,
    "redes": redes,
    "series": series,
    "riscos": riscos,
}
df_filtrado = dados.aplicar_filtros(df, filtros)

credito_sidebar()

st.session_state["ctx"] = {
    "df": df,
    "df_filtrado": df_filtrado,
    "filtros": filtros,
    "relatorio": relatorio,
    "engine": engine,
    "malha": malha,
    "origens": origens,
    "fonte": fonte,
}


# ---------------------------------------------------------------- Navegação
paginas = {
    "Painel": [
        st.Page("paginas/visao_geral.py", title="Visão geral", icon=":material/dashboard:", default=True),
    ],
    "Análises": [
        st.Page("paginas/evolucao_temporal.py", title="Evolução temporal", icon=":material/timeline:"),
        st.Page("paginas/regional.py", title="Regiões e estados", icon=":material/map:"),
        st.Page("paginas/redes_series.py", title="Redes e séries", icon=":material/school:"),
        st.Page("paginas/fatores.py", title="Fatores associados", icon=":material/scatter_plot:"),
    ],
    "Dados": [
        st.Page("paginas/explorar.py", title="Explorar dados e SQL", icon=":material/table_view:"),
        st.Page("paginas/conclusao.py", title="Conclusão executiva", icon=":material/flag:"),
    ],
}
pagina = st.navigation(paginas)

if df_filtrado.empty:
    st.title(TITULO)
    st.warning("Nenhum registro corresponde aos filtros selecionados. Amplie a seleção na barra lateral.",
               icon=":material/filter_alt_off:")
    st.stop()

pagina.run()
