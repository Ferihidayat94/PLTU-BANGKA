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
        
        div[data-baseweb="input"] > div, 
        div[data-baseweb="textarea"] > div, 
        div[data-baseweb="select"] > div {
            background-color: rgba(236, 240, 241, 0.4) !important;
            border-color: rgba(52, 152, 219, 0.4) !important;
            color: #FFFFFF !important;
            transition: all 0.2s ease-in-out;
        }
        label, div[data-testid="stWidgetLabel"] label { color: #FFFFFF !important; font-weight: 500; }
        [data-testid="stMetricLabel"] { color: #A9C5E1 !important; }
        [data-testid="stMetricValue"] { color: #FFFFFF !important; }
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

# ================== Fungsi-Fungsi Helper ==================
def verify_user_and_get_role(email, password):
    try:
        session = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if session.user:
            role = session.user.user_metadata.get('role', 'operator')
            return {"role": role, "email": session.user.email}
    except Exception as e:
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
        st.error(f"Gagal mengambil data pekerjaan: {e}")
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
        return pd.DataFrame()

@st.cache_data(ttl=300)
def load_personnel_data():
    try:
        response = supabase.table('personel').select('id, nama').order('nama', desc=False).execute()
        return pd.DataFrame(response.data)
    except Exception:
        return pd.DataFrame(columns=['id', 'nama'])

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
            for col_idx, url_key in [(image_col_before, "Evidance"), (image_col_after, "Evidance After")]:
                img_url = row_data.get(url_key)
                if img_url and isinstance(img_url, str) and col_idx != -1:
                    try:
                        response = requests.get(img_url, stream=True, timeout=10)
                        img_data = io.BytesIO(response.content)
                        img = Image.open(img_data).convert("RGB")
                        img = fix_image_orientation(img)
                        img.thumbnail((120, 90))
                        resized_img_buffer = io.BytesIO()
                        img.save(resized_img_buffer, format="JPEG", quality=80)
                        worksheet.insert_image(excel_row, col_idx, "img.jpg", {'image_data': resized_img_buffer, 'x_offset': 5, 'y_offset': 5, 'object_position': 3})
                    except Exception: pass
    output.seek(0)
    return output.getvalue()

def create_pdf_report(filtered_data, report_type):
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=30)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', alignment=TA_CENTER, fontSize=14, leading=20, spaceAfter=10, spaceBefore=10, textColor=colors.HexColor('#2C3E50')))
    styles.add(ParagraphStyle(name='Header', alignment=TA_LEFT, textColor=colors.HexColor('#2C3E50')))
    elements = []
    
    # Logo di PDF
    try:
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            header_text = "<b>PT PLN NUSANTARA POWER SERVICES</b><br/>Unit PLTU Bangka"
            logo_img = RLImage(logo_path, width=0.9*inch, height=0.4*inch, hAlign='LEFT')
            header_table = Table([[logo_img, Paragraph(header_text, styles['Header'])]], colWidths=[1*inch, 6*inch])
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
            ["Nama Personel", str(row.get('Nama Personel', ''))],
            ["Status", str(row.get('Status', ''))],
            ["Keterangan", Paragraph(str(row.get('Keterangan', '')).replace('\n', '<br/>'), styles['Normal'])],
        ]
        table = Table(data, colWidths=[100, 380], style=[
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ECF0F1')), ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#BDC3C7')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BDC3C7')), ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ])
        elements.append(table)
        
        img1, img2 = None, None
        for img_url, pos in [(row.get("Evidance"), 1), (row.get("Evidance After"), 2)]:
            if img_url and isinstance(img_url, str):
                try:
                    resp = requests.get(img_url, stream=True, timeout=10)
                    img_data = io.BytesIO(resp.content)
                    image_element = RLImage(img_data, width=3*inch, height=2.25*inch, kind='bound')
                    if pos == 1: img1 = image_element
                    else: img2 = image_element
                except Exception: pass
        
        if img1 or img2:
            elements.append(Spacer(1, 5))
            image_table = Table([[Paragraph("<b>Evidence Before:</b>", styles['Normal']), Paragraph("<b>Evidence After:</b>", styles['Normal'])], [img1, img2]], colWidths=[3.2*inch, 3.2*inch])
            elements.append(image_table)
        elements.append(PageBreak())

    doc.build(elements)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

# ================== Logika Login (LOGO DIKEMBALIKAN) ==================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.get("logged_in"):
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">ARMOR</h1>', unsafe_allow_html=True)
        # --- LOGO LOGIN ---
        try: st.image("logo.png", width=150)
        except FileNotFoundError: pass
        
        with st.form("login_form"):
            st.markdown('<h3 style="color: #FFFFFF; text-align: center; border-bottom: none;">User Login</h3>', unsafe_allow_html=True)
            email = st.text_input("Email", placeholder="e.g., admin@example.com").lower()
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user_data = verify_user_and_get_role(email, password)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user_data['email']
                    st.session_state.user_role = user_data['role']
                    st.session_state.last_activity = datetime.now()
                    st.rerun()
                else: st.error("Email atau password salah.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ================== Inisialisasi Data & Sidebar (LOGO DIKEMBALIKAN) ==================
user_role = st.session_state.get("user_role", "operator")
if 'last_activity' not in st.session_state or datetime.now() - st.session_state.last_activity > timedelta(minutes=30): logout()
st.session_state.last_activity = datetime.now()

if 'data' not in st.session_state: st.session_state.data = load_data_from_db()
df = st.session_state.data.copy()
if 'Nama Pelaksana' in df.columns: df.rename(columns={'Nama Pelaksana': 'Nama Personel'}, inplace=True)

with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"Selamat datang, **{st.session_state.get('user_email', 'Guest')}**!")
    st.write(f"Peran: **{user_role.capitalize()}**")
    # --- LOGO SIDEBAR ---
    try: st.image("logo.png", use_container_width=True)
    except FileNotFoundError: pass
    
    menu_options = ["Input Data", "Report Data", "Analisis FLM", "Absensi Personel"]
    if user_role == 'admin': menu_options.append("Kelola Personel")
    menu = st.radio("Pilih Halaman:", menu_options, label_visibility="collapsed")
    if st.button("Logout"): logout()
    st.markdown("---"); st.caption("Dibuat oleh Tim Operasi - PLTU Bangka 🛠️")

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
            nama_personel = st.text_input("Nama Personel")
            status = st.selectbox("Status", ["Finish", "On Progress", "Pending", "Open"])
            keterangan = st.text_area("Keterangan / Uraian Pekerjaan")
        
        st.subheader("Upload Bukti Pekerjaan (Evidence)")
        col_ev1, col_ev2 = st.columns(2)
        with col_ev1: evidance_file = st.file_uploader("Upload Evidence (Before)", type=["png", "jpg", "jpeg"])
        with col_ev2: evidance_after_file = st.file_uploader("Upload Evidence (After)", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Simpan Data"):
            if not all([nomor_sr, nama_personel, keterangan]): st.error("Mohon isi semua field.")
            else:
                with st.spinner("Menyimpan..."):
                    new_id = generate_next_id(df, jenis)
                    u1 = upload_image_to_storage(evidance_file)
                    u2 = upload_image_to_storage(evidance_after_file)
                    payload = {"ID": new_id, "Tanggal": str(tanggal), "Jenis": jenis, "Area": area, "Nomor SR": nomor_sr, "Nama Pelaksana": nama_personel, "Keterangan": keterangan, "Status": status, "Evidance": u1, "Evidance After": u2}
                    supabase.table("jobs").insert(payload).execute()
                    st.cache_data.clear(); st.session_state.data = load_data_from_db()
                    st.success(f"Data '{new_id}' tersimpan!"); st.rerun()

elif menu == "Report Data":
    st.header("Integrated Data & Report")
    data_to_display = df.copy()
    if 'Hapus' not in data_to_display.columns: data_to_display['Hapus'] = False
    
    col_config_dict = {
        "Hapus": st.column_config.CheckboxColumn("Hapus?"), 
        "ID": st.column_config.TextColumn("ID", disabled=True),
        "Tanggal": st.column_config.DateColumn("Tanggal", format="DD-MM-YYYY", disabled=True),
        "Evidance": st.column_config.LinkColumn("Evidence Before", display_text="Lihat"),
        "Evidance After": st.column_config.LinkColumn("Evidence After", display_text="Lihat"),
    }
    
    edited_df = st.data_editor(data_to_display, key="data_editor", use_container_width=True, column_config=col_config_dict)
    
    if st.button("💾 Simpan Perubahan Data") and user_role == 'admin':
        changes = st.session_state.data_editor.get("edited_rows", {})
        for idx, val in changes.items():
            orig_id = data_to_display.iloc[idx]['ID']
            if 'Nama Personel' in val: val['Nama Pelaksana'] = val.pop('Nama Personel')
            supabase.table("jobs").update(val).eq("ID", orig_id).execute()
        st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.rerun()

    # Laporan
    with st.container(border=True):
        st.subheader("📄 Unduh Laporan")
        c_dl1, c_dl2 = st.columns(2)
        with c_dl1:
            if st.button("📊 Siapkan Excel"): st.session_state.ex_b = create_excel_report_with_images(data_to_display)
            if 'ex_b' in st.session_state: st.download_button("⬇️ Download Excel", st.session_state.ex_b, "laporan.xlsx")
        with c_dl2:
            if st.button("📄 Siapkan PDF"): st.session_state.pd_b = create_pdf_report(data_to_display, "Report")
            if 'pd_b' in st.session_state: st.download_button("⬇️ Download PDF", st.session_state.pd_b, "laporan.pdf")

# ================== Halaman: Analisis FLM (DENGAN SCOREBOARD AREA & CM) ==================
elif menu == "Analisis FLM":
    st.header("📊 Analisis FLM (Scoreboard)")
    if df.empty: st.info("Data tidak tersedia.")
    else:
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
        st.sidebar.subheader("Filter Analisis")
        s_date = st.sidebar.date_input("Mulai", df['Tanggal'].min().date())
        e_date = st.sidebar.date_input("Selesai", date.today())
        
        mask_flm = (df['Tanggal'].dt.date >= s_date) & (df['Tanggal'].dt.date <= e_date) & (df['Jenis'].str.startswith('First Line', na=False))
        df_flm = df[mask_flm]
        
        if not df_flm.empty:
            flm_c = df_flm['Jenis'].value_counts().reset_index()
            flm_c.columns = ['Jenis', 'Jumlah']
            
            # KPI
            st.markdown("### Ringkasan Dominasi FLM")
            ck1, ck2, ck3 = st.columns(3)
            ck1.metric("Total Pelaksanaan", f"{flm_c['Jumlah'].sum()} Kali")
            ck2.metric("FLM Dominan", flm_c.iloc[0]['Jenis'].replace("First Line Maintenance ", ""))
            ck3.metric("Personel Terlibat", f"{df_flm['Nama Personel'].nunique()} Orang")

            ch_col1, ch_col2 = st.columns(2)
            with ch_col1: st.plotly_chart(px.pie(flm_c, names='Jenis', values='Jumlah', hole=0.4, title='Proporsi FLM', template='plotly_dark'), use_container_width=True)
            with ch_col2: st.plotly_chart(px.bar(flm_c, x='Jumlah', y='Jenis', orientation='h', title='Peringkat FLM', template='plotly_dark'), use_container_width=True)

            # Leaderboard
            st.markdown("---")
            st.header("🏆 Skor Personel FLM")
            p_cnt = df_flm['Nama Personel'].str.split(',').explode().str.strip().value_counts().reset_index()
            p_cnt.columns = ['Nama', 'Total']
            st.plotly_chart(px.bar(p_cnt, x='Total', y='Nama', orientation='h', title='Leaderboard Personel', color='Total', template='plotly_dark'), use_container_width=True)

            # ==============================================================================
            # TAMBAHAN BARU: SCOREBOARD AREA & PERALATAN FLM
            # ==============================================================================
            st.markdown("---")
            st.header("📍 Scoreboard Area & Peralatan (FLM)")
            col_area1, col_area2 = st.columns(2)
            with col_area1:
                st.subheader("Dominasi FLM per Area")
                area_cnt = df_flm['Area'].value_counts().reset_index()
                area_cnt.columns = ['Area', 'Jumlah']
                st.plotly_chart(px.bar(area_cnt, x='Area', y='Jumlah', color='Jumlah', title='Frekuensi per Area', template='plotly_dark', text_auto=True), use_container_width=True)
            with col_area2:
                st.subheader("Top Peralatan Tersering (FLM)")
                eq_cnt = df_flm['Keterangan'].value_counts().nlargest(10).reset_index()
                eq_cnt.columns = ['Peralatan', 'Frekuensi']
                st.plotly_chart(px.bar(eq_cnt, x='Frekuensi', y='Peralatan', orientation='h', title='10 Alat Sering Dirawat', template='plotly_dark', color='Frekuensi'), use_container_width=True)

            # ==============================================================================
            # TAMBAHAN BARU: SCOREBOARD KERUSAKAN (CM)
            # ==============================================================================
            st.markdown("---")
            st.header("🛠️ Analisis Kerusakan (Corrective Maintenance)")
            df_cm = df[(df['Tanggal'].dt.date >= s_date) & (df['Tanggal'].dt.date <= e_date) & (df['Jenis'] == 'Corrective Maintenance')]
            if df_cm.empty: st.info("Tidak ada data CM pada periode ini.")
            else:
                col_cm1, col_cm2 = st.columns([1, 2])
                with col_cm1:
                    cm_area = df_cm['Area'].value_counts().reset_index()
                    cm_area.columns = ['Area', 'Kasus']
                    st.metric("Total Kasus Kerusakan", f"{len(df_cm)} CM")
                    st.plotly_chart(px.pie(cm_area, names='Area', values='Kasus', title='Proporsi Kasus CM', hole=0.3, template='plotly_dark', color_discrete_sequence=px.colors.sequential.Reds_r), use_container_width=True)
                with col_cm2:
                    st.plotly_chart(px.bar(cm_area, x='Kasus', y='Area', orientation='h', title='Area Dominan Gangguan', color='Kasus', color_continuous_scale='Reds', template='plotly_dark'), use_container_width=True)

# ================== Halaman: Absensi (VERSI LENGKAP) ==================
elif menu == "Absensi Personel":
    st.header("🗓️ Input & Dashboard Absensi")
    df_personnel = load_personnel_data()
    pers_list = df_personnel['nama'].tolist() if not df_personnel.empty else []

    if user_role == 'admin':
        with st.expander("✅ Input Absensi Massal (Hadir)", expanded=True):
            with st.form("mass_abs"):
                c_m1, c_m2 = st.columns([3, 1])
                with c_m1: sel_pers = st.multiselect("Pilih Personel:", pers_list, default=pers_list)
                with c_m2: tgl_m = st.date_input("Tanggal", date.today())
                if st.form_submit_button("Simpan Massal"):
                    payload_abs = [{"tanggal": str(tgl_m), "nama_personel": n, "status_absensi": "Hadir", "keterangan": ""} for n in sel_pers]
                    supabase.table("absensi").upsert(payload_abs, on_conflict="tanggal,nama_personel").execute()
                    st.cache_data.clear(); st.success("Data Tersimpan"); st.rerun()

    st.markdown("---")
    df_absensi = load_absensi_data()
    if not df_absensi.empty:
        st.subheader("📊 Laporan Kehadiran")
        abs_count = df_absensi[df_absensi['status_absensi']=='Hadir']['nama_personel'].value_counts().reset_index()
        abs_count.columns = ['Nama', 'Hadir']
        st.plotly_chart(px.bar(abs_count, x='Hadir', y='Nama', orientation='h', title="Top Kehadiran", template='plotly_dark', color='Hadir'), use_container_width=True)
        st.dataframe(df_absensi, use_container_width=True)

# ================== Halaman: Kelola Personel ==================
elif menu == "Kelola Personel" and user_role == 'admin':
    st.header("👥 Kelola Personel")
    df_p = load_personnel_data()
    with st.expander("Tambah Personel Baru"):
        with st.form("add_p"):
            new_name = st.text_input("Nama Lengkap")
            if st.form_submit_button("Simpan"):
                supabase.table("personel").insert({"nama": new_name}).execute()
                st.cache_data.clear(); st.success("Personel ditambahkan"); st.rerun()
    
    df_p['Hapus'] = False
    ed_p = st.data_editor(df_p, use_container_width=True)
    if st.button("🗑️ Hapus Terpilih"):
        ids_del = ed_p[ed_p['Hapus']]['id'].tolist()
        supabase.table("personel").delete().in_("id", ids_del).execute()
        st.cache_data.clear(); st.rerun()
