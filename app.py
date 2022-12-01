import pandas as pd
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import requests
import spacy
import streamlit as st
import concurrent.futures

nlp = spacy.load("pt_core_news_sm")

sheet_id = "1Cl-OcL0Kb3IHtjnH3M0_0mkKkK0pna7eOxhu9hvx688"
sheet_name = "Pagina1"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
colunas = ["Município", "Regional", "Departamento", "Título", "Links"]


def municipio_string_format(var):
    lista_string = []
    for word in var.split():
        if word.lower() in ["da", "das", "do", "dos", "de"]:
            word = word.lower()
        else:
            word = word.capitalize()
        lista_string.append(word)
    return " ".join(lista_string)


if "dados_municipios" in st.session_state:
    dados_municipios = st.session_state["dados_municipios"]
else:
    dados_municipios = pd.read_csv(url)
    dados_municipios["Municipio"] = dados_municipios["Municipio"].apply(
        lambda x: municipio_string_format(x)
    )
    st.session_state["dados_municipios"] = dados_municipios


def remove_tags(html):
    try:
        soup = BeautifulSoup(html, "html.parser")
        for data in soup(["style", "script"]):
            data.decompose()
        return " ".join(soup.stripped_strings)
    except Exception as e:
        print("Erro de análise de html", e.args[0])
        return ""


def get_text_url(url):
    try:
        page = requests.get(url, timeout=5)
        return remove_tags(page.content)
    except Exception as e:
        print("Erro de busca dos dados do site", e.args[0])
        return ""


def convert_df(df):
    return df.to_csv(index=False).encode("utf-8")


def format_news(url):
    noticias = feedparser.parse(url)["entries"][:noticias_maximo_retornado]
    lista_formatada = []
    for news in noticias:
        titulo = news["title"]
        link = news["links"][0]["href"]
        link_text = get_text_url(link)
        doc_link_text = nlp(link_text)
        list_ent_gpe = []
        for ent in doc_link_text.ents:
            if ent.label_ in ("LOC", "GPE"):
                list_ent_gpe.append(ent.text)
        for row in dados_municipios.iterrows():
            municipio = row[1]["Municipio"]
            if municipio in list_ent_gpe:
                regional = row[1]["Regional"]
                departamento = row[1]["Departamento"]
                lista_formatada.append(
                    [municipio, regional, departamento, titulo, link]
                )
    return lista_formatada


def executar():

    lista_formatada = []
    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for pesquisa in lista_parametros_pesquisa:
            pesquisa_url = urllib.parse.quote_plus(pesquisa)
            url = f"https://news.google.com/rss/search?q={pesquisa_url}&hl=pt-BR&gl=BR&ceid=BR%3Apt-419"
            future = executor.submit(format_news, url)
            futures.append(future)

    for future in futures:
        lista_formatada += future.result()

    dados_crimes = pd.DataFrame(lista_formatada, columns=colunas)
    return dados_crimes


st.set_page_config(layout="wide")

st.title("Análise de crimes")

lista_parametros_pesquisa_default = [
    "delegado",
    "chefe de polícia",
    "chefe de departamento",
    "delegado regional",
    "investigador",
    "escrivão",
    "perito",
    "perícia",
    "médico legista",
    "médico legal",
    "IML",
    "homicídio",
    "feminicídio",
    "roubo",
    "tráfico",
    "lavagem de dinheiro",
    "receptação",
    "furto",
    "arma de fogo",
    "ameaça",
    "ameaçar",
    "ameaçou",
    "foragido",
]

col1, col2 = st.columns(2)

with col1:

    lista_parametros_pesquisa = st.multiselect(
        "Parâmetros de pesquisa:",
        options=lista_parametros_pesquisa_default,
        default=lista_parametros_pesquisa_default,
    )


with col2:
    noticias_maximo_retornado = st.number_input(
        "Numero de notícias a serem retornadas", value=10
    )


if st.button("Executar"):
    st.session_state["df"] = executar()

if "df" in st.session_state:
    df = st.session_state["df"]
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown("#### Município")
    col2.markdown("#### Regional")
    col3.markdown("#### Departamento")
    col4.markdown("#### Título")
    col5.markdown("#### Link")
    for index, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.write(row["Município"])
            col2.write(row["Regional"])
            col3.write(row["Departamento"])
            col4.markdown("*%s*" % row["Título"])
            col5.write("[link](%s)" % row["Links"])
    csv = convert_df(df)
    st.download_button(
        "Fazer download", csv, "crimes.csv", "text/csv", key="download-csv"
    )
