import html
import re
from datetime import date, timedelta
from urllib.parse import quote

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Monitoring Setoran Omset",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =====================================================
# KONFIGURASI
# =====================================================
SHEET_ID = "1bCvWOsmBIr568kzoNed3gzmPk8EnCAXwE0umdeDj5D4"
SHEET_NAME = "Data Setoran"
MASTER_SHEET_NAME = "Master Store"

COL_STORE = "Store"
COL_TANGGAL = "Tanggal"
COL_CASHIER = "Cashier"
COL_PAGI = "Setoran Pagi"
COL_SIANG = "Setoran Siang"
COL_STATUS_MGR = "Status Mgr"
COL_STATUS_FIN = "Status Finance"

MASTER_COL_KODE = None
MASTER_COL_NAMA = None
STORE_NAMES_MANUAL: dict[str, str] = {}

HARI = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}
BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

# =====================================================
# STYLE CSS (DIPERBARUI UNTUK MOBILE FRIENDLY)
# =====================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', 'Segoe UI', Arial, sans-serif; }
.stApp { background: #F4F6FA; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1280px; }

/* Header / Logo */
.topbar {
  background: linear-gradient(135deg, #0B1F3A 0%, #1A467D 100%);
  border-radius: 16px; padding: 24px 32px; margin-bottom: 20px;
  display: flex; justify-content: space-between; align-items: center;
  box-shadow: 0 4px 15px rgba(11,31,58,0.15);
}
.topbar .brand { display: flex; align-items: center; color: #FFFFFF; font-size: 1.55rem; font-weight: 800; letter-spacing: .2px; }
.topbar .brand .icon { font-size: 2.2rem; margin-right: 18px; background: rgba(255,255,255,0.15); padding: 12px; border-radius: 14px; line-height: 1; backdrop-filter: blur(5px); }
.topbar .brand .texts { display: flex; flex-direction: column; }
.topbar .brand small { color: #A8C5EA; font-size: .88rem; font-weight: 400; margin-top: 4px; }
.topbar .stamp { color: #A8C5EA; font-size: .85rem; text-align: right; }
.topbar .stamp b { color: #FFFFFF; font-weight: 600; font-size: 1rem;}

/* Hero */
.hero {
  background: #FFFFFF; border: 1px solid #E3E8F0; border-left: 6px solid #12335E;
  border-radius: 14px; padding: 26px 30px; margin: 6px 0 16px 0;
  box-shadow: 0 2px 10px rgba(11,31,58,.05);
}
.hero .label { color: #5B6B82; font-size: .78rem; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase; }
.hero .amount { color: #0B1F3A; font-size: 2.9rem; font-weight: 800; line-height: 1.15; margin: 6px 0 8px 0; }
.hero .meta { color: #44546A; font-size: .92rem; }
.hero .meta b { color: #0B1F3A; }
.hero .split { margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap; }

/* Badge */
.badge { display: inline-block; padding: 4px 11px; border-radius: 20px; font-size: .76rem; font-weight: 600; }
.b-ok { background: #E6F4EA; color: #1E7B3A; }
.b-wait { background: #FFF4DE; color: #9A6200; }
.b-miss { background: #FDE8E8; color: #B42318; }
.b-neutral { background: #EAEFF7; color: #26456E; }

/* KPI */
.kpi {
  background: #FFFFFF; border: 1px solid #E3E8F0; border-radius: 12px;
  padding: 16px 18px; box-shadow: 0 1px 6px rgba(11,31,58,.04);
}
.kpi .k { color: #5B6B82; font-size: .74rem; font-weight: 600; letter-spacing: .8px; text-transform: uppercase; }
.kpi .v { color: #0B1F3A; font-size: 1.35rem; font-weight: 700; margin-top: 4px; }

/* Section */
.section-title { color: #0B1F3A; font-size: 1.05rem; font-weight: 700; margin: 22px 0 8px 0; }

/* Table */
.tbl-wrap { background: #FFFFFF; border: 1px solid #E3E8F0; border-radius: 12px; overflow-x: auto; margin-top: 8px; box-shadow: 0 1px 6px rgba(11,31,58,.04); }
table.pro { width: 100%; border-collapse: collapse; font-size: .88rem; }
table.pro th { background: #0B1F3A; color: #FFFFFF; font-weight: 600; text-align: left; padding: 12px 14px; white-space: nowrap; font-size: .8rem; letter-spacing: .3px; }
table.pro th.num, table.pro td.num { text-align: right; font-variant-numeric: tabular-nums; }
table.pro td { padding: 11px 14px; border-bottom: 1px solid #EEF1F6; color: #1F2D3D; }
table.pro tbody tr:nth-child(even) td { background: #F8FAFC; }
table.pro tbody tr:hover td { background: #EEF3FA; }
table.pro td.strong { font-weight: 700; color: #0B1F3A; }
table.pro tr.total td { background: #EAEFF7 !important; font-weight: 700; color: #0B1F3A; border-top: 2px solid #12335E; }

/* Buttons */
.stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {
  background: #FFFFFF; color: #12335E; border: 1px solid #C9D3E3; border-radius: 8px; font-weight: 600; font-size: .85rem; padding: .45rem 1rem; transition: all .15s; width: 100%;
}
.stButton > button:hover, .stDownloadButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
  background: #12335E; color: #FFFFFF; border-color: #12335E;
}
div[data-testid="stFormSubmitButton"] > button { background: #12335E; color: #FFFFFF; border-color: #12335E; }

/* Tabs */
button[data-baseweb="tab"] { font-weight: 600; color: #5B6B82; }
button[data-baseweb="tab"][aria-selected="true"] { color: #0B1F3A; }
div[data-baseweb="tab-highlight"] { background-color: #12335E !important; }

/* Assistant */
.ai-card { background: #FFFFFF; border: 1px solid #E3E8F0; border-radius: 14px; padding: 20px 24px; margin-top: 8px; box-shadow: 0 1px 6px rgba(11,31,58,.04); }
.ai-card .t { color: #0B1F3A; font-weight: 700; font-size: 1.05rem; }
.ai-card .s { color: #5B6B82; font-size: .85rem; margin-bottom: 10px; }
.ai-answer { background: #F4F7FC; border-left: 4px solid #12335E; border-radius: 8px; padding: 14px 18px; color: #1F2D3D; margin-top: 12px; line-height: 1.5; }
.model-info { color: #7B8AA0; font-size: 0.75rem; text-align: right; margin-top: 4px; }

/* Footer */
.footer { text-align: center; color: #7B8AA0; font-size: .8rem; margin-top: 36px; padding-top: 16px; border-top: 1px solid #DCE3EE; }
.footer b { color: #12335E; }

/* ========================================= */
/* PENGATURAN MOBILE RESPONSIVE (HP)         */
/* ========================================= */
@media (max-width: 768px) {
  .block-container { padding-top: 1rem; padding-bottom: 1rem; }
  
  /* Topbar di HP */
  .topbar { flex-direction: column; align-items: flex-start; padding: 18px 20px; }
  .topbar .brand { font-size: 1.25rem; }
  .topbar .brand .icon { font-size: 1.8rem; padding: 10px; margin-right: 14px; }
  .topbar .stamp { text-align: left; margin-top: 12px; font-size: 0.8rem; }
  
  /* Hero di HP */
  .hero { padding: 18px 20px; }
  .hero .amount { font-size: 2.1rem; margin: 4px 0; }
  
  /* KPI di HP */
  .kpi { padding: 12px 14px; margin-bottom: 4px; }
  .kpi .v { font-size: 1.15rem; }
  
  /* Tabel di HP (Agar tidak kebesaran) */
  table.pro th, table.pro td { padding: 8px 10px; font-size: 0.8rem; }
  
  /* AI Card di HP */
  .ai-card { padding: 16px 18px; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# =====================================================
# HELPER
# =====================================================
def esc(x) -> str:
    return html.escape(str(x))

def rp(x) -> str:
    return "Rp " + "{:,.0f}".format(x).replace(",", ".")

def num(x) -> str:
    return "{:,.0f}".format(x).replace(",", ".")

def tgl_id(d: date) -> str:
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"

def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.replace(r"[^\d\-]", "", regex=True), errors="coerce").fillna(0)

def get_secret(name: str, default=None):
    try: return st.secrets[name]
    except Exception: return default

def sheet_url(name: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={quote(name)}"

def html_table(headers, rows, num_cols=(), strong_cols=(), footer=None) -> str:
    th = "".join(f'<th class="{"num" if i in num_cols else ""}">{esc(h)}</th>' for i, h in enumerate(headers))
    body = ""
    for r in rows:
        tds = ""
        for i, v in enumerate(r):
            cls = ("num " if i in num_cols else "") + ("strong" if i in strong_cols else "")
            tds += f'<td class="{cls.strip()}">{v}</td>'
        body += f"<tr>{tds}</tr>"
    if footer:
        tds = ""
        for i, v in enumerate(footer):
            tds += f'<td class="{"num" if i in num_cols else ""}">{v}</td>'
        body += f'<tr class="total">{tds}</tr>'
    return f'<div class="tbl-wrap"><table class="pro"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'

def badge(text: str, kind: str) -> str:
    return f'<span class="badge {kind}">{esc(text)}</span>'


# =====================================================
# DATA
# =====================================================
@st.cache_data(ttl=300, show_spinner="Mengambil data dari Google Sheet...")
def load_data() -> pd.DataFrame:
    df = pd.read_csv(sheet_url(SHEET_NAME), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df[[COL_STORE, COL_TANGGAL, COL_CASHIER, COL_PAGI, COL_SIANG, COL_STATUS_MGR, COL_STATUS_FIN]].copy()
    df[COL_TANGGAL] = pd.to_datetime(df[COL_TANGGAL], errors="coerce").dt.date
    df = df.dropna(subset=[COL_TANGGAL, COL_STORE])
    df[COL_STORE] = df[COL_STORE].str.strip()
    df[COL_PAGI] = to_num(df[COL_PAGI])
    df[COL_SIANG] = to_num(df[COL_SIANG])
    for c in (COL_CASHIER, COL_STATUS_MGR, COL_STATUS_FIN):
        df[c] = df[c].fillna("").str.strip()
    df["is_drop"] = df[COL_CASHIER].str.lower().str.startswith("drop dari")
    df["Asal Drop"] = df[COL_CASHIER].str.extract(r"(?i)drop dari\s+(\S+)")[0]
    df["Total"] = df[COL_PAGI] + df[COL_SIANG]
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def load_store_names() -> dict:
    names = dict(STORE_NAMES_MANUAL)
    try:
        m = pd.read_csv(sheet_url(MASTER_SHEET_NAME), dtype=str)
        m.columns = [c.strip() for c in m.columns]
        cols = list(m.columns)
        low = {c: c.lower() for c in cols}

        kode = MASTER_COL_KODE or cols[0]
        nama = MASTER_COL_NAMA
        if nama is None:
            hit = [c for c in cols if "nama" in low[c] or "name" in low[c]]
            nama = hit[0] if hit else None

        if nama:
            for k, v in zip(m[kode], m[nama]):
                if isinstance(k, str) and isinstance(v, str) and k.strip():
                    names.setdefault(k.strip(), v.strip())
    except Exception: pass
    return names

def pickup_dates(pickup_days: list[int]) -> list[date]:
    today = date.today()
    start = today - timedelta(days=730)
    days = (start + timedelta(days=i) for i in range((today - start).days + 1))
    return [d for d in days if d.weekday() in pickup_days]


# =====================================================
# HEADER / LOGO
# =====================================================
st.markdown(
    f"""
    <div class="topbar">
      <div class="brand">
        <div class="icon">💼</div>
        <div class="texts">
            Monitoring Setoran Omset
            <small>Rekapitulasi setoran pagi dan siang per toko untuk jadwal pick up</small>
        </div>
      </div>
      <div class="stamp">Data diperbarui otomatis<br><b>{tgl_id(date.today())}</b></div>
    </div>
    """, unsafe_allow_html=True
)

try:
    df = load_data()
except Exception as e:
    st.error(f"Gagal membaca Google Sheet. Detail: {e}")
    st.stop()

store_names = load_store_names()

def nama_store(kode: str) -> str:
    return store_names.get(kode, "-")


# =====================================================
# PENGATURAN PERIODE PICK UP OTOMATIS
# =====================================================
with st.expander("⚙️ Pengaturan Periode Pick Up", expanded=False):
    mode = st.radio(
        "Mode Setting Tanggal Pick Up:",
        ["1. Jadwal Rutin (Senin & Kamis)", "2. Revisi Tanggal Pick Up (Custom)"],
    )
    
    st.button("🔄 REFRESH DATA DARI SPREADSHEET", on_click=lambda: (load_data.clear(), load_store_names.clear()))

    include_pickup_day = st.checkbox("Data hari pick up ikut diambil (Jika pick up sore/malam)", value=False)
    include_drop = st.checkbox("Hitung baris titipan (Drop dari ...) pada total toko", value=False)

    if mode.startswith("1."):
        st.markdown("---")
        pickup_days = st.multiselect("Hari Pick Up Rutin:", options=list(HARI.keys()), default=[0, 3], format_func=lambda k: HARI[k])
        if not pickup_days:
            st.warning("Pilih minimal satu hari pick up rutin.")
            st.stop()

        dates = pickup_dates(pickup_days)
        idx_latest = len(dates) - 1

        if "offset" not in st.session_state:
            st.session_state.offset = 0

        # Navigasi Hari
        c1, c2, c3 = st.columns(3)
        if c1.button("⬅️ Sebelum"): st.session_state.offset -= 1
        if c2.button("Berikut ➡️"): st.session_state.offset += 1
        if c3.button("🔄 Terbaru"): st.session_state.offset = 0

        st.session_state.offset = max(-(idx_latest - 1), min(0, st.session_state.offset))
        idx = idx_latest + st.session_state.offset

        pickup_date_target = dates[idx]
        prev_pickup_date = dates[idx - 1]

        selected_pickup = st.date_input("Atau Pilih Tanggal Pick Up Target:", value=pickup_date_target)

        if selected_pickup != pickup_date_target:
            target_dt = selected_pickup
            past_pickups = [d for d in dates if d < target_dt]
            if past_pickups: prev_pickup_date = past_pickups[-1]
            else: prev_pickup_date = target_dt - timedelta(days=3)
            pickup_date_target = target_dt

        if include_pickup_day:
            start, end = prev_pickup_date + timedelta(days=1), pickup_date_target
        else:
            start, end = prev_pickup_date, pickup_date_target - timedelta(days=1)

        judul_pickup = f"Pick Up Rutin: {HARI[pickup_date_target.weekday()]}, {tgl_id(pickup_date_target)}"

    else:
        st.markdown("---")
        st.info("💡 **Mode Revisi Tanggal Pick Up**")
        
        tgl_pickup_revisi = st.date_input("Tanggal Pick Up Revisi", value=date.today())
        
        default_prev = tgl_pickup_revisi - timedelta(days=3)
        for i in range(1, 10):
            d_check = tgl_pickup_revisi - timedelta(days=i)
            if d_check.weekday() in [0, 3]: 
                default_prev = d_check
                break
                
        tgl_pickup_prev = st.date_input("Tanggal Pick Up Terakhir Sebelumnya", value=default_prev)

        if include_pickup_day:
            start, end = tgl_pickup_prev + timedelta(days=1), tgl_pickup_revisi
        else:
            start, end = tgl_pickup_prev, tgl_pickup_revisi - timedelta(days=1)

        judul_pickup = f"Pick Up Revisi: {HARI[tgl_pickup_revisi.weekday()]}, {tgl_id(tgl_pickup_revisi)}"


# =====================================================
# FILTER DATA
# =====================================================
d = df[(df[COL_TANGGAL] >= start) & (df[COL_TANGGAL] <= end)].copy()
d = d[d[COL_STATUS_MGR].str.lower() != "ditolak"]
drops = d[d["is_drop"]]
if not include_drop:
    d = d[~d["is_drop"]]

kode_list = sorted(d[COL_STORE].unique())
label_map = {k: f"{k} - {nama_store(k)}" if nama_store(k) != "-" else k for k in kode_list}
pilih = st.multiselect("Filter Toko (Cari/Pilih)", options=kode_list, format_func=lambda k: label_map.get(k, k))
if pilih:
    d = d[d[COL_STORE].isin(pilih)]
    drops = drops[drops[COL_STORE].isin(pilih)]

if d.empty:
    st.info(f"Belum ada data setoran pada periode {tgl_id(start)} s/d {tgl_id(end)}.")
    st.stop()


# =====================================================
# SMART PARSER: MENGHITUNG SELISIH AKTUAL
# =====================================================
def parse_finance_status(row):
    val_str = str(row[COL_STATUS_FIN]).lower().strip()
    total = float(row["Total"]) if pd.notnull(row["Total"]) else 0.0
    if val_str in ["verified", "ok", "v", "sesuai", "yes", "ya", "true"]: return pd.Series([total, 0.0, 0.0])
    if val_str in ["", "nan", "belum", "pending", "false", "none"]: return pd.Series([0.0, 0.0, total])
    if "lebih" in val_str:
        nums = re.findall(r'\d+', val_str.replace('.', '').replace(',', ''))
        if nums:
            selisih = float(nums[0])
            return pd.Series([total + selisih, selisih, 0.0])
    if "kurang" in val_str:
        nums = re.findall(r'\d+', val_str.replace('.', '').replace(',', ''))
        if nums:
            selisih = -float(nums[0])
            return pd.Series([total + selisih, selisih, 0.0])
    nums = re.findall(r'\d+', val_str.replace('.', '').replace(',', ''))
    if nums and len(nums[0]) >= 3:
        verif_nom = float(nums[0])
        selisih = verif_nom - total
        return pd.Series([verif_nom, selisih, 0.0])
    return pd.Series([0.0, 0.0, total])

d[['Verified_Nom', 'Selisih_Nom', 'Belum_Verif_Nom']] = d.apply(parse_finance_status, axis=1)

ringkas = (
    d.groupby(COL_STORE, as_index=False)
    .agg(
        Pagi=(COL_PAGI, "sum"), Siang=(COL_SIANG, "sum"), Total=("Total", "sum"), 
        Verified=("Verified_Nom", "sum"), Selisih_Aktual=("Selisih_Nom", "sum"),
        Belum_Verified=("Belum_Verif_Nom", "sum"), Hari_Terisi=(COL_TANGGAL, "nunique")
    )
    .reset_index(drop=True)
)
jumlah_hari = (end - start).days + 1
ringkas["Hari Kurang"] = (jumlah_hari - ringkas["Hari_Terisi"]).clip(lower=0)

total_pickup = ringkas["Total"].sum()
total_pagi = ringkas["Pagi"].sum()
total_siang = ringkas["Siang"].sum()
total_verified = ringkas["Verified"].sum()
total_belum = ringkas["Belum_Verified"].sum()
total_selisih = ringkas["Selisih_Aktual"].sum()


# =====================================================
# MENU UTAMA: TOTAL NOMINAL PICK UP
# =====================================================
st.markdown(
    f"""
    <div class="hero">
      <div class="label">Total Nominal Pick Up</div>
      <div class="amount">{rp(total_pickup)}</div>
      <div class="meta"><b>{esc(judul_pickup)}</b><br>
        Periode data: {tgl_id(start)} s/d {tgl_id(end)} ({jumlah_hari} hari) &nbsp;|&nbsp;
        <b>{len(ringkas)}</b> toko</div>
      <div class="split">
        {badge("Terverifikasi Finance: " + rp(total_verified), "b-ok")}
        {badge("Menunggu Verifikasi: " + rp(total_belum), "b-wait" if total_belum else "b-neutral")}
      </div>
    </div>
    """, unsafe_allow_html=True
)

k1, k2, k3, k4 = st.columns(4)
for col, label, value in [
    (k1, "Setoran Pagi", rp(total_pagi)), (k2, "Setoran Siang", rp(total_siang)),
    (k3, "Jumlah Toko", str(len(ringkas))), (k4, "Kurang Hari", str(int((ringkas["Hari Kurang"] > 0).sum()))),
]:
    col.markdown(f'<div class="kpi"><div class="k">{label}</div><div class="v">{value}</div></div>', unsafe_allow_html=True)


# =====================================================
# RINCIAN (SORTING DAN TEKS SELISIH)
# =====================================================
st.markdown('<div class="section-title">Rincian Data</div>', unsafe_allow_html=True)
tab_toko, tab_hari, tab_drop = st.tabs(["Per Toko", "Per Hari", "Titipan (Drop)"])

with tab_toko:
    sort_by = st.selectbox(
        "Urutkan Tabel Berdasarkan:",
        ["Total Pick Up (Tertinggi)", "Kode Toko (A - Z)", "Selisih (Terbesar)"]
    )
    
    if sort_by == "Kode Toko (A - Z)":
        ringkas = ringkas.sort_values(COL_STORE, ascending=True)
    elif sort_by == "Selisih (Terbesar)":
        ringkas["Abs_Selisih"] = ringkas["Selisih_Aktual"].abs()
        ringkas = ringkas.sort_values(["Abs_Selisih", "Selisih_Aktual"], ascending=[False, False])
    else:
        ringkas = ringkas.sort_values("Total", ascending=False)
        
    ringkas = ringkas.reset_index(drop=True)

    rows = []
    for i, r in ringkas.iterrows():
        status = ""
        if r["Hari Kurang"] > 0: status += badge(f"Kurang {int(r['Hari Kurang'])} hr", "b-miss") + " "
        if r["Belum_Verified"] > 0: status += badge("Menunggu Verifikasi", "b-wait") + " "
        
        selisih_val = r["Selisih_Aktual"]
        if selisih_val > 0:
            teks_selisih = f"Lebih Rp {num(selisih_val)}"
            status += badge("Lebih Setor", "b-wait")
        elif selisih_val < 0:
            teks_selisih = f"Kurang Rp {num(abs(selisih_val))}"
            status += badge("Kurang Setor", "b-miss")
        else:
            if r["Belum_Verified"] > 0: teks_selisih = "-"
            else: teks_selisih = "Sesuai"
                
        if r["Hari Kurang"] == 0 and r["Belum_Verified"] == 0 and selisih_val == 0:
            status += badge("Lengkap & Sesuai", "b-ok")
            
        rows.append([
            i + 1, esc(r[COL_STORE]), esc(nama_store(r[COL_STORE])), 
            num(r["Pagi"]), num(r["Siang"]), num(r["Total"]), num(r["Verified"]), 
            teks_selisih, status
        ])
        
    teks_selisih_total = ""
    if total_selisih > 0: teks_selisih_total = f"Lebih Rp {num(total_selisih)}"
    elif total_selisih < 0: teks_selisih_total = f"Kurang Rp {num(abs(total_selisih))}"
    else: teks_selisih_total = "Sesuai"

    st.markdown(
        html_table(
            ["No", "Kode", "Nama Store", "Setoran Pagi", "Setoran Siang", "Total Pick Up", "Terverifikasi", "Selisih", "Status"],
            rows, num_cols=(3, 4, 5, 6, 7), strong_cols=(2, 5, 7), 
            footer=["", "", "TOTAL", num(total_pagi), num(total_siang), num(total_pickup), num(total_verified), teks_selisih_total, ""]
        ), unsafe_allow_html=True
    )
    
    exp = ringkas.copy()
    exp.insert(1, "Nama Store", exp[COL_STORE].map(nama_store))
    if "Abs_Selisih" in exp.columns: exp = exp.drop(columns=["Abs_Selisih"])
    st.download_button("📥 Unduh Laporan (CSV)", exp.to_csv(index=False).encode("utf-8"), file_name=f"pickup_{start}_{end}.csv", mime="text/csv")

# Tab Harian
harian = d.groupby([COL_TANGGAL, COL_STORE], as_index=False).agg(Pagi=(COL_PAGI, "sum"), Siang=(COL_SIANG, "sum"), Total=("Total", "sum"), Status=(COL_STATUS_FIN, "first")).sort_values([COL_TANGGAL, COL_STORE])
with tab_hari:
    rows = []
    for _, r in harian.iterrows():
        st_fin = r["Status"].lower()
        kind = "b-ok" if st_fin in ["verified", "ok", "v", "sesuai", "yes"] else ("b-miss" if "kurang" in st_fin else "b-wait")
        rows.append([esc(f"{HARI[r[COL_TANGGAL].weekday()]}, {r[COL_TANGGAL]:%d-%m-%Y}"), esc(r[COL_STORE]), esc(nama_store(r[COL_STORE])), num(r["Pagi"]), num(r["Siang"]), num(r["Total"]), badge(r["Status"] or "Menunggu", kind)])
    st.markdown(html_table(["Tanggal", "Kode", "Nama Store", "Setoran Pagi", "Setoran Siang", "Total", "Status Finance"], rows, num_cols=(3, 4, 5), strong_cols=(2,)), unsafe_allow_html=True)

# Tab Drop
with tab_drop:
    if drops.empty:
        st.info("Tidak ada titipan (Drop) pada periode ini.")
    else:
        t = drops.groupby([COL_STORE, "Asal Drop"], as_index=False)["Total"].sum().sort_values("Total", ascending=False)
        rows = [[esc(r[COL_STORE]), esc(nama_store(r[COL_STORE])), esc(r["Asal Drop"]), esc(nama_store(r["Asal Drop"])), num(r["Total"])] for _, r in t.iterrows()]
        st.markdown(html_table(["Kode Penerima", "Nama Penerima", "Kode Asal", "Nama Asal", "Nominal"], rows, num_cols=(4,), strong_cols=(1, 4), footer=["", "", "", "TOTAL", num(t["Total"].sum())]), unsafe_allow_html=True)


# =====================================================
# ASSISTEN M KHADAFI (AI) AUTO-DETECT GROQ MODEL
# =====================================================
st.markdown('<div class="section-title">🤖 Asisten M Khadafi</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="ai-card">
      <div class="t">Tanya Seputar Data Setoran</div>
      <div class="s">Tanyakan data pada tabel di atas. Contoh: "Toko mana yang selisihnya paling besar?"</div>
    </div>
    """, unsafe_allow_html=True,
)

if not get_secret("GROQ_API_KEY"):
    st.info("Assisten M Khadafi belum aktif. Isi GROQ_API_KEY pada Secrets Streamlit untuk mengaktifkan.")
else:
    with st.form("form_ai", clear_on_submit=False):
        tanya = st.text_input("Pertanyaan", placeholder="Ketik pertanyaan Anda di sini...", label_visibility="collapsed")
        kirim = st.form_submit_button("Tanya Asisten")

    if kirim and tanya.strip():
        import groq

        ringkas_ai = ringkas.copy()
        ringkas_ai.insert(1, "Nama Store", ringkas_ai[COL_STORE].map(nama_store))
        konteks = (
            f"Periode: {start} s/d {end}. Total pick up: {rp(total_pickup)}. "
            f"Terverifikasi: {rp(total_verified)}. Belum diverifikasi: {rp(total_belum)}. "
            f"Total Selisih Keseluruhan: {rp(total_selisih)}\n\n"
            "RINGKASAN PER TOKO (CSV):\n" + ringkas_ai.head(100).to_csv(index=False)
        )
        
        try:
            client = groq.Groq(api_key=get_secret("GROQ_API_KEY"))
            with st.spinner("AI sedang menganalisa data..."):
                models_data = client.models.list().data
                kata_terlarang = ["whisper", "guard", "vision", "embed", "llava"]
                model_chat_valid = [m.id for m in models_data if not any(b in m.id.lower() for b in kata_terlarang)]
                
                if not model_chat_valid:
                    st.error("API Key Groq Anda tidak memiliki akses ke model teks/chat manapun.")
                    st.stop()
                
                chosen_model = model_chat_valid[0]
                for m in model_chat_valid:
                    if "llama" in m.lower() or "gemma" in m.lower() or "mixtral" in m.lower(): 
                        chosen_model = m; break
                
                chat_completion = client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Anda merupakan Assisten M Khadafi, asisten analisa setoran omset toko. "
                                "Jawab dalam Bahasa Indonesia, ringkas, profesional, hanya berdasarkan data yang diberikan. "
                                "Jika ditanya selisih, sebutkan apakah itu Lebih Setor atau Kurang Setor."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"{konteks}\n\nPertanyaan: {tanya.strip()}",
                        }
                    ],
                    model=chosen_model, max_tokens=512,
                )
            
            jawaban = chat_completion.choices[0].message.content
            st.markdown(f'<div class="ai-answer">{esc(jawaban).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="model-info">Direspon menggunakan model: {chosen_model}</div>', unsafe_allow_html=True)
            
        except Exception as e:
            if "rate limit" in str(e).lower():
                st.error("Permintaan ditolak karena limit API Groq telah tercapai. Silakan coba beberapa saat lagi.")
            else:
                st.error(f"Terjadi kesalahan pada Asisten: {e}")

# =====================================================
# FOOTER
# =====================================================
st.markdown('<div class="footer">Powered and developed by <b>M Khadafi</b></div>', unsafe_allow_html=True)
