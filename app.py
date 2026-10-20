import html
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

# Kolom di tab "Data Setoran"
COL_STORE = "Store"
COL_TANGGAL = "Tanggal"
COL_CASHIER = "Cashier"
COL_PAGI = "Setoran Pagi"
COL_SIANG = "Setoran Siang"
COL_STATUS_MGR = "Status Mgr"
COL_STATUS_FIN = "Status Finance"

# Kolom di tab "Master Store" (None = deteksi otomatis, atau isi nama kolom persis)
MASTER_COL_KODE = None
MASTER_COL_NAMA = None

# Nama store manual (opsional). Dipakai jika Master Store belum terbaca.
# Contoh: {"F35Y": "Nama Store F35Y"}
STORE_NAMES_MANUAL: dict[str, str] = {}

# Model AI (bisa diganti lewat Secrets: ANTHROPIC_MODEL)
DEFAULT_MODEL = "claude-sonnet-4-6"

HARI = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}
BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


# =====================================================
# STYLE
# =====================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp { font-family: 'Inter', 'Segoe UI', Arial, sans-serif; }
.stApp { background: #F4F6FA; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1280px; }

/* Header */
.topbar {
  background: linear-gradient(120deg, #0B1F3A 0%, #12335E 100%);
  border-radius: 14px; padding: 22px 28px; margin-bottom: 18px;
  display: flex; justify-content: space-between; align-items: center;
}
.topbar .brand { color: #FFFFFF; font-size: 1.35rem; font-weight: 700; letter-spacing: .2px; }
.topbar .brand small { display: block; color: #9DB4D3; font-size: .82rem; font-weight: 400; margin-top: 3px; }
.topbar .stamp { color: #9DB4D3; font-size: .8rem; text-align: right; }
.topbar .stamp b { color: #FFFFFF; font-weight: 600; }

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
.tbl-wrap { background: #FFFFFF; border: 1px solid #E3E8F0; border-radius: 12px; overflow-x: auto;
  box-shadow: 0 1px 6px rgba(11,31,58,.04); }
table.pro { width: 100%; border-collapse: collapse; font-size: .88rem; }
table.pro th { background: #0B1F3A; color: #FFFFFF; font-weight: 600; text-align: left;
  padding: 12px 14px; white-space: nowrap; font-size: .8rem; letter-spacing: .3px; }
table.pro th.num, table.pro td.num { text-align: right; font-variant-numeric: tabular-nums; }
table.pro td { padding: 11px 14px; border-bottom: 1px solid #EEF1F6; color: #1F2D3D; }
table.pro tbody tr:nth-child(even) td { background: #F8FAFC; }
table.pro tbody tr:hover td { background: #EEF3FA; }
table.pro td.strong { font-weight: 700; color: #0B1F3A; }
table.pro tr.total td { background: #EAEFF7 !important; font-weight: 700; color: #0B1F3A; border-top: 2px solid #12335E; }

/* Buttons */
.stButton > button, .stDownloadButton > button, div[data-testid="stFormSubmitButton"] > button {
  background: #FFFFFF; color: #12335E; border: 1px solid #C9D3E3; border-radius: 8px;
  font-weight: 600; font-size: .85rem; padding: .45rem 1rem; transition: all .15s;
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
.ai-card { background: #FFFFFF; border: 1px solid #E3E8F0; border-radius: 14px; padding: 20px 24px; margin-top: 8px;
  box-shadow: 0 1px 6px rgba(11,31,58,.04); }
.ai-card .t { color: #0B1F3A; font-weight: 700; font-size: 1.05rem; }
.ai-card .s { color: #5B6B82; font-size: .85rem; margin-bottom: 10px; }
.ai-answer { background: #F4F7FC; border-left: 4px solid #12335E; border-radius: 8px; padding: 14px 18px;
  color: #1F2D3D; margin-top: 12px; }

/* Footer */
.footer { text-align: center; color: #7B8AA0; font-size: .8rem; margin-top: 36px; padding-top: 16px;
  border-top: 1px solid #DCE3EE; }
.footer b { color: #12335E; }
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
    return pd.to_numeric(
        s.astype(str).str.replace(r"[^\d\-]", "", regex=True), errors="coerce"
    ).fillna(0)


def get_secret(name: str, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def sheet_url(name: str) -> str:
    return (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(name)}"
    )


def html_table(headers, rows, num_cols=(), strong_cols=(), footer=None) -> str:
    """headers: list[str]; rows: list[list]; nilai berisi HTML siap pakai."""
    th = "".join(
        f'<th class="{"num" if i in num_cols else ""}">{esc(h)}</th>' for i, h in enumerate(headers)
    )
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
    df = df[
        [COL_STORE, COL_TANGGAL, COL_CASHIER, COL_PAGI, COL_SIANG, COL_STATUS_MGR, COL_STATUS_FIN]
    ].copy()
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
    """Peta kode store -> nama store dari tab Master Store (deteksi kolom otomatis)."""
    names = dict(STORE_NAMES_MANUAL)
    try:
        m = pd.read_csv(sheet_url(MASTER_SHEET_NAME), dtype=str)
        m.columns = [c.strip() for c in m.columns]
        cols = list(m.columns)
        low = {c: c.lower() for c in cols}

        kode = MASTER_COL_KODE
        if kode is None:
            for key in ("kode", "code", "id store", "store id", "store"):
                hit = [c for c in cols if key in low[c] and "nama" not in low[c] and "name" not in low[c]]
                if hit:
                    kode = hit[0]
                    break
            kode = kode or cols[0]

        nama = MASTER_COL_NAMA
        if nama is None:
            hit = [c for c in cols if "nama" in low[c] or "name" in low[c]]
            nama = hit[0] if hit else None

        if nama:
            for k, v in zip(m[kode], m[nama]):
                if isinstance(k, str) and isinstance(v, str) and k.strip():
                    names.setdefault(k.strip(), v.strip())
    except Exception:
        pass
    return names


def pickup_dates(pickup_days: list[int]) -> list[date]:
    today = date.today()
    start = today - timedelta(days=730)
    days = (start + timedelta(days=i) for i in range((today - start).days + 1))
    return [d for d in days if d.weekday() in pickup_days]


# =====================================================
# HEADER
# =====================================================
st.markdown(
    f"""
    <div class="topbar">
      <div class="brand">Monitoring Setoran Omset
        <small>Rekapitulasi setoran pagi dan siang per toko untuk jadwal pick up</small>
      </div>
      <div class="stamp">Data diperbarui otomatis<br><b>{tgl_id(date.today())}</b></div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    df = load_data()
except Exception as e:
    st.error(
        "Gagal membaca Google Sheet. Pastikan sheet dibagikan 'Anyone with the link' "
        f"dan nama tab/kolom benar.\n\nDetail: {e}"
    )
    st.stop()

store_names = load_store_names()


def nama_store(kode: str) -> str:
    return store_names.get(kode, "-")


# =====================================================
# PENGATURAN & PERIODE
# =====================================================
with st.expander("Pengaturan periode dan perhitungan"):
    mode = st.radio(
        "Mode periode",
        ["Otomatis (jadwal pick up)", "Manual (pilih tanggal)"],
        horizontal=True,
    )
    pickup_days = st.multiselect(
        "Hari pick up",
        options=list(HARI.keys()),
        default=[0, 3],
        format_func=lambda k: HARI[k],
    )
    o1, o2 = st.columns(2)
    include_pickup_day = o1.checkbox(
        "Data hari pick up ikut diambil",
        value=False,
        help="Kosongkan jika pick up dilakukan pagi hari sebelum setoran hari itu masuk. "
        "Centang jika pick up dilakukan sore atau malam.",
    )
    include_drop = o2.checkbox(
        "Hitung baris titipan (Drop dari ...) pada total toko",
        value=False,
        help="Nominal titipan sudah tercatat di toko asal. Jika dicentang, total dapat terhitung dua kali.",
    )
    if st.button("Muat ulang data dari Google Sheet"):
        load_data.clear()
        load_store_names.clear()
        st.rerun()
    if not store_names:
        st.caption(
            "Nama toko belum terbaca dari tab Master Store. "
            "Isi MASTER_COL_KODE dan MASTER_COL_NAMA di bagian konfigurasi app.py."
        )

if "offset" not in st.session_state:
    st.session_state.offset = 0

if mode.startswith("Otomatis"):
    if not pickup_days:
        st.warning("Pilih minimal satu hari pick up pada menu pengaturan.")
        st.stop()

    dates = pickup_dates(pickup_days)
    idx_latest = len(dates) - 1

    c1, c2, c3, _ = st.columns([1.1, 1.1, 1, 4])
    if c1.button("Periode sebelumnya"):
        st.session_state.offset -= 1
    if c2.button("Periode berikutnya"):
        st.session_state.offset += 1
    if c3.button("Terbaru"):
        st.session_state.offset = 0
    st.session_state.offset = max(-(idx_latest - 1), min(0, st.session_state.offset))

    idx = idx_latest + st.session_state.offset
    pickup, prev_pickup = dates[idx], dates[idx - 1]
    if include_pickup_day:
        start, end = prev_pickup + timedelta(days=1), pickup
    else:
        start, end = prev_pickup, pickup - timedelta(days=1)
    judul_pickup = f"Pick up {HARI[pickup.weekday()]}, {tgl_id(pickup)}"
else:
    c1, c2, _ = st.columns([1, 1, 3])
    start = c1.date_input("Dari tanggal", date.today() - timedelta(days=3))
    end = c2.date_input("Sampai tanggal", date.today())
    judul_pickup = "Periode manual"

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
pilih = st.multiselect(
    "Filter toko (kosongkan untuk semua toko)",
    options=kode_list,
    format_func=lambda k: label_map.get(k, k),
)
if pilih:
    d = d[d[COL_STORE].isin(pilih)]
    drops = drops[drops[COL_STORE].isin(pilih)]

if d.empty:
    st.info("Belum ada data setoran pada periode ini.")
    st.markdown(
        '<div class="footer">Powered and developed by <b>M Khadafi</b></div>',
        unsafe_allow_html=True,
    )
    st.stop()

# =====================================================
# PERHITUNGAN
# =====================================================
d["Verified"] = d["Total"].where(d[COL_STATUS_FIN].str.lower() == "verified", 0)

ringkas = (
    d.groupby(COL_STORE, as_index=False)
    .agg(
        Pagi=(COL_PAGI, "sum"),
        Siang=(COL_SIANG, "sum"),
        Total=("Total", "sum"),
        Verified=("Verified", "sum"),
        Hari_Terisi=(COL_TANGGAL, "nunique"),
    )
    .sort_values("Total", ascending=False)
    .reset_index(drop=True)
)
ringkas["Belum Verified"] = ringkas["Total"] - ringkas["Verified"]
jumlah_hari = (end - start).days + 1
ringkas["Hari Kurang"] = (jumlah_hari - ringkas["Hari_Terisi"]).clip(lower=0)

total_pickup = ringkas["Total"].sum()
total_pagi = ringkas["Pagi"].sum()
total_siang = ringkas["Siang"].sum()
total_verified = ringkas["Verified"].sum()
total_belum = ringkas["Belum Verified"].sum()

# =====================================================
# MENU UTAMA: TOTAL NOMINAL PICK UP
# =====================================================
st.markdown(
    f"""
    <div class="hero">
      <div class="label">Total Nominal Pick Up</div>
      <div class="amount">{rp(total_pickup)}</div>
      <div class="meta"><b>{esc(judul_pickup)}</b> &nbsp;|&nbsp;
        Periode data {tgl_id(start)} s/d {tgl_id(end)} ({jumlah_hari} hari) &nbsp;|&nbsp;
        <b>{len(ringkas)}</b> toko</div>
      <div class="split">
        {badge("Terverifikasi Finance: " + rp(total_verified), "b-ok")}
        {badge("Menunggu verifikasi: " + rp(total_belum), "b-wait" if total_belum else "b-neutral")}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
for col, label, value in [
    (k1, "Setoran Pagi", rp(total_pagi)),
    (k2, "Setoran Siang", rp(total_siang)),
    (k3, "Jumlah Toko", str(len(ringkas))),
    (k4, "Toko Belum Lengkap", str(int((ringkas["Hari Kurang"] > 0).sum()))),
]:
    col.markdown(
        f'<div class="kpi"><div class="k">{label}</div><div class="v">{value}</div></div>',
        unsafe_allow_html=True,
    )

# =====================================================
# RINCIAN
# =====================================================
st.markdown('<div class="section-title">Rincian</div>', unsafe_allow_html=True)
tab_toko, tab_hari, tab_drop = st.tabs(["Per Toko", "Per Hari", "Titipan (Drop)"])

with tab_toko:
    rows = []
    for i, r in ringkas.iterrows():
        status = ""
        if r["Hari Kurang"] > 0:
            status += badge(f"Kurang {int(r['Hari Kurang'])} hari", "b-miss") + " "
        if r["Belum Verified"] > 0:
            status += badge("Menunggu verifikasi", "b-wait")
        elif r["Hari Kurang"] == 0:
            status += badge("Lengkap", "b-ok")
        rows.append(
            [
                i + 1,
                esc(r[COL_STORE]),
                esc(nama_store(r[COL_STORE])),
                num(r["Pagi"]),
                num(r["Siang"]),
                num(r["Total"]),
                status,
            ]
        )
    st.markdown(
        html_table(
            ["No", "Kode", "Nama Store", "Setoran Pagi", "Setoran Siang", "Total Pick Up", "Status"],
            rows,
            num_cols=(3, 4, 5),
            strong_cols=(2, 5),
            footer=["", "", "TOTAL", num(total_pagi), num(total_siang), num(total_pickup), ""],
        ),
        unsafe_allow_html=True,
    )
    exp = ringkas.copy()
    exp.insert(1, "Nama Store", exp[COL_STORE].map(nama_store))
    st.download_button(
        "Unduh rincian (CSV)",
        exp.to_csv(index=False).encode("utf-8"),
        file_name=f"pickup_{start}_{end}.csv",
        mime="text/csv",
    )

harian = (
    d.groupby([COL_TANGGAL, COL_STORE], as_index=False)
    .agg(
        Pagi=(COL_PAGI, "sum"),
        Siang=(COL_SIANG, "sum"),
        Total=("Total", "sum"),
        Status=(COL_STATUS_FIN, "first"),
    )
    .sort_values([COL_TANGGAL, COL_STORE])
)

with tab_hari:
    rows = []
    for _, r in harian.iterrows():
        st_fin = r["Status"].lower()
        kind = "b-ok" if st_fin == "verified" else "b-wait"
        rows.append(
            [
                esc(f"{HARI[r[COL_TANGGAL].weekday()]}, {r[COL_TANGGAL]:%d-%m-%Y}"),
                esc(r[COL_STORE]),
                esc(nama_store(r[COL_STORE])),
                num(r["Pagi"]),
                num(r["Siang"]),
                num(r["Total"]),
                badge(r["Status"] or "Menunggu", kind),
            ]
        )
    st.markdown(
        html_table(
            ["Tanggal", "Kode", "Nama Store", "Setoran Pagi", "Setoran Siang", "Total", "Status Finance"],
            rows,
            num_cols=(3, 4, 5),
            strong_cols=(2,),
        ),
        unsafe_allow_html=True,
    )

with tab_drop:
    if drops.empty:
        st.info("Tidak ada titipan (Drop) pada periode ini.")
    else:
        t = (
            drops.groupby([COL_STORE, "Asal Drop"], as_index=False)["Total"]
            .sum()
            .sort_values("Total", ascending=False)
        )
        rows = [
            [
                esc(r[COL_STORE]),
                esc(nama_store(r[COL_STORE])),
                esc(r["Asal Drop"]),
                esc(nama_store(r["Asal Drop"])),
                num(r["Total"]),
            ]
            for _, r in t.iterrows()
        ]
        st.markdown(
            html_table(
                ["Kode Penerima", "Nama Penerima", "Kode Asal", "Nama Asal", "Nominal"],
                rows,
                num_cols=(4,),
                strong_cols=(1, 4),
                footer=["", "", "", "TOTAL", num(t["Total"].sum())],
            ),
            unsafe_allow_html=True,
        )
        st.caption("Titipan adalah nominal dari toko asal yang disetorkan melalui toko penerima.")

# =====================================================
# ASSISTEN M KHADAFI (AI)
# =====================================================
st.markdown('<div class="section-title">Asisten</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="ai-card">
      <div class="t">Assisten M Khadafi</div>
      <div class="s">Tanyakan data setoran pada periode yang sedang ditampilkan.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not get_secret("ANTHROPIC_API_KEY"):
    st.info("Assisten M Khadafi belum aktif. Isi ANTHROPIC_API_KEY pada Secrets Streamlit untuk mengaktifkan.")
else:
    with st.form("form_ai", clear_on_submit=False):
        tanya = st.text_input(
            "Pertanyaan",
            placeholder="Contoh: toko mana yang setoran siangnya paling rendah?",
            label_visibility="collapsed",
        )
        kirim = st.form_submit_button("Tanya Assisten")

    if kirim and tanya.strip():
        import anthropic

        ringkas_ai = ringkas.copy()
        ringkas_ai.insert(1, "Nama Store", ringkas_ai[COL_STORE].map(nama_store))
        harian_ai = harian.copy()
        harian_ai["Nama Store"] = harian_ai[COL_STORE].map(nama_store)
        konteks = (
            f"Periode: {start} s/d {end}. Total pick up: {rp(total_pickup)}.\n"
            "RINGKASAN PER TOKO (CSV):\n" + ringkas_ai.head(100).to_csv(index=False)
            + "\nRINCIAN PER HARI (CSV):\n" + harian_ai.head(300).to_csv(index=False)
        )
        model = get_secret("ANTHROPIC_MODEL", DEFAULT_MODEL)
        try:
            client = anthropic.Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
            with st.spinner("Assisten M Khadafi sedang menganalisa..."):
                res = client.messages.create(
                    model=model,
                    max_tokens=1000,
                    system=(
                        "Anda adalah Assisten M Khadafi, asisten analisa setoran omset toko. "
                        "Jawab dalam Bahasa Indonesia, ringkas, profesional, hanya berdasarkan data yang diberikan. "
                        "Sebut nama store bersama kodenya bila tersedia. Jika data tidak cukup, katakan dengan jelas."
                    ),
                    messages=[
                        {
                            "role": "user",
                            "content": f"{konteks}\n\nPertanyaan: {tanya.strip()}",
                        }
                    ],
                )
            jawaban = "".join(b.text for b in res.content if getattr(b, "type", "") == "text")
            st.markdown(f'<div class="ai-answer">{esc(jawaban).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        except anthropic.APIStatusError as e:
            pesan = getattr(e, "message", str(e))
            if "credit balance" in pesan.lower():
                st.error("Saldo kredit API Anthropic habis. Lakukan top up di console.anthropic.com (menu Billing).")
            else:
                st.error(f"Permintaan ke AI ditolak (kode {e.status_code}): {pesan}")
        except Exception as e:
            st.error(f"Terjadi kesalahan pada Assisten M Khadafi: {e}")

# =====================================================
# FOOTER
# =====================================================
st.markdown(
    '<div class="footer">Powered and developed by <b>M Khadafi</b></div>',
    unsafe_allow_html=True,
)
