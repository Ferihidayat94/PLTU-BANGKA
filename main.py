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

# ================== Konfigurasi Halaman Streamlit ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS Kustom untuk Tampilan ==================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
        .stApp { background-color: #F8F9FA; color: #212529; }
        .stApp h1, .stApp h2, .stApp h3 { color: #0d3b66; }
        [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #DEE2E6; }
        [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] .stRadio > label { color: #495057; }
        .stButton>button { font-weight: 600; border-radius: 8px; border: 1px solid #0d3b66; background-color: #0d3b66; color: #FFFFFF; transition: all 0.2s ease-in-out; padding: 10px 24px; }
        .stButton>button:hover { background-color: #FFFFFF; color: #0d3b66; }
        [data-testid="stForm"], [data-testid="stExpander"] { border: 1px solid #DEE2E6; border-radius: 10px; background-color: #FFFFFF; }
        hr { border-top: 1px solid #DEE2E6; }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== Inisialisasi Awal ==================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATA_FILE = "monitoring_data.csv"

# ================== Fungsi-Fungsi Helper ==================

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_data():
    try:
        df = pd.read_csv(DATA_FILE, parse_dates=["Tanggal"])
        required_cols = ["ID", "Tanggal", "Jenis", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan", "Status", "Evidance", "Evidance After"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        df[['Evidance', 'Evidance After']] = df[['Evidance', 'Evidance After']].fillna('')
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=["ID", "Tanggal", "Jenis", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan", "Status", "Evidance", "Evidance After"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def generate_next_id(df, jenis):
    prefix = 'FLM' if jenis == 'FLM' else 'CM'
    relevant_ids = df[df['ID'].str.startswith(prefix, na=False)]
    if relevant_ids.empty:
        return f"{prefix}-001"
    
    max_num = relevant_ids['ID'].str.split('-').str[1].astype(int).max()
    return f"{prefix}-{max_num + 1:03d}"

def fix_image_orientation(image):
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        exif = image._getexif()
        if exif is not None:
            orientation_val = exif.get(orientation)
            if orientation_val == 3: image = image.rotate(180, expand=True)
            elif orientation_val == 6: image = image.rotate(270, expand=True)
            elif orientation_val == 8: image = image.rotate(90, expand=True)
    except Exception:
        pass
    return image

# --- FUNGSI BARU DAN KRUSIAL: Memastikan semua gambar adalah file fisik ---
def ensure_images_are_saved(df):
    """Iterasi melalui DataFrame, menemukan gambar di memori, menyimpannya, dan memperbarui path."""
    for i, row in df.iterrows():
        for col in ['Evidance', 'Evidance After']:
            cell_value = row[col]
            # Cek jika nilai sel adalah byte (gambar dari data_editor)
            if isinstance(cell_value, bytes):
                try:
                    image = Image.open(io.BytesIO(cell_value))
                    # Gunakan format PNG untuk konsistensi
                    new_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.png")
                    image.save(new_path, "PNG")
                    # Update nilai di DataFrame dengan path string yang baru
                    df.loc[i, col] = new_path
                except Exception as e:
                    print(f"Gagal menyimpan gambar dari buffer untuk baris {i}: {e}")
                    df.loc[i, col] = "" # Gagal, set menjadi kosong
    return df


def create_pdf_report(filtered_data):
    file_path = f"laporan_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=16, leading=22, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubTitle', alignment=TA_LEFT, fontSize=12, leading=16, spaceAfter=10, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='NormalLeft', alignment=TA_LEFT, fontSize=10, leading=14, fontName='Helvetica'))

    elements = []
    
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            header_text = "<b>PT PLN NUSANTARA SERVICES</b><br/>Unit PLTU Bangka"
            logo_img = RLImage(logo_path, width=0.8*inch, height=0.6*inch)
            header_data = [[logo_img, Paragraph(header_text, styles['NormalLeft'])]]
            header_table = Table(header_data, colWidths=[1*inch, 6*inch])
            header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (1,0), (1,0), 0)]))
            elements.append(header_table)
            elements.append(Spacer(1, 20))
    except Exception as e:
        st.warning(f"Logo tidak bisa dimuat ke PDF: {e}")

    elements.append(Paragraph("LAPORAN MONITORING FLM & CORRECTIVE MAINTENANCE", styles['TitleCenter']))
    elements.append(Spacer(1, 12))

    for i, row in filtered_data.iterrows():
        data = [
            ["ID Laporan", f": {row.get('ID', 'N/A')}"], ["Tanggal", f": {pd.to_datetime(row.get('Tanggal')).strftime('%d %B %Y')}"],
            ["Jenis Pekerjaan", f": {row.get('Jenis', 'N/A')}"], ["Area", f": {row.get('Area', 'N/A')}"],
            ["Nomor SR", f": {row.get('Nomor SR', 'N/A')}"], ["Nama Pelaksana", f": {row.get('Nama Pelaksana', 'N/A')}"],
            ["Status", f": {row.get('Status', 'N/A')}"], ["Keterangan", Paragraph(f": {row.get('Keterangan', 'N/A')}", styles['NormalLeft'])],
        ]
        table = Table(data, colWidths=[120, 360])
        table.setStyle(TableStyle([('ALIGN', (0, 0), (0, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 2)]))
        elements.append(table)
        elements.append(Spacer(1, 10))
        
        def process_image(path):
            if isinstance(path, str) and os.path.exists(path):
                try:
                    pil_image = Image.open(path)
                    pil_image = fix_image_orientation(pil_image)
                    return RLImage(pil_image, width=3*inch, height=2.25*inch, kind='bound')
                except Exception as e:
                    print(f"Error saat memproses gambar untuk PDF {path}: {e}")
            return None

        img_data, col_widths, title_row, img_row = [], [], [], []
        img_before = process_image(row.get("Evidance"))
        img_after = process_image(row.get("Evidance After"))

        if img_before:
            title_row.append(Paragraph("<b>Evidence Before</b>", styles['SubTitle']))
            img_row.append(img_before)
            col_widths.append(3*inch)
        if img_after:
            title_row.append(Paragraph("<b>Evidence After</b>", styles['SubTitle']))
            img_row.append(img_after)
            col_widths.append(3*inch)
        
        if img_row:
            img_data.append(title_row)
            img_data.append(img_row)
            img_table = Table(img_data, colWidths=col_widths)
            img_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
            elements.append(img_table)
            elements.append(Spacer(1, 20))
        elements.append(PageBreak())

    if elements:
        doc.build(elements)
        return file_path
    return None

# ================== Inisialisasi Session State ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.data = load_data()
    st.session_state.last_activity = datetime.now()

if st.session_state.logged_in:
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        logout()
        st.warning("Sesi Anda telah berakhir.")
        st.stop()
    st.session_state.last_activity = datetime.now()

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.title("Login Sistem Monitoring")
        try: st.image(Image.open("logo.png"), width=150)
        except FileNotFoundError: st.error("File `logo.png` tidak ditemukan.")
        ADMIN_CREDENTIALS = {"admin": hash_password("pltubangka"), "operator": hash_password("op123")}
        with st.form("login_form"):
            st.markdown("### Silakan Masuk")
            username = st.text_input("Username", placeholder="e.g., admin")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            st.markdown("---")
            if st.form_submit_button("Login"):
                if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.rerun()
                else: st.error("Username atau password salah.")
    st.stop()

# ================== Tampilan Utama Setelah Login ==================
with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"Selamat datang, **{st.session_state.user}**!")
    try: st.image(Image.open("logo.png"), use_container_width=True) 
    except FileNotFoundError: st.info("logo.png tidak ditemukan.")
    menu = st.radio("Pilih Menu:", ["Input Data", "Manajemen & Laporan Data"], label_visibility="collapsed")
    st.markdown("<br/><br/>", unsafe_allow_html=True)
    if st.button("Logout"): logout()
    st.markdown("<hr>"); st.caption("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")

st.title("MONITORING FLM & CORRECTIVE MAINTENANCE")
st.write("#### Produksi A PLTU Bangka")
st.markdown("---")

if menu == "Input Data":
    st.header("📋 Input Data Pekerjaan Baru")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tanggal = st.date_input("Tanggal", date.today())
            jenis = st.selectbox("Jenis Pekerjaan", ["FLM", "Corrective Maintenance"])
            area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP", "Common"])
            nomor_sr = st.text_input("Nomor SR (Service Request)")
        with col2:
            nama_pelaksana = st.text_input("Nama Pelaksana")
            status = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
            keterangan = st.text_area("Keterangan / Uraian Pekerjaan")
        st.markdown("---"); st.subheader("Upload Bukti Pekerjaan (Evidence)")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1: evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
        with col_ev2: evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Simpan Data"):
            if not all([nomor_sr, nama_pelaksana, keterangan]):
                st.error("Mohon isi semua field yang wajib.")
            else:
                def save_uploaded_file(uploaded_file):
                    if uploaded_file:
                        path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}{os.path.splitext(uploaded_file.name)[1]}")
                        with open(path, "wb") as f: f.write(uploaded_file.getbuffer())
                        return path
                    return ""
                evidance_path = save_uploaded_file(evidance_file)
                evidance_after_path = save_uploaded_file(evidance_after_file)
                new_id = generate_next_id(st.session_state.data, jenis)
                new_row = pd.DataFrame([{"ID": new_id, "Tanggal": pd.to_datetime(tanggal), "Jenis": jenis, "Area": area, "Nomor SR": nomor_sr, "Nama Pelaksana": nama_pelaksana, "Keterangan": keterangan, "Status": status, "Evidance": evidance_path, "Evidance After": evidance_after_path}])
                st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
                save_data(st.session_state.data)
                st.success(f"Data dengan ID '{new_id}' berhasil disimpan!")

elif menu == "Manajemen & Laporan Data":
    st.header("📊 Manajemen & Laporan Data")
    
    with st.container():
        st.write("Gunakan filter di bawah untuk mencari data spesifik.")
        data_to_display = st.session_state.data.copy()
        col1, col2, col3 = st.columns(3)
        with col1: filter_jenis = st.selectbox("Saring berdasarkan Jenis:", ["Semua"] + list(data_to_display["Jenis"].unique()))
        with col2: filter_status = st.selectbox("Saring berdasarkan Status:", ["Semua"] + list(data_to_display["Status"].unique()))
        if filter_jenis != "Semua": data_to_display = data_to_display[data_to_display["Jenis"] == filter_jenis]
        if filter_status != "Semua": data_to_display = data_to_display[data_to_display["Status"] == filter_status]
        
    st.markdown("---")
    st.info("Anda dapat mengedit data langsung di tabel di bawah. Perubahan akan disimpan otomatis jika Anda adalah admin.")
    
    column_config = { "Tanggal": st.column_config.DateColumn("Tanggal", format="YYYY-MM-DD"), "Jenis": st.column_config.SelectboxColumn("Jenis", options=["FLM", "Corrective Maintenance"]), "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"]), "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"]), "Keterangan": st.column_config.TextColumn("Keterangan", width="large"), "Evidance": st.column_config.ImageColumn("Evidence Before"), "Evidance After": st.column_config.ImageColumn("Evidence After"), "ID": st.column_config.TextColumn("ID", disabled=True), }
    
    edited_data_display = st.data_editor(data_to_display, column_config=column_config, num_rows="dynamic", key="data_editor", use_container_width=True, column_order=["ID", "Tanggal", "Jenis", "Area", "Status", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance", "Evidance After"])

    # --- PERBAIKAN FINAL: Logika penyimpanan yang andal ---
    if not edited_data_display.reset_index(drop=True).equals(data_to_display.reset_index(drop=True)):
        if st.session_state.user == 'admin':
            # 1. Proses semua gambar untuk memastikan semuanya adalah file path
            processed_df = ensure_images_are_saved(edited_data_display)
            
            # 2. Update data utama dengan data yang sudah diproses
            # Menggunakan ID sebagai kunci untuk update yang akurat
            main_df = st.session_state.data.set_index('ID')
            update_df = processed_df.set_index('ID')
            main_df.update(update_df)
            
            # 3. Simpan kembali data utama yang sudah diperbarui
            st.session_state.data = main_df.reset_index()
            save_data(st.session_state.data)
            st.toast("Perubahan telah disimpan!", icon="✅")
            st.rerun() 
        else:
            st.warning("Hanya 'admin' yang dapat mengedit atau menghapus data.")
            st.rerun()

    st.markdown("---"); st.subheader("📄 Laporan & Unduh Data")
    with st.expander("**Export Laporan ke PDF**"):
        col1, col2, col3 = st.columns(3)
        with col1: export_start_date = st.date_input("Tanggal Mulai", date.today().replace(day=1))
        with col2: export_end_date = st.date_input("Tanggal Akhir", date.today())
        with col3: export_type = st.selectbox("Pilih Jenis Pekerjaan", ["Semua", "FLM", "Corrective Maintenance"], key="pdf_export_type")

        if st.button("Buat Laporan PDF"):
            report_data = st.session_state.data.copy()
            report_data["Tanggal"] = pd.to_datetime(report_data["Tanggal"])
            mask = (report_data["Tanggal"].dt.date >= export_start_date) & (report_data["Tanggal"].dt.date <= export_end_date)
            if export_type != "Semua": mask &= (report_data["Jenis"] == export_type)
            final_data_to_export = report_data[mask]

            if final_data_to_export.empty:
                st.warning("Tidak ada data yang ditemukan.")
            else:
                with st.spinner("Membuat file PDF..."):
                    pdf_file = create_pdf_report(final_data_to_export)
                if pdf_file:
                    st.success("Laporan PDF berhasil dibuat!")
                    with open(pdf_file, "rb") as f:
                        st.download_button("Unduh Laporan PDF", f, file_name=os.path.basename(pdf_file))

