# APLIKASI PRODUKSI LENGKAP - ARMOR (VERSION: FULL RESTORE + SORTED ANALYSYS)
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
        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div {
            background-color: rgba(236, 240, 241, 0.4) !important;
            border-color: rgba(52, 152, 219, 0.4) !important;
            color: #FFFFFF !important;
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
    except Exception as e:
        st.error(f"Gagal memuat data: {e}")
        return pd.DataFrame()

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
            if exif[orientation] in actions: image = image.rotate(actions[exif[orientation]], expand=True)
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
    elements = []
    
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

# ================== Logika Login ==================
if "logged_in" not in st.session_state: st.session_state.logged_in = False

if not st.session_state.get("logged_in"):
    col1, col2, col3 = st.columns([1,1.5,1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="login-title">ARMOR</h1>', unsafe_allow_html=True)
        try: st.image("logo.png", width=150)
        except FileNotFoundError: pass
        with st.form("login_form"):
            st.markdown('<h3 style="color: #FFFFFF; text-align: center;">User Login</h3>', unsafe_allow_html=True)
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

# ================== Sesi & Sidebar ==================
user_role = st.session_state.get("user_role", "operator")
if 'last_activity' not in st.session_state or datetime.now() - st.session_state.last_activity > timedelta(minutes=30): logout()
st.session_state.last_activity = datetime.now()

if 'data' not in st.session_state: st.session_state.data = load_data_from_db()
df = st.session_state.data.copy()
if 'Nama Pelaksana' in df.columns: df.rename(columns={'Nama Pelaksana': 'Nama Personel'}, inplace=True)

with st.sidebar:
    st.title("Menu Navigasi")
    st.write(f"Halo, **{st.session_state.get('user_email', 'User')}**!")
    try: st.image("logo.png", use_container_width=True)
    except FileNotFoundError: pass
    menu_options = ["Input Data", "Report Data", "Analisis FLM", "Absensi Personel"]
    if user_role == 'admin': menu_options.append("Kelola Personel")
    menu = st.radio("Halaman:", menu_options, label_visibility="collapsed")
    if st.button("Logout"): logout()
    st.markdown("---"); st.caption("Tim Operasi - PLTU Bangka 🛠️")

# ================== Halaman: Input Data ==================
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
        
        c_ev1, c_ev2 = st.columns(2)
        with c_ev1: ev_before = st.file_uploader("Evidence Before", type=["png", "jpg", "jpeg"])
        with c_ev2: ev_after = st.file_uploader("Evidence After", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("Simpan Data"):
            if not all([nomor_sr, nama_personel, keterangan]): st.error("Lengkapi data.")
            else:
                with st.spinner("Menyimpan..."):
                    new_id = generate_next_id(df, jenis)
                    u1 = upload_image_to_storage(ev_before)
                    u2 = upload_image_to_storage(ev_after)
                    payload = {"ID": new_id, "Tanggal": str(tanggal), "Jenis": jenis, "Area": area, "Nomor SR": nomor_sr, "Nama Pelaksana": nama_personel, "Keterangan": keterangan, "Status": status, "Evidance": u1, "Evidance After": u2}
                    supabase.table("jobs").insert(payload).execute()
                    st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.success(f"Data tersimpan: {new_id}"); st.rerun()

# ================== Halaman: Report Data (RESTORED KODE AWAL) ==================
elif menu == "Report Data":
    st.header("Integrated Data & Report")
    with st.container(border=True):
        st.subheader("Filter & Edit Data")
        data_to_display = df.copy()
        if 'Hapus' not in data_to_display.columns: data_to_display['Hapus'] = False
        
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            all_jenis = ["Semua"] + sorted(list(data_to_display["Jenis"].dropna().unique()))
            filter_jenis = st.selectbox("Saring berdasarkan Jenis:", all_jenis)
        with filter_col2:
            all_status = ["Semua"] + sorted(list(data_to_display["Status"].dropna().unique()))
            filter_status = st.selectbox("Saring berdasarkan Status:", all_status)
        
        if filter_jenis != "Semua": data_to_display = data_to_display[data_to_display["Jenis"] == filter_jenis]
        if filter_status != "Semua": data_to_display = data_to_display[data_to_display["Status"] == filter_status]
        
        col_config_dict = {
            "Hapus": st.column_config.CheckboxColumn("Hapus?"), 
            "ID": st.column_config.TextColumn("ID", disabled=True),
            "Tanggal": st.column_config.DateColumn("Tanggal", format="DD-MM-YYYY", disabled=True),
            "Jenis": st.column_config.SelectboxColumn("Jenis", options=JOB_TYPES, disabled=False if user_role == 'admin' else True),
            "Area": st.column_config.SelectboxColumn("Area", options=["Boiler", "Turbine", "CHCB", "WTP", "Common"], disabled=False if user_role == 'admin' else True),
            "Status": st.column_config.SelectboxColumn("Status", options=["Finish", "On Progress", "Pending", "Open"], disabled=True),
            "Evidance": st.column_config.LinkColumn("Evidence Before", display_text="Lihat"),
            "Evidance After": st.column_config.LinkColumn("Evidence After", display_text="Lihat"),
        }
        
        edited_df = st.data_editor(data_to_display, key="data_editor", use_container_width=True, column_config=col_config_dict,
                                   column_order=["Hapus", "ID", "Tanggal", "Jenis", "Area", "Status", "Nomor SR", "Nama Personel", "Keterangan", "Evidance", "Evidance After"])
        
        if st.session_state.get("data_editor") and st.session_state["data_editor"]["edited_rows"] and user_role == 'admin':
            if st.button("💾 Simpan Perubahan Data"):
                for idx, changes in st.session_state["data_editor"]["edited_rows"].items():
                    orig_id = data_to_display.iloc[idx]['ID']
                    if 'Nama Personel' in changes: changes['Nama Pelaksana'] = changes.pop('Nama Personel')
                    supabase.table("jobs").update(changes).eq("ID", orig_id).execute()
                st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.rerun()

        # Tombol Hapus Terpilih
        rows_to_delete = edited_df[edited_df['Hapus'] == True]
        if not rows_to_delete.empty and user_role == 'admin':
            st.markdown('<div class="delete-button">', unsafe_allow_html=True)
            if st.button(f"🗑️ Hapus ({len(rows_to_delete)}) Baris Terpilih"):
                ids_del = rows_to_delete['ID'].tolist()
                supabase.table("jobs").delete().in_("ID", ids_del).execute()
                st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Quick Update Status Expander
    st.write("---")
    col_func1, col_func2 = st.columns([2, 1])
    with col_func1:
        with st.expander("✅ **Update Status Pekerjaan**", expanded=True):
            open_jobs = df[df['Status'].isin(['Open', 'On Progress'])]
            if not open_jobs.empty:
                job_opts = {f"{row['ID']} - {row['Nama Personel']} - {str(row.get('Keterangan',''))[:40]}...": row['ID'] for _, row in open_jobs.iterrows()}
                sel_job = st.selectbox("Pilih Pekerjaan:", list(job_opts.keys()))
                up_ev_after = st.file_uploader("Upload Bukti Selesai", type=["png", "jpg", "jpeg"])
                if st.button("Submit Update"):
                    if up_ev_after:
                        new_url = upload_image_to_storage(up_ev_after)
                        supabase.table("jobs").update({"Status": "Finish", "Evidance After": new_url}).eq("ID", job_opts[sel_job]).execute()
                        st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.success("Update Berhasil"); st.rerun()
            else: st.info("Tidak ada pekerjaan Open.")
    with col_func2:
        if st.button("🔄 Refresh Data Tabel"): st.cache_data.clear(); st.session_state.data = load_data_from_db(); st.rerun()

    # Laporan Unduhan
    with st.container(border=True):
        st.subheader("📄 Unduh Laporan")
        if not df.empty:
            df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
            c_r1, c_r2, c_r3 = st.columns(3)
            with c_r1: s_date_rep = st.date_input("Dari", df['Tanggal'].min().date())
            with c_r2: e_date_rep = st.date_input("Sampai", date.today())
            with c_r3: type_rep = st.selectbox("Jenis Laporan", ["Semua"] + JOB_TYPES)
            
            mask_rep = (df['Tanggal'].dt.date >= s_date_rep) & (df['Tanggal'].dt.date <= e_date_rep)
            if type_rep != "Semua": mask_rep &= (df["Jenis"] == type_rep)
            filtered_rep = df[mask_rep]
            
            cd1, cd2 = st.columns(2)
            with cd1:
                if st.button("📊 Siapkan Excel"): st.session_state.ex_b = create_excel_report_with_images(filtered_rep)
                if 'ex_b' in st.session_state: st.download_button("⬇️ Download Excel", st.session_state.ex_b, "laporan.xlsx")
            with cd2:
                if st.button("📄 Siapkan PDF"): st.session_state.pd_b = create_pdf_report(filtered_rep, type_rep)
                if 'pd_b' in st.session_state: st.download_button("⬇️ Download PDF", st.session_state.pd_b, "laporan.pdf")

# ================== Halaman: Analisis FLM (SORTED) ==================
elif menu == "Analisis FLM":
    st.header("📊 Analisis FLM & Kerusakan")
    if df.empty: st.info("Data tidak tersedia.")
    else:
        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.tz_localize(None)
        st.sidebar.subheader("Filter Dashboard")
        s_date_flm = st.sidebar.date_input("Mulai", df['Tanggal'].min().date())
        e_date_flm = st.sidebar.date_input("Selesai", date.today())
        
        mask_flm = (df['Tanggal'].dt.date >= s_date_flm) & (df['Tanggal'].dt.date <= e_date_flm) & (df['Jenis'].str.startswith('First Line', na=False))
        df_flm = df[mask_flm]
        
        if not df_flm.empty:
            st.header("🏆 Skor Personel FLM")
            p_cnt = df_flm['Nama Personel'].str.split(',').explode().str.strip().value_counts().reset_index()
            p_cnt.columns = ['Nama', 'Total']
            fig_p = px.bar(p_cnt, x='Total', y='Nama', orientation='h', title='Leaderboard Personel', color='Total', template='plotly_dark')
            fig_p.update_yaxes(categoryorder='total ascending') # TERTINGGI DI ATAS
            st.plotly_chart(fig_p, use_container_width=True)

            st.markdown("---")
            st.header("📍 Scoreboard Area & Peralatan (FLM)")
            ca1, ca2 = st.columns(2)
            with ca1:
                area_cnt = df_flm['Area'].value_counts().reset_index()
                area_cnt.columns = ['Area', 'Jumlah']
                fig_area = px.bar(area_cnt, x='Jumlah', y='Area', orientation='h', title='Frekuensi FLM per Area', template='plotly_dark', color='Jumlah')
                fig_area.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_area, use_container_width=True)
            with ca2:
                eq_cnt = df_flm['Keterangan'].value_counts().nlargest(10).reset_index()
                eq_cnt.columns = ['Peralatan', 'Frekuensi']
                fig_eq = px.bar(eq_cnt, x='Frekuensi', y='Peralatan', orientation='h', title='10 Alat Sering Dirawat', template='plotly_dark', color='Frekuensi')
                fig_eq.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_eq, use_container_width=True)

            st.markdown("---")
            st.header("🛠️ Analisis Kerusakan (Corrective Maintenance)")
            df_cm = df[(df['Tanggal'].dt.date >= s_date_flm) & (df['Tanggal'].dt.date <= e_date_flm) & (df['Jenis'] == 'Corrective Maintenance')]
            if not df_cm.empty:
                cm_area = df_cm['Area'].value_counts().reset_index()
                cm_area.columns = ['Area', 'Kasus']
                fig_cm = px.bar(cm_area, x='Kasus', y='Area', orientation='h', title='Area Dominan Gangguan (CM)', color='Kasus', color_continuous_scale='Reds', template='plotly_dark')
                fig_cm.update_yaxes(categoryorder='total ascending')
                st.plotly_chart(fig_cm, use_container_width=True)

# ================== Halaman: Absensi Personel (SORTED & COMPLETE) ==================
elif menu == "Absensi Personel":
    st.header("🗓️ Dashboard Absensi")
    df_personnel = load_personnel_data()
    pers_list = df_personnel['nama'].tolist() if not df_personnel.empty else []

    if user_role == 'admin':
        with st.expander("✅ Input Absensi Massal (Hadir)", expanded=True):
            with st.form("mass_abs"):
                c1, c2 = st.columns([3, 1])
                with c1: sel_pers = st.multiselect("Pilih Personel Hadir:", options=pers_list, default=pers_list)
                with c2: tgl_m = st.date_input("Tanggal", date.today())
                if st.form_submit_button("Simpan Massal"):
                    records = [{"tanggal": str(tgl_m), "nama_personel": n, "status_absensi": "Hadir", "keterangan": ""} for n in sel_pers]
                    supabase.table("absensi").upsert(records, on_conflict="tanggal,nama_personel").execute()
                    st.cache_data.clear(); st.rerun()

    st.markdown("---")
    df_absensi = load_absensi_data()
    if not df_absensi.empty:
        df_absensi['tanggal'] = pd.to_datetime(df_absensi['tanggal']).dt.tz_localize(None)
        c_y, c_m = st.columns(2)
        with c_y: sel_year = st.selectbox("Tahun:", sorted(df_absensi['tanggal'].dt.year.unique(), reverse=True))
        with c_m: 
            month_dict = {1:"Januari",2:"Februari",3:"Maret",4:"April",5:"Mei",6:"Juni",7:"Juli",8:"Agustus",9:"September",10:"Oktober",11:"November",12:"Desember"}
            sel_month_str = st.selectbox("Bulan:", ["Semua Bulan"] + list(month_dict.values()))
        
        mask_abs = (df_absensi['tanggal'].dt.year == sel_year)
        if sel_month_str != "Semua Bulan":
            sel_month_num = [k for k, v in month_dict.items() if v == sel_month_str][0]
            mask_abs &= (df_absensi['tanggal'].dt.month == sel_month_num)
        
        f_abs = df_absensi[mask_abs]
        if not f_abs.empty:
            df_hadir = f_abs[f_abs['status_absensi'] == 'Hadir']
            df_absen = f_abs[f_abs['status_absensi'] != 'Hadir']
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.subheader("✅ Peringkat Kehadiran")
                if not df_hadir.empty:
                    h_counts = df_hadir['nama_personel'].value_counts().reset_index()
                    h_counts.columns = ['Nama', 'Hari']
                    fig_h = px.bar(h_counts, x='Hari', y='Nama', orientation='h', title='Top Kehadiran', color='Hari', color_continuous_scale='Greens', template='plotly_dark')
                    fig_h.update_yaxes(categoryorder='total ascending')
                    st.plotly_chart(fig_h, use_container_width=True)
            with col_chart2:
                st.subheader("❌ Peringkat Ketidakhadiran")
                if not df_absen.empty:
                    a_counts = df_absen.groupby(['nama_personel', 'status_absensi']).size().reset_index(name='Jumlah')
                    fig_a = px.bar(a_counts, x='Jumlah', y='nama_personel', color='status_absensi', orientation='h', title='Detail Ketidakhadiran', template='plotly_dark', barmode='stack')
                    fig_a.update_yaxes(categoryorder='total ascending')
                    st.plotly_chart(fig_a, use_container_width=True)
            st.dataframe(f_abs[['tanggal', 'nama_personel', 'status_absensi', 'keterangan']], use_container_width=True)

# ================== Halaman: Kelola Personel ==================
elif menu == "Kelola Personel" and user_role == 'admin':
    st.header("👥 Kelola Personel")
    df_p = load_personnel_data()
    with st.form("add_p"):
        n_p = st.text_input("Nama Personel Baru")
        if st.form_submit_button("Simpan"):
            supabase.table("personel").insert({"nama": n_p}).execute()
            st.cache_data.clear(); st.rerun()
    if not df_p.empty:
        df_p['Hapus'] = False
        ed_p = st.data_editor(df_p, use_container_width=True)
        if st.button("🗑️ Hapus Terpilih"):
            to_del = ed_p[ed_p['Hapus']]['id'].tolist()
            supabase.table("personel").delete().in_("id", to_del).execute()
            st.cache_data.clear(); st.rerun()
