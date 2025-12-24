# APLIKASI PRODUKSI LENGKAP - ARMOR (FLM & CM MONITORING)
import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta, date
import uuid
from PIL import Image, ExifTags
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import requests
from supabase import create_client, Client
import plotly.express as px

# ================== Konfigurasi Halaman Streamlit ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS Kustom (PLN Corporate Style) ==================
st.markdown(
    """
    <style>
        .stApp {
            background-color: #021021;
            background-image: radial-gradient(ellipse at bottom, rgba(52, 152, 219, 0.25) 0%, rgba(255,255,255,0) 50%),
                              linear-gradient(to top, #062b54, #021021);
            background-attachment: fixed;
            color: #ECF0F1;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 { color: #FFFFFF; }
        .stApp [data-testid="stHeading"] { color: #FFFFFF !important; }
        .stApp p { color: #ECF0F1 !important; }
        h1 { border-bottom: 2px solid #3498DB; padding-bottom: 10px; margin-bottom: 0.8rem; }
        [data-testid="stSidebar"] {
            background-color: rgba(2, 16, 33, 0.8);
            backdrop-filter: blur(5px);
            border-right: 1px solid rgba(52, 152, 219, 0.3);
        }
        .login-container [data-testid="stForm"], [data-testid="stForm"], [data-testid="stExpander"],
        [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stContainer"] {
            background-color: rgba(44, 62, 80, 0.6);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(52, 152, 219, 0.4);
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        .login-title { color: #FFFFFF; text-align: center; border-bottom: none; font-size: 1.9rem; white-space: nowrap; }
        div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button, div[data-testid="stForm"] button {
            font-weight: 600; border-radius: 8px; border: 1px solid #3498DB !important;
            background-color: transparent !important; color: #FFFFFF !important;
            transition: all 0.3s ease-in-out; padding: 10px 24px; width: 100%;
        }
        div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover, div[data-testid="stForm"] button:hover {
            background-color: #3498DB !important; border-color: #3498DB !important;
        }
        .delete-button button { border-color: #E74C3C !important; }
        .delete-button button:hover { background-color: #C0392B !important; border-color: #C0392B !important; }
        
        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {
            background-color: rgba(236, 240, 241, 0.4) !important;
            border-color: rgba(52, 152, 219, 0.4) !important;
            color: #FFFFFF !important;
        }
        label, div[data-testid="stWidgetLabel"] label { color: #FFFFFF !important; font-weight: 500; }
        [data-testid="stMetricLabel"] { color: #A9C5E1 !important; }
        [data-testid="stMetricValue"] { color: #FFFFFF !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== Koneksi & Konfigurasi Global ==================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()
JOB_TYPES = ["First Line Maintenance ( A )", "First Line Maintenance ( B )", "First Line Maintenance ( C )", "First Line Maintenance ( D )", "Corrective Maintenance", "Preventive Maintenance"]
ABSENSI_STATUS = ['Hadir', 'Sakit', 'Izin', 'Cuti', 'Tukar Dinas']

# ================== Fungsi-Fungsi Helper ==================
def verify_user_and_get_role(email, password):
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if session.user:
            role = session.user.user_metadata.get('role', 'operator')
            return {"role": role, "email": session.user.email}
    except Exception: return None
    return None

@st.cache_data(ttl=600)
def load_data_from_db():
    try:
        response = supabase.table('jobs').select('*').order('created_at', desc=True).limit(50000).execute()
        df = pd.DataFrame(response.data)
        if 'Tanggal' in df.columns and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_absensi_data():
    try:
        response = supabase.table('absensi').select('*').order('tanggal', desc=True).execute()
        df = pd.DataFrame(response.data)
        if 'tanggal' in df.columns and not df.empty:
            df['tanggal'] = pd.to_datetime(df['tanggal'])
        return df
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_personnel_data():
    try:
        response = supabase.table('personel').select('id, nama').order('nama', desc=False).execute()
        return pd.DataFrame(response.data)
    except Exception: return pd.DataFrame(columns=['id', 'nama'])

def logout():
    for key in list(st.session_state.keys()): del st.session_state[key]
    st.session_state.logged_in = False
    st.rerun()

def generate_next_id(df, jenis):
    prefix_map = {'First Line Maintenance': 'FLM', 'Corrective Maintenance': 'CM', 'Preventive Maintenance': 'PM'}
    prefix = next((p for key, p in prefix_map.items() if jenis.startswith(key)), 'JOB')
    if df.empty: return f"{prefix}-001"
    relevant_ids = df[df['ID'].str.startswith(prefix, na=False)]['ID'].str.split('-').str[1].dropna().astype(int)
    if relevant_ids.empty: return f"{prefix}-001"
    return f"{prefix}-{relevant_ids.max() + 1:03d}"

def fix_image_orientation(image):
    try:
        exif = image.getexif()
        for tag, value in exif.items():
            if ExifTags.TAGS.get(tag) == 'Orientation':
                if value == 3: image = image.rotate(180, expand=True)
                elif value == 6: image = image.rotate(270, expand=True)
                elif value == 8: image = image.rotate(90, expand=True)
    except Exception: pass
    return image

def upload_image_to_storage(uploaded_file):
    if not uploaded_file: return ""
    try:
        image = Image.open(uploaded_file).convert("RGB")
        image = fix_image_orientation(image)
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=80)
        file_name = f"{uuid.uuid4()}.jpg"
        supabase.storage.from_("evidences").upload(file=output.getvalue(), path=file_name, file_options={"content-type": "image/jpeg"})
        return supabase.storage.from_("evidences").get_public_url(file_name)
    except Exception: return ""

def create_excel_report_with_images(filtered_data):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        filtered_data.drop(columns=['Hapus'], errors='ignore').to_excel(writer, sheet_name='Laporan', index=False)
    return output.getvalue()

def create_pdf_report(filtered_data, report_type):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = [Paragraph(f"LAPORAN {report_type.upper()}", getSampleStyleSheet()['Title'])]
    doc.build(elements)
    return buffer.getvalue()

# ================== Logika Utama ==================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        with st.form("login"):
            st.markdown('<h1 class="login-title">ARMOR LOGIN</h1>', unsafe_allow_html=True)
            u = st.text_input("Email").lower()
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user = verify_user_and_get_role(u, p)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user['role']
                    st.session_state.user_email = user['email']
                    st.rerun()
                else: st.error("Login Gagal")
    st.stop()

# Load Data
if 'data' not in st.session_state: st.session_state.data = load_data_from_db()
df = st.session_state.data.copy()
if 'Nama Pelaksana' in df.columns: df.rename(columns={'Nama Pelaksana': 'Nama Personel'}, inplace=True)

with st.sidebar:
    st.header("MENU")
    menu_options = ["Input Data", "Report Data", "Analisis FLM", "Absensi Personel"]
    if st.session_state.user_role == 'admin': menu_options.append("Kelola Personel")
    menu = st.radio("Navigasi", menu_options, label_visibility="collapsed")
    if st.button("Logout"): logout()

# --- HALAMAN INPUT DATA ---
if menu == "Input Data":
    st.header("Input Pekerjaan")
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            tgl = st.date_input("Tanggal", date.today())
            jns = st.selectbox("Jenis", JOB_TYPES)
            ar = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP", "Common"])
            sr = st.text_input("Nomor SR")
        with c2:
            prs = st.text_input("Nama Personel")
            sts = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
            ket = st.text_area("Keterangan")
        ev_b = st.file_uploader("Evidence Before", type=['jpg','jpeg','png'])
        ev_a = st.file_uploader("Evidence After", type=['jpg','jpeg','png'])
        
        if st.form_submit_button("Simpan"):
            new_id = generate_next_id(df, jns)
            u_b = upload_image_to_storage(ev_b)
            u_a = upload_image_to_storage(ev_a)
            supabase.table("jobs").insert({"ID":new_id, "Tanggal":str(tgl), "Jenis":jns, "Area":ar, "Nomor SR":sr, "Nama Pelaksana":prs, "Keterangan":ket, "Status":sts, "Evidance":u_b, "Evidance After":u_a}).execute()
            st.cache_data.clear()
            st.session_state.data = load_data_from_db()
            st.success("Data Berhasil Disimpan!"); st.rerun()

# --- HALAMAN REPORT DATA ---
elif menu == "Report Data":
    st.header("Data Pekerjaan")
    st.data_editor(df, use_container_width=True)
    if st.button("Refresh"):
        st.cache_data.clear()
        st.session_state.data = load_data_from_db()
        st.rerun()

# --- HALAMAN ANALISIS (DENGAN FITUR BARU) ---
elif menu == "Analisis FLM":
    st.header("📊 Dashboard Analisis & Scoreboard")
    
    if df.empty:
        st.warning("Data kosong.")
    else:
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
        st.sidebar.subheader("Filter Analisis")
        s_d = st.sidebar.date_input("Mulai", df['Tanggal'].min().date())
        e_d = st.sidebar.date_input("Selesai", date.today())
        
        # Filter Dasar FLM
        df_flm = df[(df['Tanggal'].dt.date >= s_d) & (df['Tanggal'].dt.date <= e_d) & (df['Jenis'].str.startswith('First Line', na=False))]
        
        # 1. Leaderboard Personel FLM (Eksisting)
        st.subheader("🏆 Leaderboard Personel (FLM)")
        if not df_flm.empty:
            pers_counts = df_flm['Nama Personel'].str.split(',').explode().str.strip().value_counts().reset_index()
            pers_counts.columns = ['Nama', 'Total']
            st.plotly_chart(px.bar(pers_counts, x='Total', y='Nama', orientation='h', template='plotly_dark', color='Total'), use_container_width=True)
        
        st.markdown("---")
        
        # 2. Scoreboard Area & Peralatan FLM (TAMBAHAN BARU)
        st.subheader("📍 Scoreboard Area & Peralatan Tersering (FLM)")
        c1, c2 = st.columns(2)
        if not df_flm.empty:
            with c1:
                area_cnt = df_flm['Area'].value_counts().reset_index()
                area_cnt.columns = ['Area', 'Jumlah']
                st.plotly_chart(px.pie(area_cnt, names='Area', values='Jumlah', title="Distribusi FLM per Area", template='plotly_dark'), use_container_width=True)
            with c2:
                # Top 10 Peralatan berdasarkan Keterangan
                eq_cnt = df_flm['Keterangan'].value_counts().nlargest(10).reset_index()
                eq_cnt.columns = ['Peralatan/Pekerjaan', 'Frekuensi']
                st.plotly_chart(px.bar(eq_cnt, x='Frekuensi', y='Peralatan/Pekerjaan', orientation='h', title="Top 10 Peralatan di-FLM", template='plotly_dark', color_discrete_sequence=['#3498DB']), use_container_width=True)

        st.markdown("---")

        # 3. Scoreboard Dominan Kerusakan CM (TAMBAHAN BARU)
        st.subheader("🛠️ Scoreboard Dominan Kerusakan (Corrective Maintenance)")
        df_cm = df[(df['Tanggal'].dt.date >= s_d) & (df['Tanggal'].dt.date <= e_d) & (df['Jenis'] == 'Corrective Maintenance')]
        
        if df_cm.empty:
            st.info("Tidak ada data CM pada periode ini.")
        else:
            cm_area = df_cm['Area'].value_counts().reset_index()
            cm_area.columns = ['Area', 'Kasus']
            
            col_cm1, col_cm2 = st.columns([1, 2])
            with col_cm1:
                st.metric("Total Kerusakan (CM)", f"{len(df_cm)} Kasus")
                st.plotly_chart(px.pie(cm_area, names='Area', values='Kasus', hole=0.4, title="Proporsi Kerusakan", template='plotly_dark', color_discrete_sequence=px.colors.sequential.Reds_r), use_container_width=True)
            with col_cm2:
                st.plotly_chart(px.bar(cm_area, x='Kasus', y='Area', orientation='h', title="Area Dominan Gangguan/Kerusakan", template='plotly_dark', color='Kasus', color_continuous_scale='Reds'), use_container_width=True)

# --- HALAMAN ABSENSI ---
elif menu == "Absensi Personel":
    st.header("🗓️ Absensi")
    df_abs = load_absensi_data()
    st.dataframe(df_abs, use_container_width=True)

# --- HALAMAN KELOLA PERSONEL ---
elif menu == "Kelola Personel":
    st.header("👥 Kelola Personel")
    df_p = load_personnel_data()
    st.data_editor(df_p, use_container_width=True)
