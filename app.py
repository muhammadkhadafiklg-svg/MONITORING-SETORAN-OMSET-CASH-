from datetime import date, timedelta
from urllib.parse import quote

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Setoran Omset - Periode Pick Up", layout="wide")

# =====================================================
# KONFIGURASI
# =====================================================
SHEET_ID = "1bCvWOsmBIr568kzoNed3gzmPk8EnCAXwE0umdeDj5D4"
SHEET_NAME = "Data Setoran"

COL_STORE = "Store"
COL_TANGGAL = "Tanggal"
COL_CASHIER = "Cashier"
COL_PAGI = "Setoran Pagi"
COL_SIANG = "Setoran Siang"
COL_STATUS_MGR = "Status Mgr"
COL_STATUS_FIN = "Status Finance"

HARI = {0: "Senin", 1: "Selasa", 2: "Rabu", 3: "Kamis", 4: "Jumat", 5: "Sabtu", 6: "Minggu"}


# =====================================================
# DATA
# =====================================================
def to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace(r"[^\d\-]", "", regex=True), errors="coerce"
    ).fillna(0)


@st.cache_data(ttl=300, show_spinner="Mengambil data dari Google Sheet...")
def load_data() -> pd.DataFrame:
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq"
        f"?tqx=out:csv&sheet={quote(SHEET_NAME)}"
    )
    df = pd.read_csv(url, dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df = df[
        [COL_STORE, COL_TANGGAL, COL_CASHIER, COL_PAGI, COL_SIANG, COL_STATUS_MGR, COL_STATUS_FIN]
    ].copy()
    df[COL_TANGGAL] = pd.to_datetime(df[COL_TANGGAL], errors="coerce").dt.date
    df = df.dropna(subset=[COL_TANGGAL, COL_STORE])
    df[COL_PAGI] = to_num(df[COL_PAGI])
    df[COL_SIANG] = to_num(df[COL_SIANG])
    for c in (COL_CASHIER, COL_STATUS_MGR, COL_STATUS_FIN):
        df[c] = df[c].fillna("").str.strip()
    # Baris titipan: Cashier berisi "Drop dari F347"
    df["is_drop"] = df[COL_CASHIER].str.lower().str.startswith("drop dari")
    df["Asal Drop"] = df[COL_CASHIER].str.extract(r"(?i)drop dari\s+(\S+)")[0]
    df["Total"] = df[COL_PAGI] + df[COL_SIANG]
    return df


def pickup_dates(pickup_days: list[int]) -> list[date]:
    today = date.today()
    start = today - timedelta(days=730)
    days = (start + timedelta(days=i) for i in range((today - start).days + 1))
    return [d for d in days if d.weekday() in pickup_days]


def rp(x) -> str:
    return "Rp {:,.0f}".format(x).replace(",", ".")


# =====================================================
# SIDEBAR
# =====================================================
st.title("Setoran Omset per Toko")

with st.sidebar:
    st.header("Pengaturan")
    mode = st.radio("Mode periode", ["Otomatis (jadwal pick up)", "Manual (pilih tanggal)"])
    pickup_days = st.multiselect(
        "Hari pick up",
        options=list(HARI.keys()),
        default=[0, 3],
        format_func=lambda k: HARI[k],
    )
    include_pickup_day = st.checkbox(
        "Data hari pick up ikut diambil",
        value=False,
        help="Biarkan kosong jika pick up dilakukan pagi hari (sebelum setoran hari itu masuk). "
        "Centang jika pick up sore/malam.",
    )
    include_drop = st.checkbox(
        "Hitung baris 'Drop dari ...' di total toko",
        value=False,
        help="Baris Drop adalah titipan dari toko lain dan nominalnya sudah tercatat di toko asal. "
        "Jika dicentang, total bisa dobel.",
    )
    if st.button("Refresh data dari Google Sheet"):
        load_data.clear()
        st.rerun()

if "offset" not in st.session_state:
    st.session_state.offset = 0

try:
    df = load_data()
except Exception as e:
    st.error(
        "Gagal membaca Google Sheet. Pastikan sheet dibagikan 'Anyone with the link' "
        f"dan nama tab/kolom benar.\n\nDetail: {e}"
    )
    st.stop()

# =====================================================
# HITUNG PERIODE
# =====================================================
if mode.startswith("Otomatis"):
    if not pickup_days:
        st.warning("Pilih minimal satu hari pick up.")
        st.stop()

    dates = pickup_dates(pickup_days)
    idx_latest = len(dates) - 1

    c1, c2, c3, _ = st.columns([1, 1, 1, 3])
    if c1.button("◀ Periode sebelumnya"):
        st.session_state.offset -= 1
    if c2.button("Periode berikutnya ▶"):
        st.session_state.offset += 1
    if c3.button("Reset ke terbaru"):
        st.session_state.offset = 0
    st.session_state.offset = max(-(idx_latest - 1), min(0, st.session_state.offset))

    idx = idx_latest + st.session_state.offset
    pickup, prev_pickup = dates[idx], dates[idx - 1]
    if include_pickup_day:
        start, end = prev_pickup + timedelta(days=1), pickup
    else:
        start, end = prev_pickup, pickup - timedelta(days=1)
    st.subheader(f"Pick up {HARI[pickup.weekday()]}, {pickup:%d-%m-%Y}")
else:
    c1, c2 = st.columns(2)
    start = c1.date_input("Dari tanggal", date.today() - timedelta(days=3))
    end = c2.date_input("Sampai tanggal", date.today())

st.caption(
    f"Periode data: {HARI[start.weekday()]} {start:%d-%m-%Y} s/d {HARI[end.weekday()]} {end:%d-%m-%Y}"
)

# =====================================================
# FILTER DATA
# =====================================================
d = df[(df[COL_TANGGAL] >= start) & (df[COL_TANGGAL] <= end)].copy()
d = d[d[COL_STATUS_MGR].str.lower() != "ditolak"]  # setoran/drop yang ditolak tidak dihitung

drops = d[d["is_drop"]]
if not include_drop:
    d = d[~d["is_drop"]]

stores = sorted(d[COL_STORE].unique())
pilih = st.multiselect("Filter toko (kosong = semua)", stores)
if pilih:
    d = d[d[COL_STORE].isin(pilih)]
    drops = drops[drops[COL_STORE].isin(pilih)]

if d.empty:
    st.info("Belum ada data setoran pada periode ini.")
    st.stop()

# =====================================================
# RINGKASAN PER TOKO
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
)
ringkas["Belum Verified"] = ringkas["Total"] - ringkas["Verified"]
jumlah_hari = (end - start).days + 1
ringkas["Hari Kurang"] = (jumlah_hari - ringkas["Hari_Terisi"]).clip(lower=0)
ringkas = ringkas.rename(columns={"Hari_Terisi": "Hari Terisi", COL_STORE: "Store"})

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Pagi", rp(ringkas["Pagi"].sum()))
m2.metric("Total Siang", rp(ringkas["Siang"].sum()))
m3.metric("Total Setoran", rp(ringkas["Total"].sum()))
m4.metric("Belum Verified Finance", rp(ringkas["Belum Verified"].sum()))

st.markdown("### Ringkasan per Toko")
num_cfg = {c: st.column_config.NumberColumn(format="%d") for c in ["Pagi", "Siang", "Total", "Verified", "Belum Verified"]}
st.dataframe(ringkas, use_container_width=True, hide_index=True, column_config=num_cfg)

kurang = ringkas[ringkas["Hari Kurang"] > 0]
if not kurang.empty:
    daftar = ", ".join(
        f"{store} ({n} hari)" for store, n in zip(kurang["Store"], kurang["Hari Kurang"])
    )
    st.warning(f"Toko dengan hari belum terisi: {daftar}")

st.markdown("### Pagi vs Siang per Toko")
st.bar_chart(ringkas.set_index("Store")[["Pagi", "Siang"]])

# =====================================================
# TITIPAN (DROP)
# =====================================================
if not drops.empty:
    with st.expander("Titipan (Drop) diterima per toko"):
        t = (
            drops.groupby([COL_STORE, "Asal Drop"], as_index=False)["Total"]
            .sum()
            .rename(columns={COL_STORE: "Toko Penerima", "Total": "Nominal"})
        )
        st.dataframe(t, use_container_width=True, hide_index=True,
                     column_config={"Nominal": st.column_config.NumberColumn(format="%d")})

# =====================================================
# DETAIL PER HARI
# =====================================================
harian = (
    d.groupby([COL_TANGGAL, COL_STORE], as_index=False)
    .agg(Pagi=(COL_PAGI, "sum"), Siang=(COL_SIANG, "sum"), Total=("Total", "sum"))
    .sort_values([COL_STORE, COL_TANGGAL])
)
with st.expander("Detail per hari"):
    st.dataframe(harian, use_container_width=True, hide_index=True)

st.download_button(
    "Unduh ringkasan (CSV)",
    ringkas.to_csv(index=False).encode("utf-8"),
    file_name=f"setoran_{start}_{end}.csv",
    mime="text/csv",
)

# =====================================================
# AI (opsional) - aktif jika ANTHROPIC_API_KEY ada di Secrets
# =====================================================
st.markdown("### Tanya AI tentang data ini")
if "ANTHROPIC_API_KEY" not in st.secrets:
    st.info("Fitur AI belum aktif. Isi ANTHROPIC_API_KEY di Secrets Streamlit untuk mengaktifkan.")
else:
    tanya = st.text_input("Contoh: toko mana yang setoran siangnya paling rendah?")
    if st.button("Tanya") and tanya:
        import anthropic

        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        konteks = (
            "RINGKASAN PER TOKO:\n" + ringkas.head(100).to_csv(index=False)
            + "\nDETAIL PER HARI:\n" + harian.head(300).to_csv(index=False)
        )
        with st.spinner("AI sedang menganalisa..."):
            res = client.messages.create(
                model="claude-sonnet-5-5",
                max_tokens=1000,
                system=(
                    "Anda analis keuangan. Jawab dalam Bahasa Indonesia, singkat, "
                    "hanya berdasarkan data yang diberikan. Jika data tidak cukup, katakan."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": f"Periode {start} s/d {end}.\n{konteks}\n\nPertanyaan: {tanya}",
                    }
                ],
            )
        st.write(res.content[0].text)
