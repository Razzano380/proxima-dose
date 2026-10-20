"""Limpa os CSVs de cobertura vacinal do TabNet e grava no banco SQLite.

Como rodar (na pasta do projeto):
    python scripts/preparar_dados.py

Entrada: data/raw/cobertura_sp_<ano>.csv (exportados do TabNet, sem alteração)
         data/calendario_crianca_2026.csv (transcrito do PDF oficial)
Saída:   data/proxima_dose.db, tabelas "cobertura" e "calendario"
"""
import sqlite3
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parent.parent
RAW = PASTA / "data" / "raw"
BANCO = PASTA / "data" / "proxima_dose.db"

# Vacinas de gestantes não fazem parte do calendário da criança.
VACINAS_FORA = ["Dupla adulto e dTpa gestante", "dTpa gestante"]


def ler_csv(caminho, ano):
    # O TabNet exporta em latin1, separado por ";" e com vírgula decimal.
    df = pd.read_csv(caminho, sep=";", encoding="latin1", decimal=",")

    # A última linha é o "Total" do estado; não é um município.
    df = df[df["Município"] != "Total"]

    # "350010 ADAMANTINA" -> código IBGE "350010" e nome "ADAMANTINA".
    df[["cod_ibge", "municipio"]] = df["Município"].str.split(" ", n=1, expand=True)
    df = df.drop(columns=["Município"])

    # Formato "largo" (uma coluna por vacina) -> formato "longo" (uma linha por vacina).
    df = df.melt(id_vars=["cod_ibge", "municipio"], var_name="vacina", value_name="cobertura")
    df["ano"] = ano
    return df


def main():
    arquivos = sorted(RAW.glob("cobertura_sp_*.csv"))
    tabelas = [ler_csv(a, int(a.stem[-4:])) for a in arquivos]
    df = pd.concat(tabelas, ignore_index=True)

    # Tira espaços duplicados dos nomes ("Tríplice Viral  D1" -> "Tríplice Viral D1").
    df["vacina"] = df["vacina"].str.split().str.join(" ")

    # Vacinas que valem zero em todos os municípios e anos foram descontinuadas.
    zeradas = df.groupby("vacina")["cobertura"].sum()
    zeradas = zeradas[zeradas == 0].index.tolist()
    df = df[~df["vacina"].isin(VACINAS_FORA + zeradas)]

    # Conferências simples: se alguma falhar, o script para com erro.
    assert df["cobertura"].notna().all(), "há coberturas vazias"
    assert (df["cobertura"] >= 0).all(), "há coberturas negativas"
    assert df["cod_ibge"].str.len().eq(6).all(), "código IBGE fora do padrão"

    # Calendário transcrito à mão do PDF oficial (data/raw/calendario_nacional_vacinacao_crianca_2026.pdf).
    calendario = pd.read_csv(PASTA / "data" / "calendario_crianca_2026.csv")

    with sqlite3.connect(BANCO) as con:
        df.to_sql("cobertura", con, if_exists="replace", index=False)
        calendario.to_sql("calendario", con, if_exists="replace", index=False)

    print(f"Anos: {sorted(df['ano'].unique())}")
    print(f"Municípios: {df['cod_ibge'].nunique()}")
    print(f"Vacinas mantidas ({df['vacina'].nunique()}): {sorted(df['vacina'].unique())}")
    print(f"Vacinas removidas: {VACINAS_FORA + zeradas}")
    print(f"Linhas gravadas em {BANCO.name}: {len(df)}")


if __name__ == "__main__":
    main()
