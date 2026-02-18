# APLIKASI PRODUKSI LENGKAP - VERSI DENGAN ABSENSI, KELOLA PERSONEL & AI PREDICTIVE
import streamlit as st
import pandas as pd
import numpy as np
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
from sklearn.linear_model import LinearRegression

# ================== Konfigurasi Halaman Streamlit ==================
st.set_page_config(page_title="FLM & Corrective Maintenance", layout="wide")

# ================== CSS Kustom ==================
st.markdown(
    """
    <style>
        /* Background aplikasi */
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

        /* Efek HOVER & FOCUS */
        div[data-baseweb="input"] > div:hover, div[data-baseweb="textarea"] > div:hover, div[data-baseweb="select"] > div:hover {
            background-color: rgba(236, 240, 241, 0.55) !important;
            border-color: rgba(52, 152, 219, 0.7) !important;
        }
        div[data-baseweb="input"] > div:focus-within, div[data-baseweb="textarea"] > div:focus-within, div[data-baseweb="select"] > div:focus-within {
            background-color: rgba(236, 240, 241, 0.7) !important;
            border-color: #3498DB !important;
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.3) !important;
        }

        label, div[data-testid="stWidgetLabel"] label {
            color: #FFFFFF !important; font-weight: 500;
        }

        .ai-card {
            background-color: rgba(52, 152, 219, 0.15);
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #3498DB;
            margin-bottom: 10px;
        }
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

# ================== Fungsi Machine Learning ==================
def get_ml_analysis(df):
    if df.empty: return None, None, None
    df_cm = df[df['Jenis'] == 'Corrective Maintenance'].copy()
    if df_cm.empty: return None, None, None
    df_cm['Tanggal'] = pd.to_datetime(df_cm['Tanggal']).dt.tz_localize(None)
    
    # Early Warning (30 hari terakhir)
    today = datetime.now()
    last_30_days = today - timedelta(days=30)
    warning_data = df_cm[df_cm['Tanggal'] >= last_30_days]['Area'].value_counts().reset_index()
    warning_data.columns = ['Area', 'Jumlah_Kasus']
    
    def set_risk(count):
        if count >= 5: return "🚨 BAHAYA (High Risk)"
        elif count >= 3: return "⚠️ SIAGA (Medium Risk)"
        return "✅ AMAN"
    
    warning_data['Status'] = warning_data['Jumlah_Kasus'].apply(set_risk)

    # Forecasting (Linear Regression)
    monthly_trend = df_cm.resample('M', on='Tanggal').size().reset_index(name='Total')
    prediction_val = 0
    if len(monthly_trend) >= 2:
        X = np.arange(len(monthly_trend)).reshape(-1, 1)
        y = monthly_trend['Total'].values
        model = LinearRegression().fit(X, y)
        prediction_val = max(0, int(round(model.predict(np.array([[len(monthly_trend)]]))[0])))
        
    return warning_data, prediction_val, monthly_trend

# ================== Fungsi-Fungsi Helper ==================
def send_telegram_notification(ticket_id, area, description, personnel, sr_number, image_url=None):
    TOKEN = "8507107791:AAFd8BKfsMGZCzS7UctwNlWRiPipe45TkGE"
    CHAT_ID = "-1003701349665"
    caption = (
        f"🚨 *NOTIFIKASI SR BARU (ARMOR)* 🚨\n\n"
        f"*ID Tiket:* `{ticket_id}`\n"
        f"*Nomor SR:* `{sr_number}`\n"
        f"*Area:* {area}\n"
        f"*Pelaksana:* {personnel}\n"
        f"*Keterangan:* {description}\n\n"
        f"🛠️ _Mohon segera ditindaklanjuti. Terima kasih._"
    )
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto" if image_url else f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "parse_mode": "Markdown"}
    if image_url:
        payload["photo"] = image_url
        payload["caption"] = caption
    else:
        payload["text"] = caption
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception: pass

def verify_user_and_get_role(email, password):
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if session.user:
            role = session.user.user_metadata.get('role', 'operator')
            return {"role": role, "email": session.user.email}
    except Exception: return None
    return None

@st.cache_data(ttl=600)
def load_data_from_db():
    try:
        response = supabase.table('jobs').select('*').order('created_at', desc=True).limit(50000).execute()
        df = pd.DataFrame(response.data)
        if 'Tanggal' in df.columns and not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_absensi_data():
    try:
        response = supabase.table('absensi').select('*').order('tanggal', desc=True).limit(50000).execute()
        df = pd.DataFrame(response.data)
        if 'tanggal' in df.columns and not df.empty:
            df['tanggal'] = pd.to_datetime(df['tanggal'])
        return df
    except Exception: return pd.DataFrame()

@st.cache_data(ttl=300)
def load_personnel_data():
    try:
        response = supabase.table('personel').select('id, nama').order('nama', desc=False).execute()
        return pd.DataFrame(response.data)
    except Exception: return pd.DataFrame(columns=['id', 'nama'])

def logout():
    for key in list(st.session_state.keys()):
        if key not in ['logged_in', 'user_role', 'user_email']: del st.session_state[key]
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
    except Exception: pass
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
    except Exception: return ""

# ================== Pelaporan Excel & PDF Detail ==================
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
            worksheet.set_column(image_col_before, image_col_before, 25)
            worksheet.set_column(image_col_after, image_col_after, 25)
        except KeyError:
            image_col_before, image_col_after = -1, -1

        for row_num, row_data in filtered_data.iterrows():
            excel_row = row_num + 1
            worksheet.set_row(excel_row, 90)
            
            # Evidence Before
            img_url_before = row_data.get("Evidance")
            if img_url_before and isinstance(img_url_before, str) and image_col_before != -1:
                try:
                    resp = requests.get(img_url_before, stream=True, timeout=10)
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    img = fix_image_orientation(img)
                    img.thumbnail((150, 90))
                    img_buf = io.BytesIO()
                    img.save(img_buf, format="JPEG")
                    worksheet.insert_image(excel_row, image_col_before, "b.jpg", {'image_data': img_buf, 'x_offset': 5, 'y_offset': 5})
                except: pass

            # Evidence After
            img_url_after = row_data.get("Evidance After")
            if img_url_after and isinstance(img_url_after, str) and image_col_after != -1:
                try:
                    resp = requests.get(img_url_after, stream=True, timeout=10)
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    img = fix_image_orientation(img)
                    img.thumbnail((150, 90))
                    img_buf = io.BytesIO()
                    img.save(img_buf, format="JPEG")
                    worksheet.insert_image(excel_row, image_col_after, "a.jpg", {'image_data': img_buf, 'x_offset': 5, 'y_offset': 5})
                except: pass
                
    output.seek(0)
    return output.getvalue()

def create_pdf_report(filtered_data, report_type):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, textColor=colors.HexColor('#2C3E50')))
    elements = []
    
    # Header
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        header_text = "<b>PT PLN NUSANTARA POWER SERVICES</b><br/>Unit PLTU Bangka"
        logo_img = RLImage(logo_path, width=0.9*inch, height=0.4*inch, hAlign='LEFT')
        header_table = Table([[logo_img, Paragraph(header_text, styles['Normal'])]], colWidths=[1*inch, 6*inch])
        header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        elements.append(header_table)
        elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"<b>LAPORAN MONITORING {report_type.upper()}</b>", styles["TitleCenter"]))
    elements.append(Spacer(1, 12))

    for _, row in filtered_data.iterrows():
        data = [
            ["ID", str(row.get('ID', ''))],
            ["Tanggal", pd.to_datetime(row.get('Tanggal')).strftime('%d-%m-%Y')],
            ["Jenis", str(row.get('Jenis', ''))],
            ["Area", str(row.get('Area', ''))],
            ["Pelaksana", str(row.get('Nama Personel', ''))],
            ["Status", str(row.get('Status', ''))],
            ["Keterangan", Paragraph(str(row.get('Keterangan', '')), styles['Normal'])],
        ]
        t = Table(data, colWidths=[100, 380])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#ECF0F1')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#BDC3C7')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BDC3C7')),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        elements.append(t)
        
        # Images logic
        img1, img2 = None, None
        for url, pos in [(row.get("Evidance"), 1), (row.get("Evidance After"), 2)]:
            if url and isinstance(url, str):
                try:
                    resp = requests.get(url, stream=True, timeout=10)
                    image_element = RLImage(io.BytesIO(resp.content), width=2.8*inch, height=2.1*inch, kind='bound')
                    if pos == 1: img1 = image_element
                    else: img2 = image_element
                except: pass
        
        if img1 or img2:
            elements.append(Spacer(1, 10))
            img_table = Table([[Paragraph("Before", styles['Normal']), Paragraph("After", styles['Normal'])], [img1, img2]], colWidths=[3.2*inch, 3.2*inch])
            elements.append(img_table)
            
        elements.append(PageBreak())
    
    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ================== Logika Utama Aplikasi ==================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.get("logged_in"):
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">ARMOR</h1>', unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="admin@example.com").lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user_data = verify_user_and_get_role(email, password)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user_data['role']
                    st.session_state.user_email = user_data['email']
                    st.rerun()
                else: st.error("Email atau Password salah.")
    st.stop()

# Data Load
if 'data' not in st.session_state: st.session_state.data = load_data_from_db()
df = st.session_state.data.copy()
if 'Nama Pelaksana' in df.columns: df.rename(columns={'Nama Pelaksana': 'Nama Personel'}, inplace=True)
user_role = st.session_state.user_role

with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"User: **{st.session_state.user_email}** ({user_role})")
    menu_options = ["Input Data", "Report Data", "Analisis FLM", "Absensi Personel", "AI Predictive"]
    if user_role == 'admin': menu_options.append("Kelola Personel")
    menu = st.radio("Pilih Halaman:", menu_options)
    if st.button("Logout"): logout()

# ================== HALAMAN: INPUT DATA ==================
if menu == "Input Data":
    st.header("Input Data Pekerjaan Baru")
    with st.form("input_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tanggal = st.date_input("Tanggal", date.today())
            jenis = st.selectbox("Jenis Pekerjaan", JOB_TYPES)
            area = st.selectbox("Area", ["Boiler", "Turbine", "CHCB", "WTP", "Common"])
            nomor_sr = st.text_input("Nomor SR")
        with col2:
            nama_personel = st.text_input("Nama Personel")
            status = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
            keterangan = st.text_area("Keterangan")
        
        st.subheader("Bukti Evidence")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1: ev_before = st.file_uploader("Evidence Before", type=["png", "jpg", "jpeg"])
        with col_ev2: ev_after = st.file_uploader("Evidence After", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Simpan Data"):
            new_id = generate_next_id(df, jenis)
            url_b = upload_image_to_storage(ev_before)
            url_a = upload_image_to_storage(ev_after)
            new_job = {
                "ID": new_id, "Tanggal": str(tanggal), "Jenis": jenis, "Area": area, 
                "Nomor SR": nomor_sr, "Nama Pelaksana": nama_personel, 
                "Keterangan": keterangan, "Status": status, 
                "Evidance": url_b, "Evidance After": url_a
            }
            try:
                supabase.table("jobs").insert(new_job).execute()
                if jenis == "Corrective Maintenance":
                    send_telegram_notification(new_id, area, keterangan, nama_personel, nomor_sr, url_b)
                st.cache_data.clear()
                st.session_state.data = load_data_from_db()
                st.success(f"Berhasil menyimpan {new_id}")
                st.rerun()
            except Exception as e: st.error(f"Gagal: {e}")

# ================== HALAMAN: AI PREDICTIVE ==================
elif menu == "AI Predictive":
    st.header("🤖 AI Predictive Maintenance")
    st.write("Fitur Machine Learning untuk deteksi risiko dan prediksi beban kerja.")
    
    warning_df, prediction, trend_df = get_ml_analysis(df)
    
    if warning_df is not None:
        st.subheader("⚠️ Early Warning System (Area Berisiko)")
        cols = st.columns(len(warning_df) if not warning_df.empty else 1)
        if warning_df.empty: st.success("Seluruh area aman.")
        else:
            for i, row in warning_df.iterrows():
                color = "#E74C3C" if "BAHAYA" in row['Status'] else ("#F39C12" if "SIAGA" in row['Status'] else "#2ECC71")
                with cols[i % len(cols)]:
                    st.markdown(f'<div style="background-color:rgba(44, 62, 80, 0.6); padding:15px; border-radius:10px; border-top: 5px solid {color}; text-align:center;"><small>{row["Area"]}</small><h2 style="margin:0;">{row["Jumlah_Kasus"]}</h2><small>{row["Status"]}</small></div>', unsafe_allow_html=True)
        
        st.divider()
        col_c, col_p = st.columns([2, 1])
        with col_c:
            st.subheader("📈 Tren Kasus CM Bulanan")
            trend_df['Tgl'] = trend_df['Tanggal'].dt.strftime('%b %Y')
            st.plotly_chart(px.line(trend_df, x='Tgl', y='Total', markers=True, template="plotly_dark", title="Historis Kasus CM"), use_container_width=True)
        with col_p:
            st.subheader("🔮 Estimasi AI")
            st.markdown(f'<div class="ai-card"><h1 style="margin:0; font-size: 50px;">{prediction}</h1><p style="color:#3498DB;"><b>Prediksi Kasus Bulan Depan</b></p><small>Berdasarkan regresi linear tren data.</small></div>', unsafe_allow_html=True)
    else: st.info("Data belum mencukupi.")

# ================== HALAMAN: REPORT DATA (DETAIL) ==================
elif menu == "Report Data":
    st.header("Integrated Data & Report")
    with st.container(border=True):
        st.subheader("Filter & Edit Data")
        data_to_edit = df.copy()
        data_to_edit['Hapus'] = False
        
        # Filter Logic
        f_j = st.selectbox("Saring Jenis:", ["Semua"] + JOB_TYPES)
        if f_j != "Semua": data_to_edit = data_to_edit[data_to_edit['Jenis'] == f_j]
        
        # Editor
        edited_df = st.data_editor(data_to_edit, use_container_width=True, key="report_editor")
        
        if st.button("💾 Simpan Perubahan"):
            changes = st.session_state.report_editor.get("edited_rows", {})
            for idx, payload in changes.items():
                orig_id = data_to_edit.iloc[idx]['ID']
                if 'Nama Personel' in payload: payload['Nama Pelaksana'] = payload.pop('Nama Personel')
                supabase.table("jobs").update(payload).eq("ID", orig_id).execute()
            st.cache_data.clear()
            st.session_state.data = load_data_from_db()
            st.success("Tersimpan!")
            st.rerun()

    # Update Status Section
    with st.expander("✅ Update Cepat Status Selesai"):
        open_list = df[df['Status'] != 'Finish']
        if not open_list.empty:
            sel_job = st.selectbox("Pilih Pekerjaan", open_list['ID'].tolist())
            up_ev = st.file_uploader("Upload Evidence After", type=["png", "jpg", "jpeg"])
            if st.button("Update Jadi Finish"):
                url_a = upload_image_to_storage(up_ev)
                supabase.table("jobs").update({"Status": "Finish", "Evidance After": url_a}).eq("ID", sel_job).execute()
                st.cache_data.clear()
                st.rerun()

    # Export Section
    st.divider()
    st.subheader("📄 Unduh Laporan")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("📊 Siapkan Excel"):
            st.download_button("Download Excel", create_excel_report_with_images(df), "laporan.xlsx")
    with col_d2:
        if st.button("📄 Siapkan PDF"):
            st.download_button("Download PDF", create_pdf_report(df, "Semua"), "laporan.pdf")

# ================== HALAMAN: ANALISIS FLM (FULL) ==================
elif menu == "Analisis FLM":
    st.header("📊 Analisis FLM (Scoreboard)")
    df_flm = df[df['Jenis'].str.startswith('First Line Maintenance', na=False)]
    if not df_flm.empty:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.plotly_chart(px.pie(df_flm, names='Jenis', hole=0.4, title="Proporsi FLM", template="plotly_dark"), use_container_width=True)
        with col_m2:
            st.plotly_chart(px.bar(df_flm['Area'].value_counts().reset_index(), x='count', y='Area', orientation='h', title="FLM per Area", template="plotly_dark"), use_container_width=True)
            
        st.subheader("🏆 Leaderboard Personel FLM")
        scores = df_flm['Nama Personel'].str.split(',').explode().str.strip().value_counts().reset_index()
        scores.columns = ['Nama', 'Jumlah']
        st.plotly_chart(px.bar(scores, x='Jumlah', y='Nama', orientation='h', color='Jumlah', template="plotly_dark"), use_container_width=True)

# ================== HALAMAN: ABSENSI (FULL) ==================
elif menu == "Absensi Personel":
    st.header("🗓️ Dashboard & Input Absensi")
    df_p = load_personnel_data()
    p_list = df_p['nama'].tolist() if not df_p.empty else []
    
    if user_role == 'admin':
        with st.expander("📝 Input Absensi Massal (Hadir)"):
            with st.form("abs_m"):
                sel_p = st.multiselect("Pilih Personel Hadir", p_list, default=p_list)
                tgl = st.date_input("Tanggal", date.today())
                if st.form_submit_button("Simpan"):
                    recs = [{"tanggal": str(tgl), "nama_personel": n, "status_absensi": "Hadir"} for n in sel_p]
                    supabase.table("absensi").upsert(recs, on_conflict="tanggal,nama_personel").execute()
                    st.cache_data.clear()
                    st.success("Tersimpan!")
                    st.rerun()

    st.divider()
    df_abs = load_absensi_data()
    if not df_abs.empty:
        st.subheader("Peringkat Kehadiran")
        st.plotly_chart(px.bar(df_abs[df_abs['status_absensi']=='Hadir']['nama_personel'].value_counts().reset_index(), x='count', y='nama_personel', orientation='h', template="plotly_dark"), use_container_width=True)

# ================== HALAMAN: KELOLA PERSONEL ==================
elif menu == "Kelola Personel" and user_role == 'admin':
    st.header("👥 Kelola Daftar Personel")
    with st.form("add_p"):
        n_p = st.text_input("Nama Personel Baru")
        if st.form_submit_button("Tambah"):
            supabase.table("personel").insert({"nama": n_p}).execute()
            st.cache_data.clear()
            st.rerun()
    
    st.subheader("Daftar Aktif")
    st.dataframe(load_personnel_data(), use_container_width=True)

st.markdown("---"); st.caption("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")
