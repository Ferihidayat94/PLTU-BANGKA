# APLIKASI PRODUKSI LENGKAP - ARMOR (VERSION: SORTED LEADERBOARD)
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

# ================== CSS Kustom ==================
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
        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {
            background-color: rgba(236, 240, 241, 0.4) !important;
            color: #FFFFFF !important;
        }
        label, div[data-testid="stWidgetLabel"] label { color: #FFFFFF !important; }
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
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_absensi_data():
    try:
        response = supabase.table('absensi').select('*').order('tanggal', desc=True).limit(50000).execute()
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
    for key in list(st.session_state.keys()):
        if key not in ['logged_in', 'user_role', 'user_email']: del st.session_state[key]
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
        orientation = next((tag for tag, name in ExifTags.TAGS.items() if name == 'Orientation'), None)
        if orientation and orientation in exif:
            actions = {3: 180, 6: 270, 8: 90}
            if exif[orientation] in actions: image = image.rotate(actions[exif[orientation]], expand=True)
    except Exception: pass
    return image

def upload_image_to_storage(uploaded_file):
    if uploaded_file is None: return ""
    try:
        image = Image.open(uploaded_file).convert("RGB")
        image = fix_image_orientation(image)
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="JPEG", quality=85, optimize=True)
        file_name = f"{uuid.uuid4()}.jpeg"
        supabase.storage.from_("evidences").upload(file=output_buffer.getvalue(), path=file_name, file_options={"content-type": "image/jpeg"})
        return supabase.storage.from_("evidences").get_public_url(file_name)
    except Exception: return ""

def create_excel_report_with_images(filtered_data):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        filtered_data.drop(columns=['Hapus'], errors='ignore').to_excel(writer, sheet_name='Laporan', index=False)
    output.seek(0)
    return output.getvalue()

def create_pdf_report(filtered_data, report_type):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"<b>LAPORAN MONITORING {report_type.upper()}</b>", styles["Title"])]
    for _, row in filtered_data.iterrows():
        data = [["ID", str(row.get('ID', ''))], ["Tanggal", str(row.get('Tanggal'))], ["Jenis", str(row.get('Jenis', ''))], ["Status", str(row.get('Status', ''))]]
        elements.append(Table(data, colWidths=[100, 380], style=[('BOX', (0,0), (-1,-1), 1, colors.black), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
        elements.append(PageBreak())
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ================== Logika Login ==================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.get("logged_in"):
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">ARMOR</h1>', unsafe_allow_html=True)
        try: st.image("logo.png", width=150)
        except FileNotFoundError: pass
        with st.form("login_form"):
            st.markdown('<h3 style="color: #FFFFFF; text-align: center;">User Login</h3>', unsafe_allow_html=True)
            email = st.text_input("Email", placeholder="e.g., admin@example.com").lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user_data = verify_user_and_get_role(email, password)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user_data['email']
                    st.session_state.user_role = user_data['role']
                    st.session_state.last_activity = datetime.now()
                    st.rerun()
                else: st.error("Email atau password salah.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ================== Sesi & Sidebar ==================
user_role = st.session_state.get("user_role", "operator")
if 'last_activity' not in st.session_state or datetime.now() - st.session_state.last_activity > timedelta(minutes=30): logout()
st.session_state.last_activity = datetime.now()

if 'data' not in st.session_state: st.session_state.data = load_data_from_db()
df = st.session_state.data.copy()
if 'Nama Pelaksana' in df.columns: df.rename(columns={'Nama Pelaksana': 'Nama Personel'}, inplace=True)

with st.sidebar:
    st.title("Navigasi")
    try: st.image("logo.png", use_container_width=True)
    except FileNotFoundError: pass
    menu_options = ["Input Data", "Report Data", "Analisis FLM", "Absensi Personel"]
    if user_role == 'admin': menu_options.append("Kelola Personel")
    menu = st.radio("Pilih Halaman:", menu_options, label_visibility="collapsed")
    if st.button("Logout"): logout()
    st.markdown("---"); st.caption("Tim Operasi - PLTU Bangka 🛠️")

# ================== Halaman: Input Data ==================
if menu == "Input Data":
    st.header("Input Data Pekerjaan Baru")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tanggal = st.date_input("Tanggal", date.today())
            jenis = st.selectbox("Jenis Pekerjaan", JOB_TYPES)
            area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP", "Common"])
            nomor_sr = st.text_input("Nomor SR")
        with col2:
            nama_personel = st.text_input("Nama Personel")
            status = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
            keterangan = st.text_area("Keterangan")
        ev_b = st.file_uploader("Evidence Before", type=["png", "jpg", "jpeg"])
        ev_a = st.file_uploader("Evidence After", type=["png", "jpg", "jpeg"])
        if st.form_submit_button("Simpan Data"):
            if not all([nomor_sr, nama_personel, keterangan]): st.error("Lengkapi data.")
            else:
                new_id = generate_next_id(df, jenis)
                u1 = upload_image_to_storage(ev_b)
                u2 = upload_image_to_storage(ev_a)
                payload = {"ID": new_id, "Tanggal": str(tanggal), "Jenis": jenis, "Area": area, "Nomor SR": nomor_sr, "Nama Pelaksana": nama_personel, "Keterangan": keterangan, "Status": status, "Evidance": u1, "Evidance After": u2}
                supabase.table("jobs").insert(payload).execute()
                st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.rerun()

# ================== Halaman: Report Data ==================
elif menu == "Report Data":
    st.header("Integrated Data & Report")
    data_to_display = df.copy()
    if 'Hapus' not in data_to_display.columns: data_to_display['Hapus'] = False
    col_config = {"Hapus": st.column_config.CheckboxColumn("Hapus?"), "ID": st.column_config.TextColumn("ID", disabled=True)}
    st.data_editor(data_to_display, key="data_editor", use_container_width=True, column_config=col_config)
    if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.rerun()

# ================== Halaman: Analisis FLM (SORTED) ==================
elif menu == "Analisis FLM":
    st.header("📊 Analisis FLM & Kerusakan")
    if df.empty: st.info("Data tidak tersedia.")
    else:
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
        st.sidebar.subheader("Filter Dashboard")
        s_date = st.sidebar.date_input("Mulai", df['Tanggal'].min().date())
        e_date = st.sidebar.date_input("Selesai", date.today())
        
        # Filter FLM
        df_flm = df[(df['Tanggal'].dt.date >= s_date) & (df['Tanggal'].dt.date <= e_date) & (df['Jenis'].str.startswith('First Line', na=False))]
        
        if not df_flm.empty:
            flm_c = df_flm['Jenis'].value_counts().reset_index()
            flm_c.columns = ['Jenis', 'Jumlah']
            
            # --- Leaderboard Personel (Highest at Top) ---
            st.header("🏆 Skor Personel FLM")
            p_cnt = df_flm['Nama Personel'].str.split(',').explode().str.strip().value_counts().reset_index()
            p_cnt.columns = ['Nama', 'Total']
            fig_p = px.bar(p_cnt, x='Total', y='Nama', orientation='h', title='Leaderboard Personel', color='Total', template='plotly_dark')
            fig_p.update_yaxes(categoryorder='total ascending') # MEMASTIKAN YANG TERTINGGI DI ATAS
            st.plotly_chart(fig_p, use_container_width=True)

            # --- Scoreboard Area & Peralatan (Highest at Top) ---
            st.markdown("---")
            st.header("📍 Scoreboard Area & Peralatan (FLM)")
            ca1, ca2 = st.columns(2)
            with ca1:
                area_cnt = df_flm['Area'].value_counts().reset_index()
                area_cnt.columns = ['Area', 'Jumlah']
                fig_area = px.bar(area_cnt, x='Jumlah', y='Area', orientation='h', title='Frekuensi FLM per Area', template='plotly_dark', color='Jumlah')
                fig_area.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_area, use_container_width=True)
            with ca2:
                eq_cnt = df_flm['Keterangan'].value_counts().nlargest(10).reset_index()
                eq_cnt.columns = ['Peralatan', 'Frekuensi']
                fig_eq = px.bar(eq_cnt, x='Frekuensi', y='Peralatan', orientation='h', title='10 Alat Sering Dirawat', template='plotly_dark', color='Frekuensi')
                fig_eq.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_eq, use_container_width=True)

            # --- Scoreboard Kerusakan CM (Highest at Top) ---
            st.markdown("---")
            st.header("🛠️ Analisis Kerusakan (Corrective Maintenance)")
            df_cm = df[(df['Tanggal'].dt.date >= s_date) & (df['Tanggal'].dt.date <= e_date) & (df['Jenis'] == 'Corrective Maintenance')]
            if not df_cm.empty:
                cm_area = df_cm['Area'].value_counts().reset_index()
                cm_area.columns = ['Area', 'Kasus']
                fig_cm = px.bar(cm_area, x='Kasus', y='Area', orientation='h', title='Area Dominan Gangguan (CM)', color='Kasus', color_continuous_scale='Reds', template='plotly_dark')
                fig_cm.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_cm, use_container_width=True)

# ================== Halaman: Absensi Personel (SORTED) ==================
elif menu == "Absensi Personel":
    st.header("🗓️ Input & Dashboard Absensi")
    df_personnel = load_personnel_data()
    pers_list = df_personnel['nama'].tolist() if not df_personnel.empty else []

    if user_role == 'admin':
        with st.expander("✅ Input Absensi Massal (Hadir)", expanded=True):
            with st.form("mass_abs"):
                c1, c2 = st.columns([3, 1])
                with c1: sel_pers = st.multiselect("Pilih Personel Hadir:", options=pers_list, default=pers_list)
                with c2: tgl_m = st.date_input("Tanggal", date.today())
                if st.form_submit_button("Simpan Massal"):
                    records = [{"tanggal": str(tgl_m), "nama_personel": n, "status_absensi": "Hadir", "keterangan": ""} for n in sel_pers]
                    supabase.table("absensi").upsert(records, on_conflict="tanggal,nama_personel").execute()
                    st.cache_data.clear(); st.rerun()

    st.markdown("---")
    st.subheader("📊 Laporan Kehadiran & Ketidakhadiran")
    df_absensi = load_absensi_data()
    if not df_absensi.empty:
        df_absensi['tanggal'] = pd.to_datetime(df_absensi['tanggal']).dt.tz_localize(None)
        
        # Filter Periode
        c_y, c_m = st.columns(2)
        with c_y: sel_year = st.selectbox("Tahun:", sorted(df_absensi['tanggal'].dt.year.unique(), reverse=True))
        with c_m: sel_month = st.selectbox("Bulan:", ["Semua Bulan", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"])
        
        f_abs = df_absensi[df_absensi['tanggal'].dt.year == sel_year]
        
        if not f_abs.empty:
            df_hadir = f_abs[f_abs['status_absensi'] == 'Hadir']
            df_absen = f_abs[f_abs['status_absensi'] != 'Hadir']

            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("✅ Peringkat Kehadiran")
                if not df_hadir.empty:
                    h_counts = df_hadir['nama_personel'].value_counts().reset_index()
                    h_counts.columns = ['Nama', 'Hari']
                    fig_h = px.bar(h_counts, x='Hari', y='Nama', orientation='h', title='Top Kehadiran', color='Hari', color_continuous_scale='Greens', template='plotly_dark')
                    fig_h.update_yaxes(categoryorder='total ascending') # TERTINGGI DI ATAS
                    st.plotly_chart(fig_h, use_container_width=True)

            with col_chart2:
                st.subheader("❌ Peringkat Ketidakhadiran")
                if not df_absen.empty:
                    a_counts = df_absen.groupby(['nama_personel', 'status_absensi']).size().reset_index(name='Jumlah')
                    fig_a = px.bar(a_counts, x='Jumlah', y='nama_personel', color='status_absensi', orientation='h', title='Detail Ketidakhadiran', template='plotly_dark', barmode='stack')
                    fig_a.update_yaxes(categoryorder='total ascending') # TERTINGGI DI ATAS
                    st.plotly_chart(fig_a, use_container_width=True)

            st.dataframe(f_abs[['tanggal', 'nama_personel', 'status_absensi', 'keterangan']], use_container_width=True)

# ================== Halaman: Kelola Personel ==================
elif menu == "Kelola Personel" and user_role == 'admin':
    st.header("👥 Kelola Personel")
    df_p = load_personnel_data()
    with st.form("add_p"):
        n_p = st.text_input("Nama Personel Baru")
        if st.form_submit_button("Simpan"):
            supabase.table("personel").insert({"nama": n_p}).execute()
            st.cache_data.clear(); st.rerun()
    if not df_p.empty:
        df_p['Hapus'] = False
        ed_p = st.data_editor(df_p, use_container_width=True)
        if st.button("🗑️ Hapus Terpilih"):
            to_del = ed_p[ed_p['Hapus']]['id'].tolist()
            supabase.table("personel").delete().in_("id", to_del).execute()
            st.cache_data.clear(); st.rerun()
