import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta, date
import uuid
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer, PageBreak, Frame, PageTemplate
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

hide_streamlit_style = """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

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

try:
    logo = Image.open("logo.png")
    st.image(logo, width=150)
except:
    st.error("Logo tidak ditemukan.")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DATA_FILE = "monitoring_data.csv"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

ADMIN_CREDENTIALS = {
    "admin": hash_password(st.secrets.get("ADMIN_PASSWORD", "pltubangka")),
    "operator": hash_password(st.secrets.get("OPERATOR_PASSWORD", "op123")),
}

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, parse_dates=["Tanggal"])
        if "Evidance After" not in df.columns:
            df["Evidance After"] = ""
        return df
    return pd.DataFrame(columns=["ID", "Tanggal", "Jenis", "Area", "Nomor SR",
                                 "Nama Pelaksana", "Keterangan", "Status", "Evidance", "Evidance After"])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def logout():
    st.session_state.clear()
    st.experimental_rerun()

if "last_activity" in st.session_state:
    if datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
        logout()
st.session_state.last_activity = datetime.now()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "data" not in st.session_state:
    st.session_state.data = load_data()

if not st.session_state.logged_in:
    st.sidebar.title("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[username] == hash_password(password):
            st.session_state.logged_in = True
            st.session_state.user = username
            st.sidebar.success("Login berhasil!")
        else:
            st.sidebar.error("Username atau password salah")
    st.stop()
else:
    with st.sidebar:
        st.title("Menu Navigasi")
        menu = st.radio("Pilih Menu", ["Input Data", "Lihat Data", "Export PDF"])
        if st.button("Logout"):
            logout()

st.title("MONITORING FLM & Corrective Maintenance")
st.write("Produksi A PLTU Bangka")

if menu == "Input Data":
    st.subheader("Input Data")
    with st.form("input_form"):
        tanggal = st.date_input("Tanggal", date.today())
        jenis = st.selectbox("Jenis", ["FLM", "Corrective Maintenance"])
        area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP"])
        nomor_sr = st.text_input("Nomor SR")
        nama_pelaksana = st.text_input("Nama Pelaksana")
        keterangan = st.text_area("Keterangan")
        status = st.selectbox("Status", ["Finish", "Belum"])
        evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
        evidance_after_file = None
        if jenis != "FLM":
            evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
        submit_button = st.form_submit_button("Submit")

        if submit_button:
            if not nomor_sr.strip() or not nama_pelaksana.strip() or not keterangan.strip():
                st.error("Nomor SR, Nama Pelaksana, dan Keterangan tidak boleh kosong!")
            else:
                evidance_path = ""
                if evidance_file:
                    ext = evidance_file.name.split('.')[-1]
                    evidance_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.{ext}")
                    with open(evidance_path, "wb") as f:
                        f.write(evidance_file.getbuffer())
                evidance_after_path = ""
                if jenis != "FLM" and evidance_after_file:
                    ext = evidance_after_file.name.split('.')[-1]
                    evidance_after_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}.{ext}")
                    with open(evidance_after_path, "wb") as f:
                        f.write(evidance_after_file.getbuffer())
                new_id = f"{'FLM' if jenis == 'FLM' else 'CM'}-{len(st.session_state.data) + 1:03d}"
                new_row = pd.DataFrame([[new_id, tanggal, jenis, area, nomor_sr, nama_pelaksana, keterangan, status, evidance_path, evidance_after_path]],
                                        columns=st.session_state.data.columns)
                st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
                save_data(st.session_state.data)
                st.success("Data berhasil disimpan!")
                st.experimental_rerun()

elif menu == "Lihat Data":
    st.subheader("Data Monitoring")
    st.dataframe(st.session_state.data)

elif menu == "Export PDF":
    st.subheader("Export Laporan PDF")
    export_start_date = st.date_input("Export Start Date", date.today())
    export_end_date = st.date_input("Export End Date", date.today())
    export_type = st.selectbox("Pilih Tipe Export", ["Semua", "FLM", "Corrective Maintenance"])
    if st.button("Export ke PDF"):
        filtered_data = st.session_state.data.copy()
        filtered_data["Tanggal"] = pd.to_datetime(filtered_data["Tanggal"])
        filtered_data = filtered_data[
            (filtered_data["Tanggal"] >= pd.to_datetime(export_start_date)) & 
            (filtered_data["Tanggal"] <= pd.to_datetime(export_end_date))
        ]
        if export_type != "Semua":
            filtered_data = filtered_data[filtered_data["Jenis"] == export_type]
        if filtered_data.empty:
            st.warning("Data tidak ditemukan.")
        else:
            file_path = "laporan_monitoring.pdf"

            def header_footer(canvas, doc):
                canvas.saveState()
                canvas.setStrokeColor(colors.black)
                canvas.setLineWidth(1)
                canvas.rect(doc.leftMargin - 10, doc.bottomMargin - 10, doc.width + 20, doc.height + 20)
                canvas.restoreState()

            frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
            doc = SimpleDocTemplate(file_path, pagesize=A4)
            doc.addPageTemplates([PageTemplate(id='Bordered', frames=[frame], onPage=header_footer)])

            elements = []
            styles = getSampleStyleSheet()
            try:
                elements.append(RLImage("logo.png", width=1.5*inch, height=1*inch))
                elements.append(Spacer(1, 12))
            except:
                pass

            for _, row in filtered_data.iterrows():
                elements.append(Paragraph(f"<b>ID:</b> {row['ID']} | <b>Tanggal:</b> {row['Tanggal'].strftime('%Y-%m-%d')}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Jenis:</b> {row['Jenis']} | <b>Area:</b> {row['Area']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Nomor SR:</b> {row['Nomor SR']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Pelaksana:</b> {row['Nama Pelaksana']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Status:</b> {row['Status']}", styles["Normal"]))
                elements.append(Paragraph(f"<b>Keterangan:</b><br/>{row['Keterangan']}", styles["Normal"]))
                elements.append(Spacer(1, 6))

                if row["Evidance"] and os.path.exists(row["Evidance"]):
                    elements.append(Paragraph("Evidence Before:", styles["Italic"]))
                    elements.append(RLImage(row["Evidance"], width=4*inch, height=3*inch))
                if row["Evidance After"] and os.path.exists(row["Evidance After"]):
                    elements.append(Paragraph("Evidence After:", styles["Italic"]))
                    elements.append(RLImage(row["Evidance After"], width=4*inch, height=3*inch))

                elements.append(PageBreak())

            doc.build(elements)
            with open(file_path, "rb") as f:
                st.download_button("Unduh PDF", f, file_name=file_path)

st.markdown("### Preview Evidence")
if not st.session_state.data.empty:
    id_pilih = st.selectbox("Pilih ID untuk melihat evidence", st.session_state.data["ID"])
    selected_row = st.session_state.data[st.session_state.data["ID"] == id_pilih]
    if not selected_row.empty:
        ev_before = selected_row["Evidance"].values[0]
        ev_after = selected_row["Evidance After"].values[0]
        if ev_before and os.path.exists(ev_before):
            with st.expander(f"Evidence Before untuk {id_pilih}"):
                st.image(ev_before, caption=f"Before - {id_pilih}", use_column_width=True)
        if ev_after and os.path.exists(ev_after):
            with st.expander(f"Evidence After untuk {id_pilih}"):
                st.image(ev_after, caption=f"After - {id_pilih}", use_column_width=True)
    if st.button("Hapus Data"):
        st.session_state.data = st.session_state.data[st.session_state.data["ID"] != id_pilih]
        save_data(st.session_state.data)
        st.success("Data berhasil dihapus!")
        st.experimental_rerun()

csv_data = st.session_state.data.to_csv(index=False)
st.download_button("Download Data CSV", data=csv_data, file_name="monitoring_data.csv", mime="text/csv")

st.markdown(
    """
    <hr>
    <p style='text-align: center;'>Dibuat oleh Tim Operasi - PLTU Bangka 🛠️</p>
    """,
    unsafe_allow_html=True
)
