import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta, date
import uuid
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ================== Konfigurasi Halaman Streamlit ==================
# Menggunakan layout "wide" agar lebih banyak informasi bisa tampil, terutama untuk data_editor
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS Kustom untuk Tampilan ==================
# Memberikan tampilan modern dan profesional
st.markdown(
    """
    <style>
        /* Mengubah latar belakang utama aplikasi */
        .stApp {
            background: #f0f2f6; /* Warna abu-abu terang yang netral */
            color: #333; /* Warna teks gelap agar mudah dibaca */
        }
        /* Style untuk judul utama */
        .stApp h1 {
            color: #1E3A8A; /* Biru tua untuk judul, memberikan kesan korporat */
        }
        /* Style untuk tombol */
        .stButton>button {
            border-radius: 20px;
            border: 1px solid #1E3A8A;
            background-color: #1E3A8A;
            color: white;
            transition: all 0.2s ease-in-out;
        }
        .stButton>button:hover {
            background-color: white;
            color: #1E3A8A;
            border: 1px solid #1E3A8A;
        }
        /* Style untuk sidebar */
        [data-testid="stSidebar"] {
            background-color: #1E3A8A;
        }
        [data-testid="stSidebar"] .stMarkdown {
            color: white;
        }
        [data-testid="stSidebar"] .stRadio > label {
            color: white;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== Inisialisasi Awal ==================
# Menentukan path folder dan file data
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATA_FILE = "monitoring_data.csv"

# ================== Fungsi-Fungsi Helper ==================

def hash_password(password):
    """Mengenkripsi password menggunakan SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def load_data():
    """Memuat data dari file CSV. Jika file tidak ada, buat DataFrame kosong."""
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, parse_dates=["Tanggal"])
        # Pastikan semua kolom yang dibutuhkan ada
        required_cols = ["ID", "Tanggal", "Jenis", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan", "Status", "Evidance", "Evidance After"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = pd.NA
        return df
    return pd.DataFrame(columns=["ID", "Tanggal", "Jenis", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan", "Status", "Evidance", "Evidance After"])

def save_data(df):
    """Menyimpan DataFrame ke file CSV."""
    df.to_csv(DATA_FILE, index=False)

def logout():
    """Membersihkan session state untuk logout."""
    st.session_state.clear()
    st.rerun()

# --- PERUBAHAN 1: Fungsi baru untuk ID yang lebih andal ---
# Fungsi ini mencegah ID duplikat jika ada data yang dihapus.
def generate_next_id(df, jenis):
    """Membuat ID unik berikutnya berdasarkan jenis (FLM/CM) dan nomor terakhir."""
    prefix = 'FLM' if jenis == 'FLM' else 'CM'
    # Filter data berdasarkan prefix
    relevant_ids = df[df['ID'].str.startswith(prefix, na=False)]
    if relevant_ids.empty:
        return f"{prefix}-001"
    
    # Ekstrak nomor dari ID, konversi ke integer, dan cari nilai maksimal
    max_num = relevant_ids['ID'].str.split('-').str[1].astype(int).max()
    next_num = max_num + 1
    return f"{prefix}-{next_num:03d}"

def create_pdf_report(filtered_data):
    """Menciptakan laporan PDF dari data yang difilter."""
    file_path = "laporan_monitoring.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=40, bottomMargin=30)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=16, leading=22, spaceAfter=20, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubTitle', alignment=TA_LEFT, fontSize=12, leading=16, spaceAfter=10, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='NormalLeft', alignment=TA_LEFT, fontSize=10, fontName='Helvetica'))

    elements = []
    
    # Menambahkan Kop Laporan
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
             # Membuat tabel untuk kop surat (logo dan teks)
            header_data = [[RLImage(logo_path, width=0.8*inch, height=0.8*inch), 
                            Paragraph("<b>PT PLN (PERSERO)</b><br/>UNIT INDUK PEMBANGKITAN SUMATERA BAGIAN SELATAN<br/>UNIT PELAKSANA PEMBANGKITAN BANGKA BELITUNG<br/><b>PLTU BANGKA UNIT 1 & 2</b>", styles['NormalLeft'])]]
            header_table = Table(header_data, colWidths=[1*inch, 6*inch])
            header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            elements.append(header_table)
            elements.append(Spacer(1, 20))
    except Exception as e:
        st.warning(f"Logo tidak bisa dimuat ke PDF: {e}")

    elements.append(Paragraph("LAPORAN MONITORING FLM & CORRECTIVE MAINTENANCE", styles['TitleCenter']))
    elements.append(Spacer(1, 12))

    for i, row in filtered_data.iterrows():
        # Membuat tabel data untuk setiap entri
        data = [
            ["ID Laporan", f": {row.get('ID', 'N/A')}"],
            ["Tanggal", f": {pd.to_datetime(row.get('Tanggal')).strftime('%d %B %Y')}"],
            ["Jenis Pekerjaan", f": {row.get('Jenis', 'N/A')}"],
            ["Area", f": {row.get('Area', 'N/A')}"],
            ["Nomor SR", f": {row.get('Nomor SR', 'N/A')}"],
            ["Nama Pelaksana", f": {row.get('Nama Pelaksana', 'N/A')}"],
            ["Status", f": {row.get('Status', 'N/A')}"],
            ["Keterangan", Paragraph(f": {row.get('Keterangan', 'N/A')}", styles['NormalLeft'])],
        ]

        table = Table(data, colWidths=[120, 360])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 10))

        # Menambahkan gambar evidence
        img_data = []
        ev_before_path = row.get("Evidance")
        ev_after_path = row.get("Evidance After")
        
        col_widths = []
        img_row = []

        if ev_before_path and os.path.exists(str(ev_before_path)):
            img_row.append(RLImage(str(ev_before_path), width=3*inch, height=2.25*inch))
            col_widths.append(3*inch)
        
        if ev_after_path and os.path.exists(str(ev_after_path)):
            img_row.append(RLImage(str(ev_after_path), width=3*inch, height=2.25*inch))
            col_widths.append(3*inch)

        if img_row:
            # Tabel untuk judul gambar
            title_row = []
            if ev_before_path and os.path.exists(str(ev_before_path)):
                title_row.append(Paragraph("<b>Evidence Before</b>", styles['SubTitle']))
            if ev_after_path and os.path.exists(str(ev_after_path)):
                 title_row.append(Paragraph("<b>Evidence After</b>", styles['SubTitle']))

            img_data.append(title_row)
            img_data.append(img_row)
            
            img_table = Table(img_data, colWidths=col_widths)
            img_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
            elements.append(img_table)
            elements.append(Spacer(1, 20))

        elements.append(PageBreak())

    doc.build(elements)
    return file_path

# ================== Inisialisasi Session State ==================
# Dilakukan sekali saat aplikasi pertama kali dijalankan atau setelah logout
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.data = load_data()
    st.session_state.last_activity = datetime.now()

# ================== Manajemen Sesi & Logout Otomatis ==================
if st.session_state.logged_in:
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        st.warning("Sesi Anda telah berakhir karena tidak ada aktivitas. Silakan login kembali.")
        logout()
    st.session_state.last_activity = datetime.now()

# ================== Halaman Login ==================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.title("Login Sistem Monitoring")
        try:
            logo = Image.open("logo.png")
            st.image(logo, width=150)
        except FileNotFoundError:
            st.error("File `logo.png` tidak ditemukan.")

        # Kredensial login bisa dari st.secrets untuk deployment
        ADMIN_CREDENTIALS = {
            "admin": hash_password(st.secrets.get("ADMIN_PASSWORD", "pltubangka")),
            "operator": hash_password(st.secrets.get("OPERATOR_PASSWORD", "op123")),
        }
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                hashed_pw_input = hash_password(password)
                if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == hashed_pw_input:
                    st.session_state.logged_in = True
                    st.session_state.user = username
                    st.rerun()
                else:
                    st.error("Username atau password salah.")
    st.stop() # Menghentikan eksekusi script sampai login berhasil

# ================== Tampilan Utama Setelah Login ==================

# --- Sidebar Navigasi ---
with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"Selamat datang, **{st.session_state.user}**!")
    try:
        logo = Image.open("logo.png")
        st.image(logo, use_column_width=True)
    except FileNotFoundError:
        pass
        
    menu = st.radio("Pilih Menu:", ["Input Data", "Manajemen & Laporan Data"], label_visibility="collapsed")
    
    if st.button("Logout"):
        logout()
    
    st.markdown("---")
    st.info("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")

# --- Konten Halaman ---
st.title("MONITORING FLM & CORRECTIVE MAINTENANCE")
st.write("#### Produksi A PLTU Bangka")
st.markdown("---")

# --- Menu: Input Data ---
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

        st.markdown("---")
        st.subheader("Upload Bukti Pekerjaan (Evidence)")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1:
            evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
        with col_ev2:
            evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
        
        submit_button = st.form_submit_button("Simpan Data")
        
        if submit_button:
            if not all([nomor_sr, nama_pelaksana, keterangan]):
                st.error("Mohon isi semua field yang wajib: Nomor SR, Nama Pelaksana, dan Keterangan.")
            else:
                # Proses penyimpanan file evidence
                evidance_path = ""
                if evidance_file:
                    ext = os.path.splitext(evidance_file.name)[1]
                    evidance_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}{ext}")
                    with open(evidance_path, "wb") as f:
                        f.write(evidance_file.getbuffer())

                evidance_after_path = ""
                if evidance_after_file:
                    ext = os.path.splitext(evidance_after_file.name)[1]
                    evidance_after_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}{ext}")
                    with open(evidance_after_path, "wb") as f:
                        f.write(evidance_after_file.getbuffer())

                # Membuat ID baru yang andal
                new_id = generate_next_id(st.session_state.data, jenis)
                
                new_row = pd.DataFrame([{
                    "ID": new_id, "Tanggal": pd.to_datetime(tanggal), "Jenis": jenis, "Area": area, 
                    "Nomor SR": nomor_sr, "Nama Pelaksana": nama_pelaksana, "Keterangan": keterangan, 
                    "Status": status, "Evidance": evidance_path, "Evidance After": evidance_after_path
                }])
                
                st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
                save_data(st.session_state.data)
                st.success(f"Data dengan ID '{new_id}' berhasil disimpan!")


# --- Menu: Manajemen & Laporan Data ---
elif menu == "Manajemen & Laporan Data":
    st.header("📊 Manajemen & Laporan Data")
    
    # --- PERUBAHAN 2: Mengganti st.dataframe dengan st.data_editor ---
    # Ini adalah cara modern untuk menampilkan, mengedit, dan menghapus data.
    st.info("Anda dapat mengedit data langsung di tabel di bawah ini. Untuk menghapus baris, tandai baris dan tekan tombol 'delete' di keyboard Anda.")
    
    # Konfigurasi kolom agar lebih interaktif
    column_config = {
        "Tanggal": st.column_config.DateColumn("Tanggal", format="YYYY-MM-DD"),
        "Jenis": st.column_config.SelectboxColumn("Jenis", options=["FLM", "Corrective Maintenance"]),
        "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"]),
        "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"]),
        "Keterangan": st.column_config.TextColumn("Keterangan", width="large"),
        "Evidance": st.column_config.ImageColumn("Evidence Before", help="Klik untuk memperbesar"),
        "Evidance After": st.column_config.ImageColumn("Evidence After", help="Klik untuk memperbesar"),
        # Sembunyikan kolom ID karena tidak untuk diedit pengguna
        "ID": st.column_config.TextColumn("ID", disabled=True),
    }

    # Menampilkan data editor. Kunci "data_editor" digunakan untuk mendeteksi perubahan.
    edited_data = st.data_editor(
        st.session_state.data,
        column_config=column_config,
        num_rows="dynamic",  # Memungkinkan pengguna menambah dan menghapus baris
        key="data_editor",
        use_container_width=True,
        # Mengatur urutan kolom agar lebih logis
        column_order=["ID", "Tanggal", "Jenis", "Area", "Status", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance", "Evidance After"]
    )

    # Logika untuk menyimpan perubahan dari data_editor
    # `st.session_state.data_editor` akan berisi status editor (baris yang diedit, ditambah, dihapus)
    if "data_editor" in st.session_state:
        # Cek apakah ada perubahan
        if len(edited_data) != len(st.session_state.data) or not edited_data.equals(st.session_state.data):
             # Hanya admin yang bisa mengedit/menghapus
            if st.session_state.user == 'admin':
                st.session_state.data = edited_data.copy()
                save_data(st.session_state.data)
                st.toast("Perubahan telah disimpan!", icon="✅")
            else:
                 st.warning("Hanya 'admin' yang dapat mengedit atau menghapus data.")
                 # Kembalikan ke state semula jika bukan admin
                 st.rerun()


    # --- Bagian Laporan dan Unduh ---
    st.markdown("---")
    st.subheader("📄 Laporan & Unduh Data")

    col1, col2 = st.columns([1, 1])
    
    with col1:
        with st.expander("**Export Laporan ke PDF**", expanded=True):
            today = date.today()
            export_start_date = st.date_input("Tanggal Mulai", today.replace(day=1))
            export_end_date = st.date_input("Tanggal Akhir", today)
            export_type = st.selectbox("Pilih Jenis Pekerjaan", ["Semua", "FLM", "Corrective Maintenance"])

            if st.button("Buat Laporan PDF"):
                # Filter data berdasarkan rentang tanggal dan jenis
                filtered_data = st.session_state.data.copy()
                filtered_data["Tanggal"] = pd.to_datetime(filtered_data["Tanggal"])
                
                mask = (filtered_data["Tanggal"].dt.date >= export_start_date) & \
                       (filtered_data["Tanggal"].dt.date <= export_end_date)
                
                if export_type != "Semua":
                    mask &= (filtered_data["Jenis"] == export_type)
                
                final_data_to_export = filtered_data[mask]

                if final_data_to_export.empty:
                    st.warning("Tidak ada data yang ditemukan untuk rentang tanggal dan jenis yang dipilih.")
                else:
                    with st.spinner("Membuat file PDF..."):
                        pdf_file = create_pdf_report(final_data_to_export)
                    st.success("Laporan PDF berhasil dibuat!")
                    with open(pdf_file, "rb") as f:
                        st.download_button(
                            "Unduh Laporan PDF", f, 
                            file_name=f"Laporan_{export_type}_{export_start_date}_sd_{export_end_date}.pdf"
                        )
    
    with col2:
        with st.expander("**Unduh Data Mentah (CSV)**", expanded=True):
            st.write("Klik tombol di bawah untuk mengunduh semua data monitoring dalam format CSV.")
            csv_data = st.session_state.data.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Data CSV",
                data=csv_data,
                file_name="monitoring_data_lengkap.csv",
                mime="text/csv"
            )

