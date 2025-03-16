import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime

# ========== Konfigurasi Streamlit ==========
st.set_page_config(page_title="FLM Produksi A", layout="wide")

# Tambahkan CSS untuk background dan font
st.markdown(
    """
    <style>
        body {
            background-color: (to right, #141e30, #243b55); /* Gradient Dark Blue */
            color: white;
            font-family: 'Arial', sans-serif;
        }
        .stApp {
            background-color: #0A192F;
        }
        .stTextInput, .stSelectbox, .stMultiselect, .stFileUploader, .stTextArea {
            color: black;
        }
    </style>
    """,
    unsafe_allow_html=True
)

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
    return pd.DataFrame(columns=["ID", "Tanggal", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance"])

# ========== Simpan Data ==========
def save_users(df):
    df.to_csv(USER_FILE, index=False)

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# ========== Fungsi Logout ==========
def logout():
    st.session_state.logged_in = False
    st.rerun()

# ========== Tampilan Login ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "data" not in st.session_state:
    st.session_state.data = load_data()

users = load_users()

# Tambahkan daftar user dan password
ADMIN_CREDENTIALS = {
    "admin": "pltubangka",
    "operator": "op123",
}

# Cek apakah user sudah login sebelumnya
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

users = load_users()

# Login Form
if not st.session_state.logged_in:
    st.image("logo.png", width=300)
    st.markdown("## Login ")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if username in ADMIN_CREDENTIALS and password == ADMIN_CREDENTIALS[username]:
            st.session_state.logged_in = True
            st.session_state.username = username  # Simpan username agar tidak hilang saat refresh
            st.experimental_set_query_params(user=username)  # Simpan di URL untuk tracking
            st.rerun()
        else:
            st.error("Username atau password salah.")
    st.stop()

# ========== Tampilan Input Data ==========
st.title("MONITORING FIRST LINE MAINTENANCE")
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
        area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
    with col2:
        nomor_flm = st.text_input("Nomor SR")
        nama_pelaksana = st.multiselect("Nama Pelaksana", ["Winner", "Devri", "Rendy", "Selamat", "M. Yanuardi", "Hendra", "Kamil", "Gilang", "M. Soleh Alqodri", "Soleh", "Dandi", "Debby", "Budy", "Sarmidun", "Reno", "Raffi", "Akbar", "Sunir", "Aminudin", "Hasan", "Feri"])
    with col3:
        evidance = st.file_uploader("Upload Evidance")
        keterangan = st.text_area("Keterangan")
    
    submit_button = st.form_submit_button("Submit")

if submit_button:
    if not st.session_state.data.empty:
        last_id_number = (
            st.session_state.data["ID"]
            .str.extract(r"FLM-(\d+)")
            .dropna()
            .astype(int)
            .max()
            .values
        )
        new_id_number = last_id_number[0] + 1 if last_id_number.size > 0 else 1
    else:
        new_id_number = 1
    
    unique_id = f"FLM-{new_id_number:03d}"

    evidence_path = ""
    if evidance is not None:
        evidence_path = os.path.join(UPLOAD_FOLDER, evidance.name)
        with open(evidence_path, "wb") as f:
            f.write(evidance.getbuffer())
    
    new_data = pd.DataFrame({
        "ID": [unique_id],
        "Tanggal": [tanggal],
        "Area": [area],
        "Nomor SR": [nomor_flm],
        "Nama Pelaksana": [", ".join(nama_pelaksana)],
        "Keterangan": [keterangan],
        "Evidance": [evidence_path]
    })
    
    st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
    save_data(st.session_state.data)
    st.success("Data berhasil disimpan!")
    st.rerun()

# ========== Preview Evidence dengan Expander ==========
st.markdown("### Preview Evidence")

if not st.session_state.data.empty:
    id_pilih = st.selectbox("Pilih ID untuk melihat evidence", st.session_state.data["ID"])
    selected_row = st.session_state.data[st.session_state.data["ID"] == id_pilih]
    if not selected_row.empty:
        evidence_path = selected_row["Evidance"].values[0]
        st.write(f"DEBUG: Evidence Path -> {evidence_path}")
        if isinstance(evidence_path, str) and evidence_path.strip() and os.path.exists(evidence_path):
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

st.info("PLTU BANGKA 2X30 MW - Sistem Monitoring")

# ========== Footer ==========
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
