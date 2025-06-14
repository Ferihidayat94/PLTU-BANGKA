# APLIKASI PRODUKSI A
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

# ================== Konfigurasi Halaman Streamlit ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS Kustom (Dengan Perbaikan Warna Teks) ==================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        html, body, [class*="st-"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background-color: #021021; /* Fallback */
            background-image: radial-gradient(ellipse at bottom, rgba(52, 152, 219, 0.25) 0%, rgba(255,255,255,0) 50%),
                              linear-gradient(to top, #062b54, #021021);
            background-attachment: fixed;
            color: #ECF0F1;
        }

        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {
            color: #FFFFFF;
        }
        
        /* === PERBAIKAN WARNA TEKS JUDUL & KONTEN === */
        /* Memastikan header, subheader, dan teks biasa di area utama berwarna putih */
        .stApp [data-testid="stHeading"] {
            color: #FFFFFF !important;
        }
        .stApp p {
            color: #ECF0F1 !important; /* Warna putih pudar agar tidak terlalu mencolok */
        }
        /* =========================================== */
        
        h1 {
            border-bottom: 2px solid #3498DB;
            padding-bottom: 10px;
            margin-bottom: 0.8rem;
        }

        [data-testid="stSidebar"] {
            background-color: rgba(2, 16, 33, 0.8);
            backdrop-filter: blur(5px);
            border-right: 1px solid rgba(52, 152, 219, 0.3);
        }
        
        /* --- Login & Containers --- */
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
        .login-title {
            color: #FFFFFF; text-align: center; border-bottom: none; font-size: 1.9rem; white-space: nowrap;
        }

        /* --- Buttons --- */
        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button,
        div[data-testid="stForm"] button {
            font-weight: 600;
            border-radius: 8px;
            border: 1px solid #3498DB !important;
            background-color: transparent !important;
            color: #FFFFFF !important;
            transition: all 0.3s ease-in-out;
            padding: 10px 24px;
            width: 100%;
        }
        div[data-testid="stButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover,
        div[data-testid="stForm"] button:hover {
            background-color: #3498DB !important;
            border-color: #3498DB !important;
        }
        .delete-button button { border-color: #E74C3C !important; }
        .delete-button button:hover { background-color: #C0392B !important; border-color: #C0392B !important; }

        /* --- Inputs --- */
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

        /* --- Sidebar Specific Styles --- */
        [data-testid="stSidebar"] .stMarkdown p,
        [data-testid="stSidebar"] .stMarkdown strong,
        [data-testid="stSidebar"] .stRadio > label span,
        [data-testid="stSidebar"] .stCaption {
            color: #FFFFFF !important;
            opacity: 1;
        }

        [data-testid="stSidebar"] .st-bo:has(input:checked) + label span {
            color: #5DADE2 !important;
            font-weight: 700 !important;
        }
        
        [data-testid="stSidebar"] .stButton > button {
             color: #EAECEE !important;
             border-color: #EAECEE !important;
        }
        [data-testid="stSidebar"] .stButton > button:hover {
             color: #FFFFFF !important;
             border-color: #E74C3C !important;
             background-color: #E74C3C !important;
        }

        [data-testid="stSidebarNavCollapseButton"] svg {
            fill: #FFFFFF !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Inisialisasi Koneksi ke Supabase
@st.cache_resource
def init_connection():
    """Membuat dan mengembalikan koneksi ke database Supabase."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Daftar Jenis Pekerjaan terpusat
JOB_TYPES = [
    "First Line Maintenance ( A )",
    "First Line Maintenance ( B )",
    "First Line Maintenance ( C )",
    "First Line Maintenance ( D )",
    "Corrective Maintenance",
    "Preventive Maintenance"
]

# ================== Fungsi-Fungsi Helper ==================

def hash_password(password):
    """Membuat hash dari password menggunakan SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_data_from_db():
    """Mengambil semua data dari tabel 'jobs' di Supabase."""
    try:
        response = supabase.table('jobs').select('*').order('created_at', desc=True).execute()
        df = pd.DataFrame(response.data)
        if 'Tanggal' in df.columns and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data dari database: {e}")
        return pd.DataFrame()

def logout():
    """Menghapus session state untuk logout pengguna."""
    for key in list(st.session_state.keys()):
        if key != 'data':
            del st.session_state[key]
    st.session_state.logged_in = False
    st.rerun()

def generate_next_id(df, jenis):
    """Membuat ID unik baru berdasarkan jenis pekerjaan."""
    if jenis.startswith('First Line Maintenance'):
        prefix = 'FLM'
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
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = image.getexif()
        orientation_val = exif.get(orientation)
        if orientation_val == 3: image = image.rotate(180, expand=True)
        elif orientation_val == 6: image = image.rotate(270, expand=True)
        elif orientation_val == 8: image = image.rotate(90, expand=True)
    except Exception:
        pass
    return image

def upload_image_to_storage(uploaded_file):
    """Mengupload file gambar ke Supabase Storage dan mengembalikan URL publik."""
    if uploaded_file is None: return ""
    try:
        file_bytes = uploaded_file.getvalue()
        image = Image.open(io.BytesIO(file_bytes))
        image = fix_image_orientation(image)
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG", quality=85) # Tambah kompresi
        processed_bytes = output_buffer.getvalue()
        file_name = f"{uuid.uuid4()}.png"
        supabase.storage.from_("evidences").upload(file=processed_bytes, path=file_name, file_options={"content-type": "image/png"})
        public_url = supabase.storage.from_("evidences").get_public_url(file_name)
        return public_url
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

# Inisialisasi Session State
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.data = pd.DataFrame() # Mulai dengan dataframe kosong
    st.session_state.last_activity = datetime.now()

# Halaman Login
if not st.session_state.get("logged_in"):
    # Muat data di latar belakang saat halaman login ditampilkan
    if 'data' not in st.session_state or st.session_state.data.empty:
        st.session_state.data = load_data_from_db()

    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">Monitoring Job OpHar</h1>', unsafe_allow_html=True)
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
                    st.rerun()
                else: st.error("Username atau password salah.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Pemeriksaan Sesi
if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
    logout()
    st.warning("Sesi Anda telah berakhir karena tidak aktif.")
    st.rerun()
st.session_state.last_activity = datetime.now()

# Tampilan Utama Setelah Login
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

# ================== PERUBAHAN DI SINI ==================
# Sembunyikan menu hamburger dan footer Streamlit untuk user 'operator'
if st.session_state.get('user') == 'operator':
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
# =======================================================


# Muat data jika session state kosong (misalnya setelah login)
if 'data' not in st.session_state or st.session_state.data.empty:
    st.session_state.data = load_data_from_db()

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
                    evidance_url = upload_image_to_storage(evidance_file)
                    evidance_after_url = upload_image_to_storage(evidance_after_file)
                    new_id = generate_next_id(st.session_state.data, jenis)
                    new_job_data = {
                        "ID": new_id, "Tanggal": str(tanggal), "Jenis": jenis, "Area": area,
                        "Nomor SR": nomor_sr, "Nama Pelaksana": nama_pelaksana, "Keterangan": keterangan,
                        "Status": status, "Evidance": evidance_url, "Evidance After": evidance_after_url
                    }
                    try:
                        supabase.table("jobs").insert(new_job_data).execute()
                        st.session_state.data = load_data_from_db()
                        st.success(f"Data dengan ID '{new_id}' berhasil disimpan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan data ke database: {e}")

elif menu == "Report Data":
    st.header("Integrated Data & Report")
    
    # BAGIAN TABEL DATA DAN FILTER
    with st.container(border=True):
        st.subheader("Filter & Edit Data")
        data_to_display = st.session_state.data.copy()
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            all_jenis = ["Semua"] + list(data_to_display["Jenis"].dropna().unique())
            filter_jenis = st.selectbox("Saring berdasarkan Jenis:", all_jenis)
        with filter_col2:
            all_status = ["Semua"] + list(data_to_display["Status"].dropna().unique())
            filter_status = st.selectbox("Saring berdasarkan Status:", all_status)
        if filter_jenis != "Semua": data_to_display = data_to_display[data_to_display["Jenis"] == filter_jenis]
        if filter_status != "Semua": data_to_display = data_to_display[data_to_display["Status"] == filter_status]
        
        if not data_to_display.empty:
            data_to_display.insert(0, "Hapus", False)
            edited_data = st.data_editor(
                data_to_display, key="data_editor", disabled=["ID", "Evidance", "Evidance After"], use_container_width=True,
                column_config={
                    "Hapus": st.column_config.CheckboxColumn("Hapus?", help="Centang untuk menghapus."), "Tanggal": st.column_config.DateColumn("Tanggal", format="DD-MM-YYYY"),
                    "Jenis": st.column_config.SelectboxColumn("Jenis", options=JOB_TYPES),
                    "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"]),
                    "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"]),
                    "Keterangan": st.column_config.TextColumn("Keterangan", width="large"),
                    "Evidance": st.column_config.LinkColumn("Evidence Before", display_text="Lihat"), "Evidance After": st.column_config.LinkColumn("Evidence After", display_text="Lihat"),
                    "ID": st.column_config.TextColumn("ID", disabled=True),
                }, column_order=["Hapus", "ID", "Tanggal", "Jenis", "Area", "Status", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance", "Evidance After"]
            )
            rows_to_delete_df = edited_data[edited_data['Hapus']]
            if not rows_to_delete_df.empty and st.session_state.user == 'admin':
                st.markdown('<div class="delete-button">', unsafe_allow_html=True)
                if st.button(f"🗑️ Hapus ({len(rows_to_delete_df)}) Baris Terpilih", use_container_width=True):
                    with st.spinner("Menghapus data..."):
                        ids_to_delete = rows_to_delete_df['ID'].tolist()
                        supabase.table("jobs").delete().in_("ID", ids_to_delete).execute()
                        st.session_state.data = load_data_from_db()
                        st.success("Data terpilih berhasil dihapus.")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            elif not rows_to_delete_df.empty: st.warning("Hanya 'admin' yang dapat menghapus data.")

    st.write("---") # Garis pemisah visual
    
    col_func1, col_func2 = st.columns([2, 1])

    with col_func1:
        with st.expander("✅ **Update Status Pekerjaan**", expanded=True):
            open_jobs = st.session_state.data[st.session_state.data['Status'].isin(['Open', 'On Progress'])]
            if not open_jobs.empty:
                job_options = {f"{row['ID']} - {row['Nama Pelaksana']} - {str(row.get('Keterangan',''))[:40]}...": row['ID'] for index, row in open_jobs.iterrows()}
                selected_job_display = st.selectbox("Pilih Pekerjaan yang akan diselesaikan:", list(job_options.keys()))
                uploaded_evidence_after = st.file_uploader("Upload Bukti Selesai", type=["png", "jpg", "jpeg"], key="quick_upload")
                if st.button("Submit Update", use_container_width=True):
                    if selected_job_display and uploaded_evidence_after:
                        with st.spinner("Menyelesaikan pekerjaan..."):
                            job_id_to_update = job_options[selected_job_display]
                            evidence_url = upload_image_to_storage(uploaded_evidence_after)
                            update_data = {"Status": "Finish", "Evidance After": evidence_url}
                            try:
                                supabase.table("jobs").update(update_data).eq("ID", job_id_to_update).execute()
                                st.session_state.data = load_data_from_db()
                                st.success(f"Pekerjaan dengan ID {job_id_to_update} telah diselesaikan!")
                                st.rerun()
                            except Exception as e: st.error(f"Gagal update pekerjaan: {e}")
                    else: st.warning("Mohon pilih pekerjaan dan upload bukti selesai.")
            else: st.info("Tidak ada pekerjaan yang berstatus 'Open' atau 'On Progress' saat ini.")
    
    with col_func2:
        st.write("") 
        st.write("Tekan refresh jika sudah upload evidance after!!")
        if st.button("🔄 Refresh Data Tabel", use_container_width=True):
            st.session_state.data = load_data_from_db()
            st.toast("Data telah diperbarui!")
    
    with st.container(border=True):
        st.subheader("📄 Laporan & Unduh Data")
        report_col1, report_col2 = st.columns(2)
        with report_col1:
            if not st.session_state.data.empty:
                csv_data = st.session_state.data.to_csv(index=False).encode('utf-8')
                st.download_button("Download Seluruh Data (CSV)", data=csv_data, file_name="monitoring_data_lengkap.csv", mime="text/csv", use_container_width=True)
        with report_col2:
            st.write("**Export Laporan ke PDF**")
            pdf_col1, pdf_col2, pdf_col3 = st.columns(3)
            with pdf_col1: export_start_date = st.date_input("Tanggal Mulai", date.today().replace(day=1))
            with pdf_col2: export_end_date = st.date_input("Tanggal Akhir", date.today())
            with pdf_col3: 
                pdf_export_options = ["Semua"] + JOB_TYPES
                export_type = st.selectbox("Pilih Jenis", pdf_export_options, key="pdf_export_type")
            if st.button("Buat Laporan PDF", use_container_width=True):
                report_data = st.session_state.data.copy()
                if not report_data.empty:
                    report_data["Tanggal"] = pd.to_datetime(report_data["Tanggal"])
                    mask = (report_data["Tanggal"].dt.date >= export_start_date) & (report_data["Tanggal"].dt.date <= export_end_date)
                    if export_type != "Semua": mask &= (report_data["Jenis"] == export_type)
                    final_data_to_export = report_data[mask]
                    if final_data_to_export.empty: st.warning("Tidak ada data yang ditemukan untuk periode dan jenis yang dipilih.")
                    else:
                        with st.spinner("Membuat file PDF..."): 
                            pdf_bytes = create_pdf_report(final_data_to_export, export_type)
                        if pdf_bytes:
                            st.success("Laporan PDF berhasil dibuat!")
                            st.download_button("Unduh Laporan PDF", data=pdf_bytes, file_name=f"laporan_{export_type.lower().replace(' ', '_')}.pdf", mime="application/pdf")
                else: st.warning("Tidak ada data untuk membuat laporan.")
