# APLIKASI PRODUKSI LENGKAP - VERSI DENGAN ABSENSI & KELOLA PERSONEL
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

# ================== CSS Kustom ==================
st.markdown(
    """
    <style>
        .stApp {
            background-color: #021021;
            background-image: radial-gradient(ellipse at bottom, rgba(52, 152, 219, 0.25) 0%, rgba(255,255,255,0) 50%),
                              linear-gradient(to top, #062b54, #021021);
            background-attachment: fixed;
            color: #ECF0F1;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 { color: #FFFFFF; }
        .stApp [data-testid="stHeading"] { color: #FFFFFF !important; }
        .stApp p { color: #ECF0F1 !important; }
        h1 { border-bottom: 2px solid #3498DB; padding-bottom: 10px; margin-bottom: 0.8rem; }
        [data-testid="stSidebar"] {
            background-color: rgba(2, 16, 33, 0.8);
            backdrop-filter: blur(5px);
            border-right: 1px solid rgba(52, 152, 219, 0.3);
        }
        .login-container [data-testid="stForm"], [data-testid="stForm"], [data-testid="stExpander"],
        [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stContainer"] {
            background-color: rgba(44, 62, 80, 0.6);
            backdrop-filter: blur(5px);
            border: 1px solid rgba(52, 152, 219, 0.4);
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 1rem;
        }
        .login-title { color: #FFFFFF; text-align: center; border-bottom: none; font-size: 1.9rem; white-space: nowrap; }
        div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button, div[data-testid="stForm"] button {
            font-weight: 600; border-radius: 8px; border: 1px solid #3498DB !important;
            background-color: transparent !important; color: #FFFFFF !important;
            transition: all 0.3s ease-in-out; padding: 10px 24px; width: 100%;
        }
        div[data-testid="stButton"] > button:hover, div[data-testid="stDownloadButton"] > button:hover, div[data-testid="stForm"] button:hover {
            background-color: #3498DB !important; border-color: #3498DB !important;
        }
        .delete-button button { border-color: #E74C3C !important; }
        .delete-button button:hover { background-color: #C0392B !important; border-color: #C0392B !important; }
        
        /* Gaya input/select/textarea */
        div[data-baseweb="input"] > div, 
        div[data-baseweb="textarea"] > div, 
        div[data-baseweb="select"] > div {
            background-color: rgba(236, 240, 241, 0.4) !important;
            border-color: rgba(52, 152, 219, 0.4) !important;
            color: #FFFFFF !important;
            transition: all 0.2s ease-in-out;
        }

        /* Efek HOVER */
        div[data-baseweb="input"] > div:hover,
        div[data-baseweb="textarea"] > div:hover,
        div[data-baseweb="select"] > div:hover {
            background-color: rgba(236, 240, 241, 0.55) !important;
            border-color: rgba(52, 152, 219, 0.7) !important;
        }

        /* Efek FOCUS (saat diklik/aktif) */
        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="textarea"] > div:focus-within,
        div[data-baseweb="select"] > div:focus-within {
            background-color: rgba(236, 240, 241, 0.7) !important;
            border-color: #3498DB !important;
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.3) !important;
        }

        label, div[data-testid="stWidgetLabel"] label, .st-emotion-cache-1kyxreq e1i5pmia1 {
            color: #FFFFFF !important; font-weight: 500;
        }
        [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] .stMarkdown strong,
        [data-testid="stSidebar"] .stRadio > label span, [data-testid="stSidebar"] .stCaption {
            color: #FFFFFF !important; opacity: 1;
        }
        [data-testid="stSidebar"] .st-bo:has(input:checked) + label span { color: #5DADE2 !important; font-weight: 700 !important; }
        [data-testid="stSidebar"] .stButton > button { color: #EAECEE !important; border-color: #EAECEE !important; }
        [data-testid="stSidebar"] .stButton > button:hover { color: #FFFFFF !important; border-color: #E74C3C !important; background-color: #E74C3C !important; }
        [data-testid="stSidebarNavCollapseButton"] svg { fill: #FFFFFF !important; }
        [data-testid="stMetricLabel"] { color: #A9C5E1 !important; }
        [data-testid="stMetricValue"] { color: #FFFFFF !important; }
        [data-testid="stMetricDelta"] { color: #2ECC71 !important; }
        [data-testid="stMetricDelta"][style*="color: rgb(255, 43, 43)"] { color: #FF4B4B !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ================== Koneksi & Konfigurasi Global ==================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)
supabase = init_connection()
JOB_TYPES = ["First Line Maintenance ( A )", "First Line Maintenance ( B )", "First Line Maintenance ( C )", "First Line Maintenance ( D )", "Corrective Maintenance", "Preventive Maintenance"]
ABSENSI_STATUS = ['Hadir', 'Sakit', 'Izin', 'Cuti', 'Tukar Dinas']

# --- Tambahan Telegram ---
def send_telegram_notification(ticket_id, area, description, personnel, sr_number, image_url=None, nama_peralatan=None):
    """Mengirim notifikasi otomatis ke Telegram dengan tambahan tanggal & waktu"""
    TOKEN = "8507107791:AAFd8BKfsMGZCzS7UctwNlWRiPipe45TkGE"
    CHAT_ID = "-1003701349665"
    
    # --- Tambahan: Ambil Waktu Sekarang ---
    waktu_sekarang = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    
    alat_info = f"*Peralatan:* {nama_peralatan}\n" if nama_peralatan else ""

    # Membuat teks pesan dengan baris Tanggal Laporan
    caption = (
        f"🚨 *NOTIFIKASI SR BARU (ARMOR-AI)* 🚨\n\n"
        f"*ID Tiket:* `{ticket_id}`\n"
        f"*Nomor SR:* `{sr_number}`\n"
        f"*Tanggal Laporan:* `{waktu_sekarang}`\n" 
        f"*Area:* {area}\n"
        f"{alat_info}"
        f"*Pelaksana:* {personnel}\n"
        f"*Keterangan:* {description}\n\n"
        f"🛠️ _Mohon segera ditindaklanjuti. Terima kasih._"
    )
    
    if image_url:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        payload = {
            "chat_id": CHAT_ID,
            "photo": image_url,
            "caption": caption,
            "parse_mode": "Markdown"
        }
    else:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": caption,
            "parse_mode": "Markdown"
        }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")
# ------------------------------------------

# ================== Fungsi-Fungsi Helper ==================
def verify_user_and_get_role(email, password):
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if session.user:
            role = session.user.user_metadata.get('role', 'operator')
            return {"role": role, "email": session.user.email}
    except Exception as e:
        print(f"Authentication error: {e}")
        return None
    return None

@st.cache_data(ttl=600)
def load_data_from_db():
    try:
        response = supabase.table('jobs').select('*').order('created_at', desc=True).limit(50000).execute()
        df = pd.DataFrame(response.data)
        if 'Tanggal' in df.columns and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data pekerjaan dari database: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_absensi_data():
    try:
        response = supabase.table('absensi').select('*').order('tanggal', desc=True).limit(50000).execute()
        df = pd.DataFrame(response.data)
        if 'tanggal' in df.columns and not df.empty:
            df['tanggal'] = pd.to_datetime(df['tanggal'])
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data absensi dari database: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_personnel_data():
    try:
        response = supabase.table('personel').select('id, nama').order('nama', desc=False).execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Gagal mengambil daftar personel: {e}")
        return pd.DataFrame(columns=['id', 'nama'])

def logout():
    for key in list(st.session_state.keys()):
        if key not in ['logged_in', 'user_role', 'user_email']:
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
        if image_col_before != -1: worksheet.set_column(image_col_before, image_col_before, 18)
        if image_col_after != -1: worksheet.set_column(image_col_after, image_col_after, 18)
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
                    max_width, max_height = 120, 90
                    aspect_ratio = width / height
                    if width > max_width or height > max_height:
                        if width / max_width > height / max_height:
                            new_width = max_width
                            new_height = int(new_width / aspect_ratio)
                        else:
                            new_height = max_height
                            new_width = int(new_height * aspect_ratio)
                    else: new_width, new_height = width, height
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    resized_img_buffer = io.BytesIO()
                    img_resized.save(resized_img_buffer, format="JPEG", quality=80)
                    resized_img_buffer.seek(0)
                    worksheet.insert_image(excel_row, image_col_before, "image_before.jpg", {'image_data': resized_img_buffer, 'x_offset': 5, 'y_offset': 5, 'object_position': 3})
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
                    max_width, max_height = 120, 90
                    aspect_ratio = width / height
                    if width > max_width or height > max_height:
                        if width / max_width > height / max_height:
                            new_width = max_width
                            new_height = int(new_width / aspect_ratio)
                        else:
                            new_height = max_height
                            new_width = int(new_height * aspect_ratio)
                    else: new_width, new_height = width, height
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    resized_img_buffer = io.BytesIO()
                    img_resized.save(resized_img_buffer, format="JPEG", quality=80)
                    resized_img_buffer.seek(0)
                    worksheet.insert_image(excel_row, image_col_after, "image_after.jpg", {'image_data': resized_img_buffer, 'x_offset': 5, 'y_offset': 5, 'object_position': 3})
                    worksheet.write(excel_row, image_col_after, "Lihat Gambar")
                except Exception as e:
                    print(f"Gagal memuat atau menyematkan gambar after dari URL {img_url_after}: {e}")
                    worksheet.write(excel_row, image_col_after, img_url_after if pd.notna(img_url_after) else "Tidak Ada Gambar")
    output.seek(0)
    return output.getvalue()

def create_pdf_report(filtered_data, report_type):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, spaceBefore=10, textColor=colors.HexColor('#2C3E50')))
    styles.add(ParagraphStyle(name='Header', alignment=TA_LEFT, textColor=colors.HexColor('#2C3E50')))
    elements = []
    
    # 1. Menyiapkan Kop Surat (Logo dan Teks)
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            header_text = "<b>PT PLN NUSANTARA POWER SERVICES</b><br/>Unit PLTU Bangka"
            logo_img = RLImage(logo_path, width=0.9*inch, height=0.4*inch, hAlign='LEFT')
            header_table = Table([[logo_img, Paragraph(header_text, styles['Header'])]], colWidths=[1*inch, 6*inch], style=[('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('LEFTPADDING', (1,0), (1,0), 0)])
            elements.append(header_table)
            elements.append(Spacer(1, 20))
    except Exception: pass

    # 2. Judul Dokumen
    title_text = f"<b>LAPORAN MONITORING {'SEMUA PEKERJAAN' if report_type == 'Semua' else report_type.upper()}</b>"
    elements.append(Paragraph(title_text, styles["TitleCenter"]))
    elements.append(Spacer(1, 12))

    # 3. Looping untuk setiap baris pekerjaan (1 Pekerjaan = 1 Halaman)
    for _, row in filtered_data.iterrows():
        # Memastikan tidak ada error jika nama_peralatan kosong/nan
        alat = str(row.get('nama_peralatan', '-'))
        if pd.isna(row.get('nama_peralatan')) or alat == 'nan' or alat.strip() == '':
            alat = '-'

        # Data Vertikal untuk 1 Pekerjaan
        data = [
            ["ID", str(row.get('ID', ''))],
            ["Tanggal", pd.to_datetime(row.get('Tanggal')).strftime('%d-%m-%Y') if pd.notna(row.get('Tanggal')) else '-'],
            ["Jenis", str(row.get('Jenis', ''))],
            ["Area", str(row.get('Area', ''))],
            ["Peralatan", alat],  # <--- INI TAMBAHAN KOLOM PERALATAN BARU ANDA
            ["Nomor SR", str(row.get('Nomor SR', ''))],
            ["Nama Personel", str(row.get('Nama Personel', row.get('Nama Pelaksana', '-')))], 
            ["Status", str(row.get('Status', ''))],
            ["Keterangan", Paragraph(str(row.get('Keterangan', '')).replace('\n', '<br/>'), styles['Normal'])],
        ]
        
        # Desain Tabel Vertikal
        table = Table(data, colWidths=[100, 380], style=[
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')), ('TEXTCOLOR', (0,0), (0, -1), colors.HexColor('#2C3E50')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')), ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('FONTSIZE', (0, 0), (-1, -1), 10),
        ])
        elements.append(table)
        
        # 4. Menyisipkan Gambar Before & After
        img1, img2 = None, None
        for img_url, position in [(row.get("Evidance"), 1), (row.get("Evidance After"), 2)]:
            if img_url and isinstance(img_url, str) and img_url.startswith('http'):
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
            
        # Pindah ke halaman baru untuk pekerjaan selanjutnya
        elements.append(PageBreak())

    # Menghapus PageBreak kosong di akhir dokumen
    if elements and isinstance(elements[-1], PageBreak): elements.pop()
    
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

#Tambahan ML
# ================== FUNGSI PREDICTIVE ML & TELEGRAM (DIPERBARUI) ==================

def send_predictive_alert(area, equipment, total_gangguan, tanggal_terakhir):
    """Kirim notifikasi prediksi Kerusakan Berulang pada Peralatan Spesifik"""
    TOKEN = "8507107791:AAFd8BKfsMGZCzS7UctwNlWRiPipe45TkGE"
    CHAT_ID = "-1003701349665"
    
    tgl_str = tanggal_terakhir.strftime('%d-%m-%Y')
    
    pesan = (
        f"🚨 *PREDIKTIF ALARM (REPEATED FAILURE)* 🚨\n\n"
        f"Terdeteksi kerusakan berulang pada peralatan berikut:\n"
        f"🛠️ Peralatan: *{equipment}*\n"
        f"📍 Area: *{area}*\n"
        f"⚠️ Total Kerusakan: *{total_gangguan} kali* (30 hari terakhir).\n"
        f"📅 Terakhir Rusak: *{tgl_str}*\n\n"
        f"💡 *Rekomendasi:* Cek riwayat perbaikan alat ini. Mungkin diperlukan penggantian sparepart total atau Root Cause Analysis (RCA)."
    )
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": pesan, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Gagal kirim alarm: {e}")

def analyze_predictive_maintenance(df):
    """Analisis perbaikan berulang pada peralatan spesifik"""
    if df.empty:
        return

    # Filter hanya Corrective Maintenance
    df_cm = df[df['Jenis'] == 'Corrective Maintenance'].copy()
    if len(df_cm) < 2:
        return

    # Pastikan kolom 'nama_peralatan' ada (untuk kompatibilitas data lama)
    col_name = 'nama_peralatan' if 'nama_peralatan' in df_cm.columns else 'Nama Peralatan'
    
    # Jika kolom belum ada di dataframe (data lama), skip dulu
    if col_name not in df_cm.columns:
        return

    # Bersihkan data: Hapus yang nama peralatannya kosong
    df_cm = df_cm[df_cm[col_name].notna() & (df_cm[col_name] != '')]

    # Normalisasi waktu
    df_cm['Tanggal'] = pd.to_datetime(df_cm['Tanggal']).dt.tz_localize(None)
    last_30_days = datetime.now() - timedelta(days=30)
    
    # Ambil data 30 hari terakhir
    recent_data = df_cm[df_cm['Tanggal'] >= last_30_days]
    
    if not recent_data.empty:
        # LOGIKA BARU: Group by Area DAN Nama Peralatan
        # Kita hitung berapa kali 'Pompa A' rusak di 'Boiler'
        summary = recent_data.groupby(['Area', col_name]).size().reset_index(name='Jumlah')
        
        # Ambang batas kerusakan berulang (misal: 3x dalam sebulan dianggap sering)
        THRESHOLD = 3 
        
        for index, row in summary.iterrows():
            if row['Jumlah'] >= THRESHOLD:
                # Ambil tanggal kejadian terakhir untuk alat tersebut
                last_date = recent_data[
                    (recent_data['Area'] == row['Area']) & 
                    (recent_data[col_name] == row[col_name])
                ]['Tanggal'].max()
                
                # Kirim Alert Spesifik Alat
                send_predictive_alert(row['Area'], row[col_name], row['Jumlah'], last_date)

# ================== Logika Utama Aplikasi ==================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.get("logged_in"):
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">ARMOR</h1>', unsafe_allow_html=True)
        try: st.image("logo.png", width=150)
        except FileNotFoundError: pass
        
        with st.form("login_form"):
            st.markdown('<h3 style="color: #FFFFFF; text-align: center; border-bottom: none;">User Login</h3>', unsafe_allow_html=True)
            email = st.text_input("Email", placeholder="e.g., admin@example.com", key="login_email").lower()
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
            
            if st.form_submit_button("Login"):
                with st.spinner("Memverifikasi..."):
                    user_data = verify_user_and_get_role(email, password)
                
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user_data['email']
                    st.session_state.user_role = user_data['role']
                    st.session_state.last_activity = datetime.now()
                    st.rerun()
                else:
                    st.error("Email atau password salah.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

user_role = st.session_state.get("user_role", "operator")

if 'last_activity' not in st.session_state or datetime.now() - st.session_state.last_activity > timedelta(minutes=30):
    logout()
st.session_state.last_activity = datetime.now()

if 'data' not in st.session_state:
    st.session_state.data = load_data_from_db()
df = st.session_state.data.copy()
if 'Nama Pelaksana' in df.columns:
    df.rename(columns={'Nama Pelaksana': 'Nama Personel'}, inplace=True)


with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"Selamat datang, **{st.session_state.get('user_email', 'Guest')}**!")
    st.write(f"Peran: **{user_role.capitalize()}**")
    try: st.image("logo.png", use_container_width=True) 
    except FileNotFoundError: pass

    menu_options = ["Input Data", "Report Data", "Analisis FLM", "Predictive Maintenance", "Absensi Personel"]

    if user_role == 'admin':
        menu_options.append("Kelola Personel")

    menu = st.radio(
        "Pilih Halaman:", 
        menu_options, 
        label_visibility="collapsed"
    )
    st.markdown("<br/><br/>", unsafe_allow_html=True)
    if st.button("Logout"): logout()
    st.markdown("---"); st.caption("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")

if user_role == 'operator':
    st.markdown("""<style>#MainMenu, footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

# ================== Logika Halaman ==================
if menu == "Input Data":
    st.header("Input Data Pekerjaan Baru")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tanggal = st.date_input("Tanggal", date.today())
            jenis = st.selectbox("Jenis Pekerjaan", JOB_TYPES)
            area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP", "Common"])
            
            # --- TAMBAHAN BARU ---
            nama_peralatan = st.text_input("Nama Peralatan / Tag Number", placeholder="Contoh: BFP Pump A, Motor Conveyor 1")
            # ---------------------

            nomor_sr = st.text_input("Nomor SR (Service Request)")
        with col2:
            nama_personel = st.text_input("Nama Personel")
            status = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
            keterangan = st.text_area("Keterangan / Uraian Pekerjaan")
        
        st.subheader("Upload Bukti Pekerjaan (Evidence)")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1: evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
        with col_ev2: evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Simpan Data"):
            if not all([nomor_sr, nama_personel, keterangan]):
                st.error("Mohon isi semua field yang wajib.")
            elif jenis == "Corrective Maintenance" and not nama_peralatan:
                st.error("Untuk Corrective Maintenance, Nama Peralatan WAJIB diisi agar bisa dilacak.")
            else:
                with st.spinner("Menyimpan data..."):
                    job_ids_df = pd.DataFrame(supabase.table('jobs').select('ID').execute().data)
                    new_id = generate_next_id(job_ids_df, jenis)
                    
                    evidance_url = upload_image_to_storage(evidance_file)
                    evidance_after_url = upload_image_to_storage(evidance_after_file)
                    
                    new_job_data = {
                        "ID": new_id, 
                        "Tanggal": str(tanggal), 
                        "Jenis": jenis, 
                        "Area": area, 
                        "nama_peralatan": nama_peralatan,
                        "Nomor SR": nomor_sr, 
                        "Nama Pelaksana": nama_personel,
                        "Keterangan": keterangan, "Status": status, 
                        "Evidance": evidance_url, "Evidance After": evidance_after_url
                    }
                    
                    try:
                        # Simpan ke Supabase
                        supabase.table("jobs").insert(new_job_data).execute()
                        
                        # --- NOTIFIKASI TELEGRAM ---
                        if jenis == "Corrective Maintenance":
                            send_telegram_notification(
                                new_id, 
                                area, 
                                keterangan, 
                                nama_personel, 
                                nomor_sr, 
                                evidance_url,
                                nama_peralatan
                            )
                        # ---------------------------

                        st.cache_data.clear()
                        st.session_state.data = load_data_from_db()
                        st.success(f"Data '{new_id}' berhasil disimpan!")
                        
                        # Trigger Analisis Prediktif
                        analyze_predictive_maintenance(st.session_state.data)
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan data ke database: {e}")

elif menu == "Report Data":
    st.header("Integrated Data & Report")
    with st.container(border=True):
        st.subheader("Filter & Edit Data")
        data_to_display = df.copy()
        
        if 'Hapus' not in data_to_display.columns:
            data_to_display['Hapus'] = False
        
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            all_jenis = ["Semua"] + sorted(list(data_to_display["Jenis"].dropna().unique()))
            filter_jenis = st.selectbox("Saring berdasarkan Jenis:", all_jenis, key="report_filter_jenis")
        with filter_col2:
            all_status = ["Semua"] + sorted(list(data_to_display["Status"].dropna().unique()))
            filter_status = st.selectbox("Saring berdasarkan Status:", all_status, key="report_filter_status")
        
        if filter_jenis != "Semua": data_to_display = data_to_display[data_to_display["Jenis"] == filter_jenis]
        if filter_status != "Semua": data_to_display = data_to_display[data_to_display["Status"] == filter_status]
        
        col_config_dict = {
            "Hapus": st.column_config.CheckboxColumn("Hapus?", help="Centang untuk menghapus."), 
            "ID": st.column_config.TextColumn("ID", disabled=True),
            "Tanggal": st.column_config.DateColumn("Tanggal", format="DD-MM-YYYY", disabled=True),
            "Jenis": st.column_config.SelectboxColumn("Jenis", options=JOB_TYPES, disabled=False if user_role == 'admin' else True),
            "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"], disabled=False if user_role == 'admin' else True),
            "nama_peralatan": st.column_config.TextColumn("Nama Peralatan", disabled=False if user_role == 'admin' else True),
            "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"], disabled=True),
            "Nomor SR": st.column_config.TextColumn("Nomor SR", disabled=True),
            "Nama Personel": st.column_config.TextColumn("Nama Personel", disabled=False if user_role == 'admin' else True),
            "Keterangan": st.column_config.TextColumn("Keterangan", width="large", disabled=False if user_role == 'admin' else True),
            "Evidance": st.column_config.LinkColumn("Evidence Before", display_text="Lihat", disabled=True),
            "Evidance After": st.column_config.LinkColumn("Evidence After", display_text="Lihat", disabled=True),
        }
        
        # Cek kolom equipment di view
        view_cols = ["Hapus", "ID", "Tanggal", "Jenis", "Area", "nama_peralatan", "Status", "Nomor SR", "Nama Personel", "Keterangan", "Evidance", "Evidance After"]
        # Pastikan kolom ada di dataframe
        if 'nama_peralatan' not in data_to_display.columns:
            data_to_display['nama_peralatan'] = ""

        edited_df = st.data_editor(
            data_to_display, 
            key="data_editor",
            use_container_width=True,
            column_config=col_config_dict,
            column_order=view_cols
        )
        
        if st.session_state.get("data_editor") and st.session_state["data_editor"]["edited_rows"] and user_role == 'admin':
            edited_rows_data = st.session_state["data_editor"]["edited_rows"]
            
            if st.button("💾 Simpan Perubahan Data", use_container_width=True):
                with st.spinner("Menyimpan perubahan..."):
                    changes_successful = True
                    for idx, changes in edited_rows_data.items():
                        original_id = data_to_display.loc[idx, 'ID']
                        update_payload = {}
                        for col_name, new_value in changes.items():
                            if col_name == 'Nama Personel':
                                update_payload['Nama Pelaksana'] = new_value
                            else:
                                update_payload[col_name] = new_value
                        if update_payload:
                            try:
                                supabase.table("jobs").update(update_payload).eq("ID", original_id).execute()
                                st.toast(f"Data ID '{original_id}' berhasil diupdate!")
                            except Exception as e:
                                st.error(f"Gagal mengupdate data ID '{original_id}': {e}")
                                changes_successful = False
                                break 
                    if changes_successful:
                        st.cache_data.clear()
                        st.session_state.data = load_data_from_db()
                        st.success("Semua perubahan berhasil disimpan.")
                        st.rerun()
                    else:
                        st.warning("Beberapa perubahan mungkin tidak tersimpan karena error.")
        
        rows_to_delete = edited_df[edited_df['Hapus'] == True]
        if not rows_to_delete.empty and user_role == 'admin':
            st.markdown('<div class="delete-button">', unsafe_allow_html=True)
            ids_to_delete = rows_to_delete['ID'].tolist()
            if st.button(f"🗑️ Hapus ({len(ids_to_delete)}) Baris Terpilih", use_container_width=True):
                with st.spinner("Menghapus data..."):
                    try: 
                        supabase.table("jobs").delete().in_("ID", ids_to_delete).execute() 
                        st.cache_data.clear()
                        st.session_state.data = load_data_from_db()
                        st.success("Data terpilih berhasil dihapus.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menghapus data: {e}") 
            st.markdown('</div>', unsafe_allow_html=True)
        elif not rows_to_delete.empty:
            st.warning("Hanya 'admin' yang dapat menghapus data.")

    st.write("---") 
    
    col_func1, col_func2 = st.columns([2, 1])
    with col_func1:
        with st.expander("✅ **Update Status Pekerjaan**", expanded=True):
            open_jobs = df[df['Status'].isin(['Open', 'On Progress'])]
            if not open_jobs.empty:
                job_options = {f"{row['ID']} - {row['Nama Personel']} - {str(row.get('Keterangan',''))[:40]}...": row['ID'] for _, row in open_jobs.iterrows()}
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
                    if st.button("📊 Buat & Siapkan Excel", use_container_width=True, key='prepare_excel_button'):
                        with st.spinner("Membuat file Excel..."):
                            excel_bytes = create_excel_report_with_images(filtered_data) 
                            st.session_state.excel_bytes = excel_bytes
                            st.session_state.excel_filename = f"laporan_excel_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.xlsx"
                    
                    if 'excel_bytes' in st.session_state and st.session_state.excel_bytes:
                        st.download_button(label="⬇️ Download Laporan (Excel)", data=st.session_state.excel_bytes, file_name=st.session_state.excel_filename, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key='download_excel_button')
                
                with dl_col2:
                    if st.button("📄 Buat & Siapkan PDF", use_container_width=True):
                        with st.spinner("Membuat file PDF..."):
                            pdf_bytes = create_pdf_report(filtered_data, report_type)
                            st.session_state.pdf_bytes = pdf_bytes
                            st.session_state.pdf_filename = f"laporan_pdf_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.pdf"
                    
                    if 'pdf_bytes' in st.session_state and st.session_state.pdf_bytes:
                        st.download_button(label="⬇️ Download Laporan (PDF)", data=st.session_state.pdf_bytes, file_name=st.session_state.pdf_filename, mime="application/pdf", use_container_width=True, key='download_pdf_button')

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
    mask_flm = (df['Tanggal'].dt.date >= start_date_flm) & (df['Tanggal'].dt.date <= end_date_flm) & (df['Status'].isin(selected_status_flm)) & (df['Jenis'].str.startswith('First Line Maintenance', na=False))
    df_flm = df[mask_flm]
    if df_flm.empty:
        st.warning("Tidak ada data FLM yang cocok dengan filter Anda.")
    else:
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
        
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            st.subheader("Proporsi Jenis FLM")
            fig_pie = px.pie(flm_counts, names='Jenis FLM', values='Jumlah', hole=0.4, title='Persentase Pelaksanaan FLM', template='plotly_dark')
            st.plotly_chart(fig_pie, use_container_width=True)
        with chart_col2:
            st.subheader("Peringkat Dominasi FLM")
            fig_bar = px.bar(flm_counts.sort_values('Jumlah'), x='Jumlah', y='Jenis FLM', orientation='h', text='Jumlah', color='Jumlah', color_continuous_scale=px.colors.sequential.Blues_r, template='plotly_dark')
            st.plotly_chart(fig_bar, use_container_width=True)
        
        st.markdown("---") 
        st.header("🏆 Skor Personel per Regu (Leaderboard)")
        st.markdown("Peringkat personel dipisahkan berdasarkan regu (A, B, C, D).")

        # Define targets
        regu_targets = ["First Line Maintenance ( A )", "First Line Maintenance ( B )", "First Line Maintenance ( C )", "First Line Maintenance ( D )"]
        regu_labels = ["Regu A", "Regu B", "Regu C", "Regu D"]

        # Create tabs
        tabs = st.tabs(regu_labels)

        for i, target_jenis in enumerate(regu_targets):
            with tabs[i]:
                st.subheader(f"Leaderboard {regu_labels[i]}")

                # Filter data specific to this FLM type from the main filtered FLM dataframe
                df_regu = df_flm[df_flm['Jenis'] == target_jenis]

                if df_regu.empty:
                    st.info(f"Belum ada data pekerjaan untuk {target_jenis} pada periode ini.")
                elif 'Nama Personel' in df_regu and not df_regu['Nama Personel'].dropna().empty:
                    # Process personnel names
                    personel_counts = df_regu['Nama Personel'].str.split(',').explode().str.strip().value_counts().reset_index()
                    personel_counts.columns = ['Nama Personel', 'Jumlah FLM Dikerjakan']

                    if not personel_counts.empty:
                        # Top Performer logic
                        top_performer = personel_counts.iloc[0]
                        col_kpi1, col_kpi2 = st.columns(2)
                        with col_kpi1: st.success(f"**MVP {regu_labels[i]}:** {top_performer['Nama Personel']}")
                        with col_kpi2: st.metric("Total Kontribusi", f"{top_performer['Jumlah FLM Dikerjakan']} Job")

                        # Chart
                        fig_leaderboard = px.bar(
                            personel_counts.sort_values('Jumlah FLM Dikerjakan'),
                            x='Jumlah FLM Dikerjakan',
                            y='Nama Personel',
                            orientation='h',
                            text='Jumlah FLM Dikerjakan',
                            color='Jumlah FLM Dikerjakan',
                            color_continuous_scale=px.colors.sequential.Viridis,
                            template='plotly_dark'
                        )
                        fig_leaderboard.update_layout(xaxis_title="Jumlah Pekerjaan", yaxis_title="Personel")
                        st.plotly_chart(fig_leaderboard, use_container_width=True)
                    else:
                        st.info("Data personel tidak valid.")
                else:
                    st.info("Kolom nama personel kosong.")

# === HALAMAN BARU: ABSENSI PERSONEL ===
elif menu == "Absensi Personel":
    st.header("🗓️ Input & Dashboard Absensi Personel")

    # --- Bagian Input Absensi ---
    if user_role == 'admin':
        with st.expander("✅ **Input Absensi Massal (Hadir)**", expanded=True):
            df_personnel = load_personnel_data()
            personnel_list = df_personnel['nama'].tolist() if not df_personnel.empty else []
            
            if not personnel_list:
                st.warning("Daftar personel kosong. Harap isi data di halaman 'Kelola Personel' terlebih dahulu.")
            else:
                with st.form("mass_absensi_form"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        selected_personnel = st.multiselect("Pilih Personel yang Hadir:", options=personnel_list, default=personnel_list)
                    with col2:
                        tanggal_massal = st.date_input("Untuk Tanggal", date.today())
                    
                    submitted_massal = st.form_submit_button("Simpan Kehadiran Massal")
                    if submitted_massal:
                        if not selected_personnel:
                            st.warning("Mohon pilih setidaknya satu personel.")
                        else:
                            with st.spinner(f"Menyimpan {len(selected_personnel)} data kehadiran..."):
                                records_to_insert = []
                                for name in selected_personnel:
                                    records_to_insert.append({
                                        "tanggal": str(tanggal_massal),
                                        "nama_personel": name,
                                        "status_absensi": "Hadir",
                                        "keterangan": ""
                                    })
                                try:
                                    supabase.table("absensi").upsert(records_to_insert, on_conflict="tanggal,nama_personel").execute()
                                    st.cache_data.clear()
                                    st.success("Data kehadiran massal berhasil disimpan!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menyimpan data massal: {e}")

        with st.expander("📝 Input Absensi Individual (Sakit, Izin, Cuti, dll)"):
            if not personnel_list:
                st.info("Daftar personel kosong.")
            else:
                with st.form("absensi_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        tanggal_absensi = st.date_input("Tanggal Absensi", date.today(), key="ind_date")
                        nama_personel_absensi = st.selectbox("Nama Personel", options=personnel_list, key="ind_name")
                    with col2:
                        status_absensi = st.selectbox("Status Kehadiran", options=[s for s in ABSENSI_STATUS if s != 'Hadir'], key="ind_status")
                        keterangan_absensi = st.text_area("Keterangan (wajib diisi)", key="ind_ket")

                    submitted = st.form_submit_button("Simpan Absensi Individual")
                    if submitted:
                        if not keterangan_absensi:
                            st.warning("Keterangan wajib diisi untuk status selain Hadir.")
                        else:
                            with st.spinner("Menyimpan data absensi..."):
                                try:
                                    supabase.table("absensi").upsert({
                                        "tanggal": str(tanggal_absensi),
                                        "nama_personel": nama_personel_absensi,
                                        "status_absensi": status_absensi,
                                        "keterangan": keterangan_absensi
                                    }, on_conflict="tanggal,nama_personel").execute()
                                    st.cache_data.clear()
                                    st.success(f"Absensi untuk '{nama_personel_absensi}' berhasil disimpan.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menyimpan absensi: {e}")
    
    st.markdown("---")

    # --- Bagian Dashboard Absensi ---
    st.subheader("📊 Laporan Kehadiran & Ketidakhadiran")
    df_absensi = load_absensi_data()

    if df_absensi.empty:
        st.info("Belum ada data absensi untuk ditampilkan.")
    else:
        df_absensi['tanggal'] = pd.to_datetime(df_absensi['tanggal']).dt.tz_localize(None)
        
        col1, col2 = st.columns(2)
        with col1:
            year_options = sorted(df_absensi['tanggal'].dt.year.unique(), reverse=True)
            selected_year = st.selectbox("Pilih Tahun:", year_options)
        with col2:
            month_dict = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"}
            all_month_options = ["Semua Bulan"] + list(month_dict.values())
            selected_month_str = st.selectbox("Pilih Bulan:", all_month_options)
        
        mask_abs = (df_absensi['tanggal'].dt.year == selected_year)
        if selected_month_str != "Semua Bulan":
            selected_month_num = [k for k, v in month_dict.items() if v == selected_month_str][0]
            mask_abs &= (df_absensi['tanggal'].dt.month == selected_month_num)
        
        filtered_df_abs = df_absensi[mask_abs]

        if filtered_df_abs.empty:
                st.warning("Tidak ada data absensi pada periode yang dipilih.")
        else:
            if 'nama_personel' in filtered_df_abs.columns:
                df_hadir = filtered_df_abs[filtered_df_abs['status_absensi'] == 'Hadir']
                df_absen = filtered_df_abs[filtered_df_abs['status_absensi'] != 'Hadir']

                col1_chart, col2_chart = st.columns(2)

                with col1_chart:
                    st.subheader("✅ Peringkat Kehadiran")
                    if df_hadir.empty:
                        st.info("Tidak ada data kehadiran.")
                    else:
                        hadir_counts = df_hadir['nama_personel'].value_counts().reset_index()
                        hadir_counts.columns = ['Nama Personel', 'Jumlah Hari Hadir']
                        fig_bar_hadir = px.bar(
                            hadir_counts.sort_values('Jumlah Hari Hadir'), 
                            x='Jumlah Hari Hadir', 
                            y='Nama Personel', 
                            orientation='h', 
                            text='Jumlah Hari Hadir',
                            color='Jumlah Hari Hadir',
                            color_continuous_scale=px.colors.sequential.Greens,
                            template='plotly_dark',
                            title=f"Top Kehadiran - {selected_month_str} {selected_year}"
                        )
                        st.plotly_chart(fig_bar_hadir, use_container_width=True)

                with col2_chart:
                    st.subheader("❌ Peringkat Ketidakhadiran")
                    if df_absen.empty:
                        st.success("Tidak ada data ketidakhadiran.")
                    else:
                        absen_counts = df_absen.groupby(['nama_personel', 'status_absensi']).size().reset_index(name='Jumlah Hari')
                        
                        fig_bar_absen = px.bar(
                            absen_counts, 
                            x='Jumlah Hari', 
                            y='nama_personel', 
                            color='status_absensi',
                            orientation='h',
                            title=f"Detail Ketidakhadiran - {selected_month_str} {selected_year}",
                            labels={'nama_personel': 'Nama Personel', 'Jumlah Hari': 'Jumlah Hari Tidak Hadir'},
                            template='plotly_dark',
                            color_discrete_map={
                                'Sakit': '#E74C3C',
                                'Izin': '#F39C12',
                                'Cuti': '#9B59B6',
                                'Tukar Dinas': '#85929E'
                            }
                        )
                        fig_bar_absen.update_layout(barmode='stack', yaxis={'categoryorder':'total ascending'})
                        fig_bar_absen.update_xaxes(dtick=1)
                        st.plotly_chart(fig_bar_absen, use_container_width=True)
            else:
                st.error("Kolom 'nama_personel' tidak ditemukan dalam data absensi. Mohon periksa nama kolom di tabel 'absensi' pada Supabase.")

            st.markdown("---")
            st.subheader("📋 Detail Data Absensi")
            
            if user_role == 'admin':
                st.info("Anda dapat mengedit atau menghapus data absensi di bawah ini.")
                filtered_df_abs['Hapus'] = False
                
                edited_abs_df = st.data_editor(
                    filtered_df_abs[['id', 'tanggal', 'nama_personel', 'status_absensi', 'keterangan', 'Hapus']],
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "tanggal": st.column_config.DateColumn("Tanggal", format="DD-MM-YYYY"),
                        "nama_personel": st.column_config.SelectboxColumn("Nama Personel", options=load_personnel_data()['nama'].tolist()),
                        "status_absensi": st.column_config.SelectboxColumn("Status", options=ABSENSI_STATUS),
                        "keterangan": st.column_config.TextColumn("Keterangan"),
                        "Hapus": st.column_config.CheckboxColumn("Hapus?")
                    },
                    use_container_width=True,
                    hide_index=True,
                    key="absensi_editor"
                )

                save_col, delete_col = st.columns(2)
                with save_col:
                    if st.button("💾 Simpan Perubahan Absensi"):
                        changes = st.session_state.absensi_editor.get("edited_rows", {})
                        if not changes:
                            st.info("Tidak ada perubahan untuk disimpan.")
                        else:
                            with st.spinner("Menyimpan perubahan..."):
                                success = True
                                for row_idx, changed_data in changes.items():
                                    absensi_id = edited_abs_df.iloc[row_idx]['id']
                                    try:
                                        supabase.table("absensi").update(changed_data).eq("id", absensi_id).execute()
                                    except Exception as e:
                                        st.error(f"Gagal update absensi ID {absensi_id}: {e}")
                                        success = False
                                if success:
                                    st.cache_data.clear()
                                    st.success("Perubahan absensi berhasil disimpan.")
                                    st.rerun()
                
                with delete_col:
                    rows_to_delete = edited_abs_df[edited_abs_df['Hapus']]
                    if not rows_to_delete.empty:
                        ids_to_delete = rows_to_delete['id'].tolist()
                        st.markdown('<div class="delete-button">', unsafe_allow_html=True)
                        if st.button(f"🗑️ Hapus ({len(ids_to_delete)}) Absensi Terpilih"):
                            with st.spinner("Menghapus absensi..."):
                                try:
                                    supabase.table("absensi").delete().in_("id", ids_to_delete).execute()
                                    st.cache_data.clear()
                                    st.success("Data absensi terpilih berhasil dihapus.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Gagal menghapus absensi: {e}")
                        st.markdown('</div>', unsafe_allow_html=True)

            else: 
                st.dataframe(
                    filtered_df_abs[['tanggal', 'nama_personel', 'status_absensi']].sort_values('tanggal', ascending=False),
                    use_container_width=True
                )

# === HALAMAN BARU: PREDICTIVE MAINTENANCE (AI ANALYSIS) ===
elif menu == "Predictive Maintenance":
    st.header("🔮 AI Predictive Maintenance Dashboard")
    st.markdown("Analisis Machine Learning untuk mendeteksi peralatan dengan frekuensi gangguan (CM) tidak wajar.")

    if df.empty:
        st.info("Data tidak tersedia untuk analisis.")
    else:
        # 1. Filter Data CM & Bersihkan Timezone (Penting untuk cegah error gambar 2)
        df_cm = df[df['Jenis'] == 'Corrective Maintenance'].copy()
        
        if df_cm.empty:
            st.warning("Belum ada data Corrective Maintenance (CM) yang tercatat.")
        else:
            # Pastikan kolom nama_peralatan ada
            if 'nama_peralatan' not in df_cm.columns:
                df_cm['nama_peralatan'] = df_cm['nama_peralatan'].fillna('Unknown')
            
            # Mengonversi tanggal ke datetime dan membuang zona waktu
            df_cm['Tanggal'] = pd.to_datetime(df_cm['Tanggal']).dt.tz_localize(None)
            
            # Hitung 30 hari terakhir tanpa zona waktu
            last_month = datetime.now() - timedelta(days=30)
            
            df_recent = df_cm[df_cm['Tanggal'] >= last_month]
            
            if df_recent.empty:
                st.info("Tidak ada gangguan CM dalam 30 hari terakhir.")
            else:
                # LOGIKA BARU: Group by Area DAN Nama Peralatan
                # Kita hitung berapa kali 'Pompa A' rusak di 'Boiler'
                col_name = 'nama_peralatan'
                
                # Cek jika kolom nama_peralatan kosong, ganti dengan 'Unidentified' agar tetap terhitung
                # Handle kolom nama_peralatan jika belum ada di database atau cache lama
                if 'nama_peralatan' not in df_recent.columns:
                    df_recent['nama_peralatan'] = 'Unknown'
                else:
                    df_recent[col_name] = df_recent[col_name].replace('', 'Unidentified').fillna('Unidentified')

                area_stats = df_recent.groupby(['Area', col_name]).size().reset_index(name='Jumlah_Gangguan')
                area_stats = area_stats.sort_values('Jumlah_Gangguan', ascending=False)
                
                # Buat label gabungan untuk chart
                area_stats['Label'] = area_stats['Area'] + " - " + area_stats[col_name]

                # 3. Layout Dashboard
                col_metric1, col_metric2 = st.columns(2)
                
                with col_metric1:
                    st.subheader("⚠️ Status Alert System")
                    for index, row in area_stats.iterrows():
                        if row['Jumlah_Gangguan'] >= 3:
                            st.error(f"**{row['Label']}**: CRITICAL ({row['Jumlah_Gangguan']} Gangguan)")
                        elif row['Jumlah_Gangguan'] == 2:
                            st.warning(f"**{row['Label']}**: WATCHLIST ({row['Jumlah_Gangguan']} Gangguan)")
                        else:
                            st.success(f"**{row['Label']}**: NORMAL ({row['Jumlah_Gangguan']} Gangguan)")

                with col_metric2:
                    st.subheader("📊 Grafik Frekuensi Gangguan")
                    fig_pred = px.bar(
                        area_stats, 
                        x='Label', 
                        y='Jumlah_Gangguan',
                        color='Jumlah_Gangguan',
                        color_continuous_scale='Reds',
                        template='plotly_dark',
                        labels={'Label': 'Area & Peralatan'}
                    )
                    st.plotly_chart(fig_pred, use_container_width=True)

                st.markdown("---")
                st.subheader("🔍 Detail Histori Gangguan 30 Hari Terakhir")
                st.dataframe(df_recent[['ID', 'Tanggal', 'Area', 'nama_peralatan', 'Nama Personel', 'Keterangan']], use_container_width=True)


elif menu == "Kelola Personel" and user_role == 'admin':
    st.header("👥 Kelola Daftar Personel")
    
    df_personnel = load_personnel_data()

    with st.expander("➕ Tambah Personel Baru"):
        with st.form("add_personnel_form"):
            new_name = st.text_input("Nama Personel Baru", key="new_personnel_name")
            if st.form_submit_button("Simpan Personel"):
                if new_name:
                    try:
                        if new_name in df_personnel['nama'].tolist():
                            st.error(f"Personel dengan nama '{new_name}' sudah ada.")
                        else:
                            supabase.table("personel").insert({"nama": new_name}).execute()
                            st.cache_data.clear()
                            st.success(f"Personel '{new_name}' berhasil ditambahkan.")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menambahkan personel: {e}")
                else:
                    st.warning("Nama tidak boleh kosong.")
    
    st.markdown("---")

    st.subheader("✏️ Edit atau Hapus Personel")
    if df_personnel.empty:
        st.info("Belum ada data personel. Silakan tambahkan di atas.")
    else:
        df_personnel['Hapus'] = False
        
        edited_df_personnel = st.data_editor(
            df_personnel[['id', 'nama', 'Hapus']],
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True),
                "nama": st.column_config.TextColumn("Nama Personel", required=True),
                "Hapus": st.column_config.CheckboxColumn("Hapus?")
            },
            use_container_width=True,
            hide_index=True,
            key="personnel_editor"
        )

        col_save, col_delete = st.columns(2)

        with col_save:
            if st.button("💾 Simpan Perubahan Nama"):
                changes = st.session_state.personnel_editor.get("edited_rows", {})
                if not changes:
                    st.info("Tidak ada perubahan nama untuk disimpan.")
                else:
                    with st.spinner("Menyimpan perubahan..."):
                        success = True
                        for row_idx, changed_data in changes.items():
                            personnel_id = edited_df_personnel.iloc[row_idx]['id']
                            new_name = changed_data.get('nama')
                            if new_name:
                                try:
                                    supabase.table("personel").update({"nama": new_name}).eq("id", personnel_id).execute()
                                except Exception as e:
                                    st.error(f"Gagal update nama untuk ID {personnel_id}: {e}")
                                    success = False
                        if success:
                            st.cache_data.clear()
                            st.success("Semua perubahan nama berhasil disimpan.")
                            st.rerun()

        with col_delete:
            rows_to_delete = edited_df_personnel[edited_df_personnel['Hapus']]
            if not rows_to_delete.empty:
                ids_to_delete = rows_to_delete['id'].tolist()
                st.markdown('<div class="delete-button">', unsafe_allow_html=True)
                if st.button(f"🗑️ Hapus ({len(ids_to_delete)}) Personel Terpilih"):
                    with st.spinner("Menghapus personel..."):
                        try:
                            supabase.table("personel").delete().in_("id", ids_to_delete).execute()
                            st.cache_data.clear()
                            st.success("Personel terpilih berhasil dihapus.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal menghapus personel: {e}")
                st.markdown('</div>', unsafe_allow_html=True)
