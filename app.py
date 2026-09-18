import streamlit as st
import pandas as pd
from datetime import datetime
import io
import os
import re
import numpy as np
import zipfile
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Configuração inicial
st.set_page_config(page_title="Controle de Entrega FGV", page_icon="📦", layout="centered")

# Garante a criação da pasta para salvar as assinaturas digitalizadas
if not os.path.exists("assinaturas"):
    os.makedirs("assinaturas")

# Função para limpar o nome do colaborador
def sanitizar_nome(nome):
    nome_str = str(nome)
    nome_limpo = re.sub(r'[^a-zA-Z0-9À-ÖØ-öø-ÿ\s]', '', nome_str)
    return nome_limpo.strip().replace(' ', '_')

# --- CUSTOMIZAÇÃO ESTÉTICA (FLAT DESIGN E CORES FGV) ---
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    
    button, input, div[data-testid="stExpander"], div[data-testid="stAlert"], div[data-testid="metric-container"] {
        border-radius: 0px !important;
        box-shadow: none !important;
    }

    .stButton > button[kind="primary"],
    div[data-testid="stDownloadButton"] > button {
        background-color: #004b87 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover,
    div[data-testid="stDownloadButton"] > button:hover {
        background-color: #003366 !important;
    }
    
    .stButton > button[kind="secondary"] { background-color: #FFFFFF !important; color: #d9534f !important; border: 1px solid #d9534f !important; }
    .stButton > button[kind="secondary"]:hover { background-color: #d9534f !important; color: #FFFFFF !important; }

    div[data-testid="stNumberInput"] button { background-color: #F4F7F9 !important; color: #004b87 !important; border: 1px solid #CCCCCC !important; }
    div[data-testid="stNumberInput"] button:hover { background-color: #004b87 !important; color: #FFFFFF !important; border: 1px solid #004b87 !important; }
    
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="fileUploader"] > div:focus-within {
        border-color: #004b87 !important;
        box-shadow: inset 0 0 0 1px #004b87 !important;
    }

    div[data-testid="stExpander"] { border: 1px solid #EAEAEA !important; background-color: #FAFAFA !important; }
    
    div[data-testid="stAlert"] { border-left: 4px solid #004b87 !important; background-color: #F4F7F9 !important; color: #003366 !important; }
    div[data-testid="metric-container"] { border-left: 4px solid #004b87; padding-left: 15px; background-color: #F4F7F9; padding-top: 10px; padding-bottom: 10px; }
    
    /* === PERSONALIZAÇÃO DAS ABAS (TABS) PADRÃO FGV === */
    button[data-baseweb="tab"] { background-color: transparent !important; }
    button[data-baseweb="tab"] > div[data-testid="stMarkdownContainer"] > p { font-size: 16px; font-weight: bold; color: #666666; transition: color 0.3s; }
    button[data-baseweb="tab"]:hover > div[data-testid="stMarkdownContainer"] > p { color: #004b87 !important; }
    button[data-baseweb="tab"][aria-selected="true"] > div[data-testid="stMarkdownContainer"] > p { color: #004b87 !important; }
    div[data-baseweb="tab-highlight"] { background-color: #004b87 !important; }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- MODAL DE ASSINATURA DIGITAL ---
@st.dialog("✍️ Coleta de Assinatura do Colaborador")
def modal_assinatura(index, novas_caixas, novos_malotes):
    row = st.session_state.df.loc[index]
    st.markdown(f"Colaborador: **{row['Nome']}** ({row.get('Municipio', '')}-{row.get('UF', '')})")
    st.markdown("Por favor, solicite que o colaborador desenhe sua rubrica ou assinatura no quadro abaixo:")
    
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=150,
        width=450,
        drawing_mode="freedraw",
        key=f"canvas_{index}",
        return_image_data=True
    )
    
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if st.button("Salvar e Confirmar", type="primary", use_container_width=True):
            agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            caminho_img = ""
            
            if canvas_result.image_data is not None:
                img_arr = canvas_result.image_data
                img = Image.fromarray(img_arr.astype('uint8'), 'RGBA')
                
                nome_formatado = sanitizar_nome(row['Nome'])
                data_hora_arquivo = datetime.now().strftime("%d%m%Y_%H%M%S")
                
                filename = f"assinaturas/assinatura_{nome_formatado}_{data_hora_arquivo}.png"
                img.save(filename)
                caminho_img = filename
            
            st.session_state.df.loc[index, 'Caixas_Entregues'] = novas_caixas
            st.session_state.df.loc[index, 'Malotes_Entregues'] = novos_malotes
            st.session_state.df.loc[index, 'Data_Hora_Check'] = agora
            st.session_state.df.loc[index, 'Status'] = "Entregue"
            st.session_state.df.loc[index, 'Arquivo_Assinatura'] = caminho_img
            
            st.rerun()
            
    with col_m2:
        if st.button("Cancelar", type="secondary", use_container_width=True):
            st.rerun()

# --- CABEÇALHO ---
try:
    st.image("logo_fgv.png", width=180)
except:
    st.markdown("<div style='color:#004b87; font-weight:bold;'>[LOGO FGV]</div>", unsafe_allow_html=True)

st.markdown("<h2 style='color: #004b87; margin-top: 5px; margin-bottom: 20px;'>Controle de entrega de materiais</h2>", unsafe_allow_html=True)
st.info("Carregue a base de itinerantes para iniciar a operação.")

# --- LÓGICA DO APLICATIVO ---
arquivo_upload = st.file_uploader("📥 Subir Planilha (Excel ou CSV)", type=["csv", "xlsx"])

if arquivo_upload is not None:
    if 'df' not in st.session_state:
        if arquivo_upload.name.endswith('.csv'):
            st.session_state.df = pd.read_csv(arquivo_upload)
        else:
            st.session_state.df = pd.read_excel(arquivo_upload)
            
        if 'Status' not in st.session_state.df.columns:
            st.session_state.df['Status'] = "Pendente"
    
    df = st.session_state.df
    
    # --- DASHBOARD DE PROGRESSO ---
    st.divider()
    st.markdown("<h3 style='color: #004b87; margin-bottom: 15px;'>📊 Painel de Acompanhamento</h3>", unsafe_allow_html=True)
    
    total_pessoas = len(df)
    total_entregues = len(df[df['Status'] == "Entregue"])
    total_faltam = total_pessoas - total_entregues
    
    dash_col1, dash_col2, dash_col3 = st.columns(3)
    dash_col1.metric("👥 Total Previsto", total_pessoas)
    dash_col2.metric("✅ Entregues", total_entregues)
    dash_col3.metric("⏳ Faltam", total_faltam)
    
    st.divider()
    
    # --- BARRA DE PESQUISA ---
    busca = st.text_input("🔍 Buscar por Nome, UF ou Município:", "")
    
    if busca:
        df_filtrado = df[
            df['Nome'].str.contains(busca, case=False, na=False) |
            df['UF'].str.contains(busca, case=False, na=False) | 
            df['Municipio'].str.contains(busca, case=False, na=False)
        ]
    else:
        df_filtrado = df
        
    # --- DIVISÃO DAS LISTAS (PENDENTES VS FINALIZADOS) ---
    df_pendentes = df_filtrado[df_filtrado['Status'] != "Entregue"]
    df_finalizados = df_filtrado[df_filtrado['Status'] == "Entregue"]
    
    aba_pendentes, aba_finalizados = st.tabs([f"⏳ Pendentes ({len(df_pendentes)})", f"✅ Finalizados ({len(df_finalizados)})"])
    
    # === ABA 1: PENDENTES ===
    with aba_pendentes:
        if df_pendentes.empty:
            st.success("Nenhum material pendente encontrado para esta busca! 🎉")
        else:
            for index, row in df_pendentes.iterrows():
                with st.expander(f"{row['Nome']} ({row.get('Municipio', '')}-{row.get('UF', '')})"):
                    st.markdown(f"""
                    <div style="line-height: 1.4; margin-bottom: 10px;">
                        <div style="font-size: 13px; color: #666666;">UF: <b>{row.get('UF', '')}</b></div>
                        <div style="font-size: 13px; color: #666666;">Município: <b>{row.get('Municipio', '')}</b></div>
                        <div style="font-size: 18px; color: #004b87; margin-top: 4px;">Nome: <b>{row['Nome']}</b></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"**Previsto:** {row['Caixas_Previstas']} Caixas | {row['Malotes_Previstos']} Malotes")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        novas_caixas = st.number_input("Caixas Reais", min_value=0, value=int(row['Caixas_Previstas']), key=f"c_{index}")
                    with col2:
                        novos_malotes = st.number_input("Malotes Reais", min_value=0, value=int(row['Malotes_Previstos']), key=f"m_{index}")
                    
                    if st.button("Confirmar Entrega (Check)", key=f"btn_{index}", type="primary", use_container_width=True):
                        modal_assinatura(index, novas_caixas, novos_malotes)

    # === ABA 2: FINALIZADOS ===
    with aba_finalizados:
        if df_finalizados.empty:
            st.info("Nenhuma entrega finalizada ainda.")
        else:
            for index, row in df_finalizados.iterrows():
                with st.expander(f"{row['Nome']} ({row.get('Municipio', '')}-{row.get('UF', '')}) ✓ [ENTREGUE]"):
                    st.markdown(f"""
                    <div style="line-height: 1.4; margin-bottom: 10px;">
                        <div style="font-size: 13px; color: #666666;">UF: <b>{row.get('UF', '')}</b></div>
                        <div style="font-size: 13px; color: #666666;">Município: <b>{row.get('Municipio', '')}</b></div>
                        <div style="font-size: 18px; color: #004b87; margin-top: 4px;">Nome: <b>{row['Nome']}</b></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.success(f"Entregue e registrado às: {st.session_state.df.loc[index, 'Data_Hora_Check']}")
                    st.markdown(f"**Volumes Finais:** {st.session_state.df.loc[index, 'Caixas_Entregues']} Caixas | {st.session_state.df.loc[index, 'Malotes_Entregues']} Malotes")
                    
                    if 'Arquivo_Assinatura' in st.session_state.df.columns and pd.notna(st.session_state.df.loc[index, 'Arquivo_Assinatura']):
                        st.info("📝 Assinatura digital capturada e armazenada com sucesso.")
                    
                    if st.button("Restaurar Check (Corrigir)", key=f"undo_{index}", type="secondary", use_container_width=True):
                        st.session_state.df.loc[index, 'Caixas_Entregues'] = np.nan
                        st.session_state.df.loc[index, 'Malotes_Entregues'] = np.nan
                        st.session_state.df.loc[index, 'Data_Hora_Check'] = ""
                        st.session_state.df.loc[index, 'Status'] = "Pendente"
                        st.session_state.df.loc[index, 'Arquivo_Assinatura'] = ""
                        st.rerun()
                
    # --- ÁREA DE DOWNLOAD (PLANILHA E ASSINATURAS) ---
    st.divider()
    st.markdown("<h3 style='color: #004b87;'>Encerrar Operação (Downloads)</h3>", unsafe_allow_html=True)
    st.warning("⚠️ Lembre-se de baixar a Planilha e as Assinaturas ao fim da operação para não perder os dados!")
    
    col_down1, col_down2 = st.columns(2)
    
    # 1. Download da Planilha Atualizada
    with col_down1:
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            st.session_state.df.to_excel(writer, index=False, sheet_name='Logistica_Executada')
        
        st.download_button(
            label="💾 Baixar Planilha Atualizada",
            data=buffer_excel.getvalue(),
            file_name=f"controle_materiais_{datetime.now().strftime('%d%m%Y_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )

    # 2. Download do pacote ZIP com as assinaturas
    with col_down2:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            if os.path.exists("assinaturas"):
                for root, dirs, files in os.walk("assinaturas"):
                    for file in files:
                        if file.endswith(".png"):
                            file_path = os.path.join(root, file)
                            # Adiciona no ZIP apenas com o nome do arquivo, sem criar subpastas
                            zip_file.write(file_path, arcname=file) 
                            
        st.download_button(
            label="🗂️ Baixar Assinaturas (.ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"assinaturas_fgv_{datetime.now().strftime('%d%m%Y_%H%M')}.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )