import subprocess
from time import mktime, sleep
from datetime import date
from io import BytesIO
import urllib.parse
import concurrent.futures
import re
import random
import unicodedata

# Auto-install wrapper pattern (matching original file style)
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
    import requests
except Exception as e:
    print("Erro de importação do requests", e.args[0])
    print("Instalando requests...")
    subprocess.check_call(["python", "-m", "pip", "install", "requests"])
    import requests

try:
    from googlenewsdecoder import gnewsdecoder
except Exception as e:
    print("Erro de importação do googlenewsdecoder", e.args[0])
    print("Instalando googlenewsdecoder...")
    subprocess.check_call(["python", "-m", "pip", "install", "googlenewsdecoder"])
    from googlenewsdecoder import gnewsdecoder

try:
    import trafilatura
except Exception as e:
    print("Erro de importação do trafilatura", e.args[0])
    print("Instalando trafilatura...")
    subprocess.check_call(["python", "-m", "pip", "install", "trafilatura"])
    import trafilatura

# Desabilitar avisos de requisições HTTPS inseguras
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

def remove_accents(input_str):
    """Remove acentos e caracteres diacríticos de uma string."""
    if not isinstance(input_str, str):
        return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

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

# Carregar dados iniciais das planilhas
print("[DEBUG] Carregando termos de pesquisa...")
try:
    lista_parametros_pesquisa = list(
        get_data_from_sheet(sheet_id, sheet_name_termos)["TERMOS"]
    )
except Exception as e:
    print(f"[ERROR] Não foi possível carregar os termos: {e}")
    lista_parametros_pesquisa = []

print("[DEBUG] Carregando dados de municípios...")
try:
    dados_municipios = get_data_from_sheet(sheet_id, sheet_name_municipios)
    dados_municipios["Municipio"] = dados_municipios["Municipio"].apply(
        lambda x: municipio_string_format(str(x))
    )
except Exception as e:
    print(f"[ERROR] Não foi possível carregar os municípios: {e}")
    dados_municipios = pd.DataFrame(columns=["Municipio", "Regional", "Departamento"])

def chunk_list(lst, n):
    """Divide uma lista em partes de tamanho n."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def process_query_chunk(pesquisa, chunk, data_inicio, data_fim, noticias_maximo_retornado, municipios_dict, progress_callback=None):
    """
    Processa um subgrupo de municípios para um determinado termo.
    """
    resultados_chunk = []
    
    # Monta a query agrupada: "termo" ("Cidade A" OR "Cidade B" OR ...)
    query_cidades = " OR ".join(f'"{cidade}"' for cidade in chunk)
    query_completa = f'"{pesquisa}" ({query_cidades})'
    
    query_encoded = urllib.parse.quote_plus(query_completa)
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=pt-BR&gl=BR&ceid=BR%3Apt-419"
    
    log_msg = f"[DEBUG] Query: {pesquisa} | Grupo de {len(chunk)} cidades"
    print(log_msg)
    if progress_callback:
        progress_callback(log_msg)
        
    try:
        # Adicionar delay leve para evitar rate limit
        sleep(random.uniform(0.5, 1.5))
        feed = feedparser.parse(url)
        noticias = feed.get("entries", [])[:noticias_maximo_retornado]
    except Exception as e:
        err_msg = f"[ERROR] Erro ao buscar feed do grupo: {e}"
        print(err_msg)
        if progress_callback:
            progress_callback(err_msg)
        return []

    for news in noticias:
        try:
            pubdate = date.fromtimestamp(mktime(news["published_parsed"]))
            if not (data_inicio <= pubdate <= data_fim):
                continue
                
            titulo = news.get("title", "")
            link = news.get("links", [{}])[0].get("href", "")
            
            titulo_sem_acento = remove_accents(titulo)
            
            # Verificar correspondência das cidades do chunk no título
            cidades_encontradas = []
            for cidade in chunk:
                cidade_sem_acento = remove_accents(cidade)
                pattern = rf"\b{re.escape(cidade_sem_acento)}\b"
                if re.search(pattern, titulo_sem_acento, re.IGNORECASE):
                    cidades_encontradas.append(cidade)
            
            # Se não encontrou no título, decodifica a URL e extrai o texto do corpo da página
            decoded_url = ""
            if not cidades_encontradas and link:
                try:
                    res_dec = gnewsdecoder(link)
                    if res_dec.get("status"):
                        decoded_url = res_dec["decoded_url"]
                except Exception:
                    pass
                
                if not decoded_url:
                    decoded_url = link
                
                # Scraping moderno e rápido via trafilatura
                texto_artigo = ""
                try:
                    downloaded = trafilatura.fetch_url(decoded_url)
                    if downloaded:
                        texto_artigo = trafilatura.extract(downloaded) or ""
                except Exception:
                    pass
                
                if texto_artigo:
                    texto_sem_acento = remove_accents(texto_artigo)
                    for cidade in chunk:
                        cidade_sem_acento = remove_accents(cidade)
                        pattern = rf"\b{re.escape(cidade_sem_acento)}\b"
                        if re.search(pattern, texto_sem_acento, re.IGNORECASE):
                            cidades_encontradas.append(cidade)
            else:
                # Mesmo que tenha encontrado no título, decodifica a URL para salvar a URL original limpa no Excel
                if link:
                    try:
                        res_dec = gnewsdecoder(link)
                        if res_dec.get("status"):
                            decoded_url = res_dec["decoded_url"]
                    except Exception:
                        pass
                if not decoded_url:
                    decoded_url = link

            # Registrar correspondências encontradas
            for cidade in cidades_encontradas:
                regional = municipios_dict[cidade]["Regional"]
                departamento = municipios_dict[cidade]["Departamento"]
                resultados_chunk.append([
                    pubdate,
                    pesquisa,
                    cidade,
                    regional,
                    departamento,
                    titulo,
                    decoded_url
                ])
                log_match = f"   ✓ [MATCH] '{pesquisa}' em '{cidade}' -> {titulo[:50]}..."
                print(log_match)
                if progress_callback:
                    progress_callback(log_match)
                    
        except Exception as e:
            print(f"[DEBUG] Erro ao processar notícia individual: {e}")
            continue
            
    return resultados_chunk

def executar(data_inicio, data_fim, noticias_maximo_retornado=10, progress_callback=None):
    print(f"\n[DEBUG] ============ INICIANDO EXECUÇÃO SIMPLIFICADA ============")
    print(f"[DEBUG] Data início: {data_inicio} | Data fim: {data_fim}")
    print(f"[DEBUG] Máx notícias por consulta: {noticias_maximo_retornado}")
    print(f"[DEBUG] Total de termos de pesquisa: {len(lista_parametros_pesquisa)}")
    print(f"[DEBUG] Total de municípios: {len(dados_municipios)}")
    
    if progress_callback:
        progress_callback("Iniciando execução...")
        progress_callback(f"Período: {data_inicio} até {data_fim}")
        progress_callback(f"Termos de Pesquisa: {', '.join(lista_parametros_pesquisa)}")
    
    # Criar dicionário de municípios para mapeamento O(1)
    municipios_dict = {}
    lista_cidades = []
    for _, row in dados_municipios.iterrows():
        municipio = row["Municipio"]
        lista_cidades.append(municipio)
        municipios_dict[municipio] = {
            "Regional": row["Regional"],
            "Departamento": row["Departamento"]
        }
        
    lista_formatada = []
    
    # Agrupar cidades em blocos de 15 para não estourar tamanho da URL
    tamanho_bloco = 15
    blocos_cidades = list(chunk_list(lista_cidades, tamanho_bloco))
    
    # Paralelização das consultas por termos e blocos de cidades
    futures = []
    # Usando no máximo 3 workers para evitar rate limit do Google RSS
    max_workers = 3
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for termo in lista_parametros_pesquisa:
            for bloco in blocos_cidades:
                future = executor.submit(
                    process_query_chunk,
                    termo,
                    bloco,
                    data_inicio,
                    data_fim,
                    noticias_maximo_retornado,
                    municipios_dict,
                    progress_callback
                )
                futures.append(future)
                
    for idx, future in enumerate(concurrent.futures.as_completed(futures)):
        try:
            resultado = future.result()
            lista_formatada += resultado
        except Exception as e:
            print(f"[ERROR] Falha ao coletar resultado da thread {idx}: {e}")
            
    print(f"\n[DEBUG] Processamento finalizado. Total de correspondências: {len(lista_formatada)}")
    if progress_callback:
        progress_callback(f"Finalizado. Total de correspondências encontradas: {len(lista_formatada)}")
        
    if lista_formatada:
        dados_crimes = pd.DataFrame(lista_formatada, columns=colunas).sort_values(
            by="Data Publicação", ascending=False
        )
    else:
        dados_crimes = pd.DataFrame(columns=colunas)
        
    print(f"[DEBUG] ============ EXECUÇÃO CONCLUÍDA ============\n")
    return dados_crimes
