import streamlit as st
from Core import (
    executar,
    convert_df,
)

st.set_page_config(
    page_title="Crimes Reais",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Análise de crimes")

noticias_maximo_retornado = st.number_input(
        "Numero de notícias a serem retornadas", value=10
    )

col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Filtar por data (Início):")
with col2:
    data_fim = st.date_input("(Fim)")

if st.button("Executar"):
    st.session_state["df"] = executar(data_inicio, data_fim, noticias_maximo_retornado)

if "df" in st.session_state:
    st.markdown("""---""")
    df = st.session_state["df"]
    xlsx = convert_df(df)
    st.download_button("Fazer download", xlsx, "crimes.xlsx", key="download-xls")
