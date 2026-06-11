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

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Outfit', sans-serif; }

    .main-title {
        font-size: 3rem; font-weight: 800;
        background: linear-gradient(90deg, #FF4B4B, #FF8F8F);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle { font-size: 1.2rem; color: #888888; margin-bottom: 2rem; }
    .section-header {
        font-size: 1.1rem; font-weight: 600; color: #cccccc;
        border-bottom: 1px solid #333; padding-bottom: 0.4rem; margin-bottom: 0.8rem;
    }
    .tag-add { color: #4CAF50; font-weight: bold; }
    .tag-remove { color: #FF4B4B; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ── Cabeçalho ──────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">CrimesNews 📰⚖️</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Monitoramento Inteligente e Geolocalizado de Crimes em Municípios</div>', unsafe_allow_html=True)

# ── Sidebar – Período e limite ─────────────────────────────────────────────────
st.sidebar.markdown("### ⚙️ Parâmetros de Busca")
hoje = datetime.today().date()
duas_semanas_atras = hoje - timedelta(days=14)
data_inicio = st.sidebar.date_input("Data de Início", value=duas_semanas_atras, max_value=hoje)
data_fim = st.sidebar.date_input("Data de Fim", value=hoje, min_value=data_inicio, max_value=hoje)
noticias_maximo_retornado = st.sidebar.slider(
    "Limite de notícias por termo/bloco", min_value=5, max_value=50, value=10, step=5,
    help="Número máximo de notícias que o feed RSS retornará por grupo de municípios."
)
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Como funciona:**
1. Os termos e municípios são baixados de uma planilha pública no Google Sheets.
2. O scraper agrupa os municípios em buscas booleanas no Google News RSS.
3. Se houver correspondência, o link é decodificado e o texto extraído automaticamente.
""")

# ── Inicializa session_state com os dados da planilha ─────────────────────────
if "termos_ativos" not in st.session_state:
    st.session_state.termos_ativos = list(Core.lista_parametros_pesquisa)

if "municipios_ativos" not in st.session_state:
    # Mantemos o DataFrame completo; o usuário pode remover linhas pelo nome do município
    st.session_state.municipios_ativos = list(Core.dados_municipios["Municipio"].unique())

# ── Métricas gerais ────────────────────────────────────────────────────────────
st.markdown("### 📊 Parâmetros Ativos")
c1, c2, c3 = st.columns(3)
c1.metric("Termos de Busca", len(st.session_state.termos_ativos))
c2.metric("Municípios Monitorados", len(st.session_state.municipios_ativos))
c3.metric("Status da Conexão", "Ativa ✅")

# ── Seção de Refinamento ───────────────────────────────────────────────────────
with st.expander("⚙️ Refinar Termos e Cidades", expanded=False):
    tab_termos, tab_cidades = st.tabs(["📝 Termos de Pesquisa", "🗺️ Municípios"])

    # ── Tab: Termos ────────────────────────────────────────────────────────────
    with tab_termos:
        st.markdown("Selecione os termos que serão usados na busca. Você pode adicionar termos personalizados.")

        # Multiselect com todos os termos disponíveis (planilha + adicionados pelo usuário)
        todos_termos_disponiveis = sorted(set(
            list(Core.lista_parametros_pesquisa) + st.session_state.termos_ativos
        ))
        termos_selecionados = st.multiselect(
            "Termos ativos (desmarque para remover):",
            options=todos_termos_disponiveis,
            default=st.session_state.termos_ativos,
            key="ms_termos"
        )

        # Campo para adicionar termo personalizado
        col_inp_t, col_btn_t = st.columns([4, 1])
        with col_inp_t:
            novo_termo = st.text_input("Adicionar termo personalizado:", placeholder="ex: vandalismo", key="input_novo_termo", label_visibility="collapsed")
        with col_btn_t:
            if st.button("➕ Adicionar", key="btn_add_termo", use_container_width=True):
                novo_termo_strip = novo_termo.strip()
                if novo_termo_strip and novo_termo_strip not in st.session_state.termos_ativos:
                    st.session_state.termos_ativos = termos_selecionados + [novo_termo_strip]
                    st.rerun()
                elif novo_termo_strip in st.session_state.termos_ativos:
                    st.warning("Termo já está na lista.")

        # Aplica seleção do multiselect ao session_state
        if termos_selecionados != st.session_state.termos_ativos:
            st.session_state.termos_ativos = termos_selecionados

        st.caption(f"✅ {len(st.session_state.termos_ativos)} termo(s) ativo(s).")

        # Botão para restaurar padrão
        if st.button("🔄 Restaurar termos da planilha", key="btn_reset_termos"):
            st.session_state.termos_ativos = list(Core.lista_parametros_pesquisa)
            st.rerun()

    # ── Tab: Municípios ────────────────────────────────────────────────────────
    with tab_cidades:
        st.markdown("Selecione os municípios monitorados. Você pode adicionar cidades que não estão na planilha.")

        todos_municipios_disponiveis = sorted(set(
            list(Core.dados_municipios["Municipio"].unique()) + st.session_state.municipios_ativos
        ))
        municipios_selecionados = st.multiselect(
            "Municípios ativos (desmarque para remover):",
            options=todos_municipios_disponiveis,
            default=st.session_state.municipios_ativos,
            key="ms_municipios"
        )

        # Campo para adicionar município personalizado
        col_inp_m, col_btn_m = st.columns([4, 1])
        with col_inp_m:
            nova_cidade = st.text_input("Adicionar município:", placeholder="ex: Belo Horizonte", key="input_nova_cidade", label_visibility="collapsed")
        with col_btn_m:
            if st.button("➕ Adicionar", key="btn_add_cidade", use_container_width=True):
                nova_cidade_strip = nova_cidade.strip()
                if nova_cidade_strip and nova_cidade_strip not in st.session_state.municipios_ativos:
                    st.session_state.municipios_ativos = municipios_selecionados + [nova_cidade_strip]
                    st.rerun()
                elif nova_cidade_strip in st.session_state.municipios_ativos:
                    st.warning("Município já está na lista.")

        if municipios_selecionados != st.session_state.municipios_ativos:
            st.session_state.municipios_ativos = municipios_selecionados

        st.caption(f"✅ {len(st.session_state.municipios_ativos)} município(s) ativo(s).")

        if st.button("🔄 Restaurar municípios da planilha", key="btn_reset_municipios"):
            st.session_state.municipios_ativos = list(Core.dados_municipios["Municipio"].unique())
            st.rerun()

# ── Execução ───────────────────────────────────────────────────────────────────
st.markdown("### 🚀 Executar Monitoramento")

# Aviso se algum parâmetro estiver vazio
if not st.session_state.termos_ativos:
    st.warning("⚠️ Nenhum termo selecionado. Adicione ao menos um termo antes de iniciar.")
elif not st.session_state.municipios_ativos:
    st.warning("⚠️ Nenhum município selecionado. Adicione ao menos um município antes de iniciar.")
else:
    if st.button("Iniciar Busca de Notícias", type="primary", use_container_width=True):

        # Monta o DataFrame de municípios ativos (com Regional e Departamento quando disponível)
        df_mun_base = Core.dados_municipios.set_index("Municipio")
        rows = []
        for mun in st.session_state.municipios_ativos:
            if mun in df_mun_base.index:
                row = df_mun_base.loc[mun]
                rows.append({
                    "Municipio": mun,
                    "Regional": row["Regional"],
                    "Departamento": row["Departamento"]
                })
            else:
                # Município adicionado manualmente: sem Regional/Departamento
                rows.append({"Municipio": mun, "Regional": "—", "Departamento": "—"})
        df_municipios_override = pd.DataFrame(rows)

        # Fila thread-safe para logs
        log_queue = queue.Queue()
        def log_callback(message):
            log_queue.put(message)

        st.markdown("#### 🪵 Logs de Processamento")
        with st.spinner("Buscando e classificando notícias..."):
            df_resultados = Core.executar(
                data_inicio=data_inicio,
                data_fim=data_fim,
                noticias_maximo_retornado=noticias_maximo_retornado,
                progress_callback=log_callback,
                termos_selecionados=st.session_state.termos_ativos,
                municipios_df_override=df_municipios_override
            )

        # Renderiza logs — agora na thread da sessão Streamlit
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

            st.markdown("#### 📄 Tabela de Dados")
            st.dataframe(df_resultados, use_container_width=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_resultados.to_excel(writer, index=False, sheet_name='Crimes')
            buffer.seek(0)
            st.download_button(
                label="⬇️ Download Excel (crimes.xlsx)",
                data=buffer,
                file_name="crimes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

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
