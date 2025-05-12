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

# ================== Configuration ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== HIDE STREAMLIT MENU & FOOTER ==================
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ================== CSS for Design ==================
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

# ================== Helper Functions ==================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Admin Credentials
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

# ================== Timeout Session ==================
if "last_activity" in st.session_state:
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        logout()
st.session_state.last_activity = datetime.now()

# ================== Initialize State ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = load_data()

# ================== Login & Navigation ==================
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

# ================== Main Interface ==================
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

# ================== View Data ==================
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
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Add title for the report
            elements.append(Paragraph("Laporan Monitoring FLM & Corrective Maintenance", styles["Title"]))
            elements.append(Spacer(1, 12))

            # Loop through each entry and format the report
            for _, row in filtered_data.iterrows():
                # Adding each field with a simple layout
                elements.append(Paragraph(f"<b>ID :</b> {row['ID']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Tanggal :</b> {row['Tanggal'].strftime('%Y-%m-%d')}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Jenis :</b> {row['Jenis']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Area :</b> {row['Area']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Nomor SR :</b> {row['Nomor SR']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Nama Pelaksana :</b> {row['Nama Pelaksana']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Keterangan :</b> {row['Keterangan']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Status :</b> {row['Status']}", styles["Normal"]))
                elements.append(Spacer(1, 12))  # Space between sections

                # Evidence section (if exists)
                if row["Evidance"] and os.path.exists(row["Evidance"]):
                    elements.append(Paragraph("<b>Evidence :</b>", styles["Italic"]))
                    elements.append(Paragraph(f"<i>{row['Evidance']}</i>", styles["Normal"]))
                    elements.append(Spacer(1, 12))

                elements.append(PageBreak())  # Page break between each entry

            # Generate PDF
            doc.build(elements)
            with open(file_path, "rb") as f:
                st.download_button("Unduh PDF", f, file_name=file_path)


# ================== Footer ==================
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
