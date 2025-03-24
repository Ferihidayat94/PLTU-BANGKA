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

# Tambahkan Logo untuk tampilan halaman
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
    # Pastikan kolom Status juga ada
    return pd.DataFrame(columns=["ID", "Tanggal", "Jenis", "Area", "Nomor SR", "Nama Pelaksana", "Keterangan", "Status", "Evidance"])

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
    
    # Setiap halaman memuat 2 record
    records_per_page = 2
    count = 0
    
    for index, row in data.iterrows():
        if count % records_per_page == 0:
            pdf.add_page()
            # Tambahkan logo pada header
            if os.path.exists("logo.png"):
                pdf.image("logo.png", x=10, y=8, w=30)
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Monitoring FLM & Corrective Maintenance", ln=True, align="C")
            pdf.ln(10)
        
        label_width = 40  # Lebar label untuk format "Label : Value"
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "ID", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, str(row["ID"]), 0, 1)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "Tanggal", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, str(row["Tanggal"]), 0, 1)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "Jenis", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, str(row["Jenis"]), 0, 1)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "Area", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, str(row["Area"]), 0, 1)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "Nomor SR", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, str(row["Nomor SR"]), 0, 1)
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "Nama Pelaksana", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, str(row["Nama Pelaksana"]))
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "Keterangan", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, str(row["Keterangan"]))
        
        pdf.set_font("Arial", "B", 12)
        pdf.cell(label_width, 10, "Status", 0, 0)
        pdf.cell(5, 10, ":", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, str(row["Status"]), 0, 1)
        
        # Tampilkan evidence image jika ada
        if row["Evidance"] and os.path.exists(row["Evidance"]):
            pdf.set_font("Arial", "B", 12)
            pdf.cell(label_width, 10, "Evidence", 0, 0)
            pdf.cell(5, 10, ":", 0, 0)
            try:
                pdf.image(row["Evidance"], w=50)
            except Exception as e:
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 10, "Gagal menampilkan evidence", 0, 1)
            pdf.ln(10)
        else:
            pdf.ln(5)
        
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(10)
        
        count += 1
    
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
st.title("MONITORING FLM & Corrective Maintenance")
st.write("Produksi A PLTU Bangka")

col1, col2 = st.columns([9, 1])
with col1:
    st.markdown("### INPUT DATA")
with col2:
    if st.button("Logout"):
        logout()

# Gunakan container agar input terupdate secara dinamis
with st.container():
    tanggal = st.date_input("Tanggal", datetime.today())
    jenis = st.selectbox("Jenis", ["FLM", "Corrective Maintenance"], key="jenis")
    area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
    nomor_flm = st.text_input("Nomor SR")
    
    if jenis == "FLM":
        nama_pelaksana = st.multiselect("Nama Pelaksana", 
                                        ["Winner", "Devri", "Rendy", "Selamat", "M. Yanuardi", "Hendra", "Kamil", 
                                         "Gilang", "M. Soleh Alqodri", "Soleh", "Dandi", "Debby", "Budy", 
                                         "Sarmidun", "Reno", "Raffi", "Akbar", "Sunir", "Aminudin", "Hasan", "Feri"],
                                        key="nama_pelaksana")
    else:
        nama_pelaksana = st.multiselect("Nama Pelaksana", ["Mekanik", "Konin", "Elektrik"], key="nama_pelaksana")
    
    evidance_file = st.file_uploader("Upload Evidence", type=["png", "jpg", "jpeg"])
    keterangan = st.text_area("Keterangan")
    status = st.radio("Status", ["Finish", "Belum"], key="status")
    
    submit_button = st.button("Submit")

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
        "Status": [status],
        "Evidance": [evidance_path]
    })
    st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
    save_data(st.session_state.data)
    st.success("Data berhasil disimpan!")
    st.rerun()

# ========== Tampilan Data ==========
if not st.session_state.data.empty:
    st.markdown("### Data Monitoring")
    st.dataframe(st.session_state.data)

# ========== Opsi Export PDF ==========
st.markdown("### Export PDF Options")
export_start_date = st.date_input("Export Start Date", datetime.today(), key="export_start_date")
export_end_date = st.date_input("Export End Date", datetime.today(), key="export_end_date")
export_type = st.selectbox("Pilih Tipe Export", ["Semua", "FLM", "CM"], key="export_type")

# Tombol untuk Export PDF dengan filtering
if st.button("Export ke PDF"):
    # Filter data berdasarkan tanggal
    filtered_data = st.session_state.data.copy()
    if not filtered_data.empty:
        filtered_data["Tanggal"] = pd.to_datetime(filtered_data["Tanggal"])
        start_date = pd.to_datetime(export_start_date)
        end_date = pd.to_datetime(export_end_date)
        filtered_data = filtered_data[(filtered_data["Tanggal"] >= start_date) & (filtered_data["Tanggal"] <= end_date)]
    
    # Filter berdasarkan tipe jika tidak memilih "Semua"
    if export_type != "Semua":
        if export_type == "FLM":
            filtered_data = filtered_data[filtered_data["Jenis"] == "FLM"]
        elif export_type == "CM":
            filtered_data = filtered_data[filtered_data["Jenis"] == "Corrective Maintenance"]
    
    if filtered_data.empty:
        st.warning("Data tidak ditemukan untuk kriteria export tersebut.")
    else:
        pdf_file = export_pdf(filtered_data)
        with open(pdf_file, "rb") as f:
            st.download_button("Unduh PDF", f, file_name=pdf_file)

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

st.info("PLTU BANGKA 2X30 MW - Sistem Monitoring")

# ========== Footer ==========
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
