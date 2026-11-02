# Dashboard Monitoring Setoran Omset Cash (Streamlit)
# Membaca Google Sheet yang sama dengan aplikasi Apps Script. Pick up tampil langsung (tanpa menunggu approval)
# lengkap dengan foto bukti, status Manager dan FRA.
import base64
import html
import io
import math
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

SHEET_ID = "1bCvWOsmBIr568kzoNed3gzmPk8EnCAXwE0umdeDj5D4"
# GID tab (angka setelah "gid=" di alamat sheet). Jika kosong, tab dibaca lewat nama tab.
GID = {"Data Setoran": "1032464994", "Data Pickup": "", "Master Store": ""}
TZ = ZoneInfo("Asia/Pontianak")
# Jadwal pick up: 0 = Senin, 3 = Kamis. Angka = berapa hari omset sebelumnya yang diambil.
# Senin mengambil omset Kamis-Minggu (4 hari); Kamis mengambil omset Senin-Rabu (3 hari).
PICKUP_COVER = {0: 4, 3: 3}
PER_PAGE = 10
LOGO = "https://drive.google.com/thumbnail?id=1VzTk_XgppZ2HhVS1dUgKiogRD1u8jRWS&sz=w128"
BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
E = lambda s: html.escape(str(s if s is not None else ""))


# ---------------------------------------------------------------- data
def _csv(url, params=None):
    r = requests.get(url, params=params, timeout=40)
    r.raise_for_status()
    r.encoding = "utf-8"
    return pd.read_csv(io.StringIO(r.text), dtype=str, keep_default_na=False)


@st.cache_data(ttl=120, show_spinner=False)
def read_tab(name):
    base = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    gid = GID.get(name, "")
    try:
        if gid:
            df = _csv(f"{base}/export", {"format": "csv", "gid": gid})
        else:
            df = _csv(f"{base}/gviz/tq", {"tqx": "out:csv", "sheet": name, "headers": 1})
    except Exception:
        return pd.DataFrame()
    df.columns = [str(c).strip() for c in df.columns]
    return df


@st.cache_data(ttl=3600, show_spinner=False)
def db_photo(pid):
    """Foto yang tersimpan di tab 'Data Foto' (cadangan jika Google Drive gagal)."""
    if not re.fullmatch(r"[0-9a-f]{12}", str(pid)):
        return None
    try:
        df = _csv(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq",
                  {"tqx": "out:csv", "sheet": "Data Foto", "tq": f"select C,D where A = '{pid}' order by C"})
        parts = [str(x)[1:] for x in df.iloc[:, 1].tolist()]
        return base64.b64decode("".join(parts)) if parts else None
    except Exception:
        return None


def to_int(v):
    s = re.sub(r"[^\d\-]", "", str(v))
    return int(s) if s not in ("", "-") else 0


def to_date(v):
    s = str(v)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        try:
            return date(int(m[3]), int(m[2]), int(m[1]))
        except ValueError:
            return None
    return None


def col(df, name):
    return df[name].astype(str) if name in df.columns else pd.Series([""] * len(df), index=df.index)


def prep_setoran(df):
    if df.empty:
        return pd.DataFrame()
    s = pd.DataFrame({
        "store": col(df, "Store").str.strip(), "tgl": col(df, "Tanggal").map(to_date),
        "cashier": col(df, "Cashier").str.strip(), "pagi": col(df, "Setoran Pagi").map(to_int),
        "siang": col(df, "Setoran Siang").map(to_int), "total": col(df, "Total Setoran").map(to_int),
        "mS": col(df, "Status Mgr").str.strip(), "fS": col(df, "Status FRA").str.strip(),
        "fotoPagi": col(df, "Foto Pagi").str.strip(), "fotoSiang": col(df, "Foto Siang").str.strip(),
        "foto": col(df, "Foto Bukti").str.strip(), "tipe": col(df, "Tipe Shift").str.strip(),
        "ket": col(df, "Remark Pagi").str.strip(),
    })
    s["total"] = s["total"].where(s["total"] != 0, s["pagi"] + s["siang"])
    s["dropin"] = s["cashier"].str.startswith("Drop dari")
    return s[s["store"] != ""]


def prep_pickup(df):
    if df.empty:
        return pd.DataFrame()
    p = pd.DataFrame({
        "id": col(df, "ID").str.strip(), "store": col(df, "Store").str.strip(),
        "tgl": col(df, "Tanggal Pickup").map(to_date), "vendor": col(df, "Vendor").str.strip(),
        "jml": col(df, "Jumlah").map(to_int), "by": col(df, "Diinput Oleh").str.strip(),
        "mS": col(df, "Status Mgr").str.strip(), "mBy": col(df, "Mgr Oleh").str.strip(),
        "fS": col(df, "Status FRA").str.strip(), "fBy": col(df, "FRA Oleh").str.strip(),
        "foto": col(df, "Foto Bukti").str.strip(), "jenis": col(df, "Jenis").str.strip(),
        "waktu": col(df, "Waktu Input").str.strip(),
    })
    p["kind"] = ["tambahan" if j == "tambahan" else "drop" if v.startswith("Drop ke Store") else "pickup"
                 for j, v in zip(p["jenis"], p["vendor"])]
    return p[p["store"] != ""]


def store_names():
    m = read_tab("Master Store")
    if m.empty or "Kode Store" not in m.columns or "Nama Store" not in m.columns:
        return {}
    return {str(k).strip(): str(v).strip() for k, v in zip(m["Kode Store"], m["Nama Store"]) if str(k).strip()}


# ---------------------------------------------------------------- periode
def last_pickup_day(today):
    for i in range(8):
        d = today - timedelta(days=i)
        if d.weekday() in PICKUP_COVER:
            return d


def fdate(d):
    return f"{d.day} {BULAN[d.month - 1]} {d.year}"


def periods(today, mode, manual=None):
    """Mengembalikan (rentang omset, rentang pick up, label)."""
    pd_ = last_pickup_day(today)
    if mode == "Pilih manual" and manual:
        a, b = manual
        return (a, b), (a, b), f"{fdate(a)} – {fdate(b)}"
    if mode == "Periode berjalan":
        o, p = (pd_, today), (pd_ + timedelta(days=1), today)
        return o, p, f"Omset berjalan {fdate(o[0])} – {fdate(o[1])}"
    o0 = pd_ - timedelta(days=PICKUP_COVER[pd_.weekday()])
    o, p = (o0, pd_ - timedelta(days=1)), (o0 + timedelta(days=1), pd_)
    return o, p, f"Omset {HARI[o0.weekday()]} {fdate(o[0])} – {HARI[o[1].weekday()]} {fdate(o[1])} · Pick up {HARI[pd_.weekday()]} {fdate(pd_)}"


def within(series, rng):
    return series.map(lambda d: d is not None and rng[0] <= d <= rng[1])


# ---------------------------------------------------------------- ringkasan
def rp(n):
    n = int(n or 0)
    return ("-" if n < 0 else "") + "Rp " + f"{abs(n):,}".replace(",", ".")


def summarize(S, P, orng, prng, only=None):
    rows = {}
    g = lambda k: rows.setdefault(k, dict(store=k, omset=0, drop_in=0, pickup=0, drop=0, tambah=0, trx=0, tunggu_m=0, tunggu_f=0))
    if not S.empty:
        s = S[within(S["tgl"], orng) & (S["mS"] != "Ditolak")]
        for r in s[~s["dropin"]].itertuples():
            g(r.store)["omset"] += r.total
        s2 = S[within(S["tgl"], prng) & (S["mS"] != "Ditolak") & S["dropin"]]
        for r in s2.itertuples():
            g(r.store)["drop_in"] += r.total
    if not P.empty:
        p = P[within(P["tgl"], prng)]
        for r in p.itertuples():
            x = g(r.store)
            if r.mS == "Ditolak":
                continue
            if r.kind == "pickup":
                x["pickup"] += r.jml
                x["trx"] += 1
            elif r.kind == "drop":
                x["drop"] += r.jml
            else:
                x["tambah"] += r.jml
            if r.mS != "Verified":
                x["tunggu_m"] += 1
            elif r.fS != "Verified":
                x["tunggu_f"] += 1
    for x in rows.values():
        x["selisih"] = x["omset"] + x["drop_in"] + x["tambah"] - x["pickup"] - x["drop"]
    if only:
        rows = {k: v for k, v in rows.items() if k == only}
    return rows


# ---------------------------------------------------------------- tampilan
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"], [data-testid="collapsedControl"], #MainMenu, header, footer { display: none !important; }
.block-container { max-width: 1280px; padding-top: 1.4rem; padding-bottom: 3rem; }
.top { display:flex; align-items:center; gap:14px; padding-bottom:14px; border-bottom:3px solid #1d4ed8; margin-bottom:18px; }
.top img { height:44px; background:#fff; border-radius:8px; }
.top h1 { font-size:1.6rem; margin:0; color:#0f172a; font-weight:700; }
.top p { margin:0; color:#64748b; font-size:.9rem; }
.hero { background:linear-gradient(135deg,#0f172a,#1e3a8a); color:#f8fafc; border-radius:16px; padding:28px 32px; margin:10px 0 16px; }
.hero .l { font-size:.95rem; color:#bfdbfe; font-weight:500; letter-spacing:.3px; }
.hero .v { font-size:2.8rem; font-weight:700; line-height:1.15; margin:4px 0; }
.hero .s { color:#cbd5e1; font-size:.92rem; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin-bottom:8px; }
.card { background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:14px 18px; }
.card .l { color:#64748b; font-size:.82rem; font-weight:500; }
.card .v { color:#0f172a; font-size:1.35rem; font-weight:700; }
h3.sec { font-size:1.1rem; color:#0f172a; margin:26px 0 10px; font-weight:700; }
table.t { width:100%; border-collapse:collapse; font-size:.86rem; background:#fff; border:1px solid #e2e8f0; border-radius:10px; overflow:hidden; }
table.t th { background:#f1f5f9; color:#0f172a; text-align:left; padding:9px 12px; font-weight:600; }
table.t td { padding:8px 12px; border-top:1px solid #eef2f7; color:#334155; vertical-align:top; }
table.t td.n, table.t th.n { text-align:right; font-variant-numeric:tabular-nums; }
.badge { display:inline-block; font-size:.74rem; font-weight:600; padding:2px 10px; border-radius:99px; margin:0 6px 4px 0; background:#e2e8f0; color:#334155; }
.b-ok { background:#dcfce7; color:#166534; } .b-wait { background:#fef3c7; color:#92400e; } .b-bad { background:#fee2e2; color:#991b1b; } .b-info { background:#dbeafe; color:#1e40af; }
.item .h { font-weight:600; color:#0f172a; } .item .a { font-size:1.35rem; font-weight:700; color:#0f172a; margin:2px 0 6px; }
.item .m { color:#64748b; font-size:.85rem; }
.foot { text-align:center; color:#94a3b8; font-size:.85rem; margin-top:40px; padding-top:16px; border-top:1px solid #e2e8f0; }
</style>
"""


def table(rows, cols, empty="Tidak ada data."):
    if not rows:
        return f"<div class='card'>{E(empty)}</div>"
    h = "".join(f"<th class='{'n' if k == 'n' else ''}'>{E(lbl)}</th>" for _, lbl, k in cols)
    b = "".join("<tr>" + "".join(f"<td class='{'n' if k == 'n' else ''}'>{c(r)}</td>" for c, _, k in cols) + "</tr>" for r in rows)
    return f"<table class='t'><tr>{h}</tr>{b}</table>"


def drive_id(u):
    m = re.search(r"/d/([\w-]{20,})", u) or re.search(r"[?&]id=([\w-]{20,})", u)
    return m.group(1) if m else None


def show_photo(u, width=320):
    u = str(u).strip()
    if not u:
        st.caption("Tidak ada foto bukti")
    elif u.startswith("DB:"):
        b = db_photo(u[3:])
        st.image(b, width=width) if b else st.caption("Foto tidak dapat dimuat")
    elif drive_id(u):
        st.image(f"https://drive.google.com/thumbnail?id={drive_id(u)}&sz=w1000", width=width)
        st.markdown(f"[Buka foto asli]({u})")
    elif u.startswith("http"):
        st.image(u, width=width)
        st.markdown(f"[Buka foto asli]({u})")


def badges(r):
    m = {"Verified": ("Disetujui Manager", "b-ok"), "Menunggu": ("Menunggu Manager", "b-wait"), "Ditolak": ("Ditolak", "b-bad")}.get(r.mS, ("Menunggu Manager", "b-wait"))
    out = f"<span class='badge {m[1]}'>{m[0]}</span>"
    if r.mS != "Ditolak":
        out += "<span class='badge b-ok'>Terverifikasi FRA</span>" if r.fS == "Verified" else "<span class='badge b-wait'>Menunggu FRA</span>"
    kind = {"drop": "Drop ke store lain", "tambahan": "Setoran tambahan"}.get(r.kind)
    return out + (f"<span class='badge b-info'>{kind}</span>" if kind else "")


def main():
    st.set_page_config(page_title="Setoran Omset Cash", layout="wide", initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)
    today = datetime.now(TZ).date()

    S = prep_setoran(read_tab("Data Setoran"))
    P = prep_pickup(read_tab("Data Pickup"))
    names = store_names()
    if S.empty and P.empty:
        st.error("Data tidak dapat dibaca. Pastikan Google Sheet dibagikan dengan akses 'Siapa saja yang memiliki link' (Viewer).")
        st.stop()

    st.markdown(f"<div class='top'><img src='{LOGO}'><div><h1>Setoran Omset Cash</h1><p>Monitoring setoran omset dan pick up seluruh store</p></div></div>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns([2.2, 2.2, 2.2, 0.8])
    mode = c1.radio("Periode pengecekan", ["Periode pick up terakhir", "Periode berjalan", "Pilih manual"], horizontal=False)
    manual = None
    if mode == "Pilih manual":
        v = c2.date_input("Rentang tanggal", value=(today - timedelta(days=6), today))
        manual = (v[0], v[1]) if isinstance(v, (tuple, list)) and len(v) == 2 else (v, v) if isinstance(v, date) else None
        if not manual:
            c2.info("Pilih tanggal akhir.")
            st.stop()
    codes = sorted(set(S["store"]) | set(P["store"]) | set(names)) if not S.empty or not P.empty else []
    label = lambda k: f"{k} - {names[k]}" if names.get(k) else k
    pick = c3.selectbox("Store", ["Semua Store"] + codes, format_func=lambda k: k if k == "Semua Store" else label(k))
    c4.write("")
    if c4.button("Muat ulang"):
        st.cache_data.clear()
        st.rerun()
    only = None if pick == "Semua Store" else pick
    orng, prng, plabel = periods(today, mode, manual)

    rows = summarize(S, P, orng, prng, only)
    tot = {k: sum(r[k] for r in rows.values()) for k in ("omset", "drop_in", "pickup", "drop", "tambah", "trx", "tunggu_m", "tunggu_f", "selisih")}
    st.markdown(
        f"<div class='hero'><div class='l'>Total Nominal Pick up</div><div class='v'>{rp(tot['pickup'])}</div>"
        f"<div class='s'>{E(plabel)} · {E(label(pick) if only else 'Semua store')} · {tot['trx']} transaksi pick up</div></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='cards'>"
        f"<div class='card'><div class='l'>Total Setoran Omset</div><div class='v'>{rp(tot['omset'])}</div></div>"
        f"<div class='card'><div class='l'>Drop ke Store Lain</div><div class='v'>{rp(tot['drop'])}</div></div>"
        f"<div class='card'><div class='l'>Setoran Tambahan</div><div class='v'>{rp(tot['tambah'])}</div></div>"
        f"<div class='card'><div class='l'>Selisih Periode</div><div class='v'>{rp(tot['selisih'])}</div></div>"
        f"<div class='card'><div class='l'>Menunggu Manager / FRA</div><div class='v'>{tot['tunggu_m']} / {tot['tunggu_f']}</div></div>"
        "</div>", unsafe_allow_html=True)

    # rincian per store
    st.markdown("<h3 class='sec'>Rincian per Store</h3>", unsafe_allow_html=True)
    lst = sorted(rows.values(), key=lambda x: -x["pickup"])
    lst = [x for x in lst if any(x[k] for k in ("omset", "pickup", "drop", "tambah", "drop_in"))]
    cols = [(lambda r: f"<b>{E(r['store'])}</b><br><span style='color:#64748b'>{E(names.get(r['store'], ''))}</span>", "Store", ""),
            (lambda r: rp(r["omset"]), "Setoran Omset", "n"), (lambda r: f"<b>{rp(r['pickup'])}</b>", "Pick up", "n"),
            (lambda r: rp(r["drop"]), "Drop", "n"), (lambda r: rp(r["tambah"]), "Tambahan", "n"),
            (lambda r: rp(r["selisih"]), "Selisih", "n"), (lambda r: str(r["trx"]), "Transaksi", "n"),
            (lambda r: str(r["tunggu_m"]), "Tunggu Manager", "n"), (lambda r: str(r["tunggu_f"]), "Tunggu FRA", "n")]
    st.markdown(table(lst, cols, "Belum ada data pada periode ini."), unsafe_allow_html=True)

    # rincian transaksi + foto
    st.markdown("<h3 class='sec'>Rincian Transaksi Pick up dan Foto Bukti</h3>", unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    kf = f1.selectbox("Jenis", ["Semua", "Pick up vendor", "Drop", "Tambahan"])
    sf = f2.selectbox("Status", ["Semua", "Menunggu Manager", "Disetujui Manager", "Menunggu FRA", "Terverifikasi FRA", "Ditolak"])
    show = f3.toggle("Tampilkan foto", value=True)
    items = P[within(P["tgl"], prng)] if not P.empty else P
    if not items.empty:
        if only:
            items = items[items["store"] == only]
        items = items[items["kind"].isin({"Pick up vendor": ["pickup"], "Drop": ["drop"], "Tambahan": ["tambahan"]}.get(kf, ["pickup", "drop", "tambahan"]))]
        items = {
            "Menunggu Manager": items[items["mS"] == "Menunggu"], "Disetujui Manager": items[items["mS"] == "Verified"],
            "Menunggu FRA": items[(items["mS"] == "Verified") & (items["fS"] != "Verified")],
            "Terverifikasi FRA": items[items["fS"] == "Verified"], "Ditolak": items[items["mS"] == "Ditolak"],
        }.get(sf, items)
        items = items.sort_values(["tgl", "waktu"], ascending=False)
    n = len(items)
    pages = max(1, math.ceil(n / PER_PAGE))
    page = f4.number_input("Halaman", min_value=1, max_value=pages, value=1, step=1)
    st.caption(f"{n} transaksi · halaman {page} dari {pages}")
    if n == 0:
        st.markdown("<div class='card'>Belum ada transaksi pick up pada periode ini.</div>", unsafe_allow_html=True)
    for r in items.iloc[(page - 1) * PER_PAGE: page * PER_PAGE].itertuples():
        with st.container(border=True):
            a, b = st.columns([3, 2]) if show else (st.container(), None)
            a.markdown(
                f"<div class='item'><div class='h'>{E(label(r.store))} · {E(fdate(r.tgl) if r.tgl else '-')}</div>"
                f"<div class='a'>{'+ ' if r.kind == 'tambahan' else ''}{rp(r.jml)}</div>{badges(r)}"
                f"<div class='m'>{E(r.vendor)}<br>Diinput oleh {E(r.by)}{(' · Manager: ' + E(r.mBy)) if r.mBy else ''}{(' · FRA: ' + E(r.fBy)) if r.fBy else ''}</div></div>",
                unsafe_allow_html=True)
            if b is not None:
                with b:
                    show_photo(r.foto)

    # rincian setoran harian + foto
    with st.expander("Rincian Setoran Harian dan Foto Bukti Omset"):
        sd = S[within(S["tgl"], orng) & ~S["dropin"]] if not S.empty else S
        if only and not sd.empty:
            sd = sd[sd["store"] == only]
        sd = sd.sort_values(["tgl", "store"], ascending=False) if not sd.empty else sd
        srows = [r for r in sd.itertuples()]
        scols = [(lambda r: f"<b>{E(r.store)}</b><br><span style='color:#64748b'>{E(names.get(r.store, ''))}</span>", "Store", ""),
                 (lambda r: E(fdate(r.tgl) if r.tgl else "-"), "Tanggal", ""), (lambda r: E(r.cashier), "Cashier", ""),
                 (lambda r: rp(r.pagi), "Pagi", "n"), (lambda r: rp(r.siang), "Siang", "n"), (lambda r: f"<b>{rp(r.total)}</b>", "Total", "n"),
                 (lambda r: {"Verified": "Disetujui", "Ditolak": "Ditolak"}.get(r.mS, "Menunggu") + " / " + ("Terverifikasi" if r.fS == "Verified" else "Menunggu"), "Manager / FRA", "")]
        st.markdown(table(srows[:300], scols, "Belum ada setoran pada periode ini."), unsafe_allow_html=True)
        if srows:
            opt = srows[:300]
            idx = st.selectbox("Lihat foto bukti setoran", range(len(opt)), format_func=lambda i: f"{opt[i].store} · {fdate(opt[i].tgl) if opt[i].tgl else '-'} · {opt[i].cashier}")
            r = opt[idx]
            ph = [("Pagi" if r.tipe != "full" else "Full", r.fotoPagi or r.foto), ("Siang", r.fotoSiang)]
            cc = st.columns(2)
            for c, (lbl, u) in zip(cc, ph):
                if u or lbl != "Siang":
                    with c:
                        st.markdown(f"**{lbl}**")
                        show_photo(u)

    st.markdown("<div class='foot'>Powered and developed by M Khadafi</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
