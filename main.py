import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ========== Konfigurasi Streamlit ==========
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# CSS untuk tampilan Streamlit
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

# Tampilan logo di halaman Streamlit
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

# ========== Fungsi Load & Simpan Data ==========
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

# ========== Fungsi Export PDF (menggunakan ReportLab) ==========
def export_pdf(data):
    pdf_filename = "monitoring_report.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=30, bottomMargin=18)
    styles = getSampleStyleSheet()
    story = []
    
    # Header laporan: Logo di kiri, judul di bawahnya
    if os.path.exists("logo.png"):
        logo_img = RLImage("logo.png", width=1.5*inch, height=0.5*inch)
        story.append(logo_img)
    story.append(Spacer(1, 6))
    title = Paragraph("<b>Laporan Monitoring FLM & Corrective Maintenance</b>", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Proses setiap record
    for idx, row in data.iterrows():
        # Tabel data utama: dua kolom
        # Kolom kiri: ID, Tanggal, Jenis, Area
        left_data = [
            ["ID", f": {row['ID']}"],
            ["Tanggal", f": {pd.to_datetime(row['Tanggal']).strftime('%Y-%m-%d')}"],
            ["Jenis", f": {row['Jenis']}"],
            ["Area", f": {row['Area']}"]
        ]
        # Kolom kanan: Nomor SR, Nama Pelaksana, Keterangan, Status
        right_data = [
            ["Nomor SR", f": {row['Nomor SR']}"],
            ["Nama Pelaksana", f": {row['Nama Pelaksana']}"],
            ["Keterangan", f": {row['Keterangan']}"],
            ["Status", f": {row['Status']}"]
        ]
        
        left_table = Table(left_data, colWidths=[80, 150])
        left_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        right_table = Table(right_data, colWidths=[80, 150])
        right_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        combined_table = Table([[left_table, right_table]], colWidths=[doc.width/2.0, doc.width/2.0])
        combined_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black)
        ]))
        story.append(combined_table)
        story.append(Spacer(1, 12))
        
        # Evidence
        if row["Jenis"] == "FLM":
            # Untuk FLM, hanya satu evidence (finish)
            if row["Evidance"] and os.path.exists(row["Evidance"]):
                evidence = RLImage(row["Evidance"], width=2.5*inch, height=2*inch)
            else:
                evidence = Paragraph("Evidence tidak ditemukan", styles["Normal"])
            evidence_table = Table([[Paragraph("<b>Evidence</b>", styles["Normal"])],
                                    [evidence]], colWidths=[doc.width])
            evidence_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black)
            ]))
            story.append(evidence_table)
        else:
            # Untuk Corrective Maintenance, tampilkan Evidence Before dan After
            evidence_data = []
            if row["Evidance"] and os.path.exists(row["Evidance"]):
                evidence_before = RLImage(row["Evidance"], width=2.5*inch, height=2*inch)
            else:
                evidence_before = Paragraph("Evidence Before tidak ditemukan", styles["Normal"])
            if row.get("Evidance After") and pd.notna(row["Evidance After"]) and row["Evidance After"] != "" and os.path.exists(row["Evidance After"]):
                evidence_after = RLImage(row["Evidance After"], width=2.5*inch, height=2*inch)
            else:
                evidence_after = Paragraph("Tidak ada Evidence After", styles["Normal"])
            evidence_data.append([Paragraph("<b>Evidence Before</b>", styles["Normal"]),
                                  Paragraph("<b>Evidence After</b>", styles["Normal"])])
            evidence_data.append([evidence_before, evidence_after])
            evidence_table = Table(evidence_data, colWidths=[doc.width/2.0, doc.width/2.0])
            evidence_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                ('BOX', (0, 0), (-1, -1), 0.25, colors.black)
            ]))
            story.append(evidence_table)
        story.append(Spacer(1, 20))
        story.append(Spacer(1, 12))
        story.append(Paragraph("<hr/>", styles["Normal"]))
        story.append(Spacer(1, 12))
    
    doc.build(story)
    return pdf_filename

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

st.info("PLTU Bangka 2X30 MW - Sistem Monitoring")

# ========== Footer ==========
st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
