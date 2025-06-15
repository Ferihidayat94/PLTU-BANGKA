# PRODUKSI A
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

# ================== Konfigurasi Halaman Streamlit (HARUS PERTAMA) ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== Daftar & Variabel Global ==================
JOB_TYPES = [
    "First Line Maintenance ( A )", "First Line Maintenance ( B )", "First Line Maintenance ( C )", "First Line Maintenance ( D )",
    "Corrective Maintenance", "Preventive Maintenance"
]

# ================== Fungsi-Fungsi Helper ==================

@st.cache_resource
def init_connection():
    """Membuat dan mengembalikan koneksi ke database Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def hash_password(password):
    """Membuat hash dari password menggunakan SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_data_from_db(supabase_client):
    """Mengambil semua data dari tabel 'jobs' di Supabase."""
    try:
        response = supabase_client.table('jobs').select('*').order('created_at', desc=True).execute()
        df = pd.DataFrame(response.data)
        if 'Tanggal' in df.columns and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data dari database: {e}")
        return pd.DataFrame()

def login_manager(cookies):
    """Mengelola status login, memeriksa session state dan cookie."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
    
    if st.session_state.logged_in:
        return True

    user_from_cookie = cookies.get('monitoring_app_user')
    if user_from_cookie:
        st.session_state.logged_in = True
        st.session_state.user = user_from_cookie
        return True
    
    return False

def logout(cookies):
    """Menghapus session state dan cookie untuk logout pengguna."""
    for key in list(st.session_state.keys()):
        if key in ['logged_in', 'user', 'last_activity']:
            del st.session_state[key]
    cookies.delete('monitoring_app_user')
    st.rerun()

def generate_next_id(df, jenis):
    """Membuat ID unik baru berdasarkan jenis pekerjaan."""
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
    """Memperbaiki orientasi gambar berdasarkan data EXIF."""
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

def upload_image_to_storage(supabase_client, uploaded_file):
    """Mengupload file gambar ke Supabase Storage dan mengembalikan URL publik."""
    if uploaded_file is None: return ""
    try:
        file_bytes = uploaded_file.getvalue()
        image = Image.open(io.BytesIO(file_bytes))
        image = fix_image_orientation(image)
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG", quality=85)
        processed_bytes = output_buffer.getvalue()
        file_name = f"{uuid.uuid4()}.png"
        supabase_client.storage.from_("evidences").upload(file=processed_bytes, path=file_name, file_options={"content-type": "image/png"})
        return supabase_client.storage.from_("evidences").get_public_url(file_name)
    except Exception as e:
        st.error(f"Gagal upload gambar: {e}")
        return ""

def create_pdf_report(filtered_data, report_type):
    """Membuat laporan PDF dari data yang difilter."""
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, spaceBefore=10, textColor=colors.HexColor('#2C3E50')))
    styles.add(ParagraphStyle(name='Header', alignment=TA_LEFT, textColor=colors.HexColor('#2C3E50')))
    elements = []
    
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            header_text = "<b>PT PLN NUSANTARA POWER SERVICES</b><br/>Unit PLTU Bangka"
            logo_img = RLImage(logo_path, width=0.9*inch, height=0.4*inch)
            logo_img.hAlign = 'LEFT'
            header_data = [[logo_img, Paragraph(header_text, styles['Header'])]]
            header_table = Table(header_data, colWidths=[1*inch, 6*inch], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (1,0), (1,0), 0)])
            elements.append(header_table)
            elements.append(Spacer(1, 20))
    except Exception: pass

    title_text = f"<b>LAPORAN MONITORING {'FLM, CM, & PM' if report_type == 'Semua' else report_type.upper()}</b>"
    elements.append(Paragraph(title_text, styles["TitleCenter"]))
    elements.append(Spacer(1, 12))

    for i, row in filtered_data.iterrows():
        data = [
            ["ID", str(row.get('ID', ''))],
            ["Tanggal", pd.to_datetime(row.get('Tanggal')).strftime('%d-%m-%Y')],
            ["Jenis", str(row.get('Jenis', ''))],
            ["Area", str(row.get('Area', ''))],
            ["Nomor SR", str(row.get('Nomor SR', ''))],
            ["Nama Pelaksana", str(row.get('Nama Pelaksana', ''))],
            ["Status", str(row.get('Status', ''))],
            ["Keterangan", Paragraph(str(row.get('Keterangan', '')).replace('\n', '<br/>'), styles['Normal'])],
        ]
        table = Table(data, colWidths=[100, 380], style=[
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')), ('TEXTCOLOR', (0,0), (0, -1), colors.HexColor('#2C3E50')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')), ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10),
        ])
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        img1, img2 = None, None
        for img_url, position in [(row.get("Evidance"), 1), (row.get("Evidance After"), 2)]:
            if img_url and isinstance(img_url, str):
                try:
                    response = requests.get(img_url, stream=True)
                    response.raise_for_status()
                    img_data = io.BytesIO(response.content)
                    image_element = RLImage(img_data, width=3*inch, height=2.25*inch, kind='bound')
                    if position == 1: img1 = image_element
                    else: img2 = image_element
                except Exception as e: print(f"Gagal memuat gambar dari URL {img_url}: {e}")
        
        if img1 or img2:
            elements.append(Spacer(1, 5))
            image_table = Table([[Paragraph("<b>Evidence Before:</b>", styles['Normal']), Paragraph("<b>Evidence After:</b>", styles['Normal'])], [img1, img2]], colWidths=[3.2*inch, 3.2*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
            elements.append(image_table)
        elements.append(PageBreak())

    if len(elements) > 2 and isinstance(elements[-1], PageBreak): elements.pop()
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ================== Logika Utama Aplikasi ==================

def main():
    """Fungsi utama untuk menjalankan aplikasi Streamlit."""
    
    # CSS harus menjadi salah satu perintah pertama setelah set_page_config
    st.markdown(
        """
        <style>
            /* Salin semua CSS Anda ke sini */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
            html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
            .stApp {
                background-color: #021021;
                background-image: radial-gradient(ellipse at bottom, rgba(52, 152, 219, 0.25) 0%, rgba(255,255,255,0) 50%),
                                  linear-gradient(to top, #062b54, #021021);
                background-attachment: fixed; color: #ECF0F1;
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
                background-color: rgba(44, 62, 80, 0.6); backdrop-filter: blur(5px);
                border: 1px solid rgba(52, 152, 219, 0.4); padding: 1.5rem;
                border-radius: 10px; margin-bottom: 1rem;
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

    # Inisialisasi koneksi dan cookie di dalam main()
    supabase = init_connection()
    cookies = EncryptedCookieManager(password=st.secrets["COOKIE_ENCRYPTION_KEY"])
    if not cookies.ready():
        st.stop()

    is_logged_in = login_manager(cookies)

    if not is_logged_in:
        # Tampilkan halaman login
        col1, col2, col3 = st.columns([1, 1.5, 1])
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
        return

    # Jika sudah login, lanjutkan aplikasi
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()
    
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        logout(cookies)
        st.warning("Sesi Anda telah berakhir karena tidak aktif.")
        st.rerun()
    st.session_state.last_activity = datetime.now()

    if 'data' not in st.session_state or st.session_state.data.empty:
        st.session_state.data = load_data_from_db(supabase)

    with st.sidebar:
        st.title("Menu Navigasi")
        st.write(f"Selamat datang, **{st.session_state.user}**!")
        try: st.image(Image.open("logo.png"), use_container_width=True) 
        except FileNotFoundError: pass
        menu = st.radio("Pilih Halaman:", ["Input Data", "Report Data"], label_visibility="collapsed")
        st.markdown("<br/><br/>", unsafe_allow_html=True)
        if st.button("Logout"): logout(cookies)
        st.markdown("---"); st.caption("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")

    st.title("DASHBOARD MONITORING")

    # Konten Utama Aplikasi
    if menu == "Input Data":
        st.header("Input Data Pekerjaan Baru")
        with st.form("input_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                tanggal = st.date_input("Tanggal", date.today())
                jenis = st.selectbox("Jenis Pekerjaan", JOB_TYPES)
                area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP", "Common"])
                nomor_sr = st.text_input("Nomor SR (Service Request)")
            with col2:
                nama_pelaksana = st.text_input("Nama Pelaksana")
                status = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
                keterangan = st.text_area("Keterangan / Uraian Pekerjaan")
            
            st.subheader("Upload Bukti Pekerjaan (Evidence)")
            col_ev1, col_ev2 = st.columns(2)
            with col_ev1: evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
            with col_ev2: evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
            
            if st.form_submit_button("Simpan Data"):
                if not all([nomor_sr, nama_pelaksana, keterangan]):
                    st.error("Mohon isi semua field yang wajib.")
                else:
                    with st.spinner("Menyimpan data dan mengupload gambar..."):
                        evidance_url = upload_image_to_storage(supabase, evidance_file)
                        evidance_after_url = upload_image_to_storage(supabase, evidance_after_file)
                        new_id = generate_next_id(st.session_state.data, jenis)
                        new_job_data = {
                            "ID": new_id, "Tanggal": str(tanggal), "Jenis": jenis, "Area": area,
                            "Nomor SR": nomor_sr, "Nama Pelaksana": nama_pelaksana, "Keterangan": keterangan,
                            "Status": status, "Evidance": evidance_url, "Evidance After": evidance_after_url
                        }
                        try:
                            supabase.table("jobs").insert(new_job_data).execute()
                            st.session_state.data = load_data_from_db(supabase)
                            st.success(f"Data dengan ID '{new_id}' berhasil disimpan!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menyimpan data ke database: {e}")

    elif menu == "Report Data":
        st.header("Integrated Data & Report")
        
        # ... (Sisa kode Report Data sama persis seperti sebelumnya) ...
        # Tambahkan semua logika dari halaman Report Data di sini
        with st.container(border=True):
            st.subheader("Filter & Edit Data")
            # ...
        
        st.write("---")
        
        col_func1, col_func2 = st.columns([2, 1])
        with col_func1:
            with st.expander("✅ **Update Status Pekerjaan**", expanded=True):
                # ...
        
        with col_func2:
            st.write("") 
            st.write("Butuh data terbaru?")
            if st.button("🔄 Refresh Data Tabel", use_container_width=True):
                st.session_state.data = load_data_from_db(supabase)
                st.toast("Data telah diperbarui!")

        with st.container(border=True):
            st.subheader("📄 Laporan & Unduh Data")
            # ...

# Menjalankan aplikasi
if __name__ == "__main__":
    main()
