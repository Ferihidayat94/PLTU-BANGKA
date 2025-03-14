import streamlit as st
import pandas as pd
from datetime import datetime

# Title
st.markdown(
    """
    <h1 style='text-align: center; font-family: Arial, sans-serif; color: #4CAF50;'>
    MONITORING FLM Produksi A
    </h1>
    """,
    unsafe_allow_html=True
)

# Input Form
with st.form("monitoring_form"):
    tanggal = st.date_input("TANGGAL", datetime.today())
    area = st.selectbox("AREA", ["Boiler", "Turbine", "CHCB", "WTP"])
    keterangan = st.text_area("KETERANGAN")
    nomor_sr = st.text_input("NOMOR SR")
    evidance = st.file_uploader("UPLOAD EVIDANCE")
    nama_pelaksana = st.selectbox("NAMA PELAKSANA", [
        "Winner PT Daspin Sitanggang", "Devri Candra Kardios", "Rendy Eka Priansyah", "Selamat", 
        "M Yanuardi", "Hendra", "Gilang", "Kamil", "M Soleh Alqodri", "M Soleh", "Debby", 
        "Dandi", "Aminudin", "Hasan", "Budi", "Sarmidun", "Reno", "Rafi", "Akbar", 
        "Sunir", "Eka", "Hanafi", "Diki"
    ])
    
    submit_button = st.form_submit_button("SUBMIT")

# Data Storage
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Tanggal", "Area", "Keterangan", "Nomor SR", "Evidance", "Nama Pelaksana"])

# Add new data
if submit_button:
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
st.dataframe(st.session_state.data)

# Export to CSV
csv = st.session_state.data.to_csv(index=False)
st.download_button("Download Data CSV", data=csv, file_name="monitoring_kinerja.csv", mime="text/csv")

st.info("PRODUKSI A PLTU BANGKA.")
