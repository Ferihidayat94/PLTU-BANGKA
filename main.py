import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
from fpdf import FPDF
from PIL import Image

# ========== Konfigurasi Streamlit ==========
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# Tambahkan CSS untuk background dan font
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

# Tambahkan Logo
logo = Image.open("logo.png")
st.image(logo, width=150)

# Folder penyimpanan file evidence
UPLOAD_FOLDER = "uploads/"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# File database user
USER_FILE = "users.csv"
DATA_FILE = "monitoring_data.csv"

# ========== Fungsi Hashing Password ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ========== Load Data ==========
def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE)
    return pd.DataFrame(columns=["Username", "Password"])

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["ID", "Tanggal", "Jenis", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance"])

# ========== Simpan Data ==========
def save_users(df):
    df.to_csv(USER_FILE, index=False)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ========== Fungsi Logout ==========
def logout():
    st.session_state.logged_in = False
    st.session_state.page = "login"
    st.rerun()

# ========== Fungsi Export PDF ==========
def export_pdf(data):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "Monitoring FLM & Corrective Maintenance", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    columns = ["ID", "Tanggal", "Jenis", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan"]
    col_widths = [30, 30, 40, 30, 30, 60, 60]
    
    # Header tabel
    for col, width in zip(columns, col_widths):
        pdf.cell(width, 10, col, 1)
    pdf.ln()
    
    pdf.set_font("Arial", "", 10)
    for _, row in data.iterrows():
        for col, width in zip(columns, col_widths):
            pdf.cell(width, 10, str(row[col]), 1)
        pdf.ln()
    
    pdf_file = "monitoring_data.pdf"
    pdf.output(pdf_file)
    return pdf_file

# ========== Sistem Login ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "page" not in st.session_state:
    st.session_state.page = "login"

if "data" not in st.session_state:
    st.session_state.data = load_data()

ADMIN_CREDENTIALS = {
    "admin": "pltubangka",
    "operator": "op123",
}

if not st.session_state.logged_in and st.session_state.page == "login":
    st.markdown("## Login")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")
    
    if login_button:
        if username in ADMIN_CREDENTIALS and password == ADMIN_CREDENTIALS[username]:
            st.session_state.logged_in = True
            st.session_state.page = "dashboard"
            st.experimental_set_query_params(user=username)
            st.rerun()
        else:
            st.error("Username atau password salah.")
    st.stop()

# ========== Tampilan Dashboard ==========
st.title("MONITORING FLM & CORRECTive MAINTENANCE")
st.write("Produksi A PLTU Bangka")

col1, col2 = st.columns([9, 1])
with col1:
    st.markdown("### INPUT DATA")
with col2:
    if st.button("Logout"):
        logout()

with st.form("monitoring_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        tanggal = st.date_input("Tanggal", datetime.today())
        jenis = st.selectbox("Jenis", ["FLM", "Corrective Maintenance"], key="jenis")
        area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
    with col2:
        nomor_flm = st.text_input("Nomor SR")
        if jenis == "FLM":
            nama_pelaksana = st.multiselect("Nama Pelaksana", 
                                             ["Winner", "Devri", "Rendy", "Selamat", "M. Yanuardi", "Hendra", "Kamil", 
                                              "Gilang", "M. Soleh Alqodri", "Soleh", "Dandi", "Debby", "Budy", 
                                              "Sarmidun", "Reno", "Raffi", "Akbar", "Sunir", "Aminudin", "Hasan", "Feri"],
                                             key="nama_pelaksana_flm")
        else:
            nama_pelaksana = st.multiselect("Nama Pelaksana", ["Mekanik", "Konin", "Elektrik"], key="nama_pelaksana_cm")
    with col3:
        evidance_file = st.file_uploader("Upload Evidence", type=["png", "jpg", "jpeg"])
        keterangan = st.text_area("Keterangan")
    
    submit_button = st.form_submit_button("Submit")

if submit_button:
    evidance_path = ""
    if evidance_file:
        evidance_path = os.path.join(UPLOAD_FOLDER, evidance_file.name)
        with open(evidance_path, "wb") as f:
            f.write(evidance_file.getbuffer())
    
    id_prefix = "FLM" if jenis == "FLM" else "CM"
    new_data = pd.DataFrame({
        "ID": [f"{id_prefix}-{len(st.session_state.data) + 1:03d}"],
        "Tanggal": [tanggal],
        "Jenis": [jenis],
        "Area": [area],
        "Nomor SR": [nomor_flm],
        "Nama Pelaksana": [", ".join(nama_pelaksana)],
        "Keterangan": [keterangan],
        "Evidance": [evidance_path]
    })
    st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
    save_data(st.session_state.data)
    st.success("Data berhasil disimpan!")
    st.session_state.page = "dashboard"
    st.rerun()

# ========== Tampilan Data ==========
if not st.session_state.data.empty:
    st.markdown("### Data Monitoring")
    st.dataframe(st.session_state.data)

# ========== Preview Evidence dengan Expander ==========
st.markdown("### Preview Evidence")
if not st.session_state.data.empty:
    id_pilih = st.selectbox("Pilih ID untuk melihat evidence", st.session_state.data["ID"])
    selected_row = st.session_state.data[st.session_state.data["ID"] == id_pilih]
    if not selected_row.empty:
        evidence_path = selected_row["Evidance"].values[0]
        if evidence_path and os.path.exists(evidence_path):
            with st.expander(f"Evidence untuk {id_pilih}", expanded=False):
                st.image(evidence_path, caption=f"Evidence untuk {id_pilih}", use_column_width=True)
        else:
            st.warning("Evidence tidak ditemukan atau belum diupload.")
    else:
        st.warning("Pilih ID yang memiliki evidence.")
    
    # Pilih ID untuk hapus
    id_hapus = st.selectbox("Pilih ID untuk hapus", st.session_state.data["ID"])
    if st.button("Hapus Data"):
        st.session_state.data = st.session_state.data[st.session_state.data["ID"] != id_hapus]
        save_data(st.session_state.data)
        st.success("Data berhasil dihapus!")
        st.rerun()
    
    # Download CSV
    csv = st.session_state.data.to_csv(index=False)
    st.download_button("Download Data CSV", data=csv, file_name="monitoring_data.csv", mime="text/csv")

# Tombol untuk Export PDF
if st.button("Export ke PDF"):
    pdf_file = export_pdf(st.session_state.data)
    with open(pdf_file, "rb") as f:
        st.download_button("Unduh PDF", f, file_name=pdf_file)

st.info("PLTU BANGKA 2X30 MW - Sistem Monitoring")

# ========== Footer ==========
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
