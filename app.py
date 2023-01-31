import pandas as pd
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import requests
import spacy
import streamlit as st
import concurrent.futures
from time import mktime
from datetime import date
from io import BytesIO

nlp = spacy.load("pt_core_news_sm")

sheet_id = "1d12wtIAsf888mM08VqMXvL9uN1jevxoCMPwStZ910EA"
sheet_name_municipios = "MUNICIPIOS"
sheet_name_termos = "TERMOS"

colunas = [
    "Data Publicação",
    "Termo de Pesquisa",
    "Município",
    "Regional",
    "Departamento",
    "Título",
    "Links",
]


def get_data_from_sheet(sheet_id, sheet_name):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
    df = pd.read_csv(url)
    return df


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
    dados_municipios = get_data_from_sheet(sheet_id, sheet_name_municipios)
    dados_municipios["Municipio"] = dados_municipios["Municipio"].apply(
        lambda x: municipio_string_format(x)
    )
    st.session_state["dados_municipios"] = dados_municipios

if "lista_parametros_pesquisa_default" in st.session_state:
    lista_parametros_pesquisa_default = st.session_state[
        "lista_parametros_pesquisa_default"
    ]
else:
    lista_parametros_pesquisa_default = list(
        get_data_from_sheet(sheet_id, sheet_name_termos)["TERMOS"]
    )
    st.session_state[
        "lista_parametros_pesquisa_default"
    ] = lista_parametros_pesquisa_default


def remove_tags(html):
    try:
        soup = BeautifulSoup(html, "html.parser").find("main")
        for data in soup(["style", "script"]):
            data.decompose()
        return " ".join(soup.stripped_strings)
    except Exception as e:
        print("Erro de análise de html", e.args[0])
        return ""


def get_text_url(url):
    try:
        page = requests.get(url, timeout=10)
        return remove_tags(page.content)
    except Exception as e:
        print("Erro de busca dos dados do site", e.args[0])
        return ""


def convert_df(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    processed_data = output.getvalue()
    return processed_data


def format_news(pesquisa, data_inicio, data_fim):
    pesquisa_url = urllib.parse.quote_plus(pesquisa)
    url = f"https://news.google.com/rss/search?q={pesquisa_url}&hl=pt-BR&gl=BR&ceid=BR%3Apt-419"
    noticias = feedparser.parse(url)["entries"][:noticias_maximo_retornado]
    lista_formatada = []
    for news in noticias:
        pubdate = date.fromtimestamp(mktime(news["published_parsed"]))
        if pubdate >= data_inicio and pubdate <= data_fim:
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
                        [
                            pubdate,
                            pesquisa,
                            municipio,
                            regional,
                            departamento,
                            titulo,
                            link,
                        ]
                    )
    return lista_formatada


def executar():

    lista_formatada = []
    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for pesquisa in lista_parametros_pesquisa:
            future = executor.submit(format_news, pesquisa, data_inicio, data_fim)
            futures.append(future)

    for future in futures:
        lista_formatada += future.result()

    dados_crimes = pd.DataFrame(lista_formatada, columns=colunas).sort_values(
        by="Data Publicação", ascending=False
    )
    return dados_crimes


def clear_add_parametro():
    if (
        st.session_state["parametro_add"]
        not in st.session_state["lista_parametros_pesquisa_default"]
    ):
        st.session_state["lista_parametros_pesquisa_default"].append(
            st.session_state["parametro_add"]
        )
    st.session_state[
        "lista_parametros_pesquisa_default"
    ] = lista_parametros_pesquisa_default
    st.session_state["parametro_add"] = ""


st.set_page_config(
   page_title="Crimes Reais",
   page_icon="🧊",
   layout="wide",
   initial_sidebar_state="expanded",
)

st.title("Análise de crimes")

col1, col2 = st.columns(2)

with col1:
    st.text_input("Parâmetro:", key="parametro_add")
    st.button("Adicionar", on_click=clear_add_parametro)

with col2:
    noticias_maximo_retornado = st.number_input(
        "Numero de notícias a serem retornadas", value=10
    )

col1, col2 = st.columns(2)
with col1:
    data_inicio = st.date_input("Filtar por data (Início):")
with col2:
    data_fim = st.date_input("(Fim)")

lista_parametros_pesquisa = st.multiselect(
    "Parâmetros de pesquisa:",
    options=lista_parametros_pesquisa_default,
    default=lista_parametros_pesquisa_default,
)

if st.button("Executar"):
    st.session_state["df"] = executar()

if "df" in st.session_state:
    st.markdown("""---""")
    df = st.session_state["df"]
    xlsx = convert_df(df)
    st.download_button("Fazer download", xlsx, "crimes.xlsx", key="download-xls")

