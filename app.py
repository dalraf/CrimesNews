import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import queue
import Core
import io

# Configuração da página do Streamlit
st.set_page_config(
    page_title="CrimesNews 📰⚖️",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS customizada para visual premium
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4B4B, #FF8F8F);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .subtitle {
        font-size: 1.2rem;
        color: #888888;
        margin-bottom: 2rem;
    }
    
    .card {
        background-color: #1e1e1e;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 1rem;
        border-left: 5px solid #FF4B4B;
    }
    
    .log-box {
        background-color: #0f0f0f;
        color: #00FF00;
        font-family: 'Courier New', Courier, monospace;
        padding: 1rem;
        border-radius: 8px;
        height: 250px;
        overflow-y: scroll;
        margin-bottom: 1.5rem;
        border: 1px solid #333;
    }
</style>
""", unsafe_allow_html=True)

# Layout do Cabeçalho
st.markdown('<div class="main-title">CrimesNews 📰⚖️</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Monitoramento Inteligente e Geolocalizado de Crimes em Municípios</div>', unsafe_allow_html=True)

# Barra Lateral de Configuração
st.sidebar.markdown("### ⚙️ Parâmetros de Busca")

# Datas padrão
hoje = datetime.today().date()
duas_semanas_atras = hoje - timedelta(days=14)

data_inicio = st.sidebar.date_input("Data de Início", value=duas_semanas_atras, max_value=hoje)
data_fim = st.sidebar.date_input("Data de Fim", value=hoje, min_value=data_inicio, max_value=hoje)

noticias_maximo_retornado = st.sidebar.slider(
    "Limite de notícias por termo/bloco",
    min_value=5,
    max_value=50,
    value=10,
    step=5,
    help="Define o número máximo de notícias que o feed RSS do Google retornará para cada grupo de municípios pesquisado."
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
**Como funciona:**
1. Os termos e municípios são baixados de uma planilha pública no Google Sheets.
2. O scraper agrupa os municípios em buscas booleanas no Google News RSS.
3. Se houver correspondência, o link é decodificado e o texto extraído automaticamente.
""")

# Métricas rápidas da Planilha antes de rodar
st.markdown("### 📊 Dados dos Parâmetros (Planilha Google)")
col1, col2, col3 = st.columns(3)

with col1:
    total_termos = len(Core.lista_parametros_pesquisa)
    st.metric("Termos de Busca", total_termos)
    with st.expander("Ver Termos"):
        st.write(Core.lista_parametros_pesquisa)

with col2:
    total_municipios = len(Core.dados_municipios)
    st.metric("Municípios Monitorados", total_municipios)
    with st.expander("Ver Municípios"):
        st.dataframe(Core.dados_municipios[["Municipio", "Regional", "Departamento"]])

with col3:
    st.metric("Status da Conexão", "Ativa ✅")

# Área de Execução
st.markdown("### 🚀 Executar Monitoramento")

if st.button("Iniciar Busca de Notícias", type="primary", use_container_width=True):
    # Fila thread-safe: workers apenas fazem queue.put(msg).
    # A thread principal drena a fila APÓS a execução terminar e renderiza
    # os logs com segurança dentro do contexto da sessão Streamlit.
    log_queue = queue.Queue()

    def log_callback(message):
        """Apenas enfileira a mensagem — nunca toca no Streamlit diretamente."""
        log_queue.put(message)

    # Executar scraping (bloqueante na thread principal do Streamlit)
    st.markdown("#### 🪵 Logs de Processamento")
    with st.spinner("Buscando e classificando notícias..."):
        df_resultados = Core.executar(
            data_inicio=data_inicio,
            data_fim=data_fim,
            noticias_maximo_retornado=noticias_maximo_retornado,
            progress_callback=log_callback
        )

    # Drenar fila e renderizar logs — agora na thread da sessão Streamlit
    logs_list = []
    while not log_queue.empty():
        logs_list.append(log_queue.get_nowait())

    if logs_list:
        log_html = (
            "<div style='background-color:#0f0f0f; color:#00FF00; font-family:monospace; "
            "padding:10px; border-radius:5px; max-height:350px; overflow-y:auto; "
            "font-size:12px; line-height:1.6;'>"
        )
        log_html += "".join([f"<div>{line}</div>" for line in logs_list])
        log_html += "</div>"
        st.markdown(log_html, unsafe_allow_html=True)

    st.success(f"Busca finalizada! {len(df_resultados)} correspondências encontradas.")

    if not df_resultados.empty:
        # Exibir Métricas de Resultados
        st.markdown("### 📈 Resumo das Notícias Encontradas")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Notícias Encontradas", len(df_resultados))
        with m2:
            cidade_top = df_resultados["Município"].value_counts().idxmax()
            cidade_top_qtd = df_resultados["Município"].value_counts().max()
            st.metric("Cidade mais citada", f"{cidade_top} ({cidade_top_qtd})")
        with m3:
            crime_top = df_resultados["Termo de Pesquisa"].value_counts().idxmax()
            crime_top_qtd = df_resultados["Termo de Pesquisa"].value_counts().max()
            st.metric("Termo mais frequente", f"{crime_top} ({crime_top_qtd})")

        # Exibir Tabela de Resultados
        st.markdown("#### 📄 Tabela de Dados")
        st.dataframe(df_resultados, use_container_width=True)

        # Gerar buffer em memória do Excel para download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_resultados.to_excel(writer, index=False, sheet_name='Crimes')
        buffer.seek(0)

        st.download_button(
            label="Download Excel (crimes.xlsx)",
            data=buffer,
            file_name="crimes.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        # Gráficos Dinâmicos
        st.markdown("### 📊 Gráficos Estatísticos")
        g1, g2 = st.columns(2)
        with g1:
            st.markdown("**Crimes por Município**")
            st.bar_chart(df_resultados["Município"].value_counts())
        with g2:
            st.markdown("**Notícias por Regional**")
            st.bar_chart(df_resultados["Regional"].value_counts())

    else:
        st.info("Nenhuma notícia foi encontrada para os critérios selecionados no período.")
