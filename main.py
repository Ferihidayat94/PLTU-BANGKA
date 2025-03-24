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
        .input-container {
            margin-top: 20px;
            margin-bottom: 20px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Tampilan logo halaman
logo = Image.open("logo.png")
st.image(logo, width=150)

# Folder penyimpanan file evidence
UPLOAD_FOLDER = "uploads/"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# File database
USER_FILE = "users.csv"
DATA_FILE = "monitoring_data.csv"

# ========== Fungsi Hashing Password ==========
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ========== Load & Simpan Data ==========
def load_users():
    if os.path.exists(USER_FILE):
        return pd.read_csv(USER_FILE)
    return pd.DataFrame(columns=["Username", "Password"])

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if "Evidance After" not in df.columns:
            df["Evidance After"] = ""
        return df
    return pd.DataFrame(columns=["ID", "Tanggal", "Jenis", "Area", "Nomor SR",
                                   "Nama Pelaksana", "Keterangan", "Status", "Evidance", "Evidance After"])

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
    
    records_per_page = 2
    count = 0
    left_x = 10
    right_x = 110
    line_height = 10
    
    for index, row in data.iterrows():
        if count % records_per_page == 0:
            pdf.add_page()
            # Tambahkan logo pada pojok kiri atas dengan ukuran lebih besar (w=50)
            if os.path.exists("logo.png"):
                pdf.image("logo.png", x=10, y=8, w=50)
            # Atur posisi judul (tidak terlalu jauh dari logo)
            pdf.set_xy(0, 20)
            pdf.set_font("Arial", "B", 18)
            pdf.cell(0, 10, "Laporan Monitoring FLM & Corrective Maintenance", ln=True, align="C")
            pdf.ln(5)
        
        # Simpan posisi awal y untuk dua kolom
        y_start = pdf.get_y()
        
        # LEFT COLUMN: ID, Tanggal, Jenis, Area
        pdf.set_xy(left_x, y_start)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "ID", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, line_height, str(row["ID"]), 0, 1, "R")
        y_left = pdf.get_y()
        
        pdf.set_xy(left_x, y_left)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "Tanggal", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        tanggal_str = pd.to_datetime(row["Tanggal"]).strftime("%Y-%m-%d")
        pdf.cell(0, line_height, tanggal_str, 0, 1, "R")
        y_left = pdf.get_y()
        
        pdf.set_xy(left_x, y_left)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "Jenis", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, line_height, str(row["Jenis"]), 0, 1, "R")
        y_left = pdf.get_y()
        
        pdf.set_xy(left_x, y_left)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "Area", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, line_height, str(row["Area"]), 0, 1, "R")
        y_left = pdf.get_y()
        
        # RIGHT COLUMN: Nomor SR, Nama Pelaksana, Keterangan, Status
        pdf.set_xy(right_x, y_start)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "Nomor SR", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, line_height, str(row["Nomor SR"]), 0, 1, "R")
        y_right = pdf.get_y()
        
        pdf.set_xy(right_x, y_right)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "Nama Pelaksana", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, line_height, str(row["Nama Pelaksana"]), align="R")
        y_right = pdf.get_y()
        
        pdf.set_xy(right_x, y_right)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "Keterangan", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, line_height, str(row["Keterangan"]), align="R")
        y_right = pdf.get_y()
        
        pdf.set_xy(right_x, y_right)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, line_height, "Status", 0, 0, "L")
        pdf.cell(5, line_height, ":", 0, 0, "C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, line_height, str(row["Status"]), 0, 1, "R")
        y_right = pdf.get_y()
        
        # Tentukan posisi akhir (y_final) dari kedua kolom
        y_final = max(y_left, y_right)
        pdf.set_y(y_final + 5)
        
        # Evidence: Ditampilkan di bawah kolom (Evidence Before dan After)
        x_evidence_left = 10
        x_evidence_right = 120
        if row["Evidance"] and os.path.exists(row["Evidance"]):
            try:
                pdf.image(row["Evidance"], x=x_evidence_left, y=pdf.get_y(), w=50)
            except Exception as e:
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 10, "Gagal menampilkan evidence Before", 0, 1)
        if "Evidance After" in row and pd.notna(row["Evidance After"]) and row["Evidance After"] != "" and os.path.exists(row["Evidance After"]):
            try:
                pdf.image(row["Evidance After"], x=x_evidence_right, y=pdf.get_y(), w=50)
            except Exception as e:
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 10, "Gagal menampilkan evidence After", 0, 1)
        pdf.ln(55)  # Jarak vertikal setelah evidence
        
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

# Container untuk input data agar tampilan lebih terstruktur
with st.container():
    st.markdown("<div class='input-container'>", unsafe_allow_html=True)
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
    
    evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
    keterangan = st.text_area("Keterangan")
    status = st.radio("Status", ["Finish", "Belum"], key="status")
    st.markdown("</div>", unsafe_allow_html=True)
    
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
        "Evidance": [evidance_path],
        "Evidance After": [""]
    })
    st.session_state.data = pd.concat([st.session_state.data, new_data], ignore_index=True)
    save_data(st.session_state.data)
    st.success("Data berhasil disimpan!")
    st.rerun()

# ========== Edit Status Corrective Maintenance ==========
st.markdown("### Edit Status Corrective Maintenance")
editable_records = st.session_state.data[
    (st.session_state.data["Jenis"] == "Corrective Maintenance") & 
    (st.session_state.data["Status"] == "Belum")
]
if not editable_records.empty:
    edit_id = st.selectbox("Pilih ID untuk Edit Status", editable_records["ID"])
    if edit_id:
        current_record = st.session_state.data[st.session_state.data["ID"] == edit_id]
        st.write("Status saat ini:", current_record["Status"].values[0])
        st.write("Evidence Before:", current_record["Evidance"].values[0])
        new_evidence = st.file_uploader("Upload Evidence Baru (After)", type=["png", "jpg", "jpeg"], key="edit_evidence")
        if st.button("Update Status ke Finish"):
            updated_evidence_after = current_record["Evidance After"].values[0]
            if new_evidence is not None:
                new_evid_path = os.path.join(UPLOAD_FOLDER, new_evidence.name)
                with open(new_evid_path, "wb") as f:
                    f.write(new_evidence.getbuffer())
                updated_evidence_after = new_evid_path
            st.session_state.data.loc[st.session_state.data["ID"] == edit_id, "Status"] = "Finish"
            st.session_state.data.loc[st.session_state.data["ID"] == edit_id, "Evidance After"] = updated_evidence_after
            save_data(st.session_state.data)
            st.success("Status berhasil diupdate menjadi Finish!")
            st.rerun()
else:
    st.info("Tidak ada record Corrective Maintenance dengan status 'Belum' untuk diupdate.")

# ========== Tampilan Data ==========
if not st.session_state.data.empty:
    st.markdown("### Data Monitoring")
    st.dataframe(st.session_state.data)

# ========== Opsi Export PDF ==========
st.markdown("### Export PDF Options")
export_start_date = st.date_input("Export Start Date", datetime.today(), key="export_start_date")
export_end_date = st.date_input("Export End Date", datetime.today(), key="export_end_date")
export_type = st.selectbox("Pilih Tipe Export", ["Semua", "FLM", "CM"], key="export_type")

if st.button("Export ke PDF"):
    filtered_data = st.session_state.data.copy()
    if not filtered_data.empty:
        filtered_data["Tanggal"] = pd.to_datetime(filtered_data["Tanggal"])
        start_date = pd.to_datetime(export_start_date)
        end_date = pd.to_datetime(export_end_date)
        filtered_data = filtered_data[(filtered_data["Tanggal"] >= start_date) & (filtered_data["Tanggal"] <= end_date)]
    
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
        evidence_after = selected_row["Evidance After"].values[0]
        if evidence_path and os.path.exists(evidence_path):
            with st.expander(f"Evidence Before untuk {id_pilih}", expanded=False):
                st.image(evidence_path, caption=f"Evidence Before untuk {id_pilih}", use_column_width=True)
        else:
            st.warning("Evidence Before tidak ditemukan atau belum diupload.")
        if evidence_after and os.path.exists(evidence_after):
            with st.expander(f"Evidence After untuk {id_pilih}", expanded=False):
                st.image(evidence_after, caption=f"Evidence After untuk {id_pilih}", use_column_width=True)
        else:
            st.info("Tidak ada Evidence After untuk record ini.")
    else:
        st.warning("Pilih ID yang memiliki evidence.")
    
    id_hapus = st.selectbox("Pilih ID untuk hapus", st.session_state.data["ID"])
    if st.button("Hapus Data"):
        st.session_state.data = st.session_state.data[st.session_state.data["ID"] != id_hapus]
        save_data(st.session_state.data)
        st.success("Data berhasil dihapus!")
        st.rerun()
    
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
