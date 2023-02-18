import subprocess
from time import mktime
from datetime import date
from io import BytesIO
import urllib.parse
import concurrent.futures

try:
    import pandas as pd
except Exception as e:
    print("Erro de importação do pandas", e.args[0])
    print("Instalando pandas...")
    subprocess.check_call(["python", "-m", "pip", "install", "pandas"])
    import pandas as pd

try:
    import openpyxl
except Exception as e:
    print("Erro de importação do openpyxl", e.args[0])
    print("Instalando openpyxl...")
    subprocess.check_call(["python", "-m", "pip", "install", "openpyxl"])
    import openpyxl

try:
    import feedparser
except Exception as e:
    print("Erro de importação do feedparser", e.args[0])
    print("Instalando feedparser...")
    subprocess.check_call(["python", "-m", "pip", "install", "feedparser"])
    import feedparser

try:
    from bs4 import BeautifulSoup
except Exception as e:
    print("Erro de importação do BeautifulSoup", e.args[0])
    print("Instalando BeautifulSoup...")
    subprocess.check_call(["python", "-m", "pip", "install", "beautifulsoup4"])
    from bs4 import BeautifulSoup

try:
    import requests
except Exception as e:
    print("Erro de importação do requests", e.args[0])
    print("Instalando requests...")
    subprocess.check_call(["python", "-m", "pip", "install", "requests"])
    import requests

try:
    import spacy, spacy.cli
except Exception as e:
    print("Erro de importação do spacy", e.args[0])
    print("Instalando spacy...")
    subprocess.check_call(["python", "-m", "pip", "install", "spacy"])
    import spacy, spacy.cli

try:
    nlp = spacy.load("pt_core_news_sm")
except Exception as e:
    print("Erro de download do modelo de linguagem", e.args[0])
    print("Baixando modelo de linguagem...")
    spacy.cli.download("pt_core_news_sm")
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


lista_parametros_pesquisa = list(
    get_data_from_sheet(sheet_id, sheet_name_termos)["TERMOS"]
)


def municipio_string_format(var):
    lista_string = []
    for word in var.split():
        if word.lower() in ["da", "das", "do", "dos", "de"]:
            word = word.lower()
        else:
            word = word.capitalize()
        lista_string.append(word)
    return " ".join(lista_string)


dados_municipios = get_data_from_sheet(sheet_id, sheet_name_municipios)
dados_municipios["Municipio"] = dados_municipios["Municipio"].apply(
    lambda x: municipio_string_format(x)
)


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
        page = requests.get(url, timeout=60)
        return remove_tags(page.content)
    except Exception as e:
        print("Erro de busca dos dados do site", e.args[0])
        return ""


def convert_df(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    processed_data = output.getvalue()
    return processed_data


def format_news(pesquisa, data_inicio, data_fim, noticias_maximo_retornado):
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


def executar(data_inicio, data_fim, noticias_maximo_retornado=10):

    lista_formatada = []
    futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for pesquisa in lista_parametros_pesquisa:
            future = executor.submit(
                format_news, pesquisa, data_inicio, data_fim, noticias_maximo_retornado
            )
            futures.append(future)

    for future in futures:
        lista_formatada += future.result()

    dados_crimes = pd.DataFrame(lista_formatada, columns=colunas).sort_values(
        by="Data Publicação", ascending=False
    )
    return dados_crimes
