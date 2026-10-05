"""Constantes compartilhadas pelo dashboard: identificação, caminhos e paleta."""

from pathlib import Path

# ---------------- Identificação acadêmica ----------------
TITULO = "Evasão Escolar no Ensino Médio Brasileiro (2015–2024)"
DISCIPLINA = "Linguagem de Programação — Análise e Visualização de Dados com Python"
PROFESSOR = "Alexandre Neves Louzada"
ALUNO = "Enzo Ribas Torres"
AVALIACAO = "Projeto G1 — Tema 10"

# ---------------- Caminhos ----------------
BASE_DIR = Path(__file__).resolve().parent.parent
DIR_DADOS = BASE_DIR / "dados"
CAMINHO_CSV = DIR_DADOS / "simulacao_evasao_escolar_brasil.csv"
CAMINHO_ESTADOS = DIR_DADOS / "ibge_estados.json"
CAMINHO_MALHA = DIR_DADOS / "malha_ufs_brasil.geojson"
CAMINHO_BANCO = BASE_DIR / "database" / "evasao_escolar.sqlite"

# ---------------- Ordens categóricas ----------------
ORDEM_REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
ORDEM_SERIES = ["1º ano", "2º ano", "3º ano"]
ORDEM_REDES = ["Pública", "Privada"]
ORDEM_RISCO = ["Baixo", "Médio", "Alto", "Crítico"]

# ---------------- Paleta ----------------
# Cores categóricas em ordem fixa: a cor acompanha a entidade, nunca a posição no ranking.
CORES_REDE = {"Pública": "#2a78d6", "Privada": "#eb6834"}
CORES_REGIAO = {
    "Norte": "#2a78d6",
    "Nordeste": "#eb6834",
    "Centro-Oeste": "#1baf7a",
    "Sudeste": "#eda100",
    "Sul": "#e87ba4",
}
# Nível de risco é um status ordinal: sempre exibido junto do rótulo, nunca só pela cor.
CORES_RISCO = {"Baixo": "#0ca30c", "Médio": "#fab219", "Alto": "#ec835a", "Crítico": "#d03b3b"}
COR_DESTAQUE = "#2a78d6"
COR_NEUTRA = "#c3c2b7"
ESCALA_SEQUENCIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

TINTA_PRIMARIA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_SUAVE = "#898781"
GRADE = "#e1e0d9"
SUPERFICIE = "#fcfcfb"
