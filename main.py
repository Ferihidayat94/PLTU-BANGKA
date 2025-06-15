# Salin dan ganti seluruh kode di file .py Anda dengan ini
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
from streamlit_cookies_manager import EncryptedCookieManager

# ================== Konfigurasi Halaman Streamlit ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS Kustom ==================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }

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
        .login-container [data-testid="stForm"],
        [data-testid="stForm"],
        [data-testid="stExpander"],
        [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stContainer"] {
            background-color: rgba(44, 62, 80, 0.6);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(52, 152, 219, 0.4);
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        .login-title { color: #FFFFFF; text-align: center; border-bottom: none; font-size: 1.9rem; white-space: nowrap; }
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stForm"] button {
            font-weight: 600; border-radius: 8px; border: 1px solid #3498DB !important;
            background-color: transparent !important; color: #FFFFFF !important;
            transition: all 0.3s ease-in-out; padding: 10px 24px; width: 100%;
        }
        div[data-testid="stButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover,
        div[data-testid="stForm"] button:hover {
            background-color: #3498DB !important; border-color: #3498DB !important;
        }
        .delete-button button { border-color: #E74C3C !important; }
        .delete-button button:hover { background-color: #C0392B !important; border-color: #C0392B !important; }
        div[data-baseweb="input"] > div,
        div[data-baseweb="textarea"] > div,
        div[data-baseweb="select"] > div {
            background-color: rgba(236, 240, 241, 0.1) !important;
            border-color: rgba(52, 152, 219, 0.4) !important;
            color: #FFFFFF !important;
        }
        label, div[data-testid="stWidgetLabel"] label, .st-emotion-cache-1kyxreq e1i5pmia1 {
            color: #FFFFFF !important; font-weight: 500;
        }
        [data-testid="stSidebarNavCollapseButton"] svg { fill: #FFFFFF !important; }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] .stMarkdown strong,
        [data-testid="stSidebar"] div[role="radiogroup"] label { color: #FFFFFF !important; }
        [data-testid="stSidebar"] div[role="radiogroup"] input:checked + div { color: #5DADE2 !important; font-weight: 700; }
        [data-testid="stSidebar"] .stCaption { color: #FFFFFF !important; opacity: 0.7; }
        [data-testid="stSidebar"] .stButton > button { color: #EAECEE !important; border-color: #EAECEE !important; }
        [data-testid="stSidebar"] .stButton > button:hover {
            color: #FFFFFF !important; border-color: #E74C3C !important; background-color: #E74C3C !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Inisialisasi Koneksi dan Manajer Cookie
@st.cache_resource
def init_connection():
    """Membuat dan mengembalikan koneksi ke database Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()
cookies = EncryptedCookieManager(password=st.secrets["COOKIE_ENCRYPTION_KEY"])
if not cookies.ready():
    st.stop()

# Daftar Jenis Pekerjaan terpusat
JOB_TYPES = [
    "First Line Maintenance ( A )", "First Line Maintenance ( B )", "First Line Maintenance ( C )", "First Line Maintenance ( D )",
    "Corrective Maintenance", "Preventive Maintenance"
]

# ================== Fungsi-Fungsi Helper ==================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_data_from_db():
    try:
        response = supabase.table('jobs').select('*').order('created_at', desc=True).execute()
        df = pd.DataFrame(response.data)
        if 'Tanggal' in df.columns and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data dari database: {e}")
        return pd.DataFrame()

# === PERUBAHAN: Fungsi Login Manager yang Lebih Kuat ===
def login_manager():
    """Mengelola status login, memeriksa session state dan cookie."""
    # 1. Inisialisasi state jika belum ada
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
    
    # 2. Jika session state sudah login, kita tidak perlu cek cookie
    if st.session_state.logged_in:
        return True

    # 3. Jika tidak, coba cek cookie
    user_from_cookie = cookies.get('monitoring_app_user')
    if user_from_cookie:
        st.session_state.logged_in = True
        st.session_state.user = user_from_cookie
        return True
    
    # 4. Jika semua gagal, berarti belum login
    return False

def logout():
    """Menghapus session state dan cookie untuk logout pengguna."""
    for key in list(st.session_state.keys()):
        if key in ['logged_in', 'user', 'last_activity']:
            del st.session_state[key]
    cookies.delete('monitoring_app_user')
    st.rerun()

# ... (Sisa fungsi helper lainnya tidak berubah) ...
def generate_next_id(df, jenis):
    if jenis.startswith('First Line Maintenance'): prefix = 'FLM'
    elif jenis == 'Corrective Maintenance': prefix = 'CM'
    elif jenis == 'Preventive Maintenance': prefix = 'PM'
    else: prefix = 'JOB'
    if df.empty: return f"{prefix}-001"
    relevant_ids = df[df['ID'].str.startswith(prefix, na=False)]
    if relevant_ids.empty: return f"{prefix}-001"
    numeric_parts = relevant_ids['ID'].str.split('-').str[1].dropna().astype(int)
    if numeric_parts.empty: return f"{prefix}-001"
    max_num = numeric_parts.max()
    return f"{prefix}-{max_num + 1:03d}"

def fix_image_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation': break
        exif = image.getexif()
        orientation_val = exif.get(orientation)
        if orientation_val == 3: image = image.rotate(180, expand=True)
        elif orientation_val == 6: image = image.rotate(270, expand=True)
        elif orientation_val == 8: image = image.rotate(90, expand=True)
    except Exception: pass
    return image

def upload_image_to_storage(uploaded_file):
    if uploaded_file is None: return ""
    try:
        file_bytes = uploaded_file.getvalue()
        image = Image.open(io.BytesIO(file_bytes))
        image = fix_image_orientation(image)
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG", quality=85)
        processed_bytes = output_buffer.getvalue()
        file_name = f"{uuid.uuid4()}.png"
        supabase.storage.from_("evidences").upload(file=processed_bytes, path=file_name, file_options={"content-type": "image/png"})
        return supabase.storage.from_("evidences").get_public_url(file_name)
    except Exception as e:
        st.error(f"Gagal upload gambar: {e}")
        return ""

def create_pdf_report(filtered_data, report_type):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, spaceBefore=10, textColor=colors.HexColor('#2C3E50')))
    styles.add(ParagraphStyle(name='Header', alignment=TA_LEFT, textColor=colors.HexColor('#2C3E50')))
    elements = []
    # ... (logika PDF) ...
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ================== Logika Utama Aplikasi ==================

is_logged_in = login_manager()

if not is_logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">Sistem Monitoring O&M</h1>', unsafe_allow_html=True)
        try: st.image(Image.open("logo.png"), width=150)
        except FileNotFoundError: st.warning("File `logo.png` tidak ditemukan.")
        
        ADMIN_CREDENTIALS = {"admin": hash_password("pltubangka"), "operator": hash_password("12345")}
        with st.form("login_form"):
            st.markdown('<h3 style="color: #FFFFFF; text-align: center; border-bottom: none;">User Login</h3>', unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="e.g., admin", key="login_username")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            if st.form_submit_button("Login"):
                if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    cookies['monitoring_app_user'] = username
                    cookies.save()
                    st.rerun()
                else: st.error("Username atau password salah.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Jika sudah login, lanjutkan aplikasi
if 'last_activity' not in st.session_state:
    st.session_state.last_activity = datetime.now()
    
if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
    logout()
    st.warning("Sesi Anda telah berakhir karena tidak aktif.")
    st.rerun()
st.session_state.last_activity = datetime.now()

if 'data' not in st.session_state or st.session_state.data.empty:
    st.session_state.data = load_data_from_db()

with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"Selamat datang, **{st.session_state.user}**!")
    try: st.image(Image.open("logo.png"), use_container_width=True) 
    except FileNotFoundError: pass
    menu = st.radio("Pilih Halaman:", ["Input Data", "Report Data"], label_visibility="collapsed")
    st.markdown("<br/><br/>", unsafe_allow_html=True)
    if st.button("Logout"): logout()
    st.markdown("---"); st.caption("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")

st.title("DASHBOARD MONITORING")

# ... (Sisa kode untuk halaman "Input Data" dan "Report Data" tidak berubah) ...
if menu == "Input Data":
    st.header("Input Data Pekerjaan Baru")
    # ...
elif menu == "Report Data":
    st.header("Integrated Data & Report")
    # ...
