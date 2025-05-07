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


# ================== HIDE STREAMLIT MENU & FOOTER ==================
hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ================== Konfigurasi Streamlit (harus pertama) ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS untuk tampilan Streamlit ==================
st.markdown(
    """
    <style>
        .stApp {
            background: linear-gradient(to right, #141e30, #243b55);
            color: white;
            font-family: 'Arial', sans-serif;
        }
        .input-container {
            margin-top: 20px;
            margin-bottom: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== Tampilan Logo (Streamlit) ==================
try:
    logo = Image.open("logo.png")
    st.image(logo, width=150)
except Exception as e:
    st.error("Logo tidak ditemukan. Pastikan file logo.png tersedia.")

# ================== Konfigurasi Folder & File ==================
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
DATA_FILE = "monitoring_data.csv"

# ================== Fungsi Helper ==================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Kredensial (gunakan st.secrets atau .env untuk produksi)
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

# ================== Timeout Login (30 menit) ==================
if "last_activity" in st.session_state:
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        logout()
st.session_state.last_activity = datetime.now()

# ================== Inisialisasi State ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = load_data()

# ================== Sidebar: Login & Navigasi ==================
if not st.session_state.logged_in:
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == hash_password(password):
            st.session_state.logged_in = True
            st.session_state.user = username
            st.sidebar.success("Login successful!")
        else:
            st.sidebar.error("Invalid username or password")
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

# ================== Menu: Input Data ==================
if menu == "Input Data":
    st.subheader("Input Data FLM & CM")
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
                # Simpan file dengan nama unik menggunakan UUID
                evidance_path = ""
                if evidance_file is not None:
                    ext = evidance_file.name.split('.')[-1]
                    evidance_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.{ext}")
                    with open(evidance_path, "wb") as f:
                        f.write(evidance_file.getbuffer())
                evidance_after_path = ""
                if jenis != "FLM" and evidance_after_file is not None:
                    ext = evidance_after_file.name.split('.')[-1]
                    evidance_after_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.{ext}")
                    with open(evidance_after_file, "wb") as f:
                        f.write(evidance_after_file.getbuffer())
                id_prefix = "FLM" if jenis == "FLM" else "CM"
                new_id = f"{id_prefix}-{len(st.session_state.data) + 1:03d}"
                new_row = pd.DataFrame([[new_id, tanggal, jenis, area, nomor_sr, nama_pelaksana, keterangan, status, evidance_path, evidance_after_path]],
                                        columns=st.session_state.data.columns)
                st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
                save_data(st.session_state.data)
                st.success("Data berhasil disimpan!")
                st.experimental_rerun()

# ================== Menu: Lihat Data ==================
elif menu == "Lihat Data":
    st.subheader("Data Monitoring")
    st.dataframe(st.session_state.data)

# ================== Menu: Export PDF ==================
elif menu == "Export PDF":
    st.subheader("Export Laporan PDF")
    export_start_date = st.date_input("Export Start Date", date.today(), key="export_start_date")
    export_end_date = st.date_input("Export End Date", date.today(), key="export_end_date")
    export_type = st.selectbox("Pilih Tipe Export", ["Semua", "FLM", "Corrective Maintenance"], key="export_type")
    if st.button("Export ke PDF"):
        filtered_data = st.session_state.data.copy()
        if not filtered_data.empty:
            filtered_data["Tanggal"] = pd.to_datetime(filtered_data["Tanggal"])
            start = pd.to_datetime(export_start_date)
            end = pd.to_datetime(export_end_date)
            filtered_data = filtered_data[(filtered_data["Tanggal"] >= start) & (filtered_data["Tanggal"] <= end)]
        if export_type != "Semua":
            filtered_data = filtered_data[filtered_data["Jenis"] == export_type]
        if filtered_data.empty:
            st.warning("Data tidak ditemukan untuk kriteria export tersebut.")
        else:
            pdf_file = export_pdf(filtered_data)
            with open(pdf_file, "rb") as f:
                st.download_button("Unduh PDF", f, file_name=pdf_file)

# ================== Preview Evidence ==================
st.markdown("### Preview Evidence")
if not st.session_state.data.empty:
    id_pilih = st.selectbox("Pilih ID untuk melihat evidence", st.session_state.data["ID"])
    selected_row = st.session_state.data[st.session_state.data["ID"] == id_pilih]
    if not selected_row.empty:
        ev_before = selected_row["Evidance"].values[0]
        ev_after = selected_row["Evidance After"].values[0]
        if ev_before and os.path.exists(ev_before):
            with st.expander(f"Evidence Before untuk {id_pilih}", expanded=False):
                st.image(ev_before, caption=f"Evidence Before untuk {id_pilih}", use_column_width=True)
        else:
            st.warning("Evidence Before tidak ditemukan atau belum diupload.")
        if ev_after and os.path.exists(ev_after):
            with st.expander(f"Evidence After untuk {id_pilih}", expanded=False):
                st.image(ev_after, caption=f"Evidence After untuk {id_pilih}", use_column_width=True)
        else:
            st.info("Tidak ada Evidence After untuk record ini.")
    else:
        st.warning("Pilih ID yang memiliki evidence.")
    
    if st.button("Hapus Data"):
        st.session_state.data = st.session_state.data[st.session_state.data["ID"] != id_pilih]
        save_data(st.session_state.data)
        st.success("Data berhasil dihapus!")
        st.experimental_rerun()
    
    csv_data = st.session_state.data.to_csv(index=False)
    st.download_button("Download Data CSV", data=csv_data, file_name="monitoring_data.csv", mime="text/csv")

st.info("PLTU Bangka 2X30 MW - Sistem Monitoring")

# ================== Footer ==================
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
