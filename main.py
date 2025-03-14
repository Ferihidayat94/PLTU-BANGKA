import streamlit as st
import pandas as pd
from datetime import datetime

# Page Config
st.set_page_config(page_title="First Line Maintenance Produksi A", layout="wide")

# Responsive Styling
st.markdown(
    """
    <style>
    @media screen and (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
        h1 {
            font-size: 1.5rem;
        }
        .stDataFrame {
            overflow-x: auto;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Login System
st.sidebar.markdown("## Login")
username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")
login_button = st.sidebar.button("Login")

# Hardcoded admin and user credentials
credentials = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"}
}

# Role-based access control
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

if login_button:
    if username in credentials and password == credentials[username]["password"]:
        st.session_state.logged_in = True
        st.session_state.role = credentials[username]["role"]
        st.sidebar.success(f"Selamat datang, {username}!")
    else:
        st.sidebar.error("Username atau password salah.")

if not st.session_state.logged_in:
    st.warning("Silakan login untuk mengakses aplikasi.")
    st.stop()

# Logo and Title
st.image("logo.png", width=150)

st.markdown(
    """
    <h1 style='text-align: center; font-family: "Orbitron", sans-serif; color: #4CAF50;'>
    First Line Maintenance Produksi A
    </h1>
    <hr style='border: 1px solid #4CAF50;'>
    """,
    unsafe_allow_html=True
)

# Input Form
st.markdown("### Input Data Maintenance")

if st.session_state.get("wide_screen", True):
    col1, col2 = st.columns(2)
else:
    col1, col2 = st.columns([1])

if st.session_state.role == "admin":
    with st.form("monitoring_form"):
        with col1:
            tanggal = st.date_input("Tanggal", datetime.today())
            area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
            nomor_sr = st.text_input("Nomor SR")
        
        with col2:
            nama_pelaksana = st.selectbox("Nama Pelaksana", [
                "Winner PT Daspin Sitanggang", "Devri Candra Kardios", "Rendy Eka Priansyah", "Selamat", 
                "M Yanuardi", "Hendra", "Gilang", "Kamil", "M Soleh Alqodri", "M Soleh", "Debby", 
                "Dandi", "Aminudin", "Hasan", "Budi", "Sarmidun", "Reno", "Rafi", "Akbar", 
                "Sunir", "Eka", "Hanafi", "Diki"
            ])
            evidance = st.file_uploader("Upload Evidance")
        
        keterangan = st.text_area("Keterangan")
        submit_button = st.form_submit_button("Submit", help="Klik untuk menyimpan data")

elif st.session_state.role == "user":
    st.info("Anda masuk sebagai pengguna biasa. Data hanya bisa dilihat, tidak bisa diedit.")

# Data Storage
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Tanggal", "Area", "Keterangan", "Nomor SR", "Evidance", "Nama Pelaksana"])

# Add new data
if st.session_state.role == "admin" and submit_button:
    new_data = pd.DataFrame({
        "Tanggal": [tanggal],
        "Area": [area],
        "Keterangan": [keterangan],
        "Nomor SR": [nomor_sr],
        "Evidance": [evidance.name if evidance else ""],
        "Nama Pelaksana": [nama_pelaksana]
    })
    st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
    st.success("Data berhasil disimpan!")

# Show data
st.markdown("### Data Monitoring")
if st.session_state.role == "admin":
    st.dataframe(st.session_state.data, height=400)
else:
    st.dataframe(st.session_state.data.style.set_properties(**{'pointer-events': 'none'}), height=400)

# Export to CSV
st.markdown("### Export Data")
csv = st.session_state.data.to_csv(index=False)
st.download_button("Download Data CSV", data=csv, file_name="monitoring_kinerja.csv", mime="text/csv")

st.info("File CSV ini bisa langsung dihubungkan ke Power BI untuk visualisasi real-time.")

# Footer
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>
    Dibuat oleh Tim Operasi - PLTU Bangka 🛠️
    </p>
    """,
    unsafe_allow_html=True
)
