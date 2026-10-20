"""Regra que compara a idade da criança com o Calendário Nacional de Vacinação."""
import pandas as pd

JANELA_PROXIMAS = 3  # meses à frente considerados "próximas doses"
IDADE_MAXIMA = 120   # o calendário da criança vai até 9 anos, 11 meses e 29 dias


def idade_em_meses(nascimento, hoje):
    """Meses completos entre as duas datas (ex.: 10/01 a 09/03 = 1 mês)."""
    meses = (hoje.year - nascimento.year) * 12 + (hoje.month - nascimento.month)
    if hoje.day < nascimento.day:
        meses -= 1
    return meses


def classificar(nascimento, hoje, calendario):
    """Devolve o calendário com a data prevista e o status de cada dose."""
    if nascimento > hoje:
        raise ValueError("A data de nascimento não pode estar no futuro.")
    idade = idade_em_meses(nascimento, hoje)
    if idade >= IDADE_MAXIMA:
        raise ValueError("O calendário da criança vai só até 9 anos, 11 meses e 29 dias.")

    df = calendario[calendario["rotina"] == 1].copy()
    # shortcut: usa meses de calendário; o PDF fala em dias para o rotavírus. Trocar por dias se a banca pedir precisão.
    df["data_prevista"] = [
        (pd.Timestamp(nascimento) + pd.DateOffset(months=int(m))).date() for m in df["idade_meses"]
    ]

    def status(linha):
        if pd.notna(linha["idade_max_meses"]) and idade >= linha["idade_max_meses"]:
            return "prazo encerrado"
        if idade >= linha["idade_meses"]:
            return "conferir na caderneta"
        if linha["idade_meses"] - idade <= JANELA_PROXIMAS:
            return "próxima"
        return "futura"

    df["status"] = df.apply(status, axis=1)
    return df
