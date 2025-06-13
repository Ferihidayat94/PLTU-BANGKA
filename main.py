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
        if key != 'data':
            del st.session_state[key]
    st.session_state.logged_in = False
    st.rerun()

# --- PERUBAHAN: Menambahkan handler untuk "Preventive Maintenance" ---
def generate_next_id(df, jenis):
    """Membuat ID unik berikutnya berdasarkan jenis pekerjaan."""
    if jenis == 'FLM':
        prefix = 'FLM'
    elif jenis == 'Corrective Maintenance':
        prefix = 'CM'
    elif jenis == 'Preventive Maintenance':
        prefix = 'PM'
    else:
        prefix = 'JOB' # Default prefix

    relevant_ids = df[df['ID'].str.startswith(prefix, na=False)]
    if relevant_ids.empty:
        return f"{prefix}-001"
    
    numeric_parts = relevant_ids['ID'].str.split('-').str[1].dropna().astype(int)
    if numeric_parts.empty:
        return f"{prefix}-001"
    
    max_num = numeric_parts.max()
    return f"{prefix}-{max_num + 1:03d}"

def fix_image_orientation(image):
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

def save_image_from_bytes(image_bytes):
    if not isinstance(image_bytes, bytes):
        return None
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = fix_image_orientation(image)
        new_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.png")
        image.save(new_path, "PNG")
        return new_path
    except Exception as e:
        st.error(f"Gagal memproses gambar: {e}")
        return ""

def create_pdf_report(filtered_data):
    file_path = f"laporan_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=40, bottomMargin=30)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, spaceBefore=10))
    styles.add(ParagraphStyle(name='ImageTitle', fontSize=10, spaceBefore=6, spaceAfter=2))


    elements = []
    
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            header_text = "<b>PT PLN NUSANTARA SERVICES</b><br/>Unit PLTU Bangka"
            logo_img = RLImage(logo_path, width=0.8*inch, height=0.8*inch)
            header_data = [[logo_img, Paragraph(header_text, styles['Normal'])]]
            header_table = Table(header_data, colWidths=[1*inch, 6*inch])
            header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (1,0), (1,0), 0)]))
            elements.append(header_table)
            elements.append(Spacer(1, 20))
    except Exception:
        pass

    elements.append(Paragraph("LAPORAN MONITORING FLM, CM, & PM", styles["TitleCenter"]))
    elements.append(Spacer(1, 12))

    for i, row in filtered_data.iterrows():
        data = [
            ["ID", str(row.get('ID', ''))],
            ["Tanggal", pd.to_datetime(row.get('Tanggal')).strftime('%Y-%m-%d')],
            ["Jenis", str(row.get('Jenis', ''))],
            ["Area", str(row.get('Area', ''))],
            ["Nomor SR", str(row.get('Nomor SR', ''))],
            ["Nama Pelaksana", str(row.get('Nama Pelaksana', ''))],
            ["Status", str(row.get('Status', ''))],
            ["Keterangan", Paragraph(str(row.get('Keterangan', '')), styles['Normal'])],
        ]

        table = Table(data, colWidths=[100, 380])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 10))
        
        evidance_path = row.get("Evidance")
        if evidance_path and isinstance(evidance_path, str) and os.path.exists(evidance_path):
            elements.append(Paragraph("Evidence Before:", styles['ImageTitle']))
            try:
                elements.append(RLImage(evidance_path, width=4*inch, height=3*inch, kind='bound'))
            except Exception as e:
                print(f"Gagal memuat gambar ke PDF (Before): {e}")
            elements.append(Spacer(1, 6))
        
        evidance_after_path = row.get("Evidance After")
        if evidance_after_path and isinstance(evidance_after_path, str) and os.path.exists(evidance_after_path):
            elements.append(Paragraph("Evidence After:", styles['ImageTitle']))
            try:
                elements.append(RLImage(evidance_after_path, width=4*inch, height=3*inch, kind='bound'))
            except Exception as e:
                print(f"Gagal memuat gambar ke PDF (After): {e}")
            elements.append(Spacer(1, 10))

        elements.append(PageBreak())

    if len(elements) > 2:
        doc.build(elements)
        return file_path
    return None

# ================== Inisialisasi Session State ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.data = load_data()
    st.session_state.last_activity = datetime.now()

if st.session_state.get("logged_in"):
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        logout()
        st.warning("Sesi Anda telah berakhir.")
        st.stop()
    st.session_state.last_activity = datetime.now()
else:
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

st.title("MONITORING FLM, CM, & PM")
st.write("#### Produksi A PLTU Bangka")
st.markdown("---")

if menu == "Input Data":
    st.header("📋 Input Data Pekerjaan Baru")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tanggal = st.date_input("Tanggal", date.today())
            # --- PERUBAHAN: Menambahkan opsi "Preventive Maintenance" ---
            jenis = st.selectbox("Jenis Pekerjaan", ["FLM", "Corrective Maintenance", "Preventive Maintenance"])
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

    with st.expander("✅ **Upload Cepat Evidence After & Selesaikan Pekerjaan** (Cara yang disarankan)"):
        open_jobs = st.session_state.data[st.session_state.data['Status'].isin(['Open', 'On Progress'])]
        if not open_jobs.empty:
            job_options = {f"{row['ID']} - {row['Nama Pelaksana']} - {str(row['Keterangan'])[:30]}...": row['ID'] for index, row in open_jobs.iterrows()}
            
            selected_job_display = st.selectbox("Pilih Pekerjaan yang Selesai:", list(job_options.keys()))
            
            uploaded_evidence_after = st.file_uploader("Upload Bukti Selesai (Evidence After)", type=["png", "jpg", "jpeg"], key="quick_upload")

            if st.button("Selesaikan Pekerjaan Ini"):
                if selected_job_display and uploaded_evidence_after:
                    job_id_to_update = job_options[selected_job_display]
                    
                    evidence_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}{os.path.splitext(uploaded_evidence_after.name)[1]}")
                    with open(evidence_path, "wb") as f:
                        f.write(uploaded_evidence_after.getbuffer())
                    
                    job_index = st.session_state.data.index[st.session_state.data['ID'] == job_id_to_update].tolist()
                    if job_index:
                        st.session_state.data.loc[job_index[0], 'Evidance After'] = evidence_path
                        st.session_state.data.loc[job_index[0], 'Status'] = 'Finish'
                        
                        save_data(st.session_state.data)
                        st.success(f"Pekerjaan dengan ID {job_id_to_update} telah diselesaikan!")
                        st.rerun()
                else:
                    st.warning("Mohon pilih pekerjaan dan upload bukti selesai.")
        else:
            st.info("Tidak ada pekerjaan yang berstatus 'Open' atau 'On Progress' saat ini.")
    
    st.markdown("---")

    with st.container():
        st.write("Gunakan filter di bawah untuk mencari data spesifik.")
        data_to_display = st.session_state.data.copy()
        col1, col2, col3 = st.columns(3)
        with col1: filter_jenis = st.selectbox("Saring berdasarkan Jenis:", ["Semua"] + list(data_to_display["Jenis"].dropna().unique()))
        with col2: filter_status = st.selectbox("Saring berdasarkan Status:", ["Semua"] + list(data_to_display["Status"].dropna().unique()))
        if filter_jenis != "Semua": data_to_display = data_to_display[data_to_display["Jenis"] == filter_jenis]
        if filter_status != "Semua": data_to_display = data_to_display[data_to_display["Status"] == filter_status]
        
    st.markdown("---")
    
    # --- PERUBAHAN: Menambahkan opsi "Preventive Maintenance" pada kolom editor ---
    column_config = { 
        "Tanggal": st.column_config.DateColumn("Tanggal", format="YYYY-MM-DD"), 
        "Jenis": st.column_config.SelectboxColumn("Jenis", options=["FLM", "Corrective Maintenance", "Preventive Maintenance"]), 
        "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"]), 
        "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"]), 
        "Keterangan": st.column_config.TextColumn("Keterangan", width="large"), 
        "Evidance": st.column_config.ImageColumn("Evidence Before"), 
        "Evidance After": st.column_config.ImageColumn("Evidence After"), 
        "ID": st.column_config.TextColumn("ID", disabled=True), 
    }
    
    st.info("Untuk mengedit detail lainnya (selain foto), gunakan tabel di bawah dan tekan 'Simpan Perubahan Tabel'.")
    edited_data = st.data_editor(data_to_display, key="data_editor", disabled=["Evidance", "Evidance After"], use_container_width=True, column_order=["ID", "Tanggal", "Jenis", "Area", "Status", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance", "Evidance After"])

    if st.button("Simpan Perubahan Tabel", type="primary"):
        if st.session_state.user == 'admin':
            updated_df = st.session_state.data.set_index('ID')
            edited_df = edited_data.set_index('ID')
            updated_df.update(edited_df)
            st.session_state.data = updated_df.reset_index()
            save_data(st.session_state.data)
            st.toast("Perubahan data teks telah disimpan!", icon="✅")
            st.rerun()
        else:
            st.warning("Hanya 'admin' yang dapat menyimpan perubahan.")

    st.markdown("---"); st.subheader("📄 Laporan & Unduh Data")
    csv_data = st.session_state.data.to_csv(index=False).encode('utf-8')
    st.download_button("Download Seluruh Data (CSV)", data=csv_data, file_name="monitoring_data_lengkap.csv", mime="text/csv")

    with st.expander("**Export Laporan ke PDF**"):
        col1, col2, col3 = st.columns(3)
        with col1: export_start_date = st.date_input("Tanggal Mulai", date.today().replace(day=1))
        with col2: export_end_date = st.date_input("Tanggal Akhir", date.today())
        # --- PERUBAHAN: Menambahkan opsi "Preventive Maintenance" pada filter PDF ---
        with col3: export_type = st.selectbox("Pilih Jenis Pekerjaan", ["Semua", "FLM", "Corrective Maintenance", "Preventive Maintenance"], key="pdf_export_type")

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

