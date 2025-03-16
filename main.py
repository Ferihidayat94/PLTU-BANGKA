import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Page Config
st.set_page_config(page_title="FLM Produksi A", layout="wide")

# Tambahkan custom CSS ke dalam aplikasi Streamlit
st.markdown(
    """
    <style>
    /* Ubah warna background aplikasi */
    .stApp {
        background: linear-gradient(to right, #141e30, #243b55); /* Gradient Dark Blue */
        color: white;
    }

    /* Ubah box input jadi abu-abu */
    input, textarea {
        background-color: #2c2f33 !important; /* Abu-abu gelap */
        color: white !important;
        border-radius: 10px;
        border: 1px solid #555;
        padding: 10px;
    }

    /* Dropdown (Selectbox) */
    div[data-baseweb="select"] > div {
        background-color: #2c2f33 !important;
        color: white !important;
        border-radius: 10px;
        border: 1px solid #555;
    }

    /* Tombol lebih modern */
    .stButton > button {
        background-color: #007BFF !important;
        color: white !important;
        border-radius: 10px;
        padding: 10px 20px;
        border: none;
        transition: 0.3s;
    }

    .stButton > button:hover {
        background-color: #0056b3 !important;
        transform: scale(1.05);
    }

    /* Box container */
    .stBox {
        background-color: #2c2f33;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #555;
        box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.3);
    }

    /* Perbaikan warna teks di input saat fokus */
    input:focus, textarea:focus {
        border-color: #00bfff !important;
        box-shadow: 0 0 5px rgba(0, 191, 255, 0.5);
    }

    </style>
    """,
    unsafe_allow_html=True
)

st.title("MONITORING FIRST LINE MAINTENANCE")  # Contoh konten
st.write("Produksi A PLTU Bangka")




# Hapus Fork dan Git dari tampilan Streamlit
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .st-emotion-cache-16txtl3 {display: none;} /* Menghilangkan tombol Fork */
    .st-emotion-cache-1r0zrug {display: none;} /* Menghilangkan icon profil Streamlit */
    .viewerBadge_container__1QSob {display: none;} /* Menghilangkan ikon Streamlit di footer */
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Path untuk menyimpan data CSV
DATA_FILE = "monitoring_data.csv"

# Fungsi untuk memuat data dari CSV
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    return pd.DataFrame(columns=["Tanggal", "Area", "Keterangan", "Nomor SR", "Evidance", "Nama Pelaksana"])

# Fungsi untuk menyimpan data ke CSV
def save_data(df):
    df.to_csv(DATA_FILE, index=False)

# Fungsi untuk menghapus data
def delete_data(index):
    st.session_state.data = st.session_state.data.drop(index).reset_index(drop=True)
    save_data(st.session_state.data)
    st.rerun()

# Login System
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = load_data()

def logout():
    st.session_state.logged_in = False
    st.rerun()

if not st.session_state.logged_in:
    st.image("logo.png", width=300)
    st.markdown("## Login ")
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login", key="login_button", help="Klik untuk masuk", use_container_width=False)

    ADMIN_CREDENTIALS = {"admin": "pltubangka"}
    
    if login_button:
        if username in ADMIN_CREDENTIALS and password == ADMIN_CREDENTIALS[username]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Username atau password salah.")
  
    st.stop()

# Main Page
col1, col2 = st.columns([9, 1])
with col1:
    st.markdown("### INPUT DATA")
with col2:
    if st.button("Logout", key="logout", help="Klik untuk keluar", use_container_width=False):
        logout()

with st.form("monitoring_form"):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        tanggal = st.date_input("Tanggal", datetime.today())
    with col2:
        area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
    with col3:
        nomor_sr = st.text_input("Nomor SR")
    with col4:
        nama_pelaksana = st.multiselect("Nama Pelaksana", [
            "Winner PT Daspin Sitanggang", "Devri Candra Kardios", "Rendy Eka Priansyah", "Selamat", 
            "M Yanuardi", "Hendra", "Gilang", "Kamil", "M Soleh Alqodri", "M Soleh", "Debby", 
            "Dandi", "Aminudin", "Hasan", "Budi", "Sarmidun", "Reno", "Rafi", "Akbar", 
            "Sunir", "Eka", "Hanafi", "Diki"])
    evidance = st.file_uploader("Upload Evidance")
    keterangan = st.text_area("Keterangan")
    submit_button = st.form_submit_button("Submit", help="Klik untuk menyimpan data", use_container_width=False)

if submit_button:
    new_data = pd.DataFrame({
        "Tanggal": [tanggal],
        "Area": [area],
        "Keterangan": [keterangan],
        "Nomor SR": [nomor_sr],
        "Evidance": [evidance.name if evidance else ""],
        "Nama Pelaksana": [", ".join(nama_pelaksana)]
    })
    st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
    save_data(st.session_state.data)  # Simpan data ke file CSV
    st.success("Data berhasil disimpan!")
    st.rerun()

if not st.session_state.data.empty:
    st.markdown("### Data Monitoring")
    st.dataframe(st.session_state.data)
    
    nomor_hapus = st.number_input("Masukkan nomor data yang ingin dihapus", min_value=0, max_value=len(st.session_state.data)-1, step=1)
    if st.button("Hapus Data", key="delete_data"):
        delete_data(nomor_hapus)
    
    csv = st.session_state.data.to_csv(index=False)
    st.download_button("Download Data CSV", data=csv, file_name="monitoring_kinerja.csv", mime="text/csv")
    
st.info("PLTU BANGKA 2X30 MW")

# Footer
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>
    Dibuat oleh Tim Operasi - PLTU Bangka 🛠️
    </p>
    """,
    unsafe_allow_html=True)
