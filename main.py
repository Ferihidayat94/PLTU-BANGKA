# APLIKASI PRODUKSI LENGKAP - FINAL VERSION 
import streamlit as st
import pandas as pd
import os
import hashlib
from datetime import datetime, timedelta, date
import uuid
from PIL import Image, ExifTags
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image as RLImage, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import requests
from supabase import create_client, Client
import plotly.express as px

# ================== Konfigurasi Halaman Streamlit ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS Kustom (SELURUH BLOK INI DIKOMENTARI SEMENTARA UNTUK DEBUGGING) ==================
# st.markdown(
#     """
#     <style>
#         @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
#         html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
#         .stApp {
#             background-color: #021021;
#             background-image: radial-gradient(ellipse at bottom, rgba(52, 152, 219, 0.25) 0%, rgba(255,255,255,0) 50%),
#                                  linear-gradient(to top, #062b54, #021021);
#             background-attachment: fixed;
#             color: #ECF0F1;
#         }
#         .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 { color: #FFFFFF; }
#         .stApp [data-testid="stHeading"] { color: #FFFFFF !important; }
#         .stApp p { color: #ECF0F1 !important; }
#         h1 { border-bottom: 2px solid #3498DB; padding-bottom: 10px; margin-bottom: 0.8rem; }
#         [data-testid="stSidebar"] {
#             background-color: rgba(2, 16, 33, 0.8);
#             backdrop-filter: blur(5px);
#             border-right: 1px solid rgba(52, 152, 219, 0.3);
#         }
#         .login-container [data-testid="stForm"], [data-testid="stForm"], [data-testid="stExpander"],
#         [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stContainer"] {
#             background-color: rgba(44, 62, 80, 0.6);
#             backdrop-filter: blur(5px);
#             border: 1px solid rgba(52, 152, 219, 0.4);
#             padding: 1.5rem;
#             border-radius: 10px;
#             margin-bottom: 1rem;
#         }
#         .login-title { color: #FFFFFF; text-align: center; border-bottom: none; font-size: 1.9rem; white-space: nowrap; }
#         div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button, div[data-testid="stForm"] button {
#             font-weight: 600; border-radius: 8px; border: 1px solid #3498DB !important;
#             background-color: transparent !important; color: #FFFFFF !important;
#             transition: all 0.3s ease-in-out; padding: 10px 24px; width: 100%;
#         }
#         div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover, div[data-testid="stForm"] button:hover {
#             background-color: #3498DB !important; border-color: #3498DB !important;
#         }
#         .delete-button button { border-color: #E74C3C !important; }
#         .delete-button button:hover { background-color: #C0392B !important; border-color: #C0392B !important; }
#         div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {
#             background-color: rgba(236, 240, 241, 0.1) !important;
#             border-color: rgba(52, 152, 219, 0.4) !important;
#             color: #FFFFFF !important;
#         }
#         label, div[data-testid="stWidgetLabel"] label, .st-emotion-cache-1kyxreq e1i5pmia1 {
#             color: #FFFFFF !important; font-weight: 500;
#         }
#         [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] .stMarkdown strong,
#         [data-testid="stSidebar"] .stRadio > label span, [data-testid="stSidebar"] .stCaption {
#             color: #FFFFFF !important; opacity: 1;
#         }
#         [data-testid="stSidebar"] .st-bo:has(input:checked) + label span { color: #5DADE2 !important; font-weight: 700 !important; }
#         [data-testid="stSidebar"] .stButton > button { color: #EAECEE !important; border-color: #EAECEE !important; }
#         [data-testid="stSidebar"] .stButton > button:hover { color: #FFFFFF !important; border-color: #E74C3C !important; background-color: #E74C3C !important; }
#         [data-testid="stSidebarNavCollapseButton"] svg { fill: #FFFFFF !important; }
#         [data-testid="stMetricLabel"] { color: #A9C5E1 !important; }
#         [data-testid="stMetricValue"] { color: #FFFFFF !important; }
#         [data-testid="stMetricDelta"] { color: #2ECC71 !important; }
#         [data-testid="stMetricDelta"][style*="color: rgb(255, 43, 43)"] { color: #FF4B4B !important; }
#     </style>
#     """,
#     unsafe_allow_html=True
# )

# ================== Koneksi & Konfigurasi Global ==================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
supabase = init_connection()
JOB_TYPES = ["First Line Maintenance ( A )", "First Line Maintenance ( B )", "First Line Maintenance ( C )", "First Line Maintenance ( D )", "Corrective Maintenance", "Preventive Maintenance"]

# ================== Fungsi-Fungsi Helper ==================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_user(username, password):
    try:
        hashed_pass = hash_password(password)
        result = supabase.table("users").select("*").eq("username", username).single().execute()
        if result.data and result.data['hashed_password'] == hashed_pass:
            return result.data
    except Exception as e:
        print(f"Authentication error: {e}")
        return None
    return None

@st.cache_data(ttl=600)
def load_data_from_db():
    try:
        response = supabase.table('jobs').select('*').order('created_at', desc=True).execute()
        df = pd.DataFrame(response.data)
        if 'Tanggal' in df.columns and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data dari database: {e}")
        return pd.DataFrame()

def logout():
    for key in list(st.session_state.keys()):
        if key not in ['logged_in', 'user']:
            del st.session_state[key]
    st.session_state.logged_in = False
    st.rerun()

def generate_next_id(df, jenis):
    prefix_map = {'First Line Maintenance': 'FLM', 'Corrective Maintenance': 'CM', 'Preventive Maintenance': 'PM'}
    prefix = next((p for key, p in prefix_map.items() if jenis.startswith(key)), 'JOB')
    
    if df.empty: return f"{prefix}-001"
    relevant_ids = df[df['ID'].str.startswith(prefix, na=False)]['ID'].str.split('-').str[1].dropna().astype(int)
    if relevant_ids.empty: return f"{prefix}-001"
    
    return f"{prefix}-{relevant_ids.max() + 1:03d}"

def fix_image_orientation(image):
    try:
        exif = image.getexif()
        orientation = next((tag for tag, name in ExifTags.TAGS.items() if name == 'Orientation'), None)
        if orientation and orientation in exif:
            actions = {3: 180, 6: 270, 8: 90}
            if exif[orientation] in actions:
                image = image.rotate(actions[exif[orientation]], expand=True)
    except Exception:
        pass
    return image

def upload_image_to_storage(uploaded_file):
    if uploaded_file is None: return ""
    try:
        image = Image.open(uploaded_file).convert("RGB")
        image = fix_image_orientation(image)
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="JPEG", quality=85, optimize=True)
        file_name = f"{uuid.uuid4()}.jpeg"
        supabase.storage.from_("evidences").upload(file=output_buffer.getvalue(), path=file_name, file_options={"content-type": "image/jpeg"})
        return supabase.storage.from_("evidences").get_public_url(file_name)
    except Exception as e:
        st.error(f"Gagal upload gambar: {e}")
        return ""

# --- FUNGSI UNTUK EXCEL REPORT DENGAN GAMBAR (TIDAK BERUBAH DARI SEBELUMNYA) ---
def create_excel_report_with_images(filtered_data):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        data_to_write = filtered_data.drop(columns=['Hapus'], errors='ignore')
        data_to_write.to_excel(writer, sheet_name='Laporan Pekerjaan', index=False)

        workbook = writer.book
        worksheet = writer.sheets['Laporan Pekerjaan']

        try:
            image_col_before = data_to_write.columns.get_loc("Evidance")
            image_col_after = data_to_write.columns.get_loc("Evidance After")
        except KeyError:
            image_col_before = -1 
            image_col_after = -1

        if image_col_before != -1:
            worksheet.set_column(image_col_before, image_col_before, 18)
        if image_col_after != -1:
            worksheet.set_column(image_col_after, image_col_after, 18)

        for row_num, row_data in filtered_data.iterrows():
            excel_row = row_num + 1
            worksheet.set_row(excel_row, 90)

            img_url_before = row_data.get("Evidance")
            if img_url_before and isinstance(img_url_before, str) and image_col_before != -1:
                try:
                    response = requests.get(img_url_before, stream=True, timeout=10)
                    response.raise_for_status()
                    img_data = io.BytesIO(response.content)

                    img = Image.open(img_data).convert("RGB")
                    img = fix_image_orientation(img)
                    
                    width, height = img.size
                    max_width = 120
                    max_height = 90
                    aspect_ratio = width / height
                    
                    if width > max_width or height > max_height:
                        if width / max_width > height / max_height:
                            new_width = max_width
                            new_height = int(new_width / aspect_ratio)
                        else:
                            new_height = max_height
                            new_width = int(new_height * aspect_ratio)
                    else:
                        new_width, new_height = width, height

                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    resized_img_buffer = io.BytesIO()
                    img_resized.save(resized_img_buffer, format="JPEG", quality=80)
                    resized_img_buffer.seek(0)

                    worksheet.insert_image(excel_row, image_col_before, "image_before.jpg",
                                           {'image_data': resized_img_buffer, 'x_offset': 5, 'y_offset': 5,
                                            'object_position': 3
                                           })
                    worksheet.write(excel_row, image_col_before, "Lihat Gambar")
                except Exception as e:
                    print(f"Gagal memuat atau menyematkan gambar before dari URL {img_url_before}: {e}")
                    worksheet.write(excel_row, image_col_before, img_url_before if pd.notna(img_url_before) else "Tidak Ada Gambar")

            img_url_after = row_data.get("Evidance After")
            if img_url_after and isinstance(img_url_after, str) and image_col_after != -1:
                try:
                    response = requests.get(img_url_after, stream=True, timeout=10)
                    response.raise_for_status()
                    img_data = io.BytesIO(response.content)

                    img = Image.open(img_data).convert("RGB")
                    img = fix_image_orientation(img)
                    
                    width, height = img.size
                    max_width = 120
                    max_height = 90
                    aspect_ratio = width / height
                    
                    if width > max_width or height > max_height:
                        if width / max_width > height / max_height:
                            new_width = max_width
                            new_height = int(new_width / aspect_ratio)
                        else:
                            new_height = max_height
                            new_width = int(new_height * aspect_ratio)
                    else:
                        new_width, new_height = width, height

                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    resized_img_buffer = io.BytesIO()
                    img_resized.save(resized_img_buffer, format="JPEG", quality=80)
                    resized_img_buffer.seek(0)

                    worksheet.insert_image(excel_row, image_col_after, "image_after.jpg",
                                           {'image_data': resized_img_buffer, 'x_offset': 5, 'y_offset': 5,
                                            'object_position': 3
                                           })
                    worksheet.write(excel_row, image_col_after, "Lihat Gambar")
                except Exception as e:
                    print(f"Gagal memuat atau menyematkan gambar after dari URL {img_url_after}: {e}")
                    worksheet.write(excel_row, image_col_after, img_url_after if pd.notna(img_url_after) else "Tidak Ada Gambar")

    output.seek(0)
    return output.getvalue()


def create_pdf_report(filtered_data, report_type):
    # (Fungsi ini tidak diubah)
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, spaceBefore=10, textColor=colors.HexColor('#2C3E50')))
    styles.add(ParagraphStyle(name='Header', alignment=TA_LEFT, textColor=colors.HexColor('#2C3E50')))
    elements = []
    
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            header_text = "<b>PT PLN NUSANTARA POWER SERVICES</b><br/>Unit PLTU Bangka"
            logo_img = RLImage(logo_path, width=0.9*inch, height=0.4*inch, hAlign='LEFT')
            header_table = Table([[logo_img, Paragraph(header_text, styles['Header'])]], colWidths=[1*inch, 6*inch], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (1,0), (1,0), 0)])
            elements.append(header_table)
            elements.append(Spacer(1, 20))
    except Exception: pass

    title_text = f"<b>LAPORAN MONITORING {'SEMUA PEKERJAAN' if report_type == 'Semua' else report_type.upper()}</b>"
    elements.append(Paragraph(title_text, styles["TitleCenter"]))
    elements.append(Spacer(1, 12))

    for _, row in filtered_data.iterrows():
        data = [
            ["ID", str(row.get('ID', ''))],
            ["Tanggal", pd.to_datetime(row.get('Tanggal')).strftime('%d-%m-%Y')],
            ["Jenis", str(row.get('Jenis', ''))],
            ["Area", str(row.get('Area', ''))],
            ["Nomor SR", str(row.get('Nomor SR', ''))],
            ["Nama Pelaksana", str(row.get('Nama Pelaksana', ''))],
            ["Status", str(row.get('Status', ''))],
            ["Keterangan", Paragraph(str(row.get('Keterangan', '')).replace('\n', '<br/>'), styles['Normal'])],
        ]
        table = Table(data, colWidths=[100, 380], style=[
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')), ('TEXTCOLOR', (0,0), (0, -1), colors.HexColor('#2C3E50')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')), ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10),
        ])
        elements.append(table)
        
        img1, img2 = None, None
        for img_url, position in [(row.get("Evidance"), 1), (row.get("Evidance After"), 2)]:
            if img_url and isinstance(img_url, str):
                try:
                    response = requests.get(img_url, stream=True, timeout=10)
                    response.raise_for_status()
                    img_data = io.BytesIO(response.content)
                    image_element = RLImage(img_data, width=3*inch, height=2.25*inch, kind='bound')
                    if position == 1: img1 = image_element
                    else: img2 = image_element
                except Exception as e: print(f"Gagal memuat gambar dari URL {img_url}: {e}")
        
        if img1 or img2:
            elements.append(Spacer(1, 5))
            image_table = Table([[Paragraph("<b>Evidence Before:</b>", styles['Normal']), Paragraph("<b>Evidence After:</b>", styles['Normal'])], [img1, img2]], colWidths=[3.2*inch, 3.2*inch], style=[('VALIGN', (0,0), (-1,-1), 'TOP')])
            elements.append(image_table)
        elements.append(PageBreak())

    if elements and isinstance(elements[-1], PageBreak): elements.pop()
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ================== Logika Utama Aplikasi ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.get("logged_in"):
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">Monitoring Job OpHar</h1>', unsafe_allow_html=True)
        try: st.image("logo.png", width=150)
        except FileNotFoundError: pass
        
        with st.form("login_form"):
            st.markdown('<h3 style="color: #FFFFFF; text-align: center; border-bottom: none;">User Login</h3>', unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="e.g., admin", key="login_username").lower()
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            
            if st.form_submit_button("Login"):
                with st.spinner("Memverifikasi..."):
                    user_data = verify_user(username, password)
                
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user = user_data['role']
                    st.session_state.last_activity = datetime.now()
                    st.rerun()
                else:
                    st.error("Username atau password salah.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

if 'last_activity' not in st.session_state or datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
    logout()
st.session_state.last_activity = datetime.now()

if 'data' not in st.session_state:
    st.session_state.data = load_data_from_db()
df = st.session_state.data.copy()

with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"Selamat datang, **{st.session_state.user}**!")
    try: st.image("logo.png", use_container_width=True) 
    except FileNotFoundError: pass
    menu = st.radio("Pilih Halaman:", ["Input Data", "Report Data", "Analisis FLM", "Dashboard Peringatan"], label_visibility="collapsed")
    st.markdown("<br/><br/>", unsafe_allow_html=True)
    if st.button("Logout"): logout()
    st.markdown("---"); st.caption("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")

if st.session_state.get('user') == 'operator':
    st.markdown("""<style>#MainMenu, header, footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

# ================== Logika Halaman ==================
if menu == "Input Data":
    st.header("Input Data Pekerjaan Baru")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tanggal = st.date_input("Tanggal", date.today())
            jenis = st.selectbox("Jenis Pekerjaan", JOB_TYPES)
            area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP", "Common"])
            nomor_sr = st.text_input("Nomor SR (Service Request)")
        with col2:
            nama_pelaksana = st.text_input("Nama Pelaksana")
            status = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
            keterangan = st.text_area("Keterangan / Uraian Pekerjaan")
        
        st.subheader("Upload Bukti Pekerjaan (Evidence)")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1: evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
        with col_ev2: evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Simpan Data"):
            if not all([nomor_sr, nama_pelaksana, keterangan]):
                st.error("Mohon isi semua field yang wajib.")
            else:
                with st.spinner("Menyimpan data..."):
                    latest_ids_df = pd.DataFrame(supabase.table('jobs').select('ID').execute().data)
                    new_id = generate_next_id(latest_ids_df, jenis)
                    
                    evidance_url = upload_image_to_storage(evidance_file)
                    evidance_after_url = upload_image_to_storage(evidance_after_file)
                    
                    new_job_data = {
                        "ID": new_id, "Tanggal": str(tanggal), "Jenis": jenis, "Area": area, "Nomor SR": nomor_sr, 
                        "Nama Pelaksana": nama_pelaksana, "Keterangan": keterangan, "Status": status, 
                        "Evidance": evidance_url, "Evidance After": evidance_after_url
                    }
                    try:
                        supabase.table("jobs").insert(new_job_data).execute()
                        st.cache_data.clear()
                        st.session_state.data = load_data_from_db()
                        st.success(f"Data '{new_id}' berhasil disimpan!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan data: {e}")

elif menu == "Report Data":
    st.header("Integrated Data & Report")
    with st.container(border=True):
        st.subheader("Filter & Edit Data")
        data_to_display = df.copy()
        
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            all_jenis = ["Semua"] + sorted(list(data_to_display["Jenis"].dropna().unique()))
            filter_jenis = st.selectbox("Saring berdasarkan Jenis:", all_jenis, key="report_filter_jenis")
        with filter_col2:
            all_status = ["Semua"] + sorted(list(data_to_display["Status"].dropna().unique()))
            filter_status = st.selectbox("Saring berdasarkan Status:", all_status, key="report_filter_status")
        
        if filter_jenis != "Semua": data_to_display = data_to_display[data_to_display["Jenis"] == filter_jenis]
        if filter_status != "Semua": data_to_display = data_to_display[data_to_display["Status"] == filter_status]
        
        if not data_to_display.empty:
            if 'Hapus' not in data_to_display.columns:
                data_to_display.insert(0, "Hapus", False)
            
            edited_df = st.data_editor(
                data_to_display, key="data_editor", disabled=["ID", "Evidance", "Evidance After"], use_container_width=True,
                column_config={
                    "Hapus": st.column_config.CheckboxColumn("Hapus?", help="Centang untuk menghapus."), 
                    "Tanggal": st.column_config.DateColumn("Tanggal", format="DD-MM-YYYY"),
                    "Jenis": st.column_config.SelectboxColumn("Jenis", options=JOB_TYPES),
                    "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"]),
                    "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"]),
                    "Keterangan": st.column_config.TextColumn("Keterangan", width="large"),
                    "Evidance": st.column_config.LinkColumn("Evidence Before", display_text="Lihat"), 
                    "Evidance After": st.column_config.LinkColumn("Evidence After", display_text="Lihat"),
                    "ID": st.column_config.TextColumn("ID", disabled=True),
                }, column_order=["Hapus", "ID", "Tanggal", "Jenis", "Area", "Status", "Nomor SR", "Nama Pelaksana", "Keterangan", "Evidance", "Evidance After"]
            )
            
            rows_to_delete = edited_df[edited_df['Hapus'] == True]
            
            if not rows_to_delete.empty and st.session_state.user == 'admin':
                st.markdown('<div class="delete-button">', unsafe_allow_html=True)
                ids_to_delete = rows_to_delete['ID'].tolist()
                if st.button(f"🗑️ Hapus ({len(ids_to_delete)}) Baris Terpilih", use_container_width=True):
                    with st.spinner("Menghapus data..."):
                        supabase.table("jobs").delete().in_("ID", ids_to_delete).execute()
                        st.cache_data.clear()
                        st.session_state.data = load_data_from_db()
                        st.success("Data terpilih berhasil dihapus.")
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            elif not rows_to_delete.empty:
                st.warning("Hanya 'admin' yang dapat menghapus data.")

    st.write("---") 
    
    col_func1, col_func2 = st.columns([2, 1])
    with col_func1:
        with st.expander("✅ **Update Status Pekerjaan**", expanded=True):
            open_jobs = df[df['Status'].isin(['Open', 'On Progress'])]
            if not open_jobs.empty:
                job_options = {f"{row['ID']} - {row['Nama Pelaksana']} - {str(row.get('Keterangan',''))[:40]}...": row['ID'] for _, row in open_jobs.iterrows()}
                selected_job_display = st.selectbox("Pilih Pekerjaan yang akan diselesaikan:", list(job_options.keys()))
                uploaded_evidence_after = st.file_uploader("Upload Bukti Selesai", type=["png", "jpg", "jpeg"], key="quick_upload")
                if st.button("Submit Update", use_container_width=True):
                    if selected_job_display and uploaded_evidence_after:
                        with st.spinner("Menyelesaikan pekerjaan..."):
                            job_id_to_update = job_options[selected_job_display]
                            evidence_url = upload_image_to_storage(uploaded_evidence_after)
                            update_data = {"Status": "Finish", "Evidance After": evidence_url}
                            try:
                                supabase.table("jobs").update(update_data).eq("ID", job_id_to_update).execute()
                                st.cache_data.clear()
                                st.session_state.data = load_data_from_db()
                                st.success(f"Pekerjaan '{job_id_to_update}' telah diselesaikan!")
                                st.rerun()
                            except Exception as e: st.error(f"Gagal update: {e}")
                    else: st.warning("Pilih pekerjaan dan upload bukti selesai.")
            else: st.info("Tidak ada pekerjaan yang berstatus 'Open' atau 'On Progress'.")
    
    with col_func2:
        st.write("") 
        if st.button("🔄 Refresh Data Tabel", use_container_width=True):
            st.cache_data.clear()
            st.session_state.data = load_data_from_db()
            st.toast("Data telah diperbarui!")
    
    # === BAGIAN LAPORAN BARU YANG LEBIH SEDERHANA ===
    with st.container(border=True):
        st.subheader("📄 Unduh Laporan")

        if df.empty:
            st.info("Belum ada data untuk dibuat laporan.")
        else:
            df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
            min_date, max_date = df['Tanggal'].min().date(), df['Tanggal'].max().date()
            
            st.write("**1. Pilih Filter Laporan**")
            report_col1, report_col2, report_col3 = st.columns(3)
            with report_col1:
                start_date = st.date_input("Dari Tanggal", min_date, key="report_start_date")
            with report_col2:
                end_date = st.date_input("Sampai Tanggal", max_date, key="report_end_date")
            with report_col3:
                report_type = st.selectbox("Pilih Jenis (Opsional)", ["Semua"] + JOB_TYPES, key="report_type_select")
            
            mask = (df['Tanggal'].dt.date >= start_date) & (df['Tanggal'].dt.date <= end_date)
            if report_type != "Semua":
                mask &= (df["Jenis"] == report_type)
            filtered_data = df[mask]

            st.write("---")
            st.write(f"**2. Hasil Filter: Ditemukan {len(filtered_data)} baris data**")

            if filtered_data.empty:
                st.warning("Tidak ada data yang cocok dengan filter yang Anda pilih.")
            else:
                dl_col1, dl_col2 = st.columns(2)
                with dl_col1:
                    # UNDUH EXCEL
                    if st.button("📊 Buat & Siapkan Excel", use_container_width=True, key='prepare_excel_button'):
                        with st.spinner("Membuat file Excel..."):
                            excel_bytes = create_excel_report_with_images(filtered_data) 
                            st.session_state.excel_bytes = excel_bytes
                            st.session_state.excel_filename = f"laporan_excel_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
                    
                    if 'excel_bytes' in st.session_state and st.session_state.excel_bytes:
                        st.download_button(
                            label="⬇️ Download Laporan (Excel)",
                            data=st.session_state.excel_bytes,
                            file_name=st.session_state.excel_filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key='download_excel_button'
                        )
                
                with dl_col2:
                    pdf_filename = f"laporan_pdf_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
                    # Generate PDF bytes when the button is clicked
                    if st.button("📄 Buat & Siapkan PDF", use_container_width=True):
                        with st.spinner("Membuat file PDF..."):
                            pdf_bytes = create_pdf_report(filtered_data, report_type)
                            st.session_state.pdf_bytes = pdf_bytes
                            st.session_state.pdf_filename = pdf_filename
                
                # Show download button for PDF only after it has been generated
                if 'pdf_bytes' in st.session_state and st.session_state.pdf_bytes:
                    st.download_button(
                        label="⬇️ Download Laporan (PDF)",
                        data=st.session_state.pdf_bytes,
                        file_name=st.session_state.pdf_filename,
                        mime="application/pdf",
                        use_container_width=True,
                        key='download_pdf_button'
                    )

elif menu == "Analisis FLM":
    st.header("📊 Analisis FLM (Scoreboard)")
    st.markdown("Dashboard ini menganalisis jenis First Line Maintenance (FLM) yang paling sering dilaksanakan.")
    
    st.sidebar.header("Filter Dashboard")
    if not df.empty:
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
        min_date, max_date = df['Tanggal'].min().date(), df['Tanggal'].max().date()
    else: min_date, max_date = date.today(), date.today()

    start_date_flm = st.sidebar.date_input("Tanggal Mulai", min_date, key="flm_start_date")
    end_date_flm = st.sidebar.date_input("Tanggal Akhir", max_date, key="flm_end_date")
    all_status_flm = df['Status'].unique() if not df.empty else []
    selected_status_flm = st.sidebar.multiselect("Filter Status:", options=all_status_flm, default=all_status_flm, key="flm_status_filter")

    mask_flm = (df['Tanggal'].dt.date >= start_date_flm) & (df['Tanggal'].dt.date <= end_date_flm) & \
               (df['Status'].isin(selected_status_flm)) & \
               (df['Jenis'].str.startswith('First Line Maintenance', na=False))
    df_flm = df[mask_flm]

    if df_flm.empty:
        st.warning("Tidak ada data FLM yang cocok dengan filter Anda.")
    else:
        # Analisis Tipe FLM
        flm_counts = df_flm['Jenis'].value_counts().reset_index()
        flm_counts.columns = ['Jenis FLM', 'Jumlah']
        total_pelaksanaan = flm_counts['Jumlah'].sum()
        flm_teratas = flm_counts.iloc[0]

        st.markdown("### Ringkasan Dominasi FLM")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Pelaksanaan FLM", f"{total_pelaksanaan} Kali")
        col2.metric("FLM Paling Dominan", flm_teratas['Jenis FLM'].replace("First Line Maintenance ", ""))
        col3.metric("Jumlahnya", f"{flm_teratas['Jumlah']} Kali", delta="Paling Sering", delta_color="off")
        st.markdown("---")
        
        # Visualisasi Tipe FLM
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("Proporsi Jenis FLM")
            fig_pie = px.pie(flm_counts, names='Jenis FLM', values='Jumlah', hole=0.4, title='Persentase Pelaksanaan FLM', template='plotly_dark')
            st.plotly_chart(fig_pie, use_container_width=True)
        with chart_col2:
            st.subheader("Peringkat Dominasi FLM")
            fig_bar = px.bar(flm_counts.sort_values('Jumlah'), x='Jumlah', y='Jenis FLM', orientation='h', text='Jumlah', color='Jumlah', color_continuous_scale=px.colors.sequential.Blues_r, template='plotly_dark')
            st.plotly_chart(fig_bar, use_container_width=True)
        
        # Analisis Leaderboard Pelaksana
        st.markdown("---") 
        st.header("🏆 Skor Pelaksana FLM (Leaderboard)")
        st.markdown("Menganalisis pelaksana berdasarkan jumlah pekerjaan FLM yang ditangani, **termasuk pekerjaan tim**.")

        if 'Nama Pelaksana' in df_flm and not df_flm['Nama Pelaksana'].dropna().empty:
            pelaksana_counts = df_flm['Nama Pelaksana'].str.split(',').explode().str.strip().value_counts().reset_index()
            pelaksana_counts.columns = ['Nama Pelaksana', 'Jumlah FLM Dikerjakan']

            if not pelaksana_counts.empty:
                top_performer = pelaksana_counts.iloc[0]
                
                st.markdown("#### Performa Terbaik")
                col_kpi1, col_kpi2 = st.columns(2)
                with col_kpi1: st.success(f"**Top Performer:** {top_performer['Nama Pelaksana']}")
                with col_kpi2: st.success(f"**Jumlah Pekerjaan:** {top_performer['Jumlah FLM Dikerjakan']} Kali")
                st.markdown("---")
                
                st.subheader("Peringkat Semua Pelaksana")
                fig_leaderboard = px.bar(pelaksana_counts.sort_values('Jumlah FLM Dikerjakan'), x='Jumlah FLM Dikerjakan', y='Nama Pelaksana', orientation='h', title='Leaderboard Pelaksana FLM', text='Jumlah FLM Dikerjakan', color='Jumlah FLM Dikerjakan', color_continuous_scale=px.colors.sequential.Greens_r, template='plotly_dark')
                fig_leaderboard.update_yaxes(categoryorder="total ascending")
                st.plotly_chart(fig_leaderboard, use_container_width=True)
            else:
                st.info("Tidak ada data pelaksana untuk dianalisis sesuai filter.")
        else:
            st.info("Kolom 'Nama Pelaksana' kosong pada data yang difilter.")

elif menu == "Dashboard Peringatan":
    st.header("⚠️ Peringatan Corrective Maintenance (Warning CM)")
    st.markdown("Dashboard ini menganalisis area dengan frekuensi Corrective Maintenance tertinggi.")

    st.sidebar.header("Filter Dashboard")
    if not df.empty:
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
        min_date_cm, max_date_cm = df['Tanggal'].min().date(), df['Tanggal'].max().date()
    else: min_date_cm, max_date_cm = date.today(), date.today()

    start_date_cm = st.sidebar.date_input("Tanggal Mulai", min_date_cm, key="cm_start_date")
    end_date_cm = st.sidebar.date_input("Tanggal Akhir", max_date_cm, key="cm_end_date")
    all_status_cm = df['Status'].unique() if not df.empty else []
    selected_status_cm = st.sidebar.multiselect("Filter Status:", options=all_status_cm, default=all_status_cm, key="cm_status_filter")

    mask_cm = (df['Tanggal'].dt.date >= start_date_cm) & (df['Tanggal'].dt.date <= end_date_cm) & \
              (df['Status'].isin(selected_status_cm)) & \
              (df['Jenis'] == 'Corrective Maintenance')
    df_cm = df[mask_cm]
    
    if df_cm.empty:
        st.warning("Tidak ada data 'Corrective Maintenance' yang cocok dengan filter Anda.")
    else:
        cm_counts = df_cm['Area'].value_counts().reset_index()
        cm_counts.columns = ['Area', 'Jumlah Kasus']
        total_kasus = cm_counts['Jumlah Kasus'].sum()
        area_teratas = cm_counts.iloc[0]

        st.markdown("### Ringkasan Peringatan")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Kasus Corrective", f"{total_kasus} Kasus")
        col2.metric("Area Paling Bermasalah", area_teratas['Area'])
        col3.metric("Jumlah Kasus di Area Tsb", f"{area_teratas['Jumlah Kasus']} Kasus", delta="Paling Tinggi", delta_color="inverse")
        st.markdown("---")

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("Distribusi Kasus per Area")
            fig_pie = px.pie(cm_counts, names='Area', values='Jumlah Kasus', hole=0.4, template='plotly_dark')
            st.plotly_chart(fig_pie, use_container_width=True)
        with chart_col2:
            st.subheader("Peringkat Area Bermasalah")
            fig_bar = px.bar(cm_counts.sort_values('Jumlah Kasus'), x='Jumlah Kasus', y='Area', orientation='h', text='Jumlah Kasus', color='Jumlah Kasus', color_continuous_scale=px.colors.sequential.Reds, template='plotly_dark')
            st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown("---")

        st.subheader("📈 Tren Kasus Corrective Maintenance")
        df_tren = df_cm.set_index('Tanggal').resample('D').size().reset_index(name='Jumlah Kasus')
        fig_line = px.line(df_tren, x='Tanggal', y='Jumlah Kasus', title='Jumlah Kasus per Hari', markers=True, template='plotly_dark')
        st.plotly_chart(fig_line, use_container_width=True)
