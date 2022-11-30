import pandas as pd
import feedparser
import urllib.parse
from bs4 import BeautifulSoup
import requests
import spacy
import streamlit as st

nlp = spacy.load("pt_core_news_sm")

sheet_id = "1Cl-OcL0Kb3IHtjnH3M0_0mkKkK0pna7eOxhu9hvx688"
sheet_name = "Pagina1"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name}"
dados_municipios = pd.read_csv(url)


def municipio_string_format(var):
    lista_string = []
    for word in var.split():
        if word.lower() in ["da", "das", "do", "dos", "de"]:
            word = word.lower()
        else:
            word = word.capitalize()
        lista_string.append(word)
    return " ".join(lista_string)


def remove_tags(html):
  try:
    soup = BeautifulSoup(html, "html.parser")
    for data in soup(["style", "script"]):
          data.decompose()
    return " ".join(soup.stripped_strings)
  except Exception as e:
    print('Erro de análise de html', e.args[0])
    return ''

def get_text_url(url):
  try:
    page = requests.get(url, timeout=5)
    return remove_tags(page.content)
  except Exception as e:
    print('Erro de busca dos dados do site', e.args[0])
    return ""

def convert_df(df):
   return df.to_csv(index=False).encode('utf-8')

def executar():

  dados_municipios["Municipio"] = dados_municipios["Municipio"].apply(
      lambda x: municipio_string_format(x)
  )
  texto_parametros_pesquisa = "delegado,chefe de polícia,chefe de departamento,delegado regional,investigador,escrivão,perito,perícia,médico legista,médico legal,IML,homicídio,feminicídio,roubo,tráfico,lavagem de dinheiro,receptação,furto,arma de fogo,ameaça,ameaçar,ameaçou,foragido"
  lista_parametros_pesquisa = texto_parametros_pesquisa.split(",")
  lista_noticias = []
  for pesquisa in lista_parametros_pesquisa:
      pesquisa_url = urllib.parse.quote_plus(pesquisa)
      url = f"https://news.google.com/rss/search?q={pesquisa_url}&hl=pt-BR&gl=BR&ceid=BR%3Apt-419"
      lista_noticias += feedparser.parse(url)["entries"][:2]


  lista_output = []
  colunas = ["Município", "Regional", "Departamento", "Título", "Links"]
  for news in lista_noticias:
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
              lista_output.append([municipio, regional, departamento, titulo, link])
  dados_crimes = pd.DataFrame(lista_output, columns=colunas)
  return(dados_crimes)

st.title('Análise de crimes')

if st.button('Executar'):
  df = executar()
  st.dataframe(df)
  csv = convert_df(df)
  st.download_button(
    "Fazer download",
    csv,
    "crimes.csv",
    "text/csv",
    key='download-csv'
  )