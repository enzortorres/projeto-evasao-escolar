"""Persistência em SQLite com modelagem relacional via SQLAlchemy ORM.

Esquema (normalizado a partir do CSV + API do IBGE):

    regioes 1──N estados 1──N municipios 1──N indicadores_evasao
"""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import Date, Float, ForeignKey, Integer, String, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from src.config import CAMINHO_BANCO


class Base(DeclarativeBase):
    pass


class Regiao(Base):
    __tablename__ = "regioes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(20), unique=True)
    estados: Mapped[list["Estado"]] = relationship(back_populates="regiao")


class Estado(Base):
    __tablename__ = "estados"

    uf: Mapped[str] = mapped_column(String(2), primary_key=True)
    nome: Mapped[str] = mapped_column(String(40))
    codigo_ibge: Mapped[int] = mapped_column(Integer, unique=True)
    regiao_id: Mapped[int] = mapped_column(ForeignKey("regioes.id"))
    regiao: Mapped[Regiao] = relationship(back_populates="estados")
    municipios: Mapped[list["Municipio"]] = relationship(back_populates="estado")


class Municipio(Base):
    __tablename__ = "municipios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(60))
    uf: Mapped[str] = mapped_column(ForeignKey("estados.uf"))
    estado: Mapped[Estado] = relationship(back_populates="municipios")
    indicadores: Mapped[list["IndicadorEvasao"]] = relationship(back_populates="municipio")


class IndicadorEvasao(Base):
    __tablename__ = "indicadores_evasao"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    municipio_id: Mapped[int] = mapped_column(ForeignKey("municipios.id"), index=True)
    ano: Mapped[int] = mapped_column(Integer, index=True)
    semestre: Mapped[int] = mapped_column(Integer)
    data: Mapped[date] = mapped_column(Date)
    rede_ensino: Mapped[str] = mapped_column(String(10))
    serie: Mapped[str] = mapped_column(String(10))
    matriculados: Mapped[int] = mapped_column(Integer)
    evasoes: Mapped[int] = mapped_column(Integer)
    taxa_evasao: Mapped[float] = mapped_column(Float)
    renda_media_familiar: Mapped[float] = mapped_column(Float)
    indice_desempenho: Mapped[float] = mapped_column(Float)
    acesso_internet: Mapped[float] = mapped_column(Float)
    nivel_risco: Mapped[str] = mapped_column(String(10))
    municipio: Mapped[Municipio] = relationship(back_populates="indicadores")


def construir_banco(df: pd.DataFrame, estados: pd.DataFrame) -> Engine:
    """Recria o banco SQLite a partir da base tratada e da tabela de estados do IBGE."""
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    engine = create_engine(f"sqlite:///{CAMINHO_BANCO.as_posix()}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    estados = estados[estados["uf"].isin(df["uf"].unique())]
    with Session(engine) as sessao:
        regioes = {nome: Regiao(nome=nome) for nome in sorted(estados["regiao"].unique())}
        sessao.add_all(regioes.values())

        for linha in estados.itertuples():
            sessao.add(Estado(uf=linha.uf, nome=linha.nome, codigo_ibge=int(linha.codigo_ibge), regiao=regioes[linha.regiao]))

        municipios = {}
        for uf, nome in df[["uf", "municipio"]].drop_duplicates().itertuples(index=False):
            municipios[(uf, nome)] = Municipio(nome=nome, uf=uf)
        sessao.add_all(municipios.values())
        sessao.flush()

        sessao.add_all(
            IndicadorEvasao(
                municipio_id=municipios[(r.uf, r.municipio)].id,
                ano=int(r.ano),
                semestre=int(r.semestre),
                data=r.data.date(),
                rede_ensino=str(r.rede_ensino),
                serie=str(r.serie),
                matriculados=int(r.matriculados),
                evasoes=int(r.evasoes),
                taxa_evasao=float(r.taxa_evasao),
                renda_media_familiar=float(r.renda_media_familiar),
                indice_desempenho=float(r.indice_desempenho),
                acesso_internet=float(r.acesso_internet),
                nivel_risco=str(r.nivel_risco),
            )
            for r in df.itertuples()
        )
        sessao.commit()
    return engine


def conectar_somente_leitura() -> Engine:
    """Conexão read-only: consultas livres digitadas no dashboard não conseguem alterar o banco."""
    return create_engine(f"sqlite:///file:{CAMINHO_BANCO.as_posix()}?mode=ro&uri=true")


CONSULTAS = {
    "Taxa de evasão por região (JOIN entre 4 tabelas)": """
SELECT r.nome AS regiao,
       SUM(i.evasoes) AS evasoes,
       SUM(i.matriculados) AS matriculados,
       ROUND(100.0 * SUM(i.evasoes) / SUM(i.matriculados), 2) AS taxa_evasao
FROM indicadores_evasao i
JOIN municipios m ON m.id = i.municipio_id
JOIN estados e    ON e.uf = m.uf
JOIN regioes r    ON r.id = e.regiao_id
GROUP BY r.nome
ORDER BY taxa_evasao DESC""",
    "Ranking de estados": """
SELECT e.uf, e.nome AS estado,
       ROUND(100.0 * SUM(i.evasoes) / SUM(i.matriculados), 2) AS taxa_evasao,
       SUM(i.evasoes) AS evasoes
FROM indicadores_evasao i
JOIN municipios m ON m.id = i.municipio_id
JOIN estados e    ON e.uf = m.uf
GROUP BY e.uf, e.nome
ORDER BY taxa_evasao DESC""",
    "Pública x privada por ano": """
SELECT ano,
       ROUND(100.0 * SUM(CASE WHEN rede_ensino = 'Pública' THEN evasoes END)
                   / SUM(CASE WHEN rede_ensino = 'Pública' THEN matriculados END), 2) AS taxa_publica,
       ROUND(100.0 * SUM(CASE WHEN rede_ensino = 'Privada' THEN evasoes END)
                   / SUM(CASE WHEN rede_ensino = 'Privada' THEN matriculados END), 2) AS taxa_privada
FROM indicadores_evasao
GROUP BY ano
ORDER BY ano""",
    "Municípios com mais registros críticos": """
SELECT m.nome AS municipio, m.uf,
       COUNT(*) AS registros_criticos,
       ROUND(AVG(i.taxa_evasao), 2) AS taxa_media
FROM indicadores_evasao i
JOIN municipios m ON m.id = i.municipio_id
WHERE i.nivel_risco = 'Crítico'
GROUP BY m.nome, m.uf
ORDER BY registros_criticos DESC, taxa_media DESC
LIMIT 10""",
    "Evasão por série e rede": """
SELECT serie, rede_ensino,
       ROUND(100.0 * SUM(evasoes) / SUM(matriculados), 2) AS taxa_evasao,
       SUM(evasoes) AS evasoes
FROM indicadores_evasao
GROUP BY serie, rede_ensino
ORDER BY serie, rede_ensino""",
}


def executar_consulta(engine: Engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conexao:
        return pd.read_sql(text(sql), conexao)
