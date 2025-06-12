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
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle

st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== HIDE STREAMLIT MENU & FOOTER ==================
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ================== Konfigurasi Streamlit ==================


# ================== CSS untuk Tampilan ==================
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(to right, #141e30, #243b55);
            color: white;
            font-family: 'Arial', sans-serif;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== Logo ==================
try:
    logo = Image.open("logo.png")
    st.image(logo, width=150)
except:
    st.error("Logo tidak ditemukan.")

# ================== Folder & File ==================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATA_FILE = "monitoring_data.csv"

# ================== Fungsi Helper ==================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Kredensial Login
ADMIN_CREDENTIALS = {
    "admin": hash_password(st.secrets.get("ADMIN_PASSWORD", "pltubangka")),
    "operator": hash_password(st.secrets.get("OPERATOR_PASSWORD", "op123")),
}

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, parse_dates=["Tanggal"])
        if "Evidance After" not in df.columns:
            df["Evidance After"] = ""
        return df
    return pd.DataFrame(columns=["ID", "Tanggal", "Jenis", "Area", "Nomor SR",
                                 "Nama Pelaksana", "Keterangan", "Status", "Evidance", "Evidance After"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def logout():
    st.session_state.clear()
    st.experimental_rerun()

# ================== Timeout Sesi ==================
if "last_activity" in st.session_state:
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        logout()
st.session_state.last_activity = datetime.now()

# ================== Inisialisasi State ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = load_data()

# ================== Login & Navigasi ==================
if not st.session_state.logged_in:
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == hash_password(password):
            st.session_state.logged_in = True
            st.session_state.user = username
            st.sidebar.success("Login berhasil!")
        else:
            st.sidebar.error("Username atau password salah")
    st.stop()
else:
    with st.sidebar:
        st.title("Menu Navigasi")
        menu = st.radio("Pilih Menu", ["Input Data", "Lihat Data", "Export PDF"])
        if st.button("Logout"):
            logout()

# ================== Tampilan Utama ==================
st.title("MONITORING FLM & Corrective Maintenance")
st.write("Produksi A PLTU Bangka")

# ================== Input Data ==================
if menu == "Input Data":
    st.subheader("Input Data")
    with st.form("input_form"):
        tanggal = st.date_input("Tanggal", date.today())
        jenis = st.selectbox("Jenis", ["FLM", "Corrective Maintenance"])
        area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
        nomor_sr = st.text_input("Nomor SR")
        nama_pelaksana = st.text_input("Nama Pelaksana")
        keterangan = st.text_area("Keterangan")
        status = st.selectbox("Status", ["Finish", "Belum"])
        evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
        evidance_after_file = None
        if jenis != "FLM":
            evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
        submit_button = st.form_submit_button("Submit")
        
        if submit_button:
            if not nomor_sr.strip() or not nama_pelaksana.strip() or not keterangan.strip():
                st.error("Nomor SR, Nama Pelaksana, dan Keterangan tidak boleh kosong!")
            else:
                evidance_path = ""
                if evidance_file:
                    ext = evidance_file.name.split('.')[-1]
                    evidance_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.{ext}")
                    with open(evidance_path, "wb") as f:
                        f.write(evidance_file.getbuffer())
                evidance_after_path = ""
                if jenis != "FLM" and evidance_after_file:
                    ext = evidance_after_file.name.split('.')[-1]
                    evidance_after_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.{ext}")
                    with open(evidance_after_path, "wb") as f:
                        f.write(evidance_after_file.getbuffer())
                new_id = f"{'FLM' if jenis == 'FLM' else 'CM'}-{len(st.session_state.data) + 1:03d}"
                new_row = pd.DataFrame([[new_id, tanggal, jenis, area, nomor_sr, nama_pelaksana, keterangan, status, evidance_path, evidance_after_path]],
                                        columns=st.session_state.data.columns)
                st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
                save_data(st.session_state.data)
                st.success("Data berhasil disimpan!")
                st.experimental_rerun()

# ================== Lihat Data ==================
elif menu == "Lihat Data":
    st.subheader("Data Monitoring")
    st.dataframe(st.session_state.data)

# ================== Export PDF ==================
elif menu == "Export PDF":
    st.subheader("Export Laporan PDF")
    export_start_date = st.date_input("Export Start Date", date.today())
    export_end_date = st.date_input("Export End Date", date.today())
    export_type = st.selectbox("Pilih Tipe Export", ["Semua", "FLM", "Corrective Maintenance"])
    if st.button("Export ke PDF"):
        filtered_data = st.session_state.data.copy()
        filtered_data["Tanggal"] = pd.to_datetime(filtered_data["Tanggal"])
        filtered_data = filtered_data[
            (filtered_data["Tanggal"] >= pd.to_datetime(export_start_date)) & 
            (filtered_data["Tanggal"] <= pd.to_datetime(export_end_date))
        ]
        if export_type != "Semua":
            filtered_data = filtered_data[filtered_data["Jenis"] == export_type]
        if filtered_data.empty:
            st.warning("Data tidak ditemukan.")
        else:



file_path = "laporan_monitoring.pdf"
doc = SimpleDocTemplate(file_path, pagesize=A4,
                        rightMargin=30, leftMargin=30,
                        topMargin=40, bottomMargin=30)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, spaceBefore=10))

elements = []
elements.append(Paragraph("LAPORAN MONITORING FLM & CORRECTIVE MAINTENANCE", styles["TitleCenter"]))
elements.append(Spacer(1, 12))

for i, row in filtered_data.iterrows():
    data = [
        ["ID", row['ID']],
        ["Tanggal", row['Tanggal'].strftime('%Y-%m-%d')],
        ["Jenis", row['Jenis']],
        ["Area", row['Area']],
        ["Nomor SR", row['Nomor SR']],
        ["Nama Pelaksana", row['Nama Pelaksana']],
        ["Status", row['Status']],
        ["Keterangan", row['Keterangan']],
    ]

    table = Table(data, colWidths=[100, 380])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 10))

    if row["Evidance"] and os.path.exists(row["Evidance"]):
        elements.append(Paragraph("Evidence Before:", styles["Italic"]))
        elements.append(RLImage(row["Evidance"], width=4*inch, height=3*inch))
        elements.append(Spacer(1, 6))
    if row["Evidance After"] and os.path.exists(row["Evidance After"]):
        elements.append(Paragraph("Evidence After:", styles["Italic"]))
        elements.append(RLImage(row["Evidance After"], width=4*inch, height=3*inch))
        elements.append(Spacer(1, 10))

    elements.append(PageBreak())

doc.build(elements)

            
            with open(file_path, "rb") as f:
                st.download_button("Unduh PDF", f, file_name=file_path)

# ================== Preview Evidence ==================
st.markdown("### Preview Evidence")
if not st.session_state.data.empty:
    id_pilih = st.selectbox("Pilih ID untuk melihat evidence", st.session_state.data["ID"])
    selected_row = st.session_state.data[st.session_state.data["ID"] == id_pilih]
    if not selected_row.empty:
        ev_before = selected_row["Evidance"].values[0]
        ev_after = selected_row["Evidance After"].values[0]
        if ev_before and os.path.exists(ev_before):
            with st.expander(f"Evidence Before untuk {id_pilih}"):
                st.image(ev_before, caption=f"Before - {id_pilih}", use_column_width=True)
        if ev_after and os.path.exists(ev_after):
            with st.expander(f"Evidence After untuk {id_pilih}"):
                st.image(ev_after, caption=f"After - {id_pilih}", use_column_width=True)
    if st.button("Hapus Data"):
        st.session_state.data = st.session_state.data[st.session_state.data["ID"] != id_pilih]
        save_data(st.session_state.data)
        st.success("Data berhasil dihapus!")
        st.experimental_rerun()

# ================== Download CSV ==================
csv_data = st.session_state.data.to_csv(index=False)
st.download_button("Download Data CSV", data=csv_data, file_name="monitoring_data.csv", mime="text/csv")

# ================== Footer ==================
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
