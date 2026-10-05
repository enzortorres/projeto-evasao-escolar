import streamlit as st

from src.analise import calcular_kpis, destaques
from src.config import AVALIACAO, TITULO
from src.dados import formatar_numero, formatar_pct
from src.graficos import linha_temporal
from src.ui import contexto, identificacao, interpretacao, mostrar, resumo_filtro

ctx = contexto()
df, df_filtrado = ctx["df"], ctx["df_filtrado"]

st.title(TITULO)
st.caption(f"{AVALIACAO} · Dashboard interativo de análise e visualização de dados")
identificacao()

st.subheader("O problema")
st.markdown(
    """
A **evasão escolar** é um dos maiores desafios da educação brasileira. Cada estudante que deixa o
ensino médio reduz suas chances de emprego qualificado, amplia a desigualdade econômica e
compromete o desenvolvimento social do país. Fatores como **condição socioeconômica**,
**desempenho acadêmico**, **acesso digital**, **rede de ensino** e **desigualdade regional**
costumam ser apontados como causas.

Este painel investiga os padrões de evasão no ensino médio entre **2015 e 2024**, a partir de uma
base simulada com 1.480 registros semestrais de 37 municípios em 20 estados, para identificar
onde, quando e em que grupos o problema é mais grave.
"""
)

with st.expander("Perguntas orientadoras", icon=":material/help:"):
    st.markdown(
        """
- Quais estados apresentam maior evasão escolar?
- Existem regiões mais vulneráveis?
- A evasão aumentou ou diminuiu ao longo do tempo?
- Há diferenças entre escolas públicas e privadas?
- Existe relação entre renda e evasão?
- Quais séries apresentam maior abandono?
- Quais fatores parecem mais associados ao problema?
"""
    )

st.subheader("Indicadores-chave")
resumo_filtro(len(df_filtrado), len(df))

k = calcular_kpis(df_filtrado)
taxa_nacional = calcular_kpis(df)["taxa_media"]
delta = k["taxa_media"] - taxa_nacional

c1, c2, c3, c4 = st.columns(4)
c1.metric(
    "Taxa média de evasão", formatar_pct(k["taxa_media"]),
    delta=f"{formatar_numero(delta, 2)} p.p. vs. base completa" if abs(delta) >= 0.005 else None,
    delta_color="inverse", border=True,
    help="Taxa ponderada: total de evasões ÷ total de matriculados. "
         f"A média simples das taxas por registro seria {formatar_pct(k['taxa_media_simples'])}.",
)
c2.metric("Total de evasões", formatar_numero(k["total_evasoes"]), border=True,
          help=f"De {formatar_numero(k['total_matriculados'])} matrículas no recorte.")
c3.metric("Estado com maior evasão", k["estado"][0], delta=formatar_pct(k["estado"][1]), delta_color="off",
          delta_arrow="off", border=True, help="Primeiro lugar no ranking estadual pela taxa ponderada.")
c4.metric("Região mais vulnerável", k["regiao"][0], delta=formatar_pct(k["regiao"][1]), delta_color="off",
          delta_arrow="off", border=True)

c5, c6, c7, c8 = st.columns(4)
c5.metric("Rede mais afetada", k["rede"][0], delta=formatar_pct(k["rede"][1]), delta_color="off",
          delta_arrow="off", border=True)
c6.metric("Série mais crítica", k["serie"][0], delta=formatar_pct(k["serie"][1]), delta_color="off",
          delta_arrow="off", border=True)
c7.metric("Pública ÷ privada", f"{formatar_numero(k['razao_redes'], 1)}x" if k["razao_redes"] == k["razao_redes"] else "—",
          border=True, help="Quantas vezes a taxa da rede pública supera a da rede privada.")
c8.metric("Registros em risco crítico", formatar_pct(k["pct_critico"], 1), border=True,
          help="Percentual de registros classificados com nível de risco Crítico (taxa ≥ 13%).")

st.subheader("Destaques do recorte")
for frase in destaques(df_filtrado):
    st.markdown(f"- {frase}")

mostrar(linha_temporal(df_filtrado))
interpretacao(
    "A linha tracejada mostra a taxa geral; as linhas coloridas separam as redes. A distância constante "
    "entre a rede pública e a privada ao longo de toda a década indica que a desigualdade entre redes é "
    "estrutural, e não um efeito de anos específicos."
)

st.subheader("Conclusão executiva (resumo)")
st.markdown(
    """
O principal determinante da evasão nesta base é a **rede de ensino**: a rede pública tem taxa cerca de
**2,5 vezes maior** que a privada, em todas as regiões, séries e anos. As diferenças entre estados e
regiões existem, mas são pequenas (cerca de 2 p.p. entre o maior e o menor estado). A evasão recua
lentamente ao longo da década, e renda e acesso à internet não mostram relação linear com o abandono.
"""
)
st.page_link("paginas/conclusao.py", label="Ler a conclusão executiva completa", icon=":material/arrow_forward:")

with st.expander("Como os dados foram tratados", icon=":material/cleaning_services:"):
    r = ctx["relatorio"]
    st.markdown(
        f"""
Fonte: **{ctx['fonte']}** · Estados e mapa: **{ctx['origens']['estados']}** / **{ctx['origens']['malha']}**

| Etapa | Resultado |
|---|---|
| Registros lidos | {r['linhas_originais']} |
| Valores nulos encontrados | {r['valores_nulos']} |
| Duplicados removidos | {r['duplicados_removidos']} |
| Registros inválidos (evasões > matriculados ou matrícula ≤ 0) | {r['registros_invalidos']} |
| Taxas recalculadas (divergiam de evasões ÷ matriculados) | {r['taxas_corrigidas']} |
| Índices fora de 0–100 ajustados | {r['indices_ajustados']} |
| Registros finais | {r['linhas_finais']} |

Atributos criados: período semestral, permanências, quartis de renda/desempenho/internet e
nome oficial + código IBGE de cada UF (via API do IBGE).
"""
    )
