"""Testes da regra das doses. Rodar com: python -m pytest tests  (ou: python tests/test_regras.py)"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PASTA / "app"))
from regras import classificar, idade_em_meses  # noqa: E402

CALENDARIO = pd.read_csv(PASTA / "data" / "calendario_crianca_2026.csv")


def status_de(df, vacina, dose):
    return df[(df["vacina"] == vacina) & (df["dose"] == dose)]["status"].iloc[0]


def test_idade_em_meses():
    assert idade_em_meses(date(2026, 1, 10), date(2026, 3, 9)) == 1
    assert idade_em_meses(date(2026, 1, 10), date(2026, 3, 10)) == 2
    assert idade_em_meses(date(2026, 1, 31), date(2026, 2, 28)) == 0


def test_recem_nascido():
    df = classificar(date(2026, 10, 20), date(2026, 10, 20), CALENDARIO)
    assert status_de(df, "BCG", "dose única") == "conferir na caderneta"
    assert status_de(df, "penta (DTP+Hib+HB)", "1ª dose") == "próxima"
    assert status_de(df, "tríplice viral SCR", "1ª dose") == "futura"


def test_crianca_de_1_ano_e_meio():
    df = classificar(date(2025, 4, 1), date(2026, 10, 20), CALENDARIO)  # 18 meses
    assert status_de(df, "tríplice viral SCR", "2ª dose") == "conferir na caderneta"
    assert status_de(df, "rotavírus humano", "1ª dose") == "prazo encerrado"
    assert status_de(df, "rotavírus humano", "2ª dose") == "conferir na caderneta"
    assert status_de(df, "DTP", "2ª dose reforço") == "futura"


def test_data_prevista():
    df = classificar(date(2026, 8, 15), date(2026, 10, 20), CALENDARIO)
    assert df[df["vacina"] == "meningocócica C"]["data_prevista"].iloc[0] == date(2026, 11, 15)


def test_situacoes_especiais_ficam_fora():
    df = classificar(date(2026, 1, 1), date(2026, 10, 20), CALENDARIO)
    assert (df["rotina"] == 1).all()


def test_datas_invalidas():
    for nascimento in [date(2027, 1, 1), date(2010, 1, 1)]:
        try:
            classificar(nascimento, date(2026, 10, 20), CALENDARIO)
            assert False, "deveria dar erro"
        except ValueError:
            pass


if __name__ == "__main__":
    for nome, funcao in list(globals().items()):
        if nome.startswith("test_"):
            funcao()
            print("ok", nome)
