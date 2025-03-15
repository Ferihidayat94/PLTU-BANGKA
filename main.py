import streamlit as st
import pandas as pd
from datetime import datetime
from pdf import PDF

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
        border: 1px solid #ccc;
    }
    th, td {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: left;
        color: white;
    }
    th {
        background-color: #444;
    }
    .delete-button {
        visibility: hidden;
        cursor: pointer;
    }
    tr:hover .delete-button {
        visibility: visible;
    }
    .logout-button {
        position: absolute;
        top: 10px;
        right: 10px;
        background-color: red;
        color: white;
        padding: 8px 16px;
        border-radius: 5px;
        border: none;
        cursor: pointer;
    }
    .green-button {
        background-color: #4CAF50 !important;
        color: white !important;
        padding: 5px 10px !important;
        font-size: 14px !important;
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
    login_button = st.button("Login", key="login_button", help="Klik untuk masuk", use_container_width=False)

    ADMIN_CREDENTIALS = {"admin": "admin123"}
    
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
    submit_button = st.form_submit_button("Submit", help="Klik untuk menyimpan data", use_container_width=False, args=("green-button",))

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

def export_pdf():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Data Monitoring", ln=True, align='C')
    pdf.ln(10)
    for i, row in st.session_state.data.iterrows():
        pdf.cell(200, 10, f"{row['Tanggal']} - {row['Area']} - {row['Keterangan']} - {row['Nomor SR']} - {row['Nama Pelaksana']}", ln=True)
    return pdf.output(dest="S").encode("latin1")

if not st.session_state.data.empty:
    st.markdown("### Data Monitoring")
    csv = st.session_state.data.to_csv(index=False)
    pdf = export_pdf()
    st.download_button("Download Data CSV", data=csv, file_name="monitoring_kinerja.csv", mime="text/csv")
    st.download_button("Download Data PDF", data=pdf, file_name="monitoring_kinerja.pdf", mime="application/pdf")
    
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
