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

nlp = spacy.load("pt_core_news_sm")

sheet_id = "1Cl-OcL0Kb3IHtjnH3M0_0mkKkK0pna7eOxhu9hvx688"
sheet_name = "Pagina1"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
colunas = [
    "Data Publicação",
    "Termo de Pesquisa",
    "Município",
    "Regional",
    "Departamento",
    "Título",
    "Links",
]


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

if "lista_parametros_pesquisa_default" in st.session_state:
    lista_parametros_pesquisa_default = st.session_state[
        "lista_parametros_pesquisa_default"
    ]
else:
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
    return df.to_csv(index=False).encode("utf-8")


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

    dados_crimes = pd.DataFrame(lista_formatada, columns=colunas).sort_values(by='Data Publicação',ascending=False)
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


st.set_page_config(layout="wide")

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
    csv = convert_df(df)
    st.download_button(
        "Fazer download", csv, "crimes.csv", "text/csv", key="download-csv"
    )
    st.markdown("""---""")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.markdown("##### Data Publicação")
    col2.markdown('##### Termo de Pesquisa')
    col3.markdown("##### Município")
    col4.markdown("##### Regional")
    col5.markdown("##### Departamento")
    col6.markdown("##### Título")
    col7.markdown("##### Link")
    for index, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
            col1.write(row["Data Publicação"].strftime("%Y/%m/%d"))
            col2.write(row['Termo de Pesquisa'])
            col3.write(row["Município"])
            col4.write(row["Regional"])
            col5.write(row["Departamento"])
            col6.markdown("*%s*" % row["Título"])
            col7.write("[link](%s)" % row["Links"])
