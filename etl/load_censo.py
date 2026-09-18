#!/usr/bin/env python3
"""Pré-processamento e carga do Censo Escolar 2022 (INEP) no PostgreSQL."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, text

ROOT = Path(os.environ.get("CENSO_ROOT", "/work"))
RAW_CSV = ROOT / "data/raw/extracted/microdados_ed_basica_2022.csv"
MUNICIPIOS = ROOT / "data/raw/ibge/municipios.csv"
OUT_DIR = ROOT / "data/processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PG_DSN = os.environ.get(
    "PG_DSN",
    "postgresql://superset:superset@host.containers.internal:5432/postgres",
)
DB_NAME = "censo_escolar"
DB_URL = os.environ.get(
    "CENSO_DB_URL",
    "postgresql://superset:superset@host.containers.internal:5432/censo_escolar",
)

MAP_DEPENDENCIA = {1: "Federal", 2: "Estadual", 3: "Municipal", 4: "Privada"}
MAP_LOCALIZACAO = {1: "Urbana", 2: "Rural"}
MAP_SITUACAO = {1: "Em atividade", 2: "Paralisada", 3: "Extinta"}
MAP_LOC_DIF = {
    0: "Não está em área diferenciada",
    1: "Área de assentamento",
    2: "Terra indígena",
    3: "Comunidade quilombola",
    4: "Unidade de uso sustentável",
    5: "Unidade de uso sustentável em terra indígena",
    6: "Unidade de uso sustentável em comunidade quilombola",
    7: "Terra indígena e comunidade quilombola",
    8: "Assentamento e terra indígena",
}

KEEP_COLS = [
    "NU_ANO_CENSO",
    "NO_REGIAO",
    "CO_REGIAO",
    "NO_UF",
    "SG_UF",
    "CO_UF",
    "NO_MUNICIPIO",
    "CO_MUNICIPIO",
    "NO_ENTIDADE",
    "CO_ENTIDADE",
    "TP_DEPENDENCIA",
    "TP_LOCALIZACAO",
    "TP_LOCALIZACAO_DIFERENCIADA",
    "TP_SITUACAO_FUNCIONAMENTO",
    "IN_AGUA_POTAVEL",
    "IN_AGUA_INEXISTENTE",
    "IN_ENERGIA_REDE_PUBLICA",
    "IN_ENERGIA_INEXISTENTE",
    "IN_ESGOTO_REDE_PUBLICA",
    "IN_ESGOTO_INEXISTENTE",
    "IN_BIBLIOTECA",
    "IN_BIBLIOTECA_SALA_LEITURA",
    "IN_LABORATORIO_INFORMATICA",
    "IN_QUADRA_ESPORTES",
    "IN_SALA_ATENDIMENTO_ESPECIAL",
    "IN_BANHEIRO_PNE",
    "IN_DEPENDENCIAS_PNE",
    "IN_ACESSIBILIDADE_RAMPAS",
    "IN_ACESSIBILIDADE_CORRIMAO",
    "IN_ACESSIBILIDADE_ELEVADOR",
    "IN_ACESSIBILIDADE_PISOS_TATEIS",
    "IN_ACESSIBILIDADE_VAO_LIVRE",
    "IN_ACESSIBILIDADE_INEXISTENTE",
    "IN_COMPUTADOR",
    "IN_INTERNET",
    "IN_INTERNET_ALUNOS",
    "IN_INTERNET_APRENDIZAGEM",
    "IN_BANDA_LARGA",
    "QT_DESKTOP_ALUNO",
    "QT_COMP_PORTATIL_ALUNO",
    "QT_TABLET_ALUNO",
    "IN_INF",
    "IN_FUND",
    "IN_MED",
    "IN_EJA",
    "IN_ESP",
    "IN_ESP_CC",
    "IN_ESP_CE",
    "QT_MAT_BAS",
    "QT_MAT_INF",
    "QT_MAT_FUND",
    "QT_MAT_MED",
    "QT_MAT_EJA",
    "QT_MAT_ESP",
    "QT_MAT_ESP_CC",
    "QT_MAT_ESP_CE",
    "QT_MAT_BAS_FEM",
    "QT_MAT_BAS_MASC",
    "QT_MAT_BAS_BRANCA",
    "QT_MAT_BAS_PRETA",
    "QT_MAT_BAS_PARDA",
    "QT_MAT_BAS_AMARELA",
    "QT_MAT_BAS_INDIGENA",
    "QT_DOC_BAS",
    "QT_DOC_ESP",
    "QT_TUR_BAS",
]


def to_bin(series: pd.Series) -> pd.Series:
    """Converte flags INEP (0/1) para 0/1; qualquer outro valor vira nulo."""
    s = pd.to_numeric(series, errors="coerce")
    s = s.where(s.isin([0, 1]), np.nan)
    return s.astype("Int64")


def to_nonneg_int(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    s = s.where(s >= 0, np.nan)
    return s.round().astype("Int64")


def ensure_database() -> None:
    conn = psycopg2.connect(PG_DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
            print(f"created database {DB_NAME}")
        else:
            print(f"database {DB_NAME} already exists")
    conn.close()


def load_raw() -> pd.DataFrame:
    print("reading", RAW_CSV)
    df = pd.read_csv(
        RAW_CSV,
        sep=";",
        encoding="latin-1",
        usecols=KEEP_COLS,
        dtype=str,
        low_memory=False,
    )
    print("raw rows", len(df), "cols", df.shape[1])
    return df


def transform(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    qa: dict = {"n_bruto": int(len(df))}

    df["co_entidade"] = to_nonneg_int(df["CO_ENTIDADE"])
    df["nu_ano_censo"] = to_nonneg_int(df["NU_ANO_CENSO"])
    df["co_municipio"] = to_nonneg_int(df["CO_MUNICIPIO"])
    df["co_uf"] = to_nonneg_int(df["CO_UF"])
    df["co_regiao"] = to_nonneg_int(df["CO_REGIAO"])
    df["tp_dependencia"] = to_nonneg_int(df["TP_DEPENDENCIA"])
    df["tp_localizacao"] = to_nonneg_int(df["TP_LOCALIZACAO"])
    df["tp_localizacao_diferenciada"] = to_nonneg_int(df["TP_LOCALIZACAO_DIFERENCIADA"])
    df["tp_situacao_funcionamento"] = to_nonneg_int(df["TP_SITUACAO_FUNCIONAMENTO"])

    qa["sem_codigo_escola"] = int(df["co_entidade"].isna().sum())
    qa["codigo_escola_duplicado"] = int(df["co_entidade"].duplicated().sum())
    df = df.dropna(subset=["co_entidade"]).drop_duplicates(subset=["co_entidade"])

    invalid_dep = ~df["tp_dependencia"].isin(list(MAP_DEPENDENCIA))
    invalid_loc = ~df["tp_localizacao"].isin(list(MAP_LOCALIZACAO))
    invalid_sit = ~df["tp_situacao_funcionamento"].isin(list(MAP_SITUACAO))
    qa["dependencia_invalida"] = int(invalid_dep.sum())
    qa["localizacao_invalida"] = int(invalid_loc.sum())
    qa["situacao_invalida"] = int(invalid_sit.sum())
    df.loc[invalid_dep, "tp_dependencia"] = pd.NA
    df.loc[invalid_loc, "tp_localizacao"] = pd.NA
    df.loc[invalid_sit, "tp_situacao_funcionamento"] = pd.NA

    bin_cols = [c for c in KEEP_COLS if c.startswith("IN_")]
    qty_cols = [c for c in KEEP_COLS if c.startswith("QT_")]
    for col in bin_cols:
        df[col.lower()] = to_bin(df[col])
    for col in qty_cols:
        df[col.lower()] = to_nonneg_int(df[col])

    # Inconsistência: banda larga sem internet.
    banda_sem_net = (df["in_internet"] == 0) & (df["in_banda_larga"] == 1)
    qa["banda_larga_sem_internet_corrigido"] = int(banda_sem_net.sum())
    df.loc[banda_sem_net, "in_banda_larga"] = 0

    # Inconsistência: "acessibilidade inexistente" junto com item de acessibilidade.
    acess_items = [
        "in_acessibilidade_rampas",
        "in_acessibilidade_corrimao",
        "in_acessibilidade_elevador",
        "in_acessibilidade_pisos_tateis",
        "in_acessibilidade_vao_livre",
        "in_banheiro_pne",
        "in_dependencias_pne",
    ]
    any_acess = df[acess_items].fillna(0).sum(axis=1) > 0
    contradicao = (df["in_acessibilidade_inexistente"] == 1) & any_acess
    qa["acessibilidade_contraditoria_corrigida"] = int(contradicao.sum())
    df.loc[contradicao, "in_acessibilidade_inexistente"] = 0

    df["no_regiao"] = df["NO_REGIAO"].str.strip()
    df["no_uf"] = df["NO_UF"].str.strip()
    df["sg_uf"] = df["SG_UF"].str.strip().str.upper()
    df["no_municipio"] = df["NO_MUNICIPIO"].str.strip()
    df["no_escola"] = df["NO_ENTIDADE"].str.strip()
    df["no_dependencia"] = df["tp_dependencia"].map(MAP_DEPENDENCIA)
    df["no_localizacao"] = df["tp_localizacao"].map(MAP_LOCALIZACAO)
    df["no_situacao"] = df["tp_situacao_funcionamento"].map(MAP_SITUACAO)
    df["no_localizacao_diferenciada"] = (
        df["tp_localizacao_diferenciada"].map(MAP_LOC_DIF).fillna("Não informado")
    )

    df["escola_ativa"] = (df["tp_situacao_funcionamento"] == 1).astype("Int64")
    df["qt_dispositivos_aluno"] = (
        df["qt_desktop_aluno"].fillna(0)
        + df["qt_comp_portatil_aluno"].fillna(0)
        + df["qt_tablet_aluno"].fillna(0)
    ).astype("Int64")
    df["alunos_por_docente"] = np.where(
        (df["escola_ativa"] == 1) & (df["qt_doc_bas"].fillna(0) > 0),
        df["qt_mat_bas"] / df["qt_doc_bas"],
        np.nan,
    )
    df["alunos_por_dispositivo"] = np.where(
        (df["escola_ativa"] == 1) & (df["qt_dispositivos_aluno"] > 0),
        df["qt_mat_bas"] / df["qt_dispositivos_aluno"],
        np.nan,
    )

    # Indicador inovador: inclusão sem condição de acessibilidade.
    # Matrículas de educação especial em escola ativa sem nenhum recurso de acessibilidade.
    df["flag_inclusao_sem_acessibilidade"] = (
        (df["escola_ativa"] == 1)
        & (df["qt_mat_esp"].fillna(0) > 0)
        & (
            (df["in_acessibilidade_inexistente"] == 1)
            | (
                df[acess_items].fillna(0).sum(axis=1).eq(0)
                & df["in_sala_atendimento_especial"].fillna(0).eq(0)
            )
        )
    ).astype("Int64")
    df["qt_mat_esp_sem_acessibilidade"] = (
        df["qt_mat_esp"].fillna(0).where(df["flag_inclusao_sem_acessibilidade"] == 1, 0)
    ).astype("Int64")

    df["flag_deserto_digital"] = (
        (df["escola_ativa"] == 1)
        & (df["qt_mat_bas"].fillna(0) > 0)
        & (df["in_internet_aprendizagem"].fillna(0) == 0)
        & (df["in_internet"].fillna(0) == 0)
    ).astype("Int64")

    df["indice_infra_basica"] = (
        df[["in_agua_potavel", "in_energia_rede_publica"]].fillna(0).sum(axis=1)
        + (1 - df["in_esgoto_inexistente"].fillna(1)).clip(lower=0)
    ) / 3.0
    df.loc[df["escola_ativa"] != 1, "indice_infra_basica"] = np.nan

    df["indice_prontidao_digital"] = (
        df[["in_internet_aprendizagem", "in_banda_larga", "in_laboratorio_informatica"]]
        .fillna(0)
        .mean(axis=1)
    )
    df.loc[df["escola_ativa"] != 1, "indice_prontidao_digital"] = np.nan

    mun = pd.read_csv(MUNICIPIOS)
    mun = mun.rename(
        columns={
            "codigo_ibge": "co_municipio",
            "nome": "no_municipio_ibge",
            "latitude": "latitude",
            "longitude": "longitude",
            "codigo_uf": "co_uf_ibge",
            "siafi_id": "siafi_id",
            "ddd": "ddd",
            "fuso_horario": "fuso_horario",
        }
    )
    df = df.merge(
        mun[["co_municipio", "latitude", "longitude"]],
        on="co_municipio",
        how="left",
    )
    qa["escolas_sem_coordenada_municipio"] = int(df["latitude"].isna().sum())

    out_cols = [
        "nu_ano_censo",
        "co_entidade",
        "no_escola",
        "no_regiao",
        "co_regiao",
        "no_uf",
        "sg_uf",
        "co_uf",
        "no_municipio",
        "co_municipio",
        "latitude",
        "longitude",
        "tp_dependencia",
        "no_dependencia",
        "tp_localizacao",
        "no_localizacao",
        "tp_localizacao_diferenciada",
        "no_localizacao_diferenciada",
        "tp_situacao_funcionamento",
        "no_situacao",
        "escola_ativa",
        "in_agua_potavel",
        "in_agua_inexistente",
        "in_energia_rede_publica",
        "in_energia_inexistente",
        "in_esgoto_rede_publica",
        "in_esgoto_inexistente",
        "in_biblioteca",
        "in_biblioteca_sala_leitura",
        "in_laboratorio_informatica",
        "in_quadra_esportes",
        "in_sala_atendimento_especial",
        "in_banheiro_pne",
        "in_dependencias_pne",
        "in_acessibilidade_rampas",
        "in_acessibilidade_corrimao",
        "in_acessibilidade_elevador",
        "in_acessibilidade_pisos_tateis",
        "in_acessibilidade_vao_livre",
        "in_acessibilidade_inexistente",
        "in_computador",
        "in_internet",
        "in_internet_alunos",
        "in_internet_aprendizagem",
        "in_banda_larga",
        "qt_desktop_aluno",
        "qt_comp_portatil_aluno",
        "qt_tablet_aluno",
        "qt_dispositivos_aluno",
        "in_inf",
        "in_fund",
        "in_med",
        "in_eja",
        "in_esp",
        "in_esp_cc",
        "in_esp_ce",
        "qt_mat_bas",
        "qt_mat_inf",
        "qt_mat_fund",
        "qt_mat_med",
        "qt_mat_eja",
        "qt_mat_esp",
        "qt_mat_esp_cc",
        "qt_mat_esp_ce",
        "qt_mat_bas_fem",
        "qt_mat_bas_masc",
        "qt_mat_bas_branca",
        "qt_mat_bas_preta",
        "qt_mat_bas_parda",
        "qt_mat_bas_amarela",
        "qt_mat_bas_indigena",
        "qt_doc_bas",
        "qt_doc_esp",
        "qt_tur_bas",
        "alunos_por_docente",
        "alunos_por_dispositivo",
        "flag_inclusao_sem_acessibilidade",
        "qt_mat_esp_sem_acessibilidade",
        "flag_deserto_digital",
        "indice_infra_basica",
        "indice_prontidao_digital",
    ]
    escolas = df[out_cols].copy()

    ativas = escolas[escolas["escola_ativa"] == 1]
    qa["n_final"] = int(len(escolas))
    qa["n_ativas"] = int(len(ativas))
    qa["n_paralisadas_ou_extintas"] = int((escolas["escola_ativa"] != 1).sum())
    qa["matriculas_basicas_ativas"] = int(ativas["qt_mat_bas"].fillna(0).sum())
    qa["docentes_basicos_ativos"] = int(ativas["qt_doc_bas"].fillna(0).sum())
    qa["escolas_inclusao_sem_acessibilidade"] = int(
        ativas["flag_inclusao_sem_acessibilidade"].fillna(0).sum()
    )
    qa["matriculas_pcd_sem_acessibilidade"] = int(
        ativas["qt_mat_esp_sem_acessibilidade"].fillna(0).sum()
    )
    qa["pct_nulos_internet_ativas"] = float(ativas["in_internet"].isna().mean())
    qa["pct_nulos_matricula_ativas"] = float(ativas["qt_mat_bas"].isna().mean())

    ativas_flags = ativas.copy()
    ativas_flags["is_publica"] = ativas_flags["tp_dependencia"].isin([1, 2, 3]).astype(int)
    ativas_flags["is_rural"] = (ativas_flags["tp_localizacao"] == 2).astype(int)
    mun_agg = (
        ativas_flags.groupby(
            ["co_municipio", "no_municipio", "sg_uf", "no_uf", "no_regiao", "latitude", "longitude"],
            dropna=False,
        )
        .agg(
            n_escolas=("co_entidade", "count"),
            n_escolas_publicas=("is_publica", "sum"),
            n_escolas_rurais=("is_rural", "sum"),
            qt_matriculas=("qt_mat_bas", "sum"),
            qt_docentes=("qt_doc_bas", "sum"),
            qt_matriculas_esp=("qt_mat_esp", "sum"),
            n_com_internet=("in_internet", "sum"),
            n_com_banda_larga=("in_banda_larga", "sum"),
            n_deserto_digital=("flag_deserto_digital", "sum"),
            n_inclusao_sem_acessibilidade=("flag_inclusao_sem_acessibilidade", "sum"),
            qt_mat_esp_sem_acessibilidade=("qt_mat_esp_sem_acessibilidade", "sum"),
        )
        .reset_index()
    )
    mun_agg["pct_escolas_com_internet"] = np.where(
        mun_agg["n_escolas"] > 0,
        mun_agg["n_com_internet"] / mun_agg["n_escolas"],
        np.nan,
    )
    mun_agg["pct_inclusao_sem_acessibilidade"] = np.where(
        mun_agg["n_escolas"] > 0,
        mun_agg["n_inclusao_sem_acessibilidade"] / mun_agg["n_escolas"],
        np.nan,
    )

    uf_agg = (
        ativas.groupby(["co_uf", "sg_uf", "no_uf", "no_regiao"], dropna=False)
        .agg(
            n_escolas=("co_entidade", "count"),
            n_municipios=("co_municipio", "nunique"),
            qt_matriculas=("qt_mat_bas", "sum"),
            qt_docentes=("qt_doc_bas", "sum"),
            qt_matriculas_esp=("qt_mat_esp", "sum"),
            n_com_internet=("in_internet", "sum"),
            n_deserto_digital=("flag_deserto_digital", "sum"),
            n_inclusao_sem_acessibilidade=("flag_inclusao_sem_acessibilidade", "sum"),
            qt_mat_esp_sem_acessibilidade=("qt_mat_esp_sem_acessibilidade", "sum"),
            media_alunos_por_docente=("alunos_por_docente", "mean"),
        )
        .reset_index()
    )
    uf_agg["pct_escolas_com_internet"] = uf_agg["n_com_internet"] / uf_agg["n_escolas"]
    uf_agg["pct_inclusao_sem_acessibilidade"] = (
        uf_agg["n_inclusao_sem_acessibilidade"] / uf_agg["n_escolas"]
    )
    uf_agg["iso_uf"] = "BR-" + uf_agg["sg_uf"].astype(str)
    uf_agg["matriculas_por_escola"] = uf_agg["qt_matriculas"] / uf_agg["n_escolas"]
    uf_agg["docentes_por_escola"] = uf_agg["qt_docentes"] / uf_agg["n_escolas"]
    uf_agg["taxa_pcd_sem_acess"] = np.where(
        uf_agg["qt_matriculas_esp"] > 0,
        uf_agg["qt_mat_esp_sem_acessibilidade"] / uf_agg["qt_matriculas_esp"],
        np.nan,
    )
    uf_agg["pcd_sem_acess_por_mil"] = np.where(
        uf_agg["qt_matriculas"] > 0,
        1000.0 * uf_agg["qt_mat_esp_sem_acessibilidade"] / uf_agg["qt_matriculas"],
        np.nan,
    )
    mun_agg["matriculas_por_escola"] = np.where(
        mun_agg["n_escolas"] > 0,
        mun_agg["qt_matriculas"] / mun_agg["n_escolas"],
        np.nan,
    )
    mun_agg["pcd_sem_acess_por_mil"] = np.where(
        mun_agg["qt_matriculas"] > 0,
        1000.0 * mun_agg["qt_mat_esp_sem_acessibilidade"] / mun_agg["qt_matriculas"],
        np.nan,
    )

    uf_dep_agg = (
        ativas.groupby(["sg_uf", "no_uf", "no_regiao", "no_dependencia"], dropna=False)
        .agg(
            n_escolas=("co_entidade", "count"),
            qt_matriculas=("qt_mat_bas", "sum"),
            qt_docentes=("qt_doc_bas", "sum"),
            qt_matriculas_esp=("qt_mat_esp", "sum"),
            n_inclusao_sem_acessibilidade=("flag_inclusao_sem_acessibilidade", "sum"),
            qt_mat_esp_sem_acessibilidade=("qt_mat_esp_sem_acessibilidade", "sum"),
        )
        .reset_index()
    )
    tot = uf_dep_agg.groupby("sg_uf")[["n_escolas", "qt_matriculas"]].transform("sum")
    uf_dep_agg["pct_escolas_na_uf"] = uf_dep_agg["n_escolas"] / tot["n_escolas"]
    uf_dep_agg["pct_matriculas_na_uf"] = uf_dep_agg["qt_matriculas"] / tot["qt_matriculas"]
    uf_dep_agg["matriculas_por_escola"] = np.where(
        uf_dep_agg["n_escolas"] > 0,
        uf_dep_agg["qt_matriculas"] / uf_dep_agg["n_escolas"],
        np.nan,
    )
    uf_dep_agg["alunos_por_docente"] = np.where(
        uf_dep_agg["qt_docentes"] > 0,
        uf_dep_agg["qt_matriculas"] / uf_dep_agg["qt_docentes"],
        np.nan,
    )
    uf_dep_agg["pct_eisa"] = np.where(
        uf_dep_agg["n_escolas"] > 0,
        uf_dep_agg["n_inclusao_sem_acessibilidade"] / uf_dep_agg["n_escolas"],
        np.nan,
    )

    dep_agg = (
        ativas.groupby(["tp_dependencia", "no_dependencia"], dropna=False)
        .agg(
            n_escolas=("co_entidade", "count"),
            qt_matriculas=("qt_mat_bas", "sum"),
            qt_docentes=("qt_doc_bas", "sum"),
            n_inclusao_sem_acessibilidade=("flag_inclusao_sem_acessibilidade", "sum"),
            qt_mat_esp_sem_acessibilidade=("qt_mat_esp_sem_acessibilidade", "sum"),
        )
        .reset_index()
    )

    return escolas, mun_agg, uf_agg, dep_agg, uf_dep_agg, qa


def write_outputs(escolas, mun_agg, uf_agg, dep_agg, uf_dep_agg, qa) -> None:
    escolas.to_parquet(OUT_DIR / "fato_escola.parquet", index=False)
    mun_agg.to_parquet(OUT_DIR / "agg_municipio.parquet", index=False)
    uf_agg.to_parquet(OUT_DIR / "agg_uf.parquet", index=False)
    dep_agg.to_csv(OUT_DIR / "agg_dependencia.csv", index=False)
    uf_dep_agg.to_csv(OUT_DIR / "agg_uf_dependencia.csv", index=False)
    (OUT_DIR / "qualidade_etl.json").write_text(
        json.dumps(qa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    desc = escolas[escolas["escola_ativa"] == 1][
        [
            "qt_mat_bas",
            "qt_doc_bas",
            "qt_mat_esp",
            "alunos_por_docente",
            "indice_infra_basica",
            "indice_prontidao_digital",
            "qt_mat_esp_sem_acessibilidade",
        ]
    ].describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.99])
    desc.to_csv(OUT_DIR / "estatisticas_descritivas.csv")
    print("wrote processed files to", OUT_DIR)


def load_postgres(escolas, mun_agg, uf_agg, dep_agg, uf_dep_agg, qa) -> None:
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS qualidade_etl"))
        conn.execute(text("DROP TABLE IF EXISTS agg_uf_dependencia"))
        conn.execute(text("DROP TABLE IF EXISTS agg_dependencia"))
        conn.execute(text("DROP TABLE IF EXISTS agg_uf"))
        conn.execute(text("DROP TABLE IF EXISTS agg_municipio"))
        conn.execute(text("DROP TABLE IF EXISTS fato_escola"))

    escolas.to_sql("fato_escola", engine, index=False, if_exists="replace", chunksize=5000)
    mun_agg.to_sql("agg_municipio", engine, index=False, if_exists="replace", chunksize=2000)
    uf_agg.to_sql("agg_uf", engine, index=False, if_exists="replace")
    dep_agg.to_sql("agg_dependencia", engine, index=False, if_exists="replace")
    uf_dep_agg.to_sql("agg_uf_dependencia", engine, index=False, if_exists="replace")
    pd.DataFrame([qa]).to_sql("qualidade_etl", engine, index=False, if_exists="replace")

    with engine.begin() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_escola_uf ON fato_escola (sg_uf)"))
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_escola_mun ON fato_escola (co_municipio)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_escola_dep ON fato_escola (tp_dependencia)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_escola_ativa ON fato_escola (escola_ativa)")
        )
        conn.execute(
            text(
                """
                CREATE OR REPLACE VIEW v_escola_ativa AS
                SELECT * FROM fato_escola WHERE escola_ativa = 1
                """
            )
        )
        n = conn.execute(text("SELECT COUNT(*) FROM fato_escola")).scalar()
        n_mun = conn.execute(text("SELECT COUNT(*) FROM agg_municipio")).scalar()
        print(f"loaded fato_escola={n} agg_municipio={n_mun}")


def main() -> None:
    ensure_database()
    raw = load_raw()
    escolas, mun_agg, uf_agg, dep_agg, uf_dep_agg, qa = transform(raw)
    print("quality", json.dumps(qa, ensure_ascii=False, indent=2))
    write_outputs(escolas, mun_agg, uf_agg, dep_agg, uf_dep_agg, qa)
    load_postgres(escolas, mun_agg, uf_agg, dep_agg, uf_dep_agg, qa)
    print("done")


if __name__ == "__main__":
    main()
