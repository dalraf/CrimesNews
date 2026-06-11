import subprocess
from time import mktime, sleep
from datetime import date
from io import BytesIO
import urllib.parse
import concurrent.futures
import re
import random

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


requests.packages.urllib3.disable_warnings()
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
        print(f"[DEBUG]       Analisando HTML ({len(html)} bytes)...")
        try:
            soup_list = BeautifulSoup(html, "html.parser").find_all("main")
            print(f"[DEBUG]       Tags <main> encontradas: {len(soup_list)}")
        except Exception as e:
            print(f"[DEBUG]       Erro de busca da tag main: {e}")
            try:
                soup_list = BeautifulSoup(html, "html.parser").find_all(
                    "div", class_=re.compile(r"main")
                )
                print(f"[DEBUG]       Tags <div class='main'> encontradas: {len(soup_list)}")
            except Exception as e:
                print(f"[DEBUG]       Erro de busca do main class: {e}")
                soup_list = []
        
        final_text = ""
        if soup_list:
            print(f"[DEBUG]       Removendo tags de estilo e script...")
            for soup in soup_list:
                for data in soup(["style", "script"]):
                    data.decompose()
            for soup in soup_list:
                text = " ".join(soup.stripped_strings)
                final_text += text
                print(f"[DEBUG]       Texto extraído desta tag: {len(text)} caracteres")
        else:
            print(f"[DEBUG]       Nenhuma tag main/div encontrada. Tentando extrair todo o body...")
            soup = BeautifulSoup(html, "html.parser")
            body = soup.find("body")
            if body:
                for data in body(["style", "script", "nav", "header", "footer"]):
                    data.decompose()
                final_text = " ".join(body.stripped_strings)
                print(f"[DEBUG]       Texto do body: {len(final_text)} caracteres")
        
        return final_text
    except Exception as e:
        print(f"[DEBUG]       ❌ ERRO de análise de html: {e}")
        return ""


def get_text_url(url):
    try:
        print(f"[DEBUG]     Requisição HTTP para: {url}")
        
        # Headers realistas de um navegador
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Retry com backoff exponencial
        max_tentativas = 3
        tentativa = 0
        
        while tentativa < max_tentativas:
            try:
                # Delay aleatório para não parecer bot
                delay = random.uniform(1, 3)
                print(f"[DEBUG]     Aguardando {delay:.1f}s antes da requisição...")
                sleep(delay)
                
                page = requests.get(
                    url, 
                    verify=False, 
                    timeout=30,
                    headers=headers, 
                    allow_redirects=True
                )
                
                print(f"[DEBUG]     Tentativa {tentativa + 1}/{max_tentativas} - Status code: {page.status_code}")
                print(f"[DEBUG]     URL final: {page.url}")
                print(f"[DEBUG]     Tamanho: {len(page.content)} bytes")
                
                if page.status_code == 200:
                    text = remove_tags(page.content)
                    print(f"[DEBUG]     ✓ Sucesso! Texto extraído: {len(text)} caracteres")
                    return text
                
                elif page.status_code == 503:
                    tentativa += 1
                    if tentativa < max_tentativas:
                        espera = 2 ** tentativa  # Backoff: 2s, 4s
                        print(f"[DEBUG]     ⚠️ Erro 503 - Aguardando {espera}s antes de retry...")
                        sleep(espera)
                    else:
                        print(f"[DEBUG]     ❌ Erro 503 persistente após {max_tentativas} tentativas")
                        return ""
                
                elif page.status_code == 429:
                    print(f"[DEBUG]     ⚠️ Erro 429 (Rate Limited) - Google bloqueou requisições")
                    return ""
                
                elif page.status_code == 400:
                    print(f"[DEBUG]     ⚠️ Erro 400 - URL expirada ou mal formatada")
                    return ""
                
                else:
                    print(f"[DEBUG]     ⚠️ Erro {page.status_code}")
                    return ""
                    
            except requests.exceptions.Timeout:
                tentativa += 1
                print(f"[DEBUG]     ❌ Timeout na tentativa {tentativa}/{max_tentativas}")
                if tentativa < max_tentativas:
                    sleep(2 ** tentativa)
                    
            except requests.exceptions.ConnectionError as e:
                tentativa += 1
                print(f"[DEBUG]     ❌ Erro de conexão: {e}")
                if tentativa < max_tentativas:
                    sleep(2 ** tentativa)
        
        print(f"[DEBUG]     ❌ Falha após {max_tentativas} tentativas")
        return ""
        
    except Exception as e:
        print(f"[DEBUG]     ❌ ERRO inesperado: {e}")
        return ""


def convert_df(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    processed_data = output.getvalue()
    return processed_data

def encode_url(url):
    """Codifica uma URL para uso com o Google News."""
    return urllib.parse.quote_plus(url.encode("utf-8"))

def format_news(pesquisa, data_inicio, data_fim, noticias_maximo_retornado):
    print(f"[DEBUG] Iniciando format_news para pesquisa: {pesquisa}")
    
    # Delay para não sobrecarregar Google News
    delay = random.uniform(2, 5)
    print(f"[DEBUG] Aguardando {delay:.1f}s antes de buscar notícias...")
    sleep(delay)
    
    pesquisa_url = encode_url(pesquisa)
    url = f"https://news.google.com/rss/search?q={pesquisa_url}&hl=pt-BR&gl=BR&ceid=BR%3Apt-419"
    
    print(f"[DEBUG] Buscando notícias da URL: {url}")
    
    try:
        noticias = feedparser.parse(url)["entries"][:noticias_maximo_retornado]
        print(f"[DEBUG] Total de notícias encontradas: {len(noticias)}")
    except Exception as e:
        print(f"[DEBUG] ❌ ERRO ao buscar feed: {e}")
        return []
    
    lista_formatada = []
    
    # Criar dicionário para busca rápida de municípios (O(1) em vez de O(n))
    print("[DEBUG] Construindo dicionário de municípios...")
    municipios_dict = {}
    for row in dados_municipios.iterrows():
        municipio = row[1]["Municipio"]
        municipios_dict[municipio] = {
            "Regional": row[1]["Regional"],
            "Departamento": row[1]["Departamento"]
        }
    print(f"[DEBUG] Dicionário construído com {len(municipios_dict)} municípios")
    
    for idx, news in enumerate(noticias):
        print(f"[DEBUG] Processando notícia {idx + 1}/{len(noticias)}")
        try:
            pubdate = date.fromtimestamp(mktime(news["published_parsed"]))
            print(f"[DEBUG]   Data: {pubdate}")
            
            if pubdate >= data_inicio and pubdate <= data_fim:
                titulo = news["title"]
                print(f"[DEBUG]   Título: {titulo[:60]}...")
                
                link = news["links"][0]["href"]
                print(f"[DEBUG]   Link bruto do RSS: {link}")
                
                # Verificar se é URL do Google News e tentar extrair URL real
                if "news.google.com" in link:
                    print(f"[DEBUG]   ⚠️ URL é do Google News (intermediária)")
                
                print(f"[DEBUG]   Extraindo texto do link...")
                link_text = get_text_url(link)
                
                if not link_text:
                    print(f"[DEBUG]   ⚠️ Nenhum texto extraído, pulando esta notícia")
                    continue
                print(f"[DEBUG]   Texto extraído: {len(link_text)} caracteres")
                
                print(f"[DEBUG]   Processando com NLP (spacy)...")
                doc_link_text = nlp(link_text)
                
                # Usar set para busca O(1) em vez de lista
                list_ent_gpe = set()
                for ent in doc_link_text.ents:
                    if ent.label_ in ("LOC", "GPE"):
                        list_ent_gpe.add(ent.text)
                print(f"[DEBUG]   Entidades encontradas: {list_ent_gpe}")
                
                # Buscar apenas os municípios encontrados (muito mais rápido)
                matches = 0
                for municipio in list_ent_gpe:
                    if municipio in municipios_dict:
                        matches += 1
                        regional = municipios_dict[municipio]["Regional"]
                        departamento = municipios_dict[municipio]["Departamento"]
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
                print(f"[DEBUG]   Municípios encontrados: {matches}")
            else:
                print(f"[DEBUG]   Data fora do intervalo ({data_inicio} a {data_fim})")
        except Exception as e:
            print(f"[DEBUG] ❌ ERRO ao processar notícia {idx + 1}: {e}")
            continue
    
    print(f"[DEBUG] format_news concluído. Total de resultados: {len(lista_formatada)}")
    return lista_formatada


def executar(data_inicio, data_fim, noticias_maximo_retornado=10):
    print(f"\n[DEBUG] ============ INICIANDO EXECUÇÃO ============")
    print(f"[DEBUG] Data início: {data_inicio}")
    print(f"[DEBUG] Data fim: {data_fim}")
    print(f"[DEBUG] Máx notícias por pesquisa: {noticias_maximo_retornado}")
    print(f"[DEBUG] Total de termos de pesquisa: {len(lista_parametros_pesquisa)}")
    print(f"[DEBUG] Termos: {lista_parametros_pesquisa}\n")

    lista_formatada = []
    futures = []
    
    # Limitar número de workers para não sobrecarregar o servidor
    max_workers = min(3, len(lista_parametros_pesquisa))
    print(f"[DEBUG] Usando {max_workers} threads paralelas\n")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for idx, pesquisa in enumerate(lista_parametros_pesquisa):
            print(f"[DEBUG] Submetendo pesquisa {idx + 1}/{len(lista_parametros_pesquisa)}: '{pesquisa}'")
            future = executor.submit(
                format_news, pesquisa, data_inicio, data_fim, noticias_maximo_retornado
            )
            futures.append(future)

    print(f"\n[DEBUG] Aguardando resultados de {len(futures)} threads...")
    for idx, future in enumerate(futures):
        print(f"[DEBUG] Coletando resultado {idx + 1}/{len(futures)}...")
        try:
            resultado = future.result(timeout=600)  # 10 minutos timeout
            lista_formatada += resultado
            print(f"[DEBUG] ✓ Resultado {idx + 1} coletado com sucesso ({len(resultado)} itens)")
        except Exception as e:
            print(f"[DEBUG] ❌ ERRO ao coletar resultado {idx + 1}: {e}")

    print(f"\n[DEBUG] Total de notícias encontradas: {len(lista_formatada)}")
    
    if lista_formatada:
        dados_crimes = pd.DataFrame(lista_formatada, columns=colunas).sort_values(
            by="Data Publicação", ascending=False
        )
        print(f"[DEBUG] DataFrame criado com sucesso")
    else:
        print(f"[DEBUG] ⚠️ Nenhuma notícia encontrada!")
        dados_crimes = pd.DataFrame(columns=colunas)
    
    print(f"[DEBUG] ============ EXECUÇÃO CONCLUÍDA ============\n")
    return dados_crimes
