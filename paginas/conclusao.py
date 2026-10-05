import streamlit as st

from src.analise import calcular_kpis, tabela_correlacoes, tendencia_anual
from src.config import ALUNO, DISCIPLINA, PROFESSOR
from src.dados import formatar_numero, formatar_pct, taxa_ponderada
from src.ui import cabecalho, contexto

ctx = contexto()
df = ctx["df"]

cabecalho("Conclusão executiva", "Respostas às perguntas orientadoras com base na série completa 2015–2024 (independe dos filtros).")

k = calcular_kpis(df)
t = tendencia_anual(df)
ufs = taxa_ponderada(df, ["uf", "nome_uf"]).sort_values("taxa_evasao", ascending=False)
regioes = taxa_ponderada(df, "regiao").sort_values("taxa_evasao", ascending=False)
series_pub = taxa_ponderada(df[df["rede_ensino"] == "Pública"], "serie").sort_values("taxa_evasao", ascending=False)
corr = tabela_correlacoes(df).set_index("Fator")["r (geral)"]
top3 = ", ".join(f"{r.nome_uf} ({formatar_pct(r.taxa_evasao)})" for r in ufs.head(3).itertuples())

st.subheader("Respostas às perguntas orientadoras")
respostas = [
    ("Quais estados apresentam maior evasão escolar?",
     f"{top3}. A menor taxa é de {ufs.iloc[-1]['nome_uf']} ({formatar_pct(ufs.iloc[-1]['taxa_evasao'])}). "
     f"A amplitude entre estados é de {formatar_numero(ufs['taxa_evasao'].max() - ufs['taxa_evasao'].min(), 2)} p.p."),
    ("Existem regiões mais vulneráveis?",
     "Sim, mas com diferenças moderadas: "
     + ", ".join(f"{r.regiao} ({formatar_pct(r.taxa_evasao)})" for r in regioes.itertuples())
     + f". A região mais vulnerável supera a menos afetada em "
       f"{formatar_numero(regioes['taxa_evasao'].max() - regioes['taxa_evasao'].min(), 2)} p.p."),
    ("A evasão aumentou ou diminuiu ao longo do tempo?",
     f"Diminuiu levemente: de {formatar_pct(t['tabela']['taxa_evasao'].iloc[0])} em 2015 para "
     f"{formatar_pct(t['tabela']['taxa_evasao'].iloc[-1])} em 2024 (tendência de {formatar_numero(t['inclinacao'], 3)} p.p./ano). "
     f"O pico foi em {t['ano_pico']} e o menor valor em {t['ano_minimo']}; em 2020, ano da pandemia, a taxa voltou a subir."),
    ("Há diferenças entre escolas públicas e privadas?",
     f"Sim, e é a maior diferença da base: {formatar_pct(k['taxa_publica'])} na rede pública contra "
     f"{formatar_pct(k['taxa_privada'])} na privada ({formatar_numero(k['razao_redes'], 1)} vezes maior). "
     "Todos os registros em risco crítico são da rede pública."),
    ("Existe relação entre renda e evasão?",
     f"Não nesta base. A correlação é desprezível (r = {formatar_numero(corr['Renda média familiar'], 3)}) e a taxa "
     "fica praticamente igual em todos os quartis de renda, inclusive dentro de cada rede."),
    ("Quais séries apresentam maior abandono?",
     f"As diferenças entre séries são pequenas (menos de 0,3 p.p. no agregado). Na rede pública, a mais crítica é o "
     f"{series_pub.iloc[0]['serie']} ({formatar_pct(series_pub.iloc[0]['taxa_evasao'])}), na transição do ensino "
     "fundamental para o médio."),
    ("Quais fatores parecem mais associados ao problema?",
     f"A rede de ensino (r = {formatar_numero(corr['Rede pública (1 = sim)'], 2)}) domina todos os outros fatores. "
     "Desempenho, renda e acesso à internet têm correlação abaixo de |0,1|."),
]
for pergunta, resposta in respostas:
    with st.container(border=True):
        st.markdown(f"**{pergunta}**  \n{resposta}")

st.subheader("Síntese")
st.markdown(
    f"""
Entre 2015 e 2024, **{formatar_numero(k['total_evasoes'])} estudantes** abandonaram o ensino médio na base analisada,
uma taxa ponderada de **{formatar_pct(k['taxa_media'])}**. O retrato é de um problema **persistente e concentrado na
rede pública**: a taxa caiu pouco em dez anos, e a desigualdade entre redes é muito maior que a desigualdade entre
estados, regiões ou séries.

**Recomendações**

1. **Priorizar a rede pública**: programas de permanência (busca ativa, bolsas de permanência, tutoria) devem mirar
   primeiro as escolas públicas, onde estão todos os registros críticos.
2. **Atenção ao 1º ano na rede pública**: acolhimento e reforço na entrada do ensino médio.
3. **Monitoramento semestral**: as oscilações entre semestres sugerem choques locais; um painel como este permite
   agir no semestre seguinte, sem esperar o fechamento do ano.
4. **Investigar causas além da renda**: como renda e acesso à internet não explicam a variação, vale coletar
   variáveis de infraestrutura, distância até a escola, trabalho juvenil e gravidez na adolescência.

**Limitações**

- A base é **simulada**: os resultados ilustram o método analítico e não devem ser lidos como estatística oficial.
- Correlação não implica causalidade; a análise é descritiva.
- Cada registro agrega um município, uma rede e uma série; não há dados individuais de estudantes.
"""
)

st.divider()
st.caption(f"{DISCIPLINA} · Professor: {PROFESSOR} · Aluno: {ALUNO}")
