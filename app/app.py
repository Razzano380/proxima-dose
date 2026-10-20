"""Próxima Dose — aplicação Streamlit.

Como rodar (na pasta do projeto):
    python scripts/preparar_dados.py   # cria o banco, só na primeira vez
    streamlit run app/app.py
"""
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from regras import classificar

PASTA = Path(__file__).resolve().parent.parent
BANCO = PASTA / "data" / "proxima_dose.db"

AZUL, VERDE, AMARELO, CORAL = "#1B4965", "#2A9D8F", "#E9C46A", "#E76F51"

# Metas de cobertura do PNI: 90% para BCG e rotavírus, 95% para as demais vacinas infantis.
META_90 = ["BCG", "Rotavírus Humano"]

st.set_page_config(page_title="Próxima Dose", page_icon="💉", layout="centered")


@st.cache_data
def ler_tabela(nome):
    with sqlite3.connect(BANCO) as con:
        return pd.read_sql(f"SELECT * FROM {nome}", con)


if not BANCO.exists():
    st.error("Banco de dados não encontrado. Rode antes: python scripts/preparar_dados.py")
    st.stop()

st.image(str(PASTA / "assets" / "logo.png"), width=320)
st.info(
    "Esta ferramenta não substitui a caderneta de vacinação nem a orientação de um "
    "profissional de saúde. Em caso de dúvida, procure a Unidade Básica de Saúde (UBS)."
)

aba_crianca, aba_municipio = st.tabs(["Minha criança", "Meu município"])

# ---------------------------------------------------------------- Minha criança
with aba_crianca:
    st.subheader("Quais vacinas a criança deveria ter recebido?")
    st.caption(
        "Fonte: Calendário Nacional de Vacinação 2026 — Criança (Ministério da Saúde). "
        "A data digitada não é salva."
    )

    hoje = date.today()
    nascimento = st.date_input(
        "Data de nascimento da criança",
        value=None,
        min_value=date(hoje.year - 10, hoje.month, 1),
        max_value=hoje,
        format="DD/MM/YYYY",
    )

    if nascimento:
        try:
            doses = classificar(nascimento, hoje, ler_tabela("calendario"))
        except ValueError as erro:
            # st.stop() aqui esconderia também a aba "Meu município"
            st.warning(str(erro))
            doses = ler_tabela("calendario").assign(status="")

        def nome_dose(linha):
            return f"{linha['vacina']} — {linha['dose']} ({linha['idade_texto']})"

        encerradas = doses[doses["status"] == "prazo encerrado"]
        conferir = doses[doses["status"] == "conferir na caderneta"]
        proximas = doses[doses["status"] == "próxima"]
        futuras = doses[doses["status"] == "futura"]

        st.markdown(f"### ✔️ Já deveriam ter sido aplicadas ({len(conferir)})")
        st.caption("Marque as que já estão registradas na caderneta.")
        pendentes = []
        for i, linha in conferir.iterrows():
            if not st.checkbox(nome_dose(linha), key=f"dose_{i}"):
                pendentes.append(nome_dose(linha))

        if pendentes:
            st.warning(
                f"⚠️ {len(pendentes)} dose(s) não marcada(s). Leve a caderneta à UBS para conferir."
            )
        elif not conferir.empty:
            st.success("Todas as doses até agora foram marcadas como registradas na caderneta.")

        st.markdown(f"### 📅 Próximos 3 meses ({len(proximas)})")
        for _, linha in proximas.iterrows():
            st.markdown(f"- **{linha['data_prevista']:%d/%m/%Y}** — {nome_dose(linha)}")
        if proximas.empty:
            st.write("Nenhuma dose prevista para os próximos 3 meses.")

        if not encerradas.empty:
            st.markdown(f"### ⛔ Prazo encerrado ({len(encerradas)})")
            for _, linha in encerradas.iterrows():
                st.markdown(f"- {nome_dose(linha)} — {linha['observacao']}")

        with st.expander(f"Doses futuras ({len(futuras)})"):
            for _, linha in futuras.iterrows():
                st.markdown(f"- {linha['data_prevista']:%d/%m/%Y} — {nome_dose(linha)}")

# ---------------------------------------------------------------- Meu município
with aba_municipio:
    st.subheader("Como está a cobertura vacinal no seu município?")
    st.caption("Fonte: DATASUS/TabNet — SI-PNI, coberturas vacinais de 2020 a 2022 (últimos dados disponíveis).")

    cobertura = ler_tabela("cobertura")
    cobertura["meta"] = cobertura["vacina"].isin(META_90).map({True: 90, False: 95})

    municipio = st.selectbox("Município (SP)", sorted(cobertura["municipio"].unique()),
                             index=None, placeholder="Digite o nome do município")

    if municipio:
        dados = cobertura[cobertura["municipio"] == municipio]
        ano = dados["ano"].max()
        recente = dados[dados["ano"] == ano].sort_values("cobertura")
        recente["situação"] = (recente["cobertura"] >= recente["meta"]).map(
            {True: "atingiu a meta", False: "abaixo da meta"}
        )

        abaixo = (recente["situação"] == "abaixo da meta").sum()
        st.metric(f"Vacinas abaixo da meta em {ano}", f"{abaixo} de {len(recente)}")

        grafico = px.bar(
            recente, x="cobertura", y="vacina", orientation="h", color="situação",
            color_discrete_map={"atingiu a meta": VERDE, "abaixo da meta": CORAL},
            labels={"cobertura": "Cobertura (%)", "vacina": ""},
            title=f"Cobertura por vacina em {ano}", height=650,
        )
        grafico.add_vline(x=95, line_dash="dash", line_color=AZUL,
                          annotation_text="meta 95% (90% para BCG e rotavírus)",
                          annotation_position="bottom right")
        st.plotly_chart(grafico, width="stretch")

        vacina = st.selectbox("Ver evolução de uma vacina", sorted(dados["vacina"].unique()))
        serie = dados[dados["vacina"] == vacina].sort_values("ano")
        linha = px.line(serie, x="ano", y="cobertura", markers=True,
                        labels={"cobertura": "Cobertura (%)", "ano": "Ano"},
                        title=f"{vacina} — {municipio}")
        linha.update_traces(line_color=AZUL)
        linha.add_hline(y=serie["meta"].iloc[0], line_dash="dash", line_color=CORAL,
                        annotation_text=f"meta {serie['meta'].iloc[0]}%")
        linha.update_xaxes(dtick=1)
        st.plotly_chart(linha, width="stretch")

        st.caption(
            "Coberturas acima de 100% podem acontecer: crianças de outras cidades vacinadas aqui "
            "e estimativas de população imprecisas, principalmente em municípios pequenos."
        )
