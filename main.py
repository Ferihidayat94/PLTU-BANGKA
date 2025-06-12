import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta, date
import uuid
from PIL import Image, ExifTags
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer, PageBreak, Flowable
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

# Kelas untuk garis pemisah
class Line(Flowable):
    def __init__(self, width, color=colors.grey):
        Flowable.__init__(self)
        self.width = width
        self.color = color

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(1)
        self.canv.line(0, 0, self.width, 0)

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

def generate_next_id(df, jenis):
    prefix = 'FLM' if jenis == 'FLM' else 'CM'
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

# --- FUNGSI PDF DENGAN LAYOUT EVIDENCE YANG LEBIH RAPI ---
def create_pdf_report(filtered_data):
    file_path = f"laporan_monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4,
                            rightMargin=inch*0.5, leftMargin=inch*0.5,
                            topMargin=inch*0.5, bottomMargin=inch*0.5)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=16, leading=22, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubTitle', alignment=TA_CENTER, fontSize=11, fontName='Helvetica-Bold', spaceAfter=5))
    styles.add(ParagraphStyle(name='NormalLeft', alignment=TA_LEFT, fontSize=10, leading=14, fontName='Helvetica'))

    elements = []
    
    # KOP LAPORAN
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            header_text = "<b>PT PLN NUSANTARA SERVICES</b><br/>Unit PLTU Bangka"
            logo_img = RLImage(logo_path, width=0.9*inch, height=0.6*inch)
            header_data = [[logo_img, Paragraph(header_text, styles['NormalLeft'])]]
            header_table = Table(header_data, colWidths=[1*inch, 6*inch])
            header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (1,0), (1,0), 0)]))
            elements.append(header_table)
            elements.append(Spacer(1, 15))
    except Exception as e:
        st.warning(f"Logo tidak bisa dimuat ke PDF: {e}")

    elements.append(Paragraph("LAPORAN MONITORING FLM & CORRECTIVE MAINTENANCE", styles['TitleCenter']))
    elements.append(Line(doc.width))
    elements.append(Spacer(1, 20))

    for i, row in filtered_data.iterrows():
        # DATA UTAMA DALAM TABEL
        data = [
            ["ID Laporan", f": {row.get('ID', 'N/A')}"], ["Tanggal", f": {pd.to_datetime(row.get('Tanggal')).strftime('%d %B %Y')}"],
            ["Jenis Pekerjaan", f": {row.get('Jenis', 'N/A')}"], ["Area", f": {row.get('Area', 'N/A')}"],
            ["Nomor SR", f": {row.get('Nomor SR', 'N/A')}"], ["Nama Pelaksana", f": {row.get('Nama Pelaksana', 'N/A')}"],
            ["Status", f": {row.get('Status', 'N/A')}"], ["Keterangan", Paragraph(f": {str(row.get('Keterangan', ''))}", styles['NormalLeft'])],
        ]
        table = Table(data, colWidths=[1.5*inch, 5.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 15))
        
        # PROSES GAMBAR EVIDENCE
        def process_image_for_pdf(path):
            if isinstance(path, str) and os.path.exists(path):
                try:
                    pil_image = Image.open(path)
                    pil_image = fix_image_orientation(pil_image)
                    return RLImage(pil_image, width=3.4*inch, height=2.55*inch, kind='bound')
                except Exception:
                    return None
            return None

        img_before = process_image_for_pdf(row.get("Evidance"))
        img_after = process_image_for_pdf(row.get("Evidance After"))

        # BUAT TABEL UNTUK GAMBAR
        if img_before or img_after:
            evidence_data = [
                [Paragraph("<b>Evidence Before</b>", styles['SubTitle']), Paragraph("<b>Evidence After</b>", styles['SubTitle'])],
                [img_before if img_before else "", img_after if img_after else ""]
            ]
            
            evidence_table = Table(evidence_data, colWidths=[doc.width/2, doc.width/2])
            evidence_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOX', (0,0), (-1,-1), 1, colors.lightgrey),
                ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
                ('BOTTOMPADDING', (0,1), (-1,-1), 10) # Padding bawah untuk gambar
            ]))
            elements.append(evidence_table)
        
        # Garis pemisah antar entri
        elements.append(Spacer(1, 20))
        elements.append(Line(doc.width, color=colors.black))
        elements.append(Spacer(1, 20))

    if len(elements) > 4: # Check if there is more than just the header
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
    
    with st.expander("✅ Upload Cepat Evidence After & Selesaikan Pekerjaan"):
        open_jobs = st.session_state.data[st.session_state.data['Status'].isin(['Open', 'On Progress'])]
        if not open_jobs.empty:
            job_options = {f"{row['ID']} - {str(row['Keterangan'])[:30]}...": row['ID'] for index, row in open_jobs.iterrows()}
            
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


    with st.container():
        st.write("Gunakan filter di bawah untuk melihat data lainnya.")
        data_to_display = st.session_state.data.copy()
        col1, col2, col3 = st.columns(3)
        with col1: filter_jenis = st.selectbox("Saring berdasarkan Jenis:", ["Semua"] + list(data_to_display["Jenis"].dropna().unique()))
        with col2: filter_status = st.selectbox("Saring berdasarkan Status:", ["Semua"] + list(data_to_display["Status"].dropna().unique()))
        if filter_jenis != "Semua": data_to_display = data_to_display[data_to_display["Jenis"] == filter_jenis]
        if filter_status != "Semua": data_to_display = data_to_display[data_to_display["Status"] == filter_status]
        
    st.markdown("---")
    
    column_config = { "Tanggal": st.column_config.DateColumn("Tanggal", format="YYYY-MM-DD"), "Jenis": st.column_config.SelectboxColumn("Jenis", options=["FLM", "Corrective Maintenance"]), "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"]), "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"]), "Keterangan": st.column_config.TextColumn("Keterangan", width="large"), "Evidance": st.column_config.ImageColumn("Evidence Before"), "Evidance After": st.column_config.ImageColumn("Evidence After"), "ID": st.column_config.TextColumn("ID", disabled=True), }
    
    st.info("Untuk mengedit data lainnya, ubah langsung di tabel dan tekan 'Simpan Perubahan Tabel'.")
    edited_data = st.data_editor(data_to_display, column_config=column_config, num_rows="dynamic", key="data_editor", use_container_width=True, column_order=["ID", "Tanggal", "Jenis", "Area", "Status", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance", "Evidance After"])

    if st.button("Simpan Perubahan Tabel", type="primary"):
        if st.session_state.user == 'admin':
            final_df = edited_data.copy()
            
            for i, row in final_df.iterrows():
                for col in ['Evidance', 'Evidance After']:
                    if isinstance(row[col], bytes):
                        path = save_image_from_bytes(row[col])
                        final_df.loc[i, col] = path

            new_rows_mask = final_df['ID'].isna()
            if new_rows_mask.any():
                temp_data_for_id_gen = pd.concat([st.session_state.data, final_df[new_rows_mask]], ignore_index=True)
                for i in final_df[new_rows_mask].index:
                    jenis = final_df.loc[i, 'Jenis']
                    final_df.loc[i, 'ID'] = generate_next_id(temp_data_for_id_gen, jenis)
            
            main_data = st.session_state.data.copy()
            combined_data = pd.concat([main_data, final_df]).drop_duplicates(subset=['ID'], keep='last')
            
            final_ids = set(final_df['ID'].dropna())
            combined_data = combined_data[combined_data['ID'].isin(final_ids)]

            st.session_state.data = combined_data.reset_index(drop=True)
            save_data(st.session_state.data)
            st.toast("Perubahan tabel telah disimpan!", icon="✅")
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

