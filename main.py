import streamlit as st
import pandas as pd
from datetime import datetime

# Page Config
st.set_page_config(page_title="First Line Maintenance Produksi A", layout="wide")

# Hapus Fork dan Git dari tampilan Streamlit
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .st-emotion-cache-16txtl3 {display: none;} /* Menghilangkan tombol Fork */
    table {
        border-collapse: collapse;
        width: 100%;
        border: 1px solid black;
    }
    th, td {
        border: 1px solid black;
        padding: 8px;
        text-align: left;
    }
    .delete-button {
        visibility: hidden;
    }
    tr:hover .delete-button {
        visibility: visible;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Login System
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Tanggal", "Area", "Keterangan", "Nomor SR", "Evidance", "Nama Pelaksana"])

def logout():
    st.session_state.logged_in = False
    st.rerun()

if not st.session_state.logged_in:
    st.image("logo.png", width=150)
    st.markdown("## Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login", key="login_button")

    ADMIN_CREDENTIALS = {"admin": "admin123"}
    
    if login_button:
        if username in ADMIN_CREDENTIALS and password == ADMIN_CREDENTIALS[username]:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Username atau password salah.")
    
    st.stop()

# Main Page
st.markdown("### INPUT DATA")
if st.button("Logout", key="logout", help="Klik untuk keluar"):
    logout()

with st.form("monitoring_form"):
    tanggal = st.date_input("Tanggal", datetime.today())
    area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
    nomor_sr = st.text_input("Nomor SR")
    nama_pelaksana = st.multiselect("Nama Pelaksana", [
        "Winner PT Daspin Sitanggang", "Devri Candra Kardios", "Rendy Eka Priansyah", "Selamat", 
        "M Yanuardi", "Hendra", "Gilang", "Kamil", "M Soleh Alqodri", "M Soleh", "Debby", 
        "Dandi", "Aminudin", "Hasan", "Budi", "Sarmidun", "Reno", "Rafi", "Akbar", 
        "Sunir", "Eka", "Hanafi", "Diki"])
    evidance = st.file_uploader("Upload Evidance")
    keterangan = st.text_area("Keterangan")
    submit_button = st.form_submit_button("Submit", help="Klik untuk menyimpan data")

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
    st.success("Data berhasil disimpan!")

if not st.session_state.data.empty:
    st.markdown("### Data Monitoring")
    for i in range(len(st.session_state.data)):
        cols = st.columns(7)
        cols[0].write(st.session_state.data.at[i, "Tanggal"])
        cols[1].write(st.session_state.data.at[i, "Area"])
        cols[2].write(st.session_state.data.at[i, "Keterangan"])
        cols[3].write(st.session_state.data.at[i, "Nomor SR"])
        cols[4].write(st.session_state.data.at[i, "Evidance"])
        cols[5].write(st.session_state.data.at[i, "Nama Pelaksana"])
        if cols[6].button("❌", key=f"delete_{i}", help="Hapus data ini"):
            st.session_state.data.drop(i, inplace=True)
            st.session_state.data.reset_index(drop=True, inplace=True)
            st.rerun()
    
    csv = st.session_state.data.to_csv(index=False)
    st.download_button("Download Data CSV", data=csv, file_name="monitoring_kinerja.csv", mime="text/csv")
    
st.info("PLTU BANGKA 2X30 MW.")
