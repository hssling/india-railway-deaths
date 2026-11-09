"""Extract a validated state x year panel of railway deaths from NCRB ADSI PDFs (2014, 2015, 2018-2024).

Tables (state/UT-wise, printed totals kept as printed):
  traffic      Table 1A.2  Cases/Injured/Died due to Traffic Accidents (Road, Railway, Railway Crossing,
                           [2024: Incidents on Railway Tracks/In Railway Premises], Total Traffic)
  rly_class    Table 1A.12 Classification of Railway Accidents (2014-2023: Collisions, Derailments, Fall from
                           Train/Collision with People at Tracks, Explosion/Fire, Others, Total;
                           2024: Collisions, Derailments, Explosion/Fire, Total)
  rly_incid    Table 1A.13 (2024 only) Classification of Incidents on Railway Tracks/In Railway Premises
                           (Fall from Train/Collision with People at Tracks, Others, Total)
  rly_cause    Table 1A.13 (2014-2023) / 1A.14 (2024) Cause-wise Distribution of Railway Accidents
  unmanned     Table 1A.9  column group 'Unmanned Railway Crossing (Accidents)' (state-wise)

Method: PyMuPDF word coordinates. Data columns are anchored on the printed column-number line '(1) (2) (3)...';
each number token is assigned to the nearest column-number x-centre; numbers are grouped into rows by y-centre;
row labels (incl. names wrapped over two text lines) are attached to the nearest numeric row by y.
Column-group labels are read from the header words lying above each triple of Cases/Injured/Died columns.

Validation: vertical (states -> TOTAL (STATES), UTs -> TOTAL (UTs), STATES+UTs -> TOTAL (ALL INDIA)) for every
column; horizontal (categories -> printed Total per row and measure); cross-table and narrative checks.
Usage: python -I src/extract_adsi_railway.py
"""
import os
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import fitz  # PyMuPDF

sys.stdout.reconfigure(encoding="utf-8")

RAW = Path(os.environ.get("RAILWAY_RAW", Path(__file__).resolve().parents[1] / "data_raw"))   # see README
PDFS = {2014: RAW / "ncrb/ADSI_2014.pdf", 2015: RAW / "ncrb/ADSI_2015.pdf"}
PDFS.update({y: RAW / f"ncrb/ADSI_{y}.pdf" for y in range(2018, 2025)})
PROJ = Path(__file__).resolve().parents[1]
DATA = PROJ / "data"

NUM_RE = re.compile(r"^-?\d+$")
COLNUM_RE = re.compile(r"^\(\d+\)$")

# ----------------------------------------------------------------------------------------------- states
CANON = {
    "ANDHRA PRADESH": "Andhra Pradesh", "ARUNACHAL PRADESH": "Arunachal Pradesh", "ASSAM": "Assam",
    "BIHAR": "Bihar", "CHHATTISGARH": "Chhattisgarh", "GOA": "Goa", "GUJARAT": "Gujarat",
    "HARYANA": "Haryana", "HIMACHAL PRADESH": "Himachal Pradesh", "JAMMU & KASHMIR": "Jammu & Kashmir",
    "JHARKHAND": "Jharkhand", "KARNATAKA": "Karnataka", "KERALA": "Kerala",
    "MADHYA PRADESH": "Madhya Pradesh", "MAHARASHTRA": "Maharashtra", "MANIPUR": "Manipur",
    "MEGHALAYA": "Meghalaya", "MIZORAM": "Mizoram", "NAGALAND": "Nagaland", "ODISHA": "Odisha",
    "PUNJAB": "Punjab", "RAJASTHAN": "Rajasthan", "SIKKIM": "Sikkim", "TAMIL NADU": "Tamil Nadu",
    "TELANGANA": "Telangana", "TRIPURA": "Tripura", "UTTAR PRADESH": "Uttar Pradesh",
    "UTTARAKHAND": "Uttarakhand", "WEST BENGAL": "West Bengal",
    "A & N ISLANDS": "Andaman & Nicobar Islands", "CHANDIGARH": "Chandigarh",
    "D & N HAVELI": "Dadra & Nagar Haveli and Daman & Diu",
    "DAMAN & DIU": "Dadra & Nagar Haveli and Daman & Diu",
    "D & N HAVELI AND DAMAN & DIU": "Dadra & Nagar Haveli and Daman & Diu",
    "DELHI (UT)": "Delhi", "DELHI": "Delhi", "LAKSHADWEEP": "Lakshadweep", "LADAKH": "Ladakh",
    "PUDUCHERRY": "Puducherry",
}
# time-consistent panel unit (J&K+Ladakh merged; DNH+DD merged)
PANEL = {"Jammu & Kashmir": "Jammu & Kashmir incl. Ladakh", "Ladakh": "Jammu & Kashmir incl. Ladakh"}

# Data-quality flags: values are internally consistent (validated) and kept AS PRINTED, but implausible
# year-on-year patterns suggest misclassification/under-reporting by the reporting State (see docs/extraction_notes.md).
FLAGS = {
    (2014, "Telangana"): "FLAG: railway deaths 3 but railway-crossing deaths 1,070 (2015: 1,144 / 9) - probable misfiling of railway deaths as crossing deaths",
    (2015, "Haryana"): "FLAG: railway deaths 1 but railway-crossing deaths 1,286 (2014: 1,361 / 19; 2018: 2,141 / 8) - probable misfiling of railway deaths as crossing deaths",
    (2014, "Bihar"): "FLAG: railway deaths 604 vs 1,891 in 2015 while crossing deaths 485 vs 16 - possible misfiling between railway and crossing",
    (2015, "Andhra Pradesh"): "FLAG: railway-crossing deaths 268 vs <=4 in all other years",
    (2015, "Karnataka"): "FLAG: Karnataka reports 891 railway deaths in 2015 but 25 (2014) and 0 in every year 2018-2024 - Karnataka railway deaths are effectively unreported in ADSI",
    (2014, "Assam"): "FLAG: Table 1A.9 unmanned-crossing deaths 654 vs Table 1A.2 railway-crossing deaths 11",
    (2022, "Odisha"): "FLAG: railway deaths 27 vs 280-446 in 2018-2021",
    (2023, "Odisha"): "FLAG: printed 0 railway accidents with footnote '*Clarification on Railway Accidents data is pending from Odisha' - the June 2023 Balasore (Bahanaga Bazar) triple-train collision is therefore absent from ADSI 2023",
}
for _y in (2018, 2019, 2020, 2021, 2022, 2023, 2024):
    FLAGS.setdefault((_y, "Karnataka"), "FLAG: Karnataka prints 0 railway accidents/deaths (implausible; under-reporting)")


def norm_name(s):
    s = re.sub(r"\s+", " ", s.replace("&", " & ").replace("*", "")).strip().upper()
    return s


def compact(s):
    return re.sub(r"[^A-Z&()]", "", norm_name(s))


CANON_C = {compact(k): v for k, v in CANON.items()}


def canon_note(year, printed):
    n = norm_name(printed)
    c = CANON_C.get(compact(printed))
    note = "printed with '*' footnote marker (see table footnote)" if "*" in printed else ""
    if compact(n) in ("D&NHAVELI", "DAMAN&DIU"):
        note = "printed separately pre-2020; canonical = merged UT (sum in wide file)"
    if compact(n) == "JAMMU&KASHMIR" and year < 2020:
        note = "pre-2020 J&K State includes Ladakh"
    return c, note


# ----------------------------------------------------------------------------------------------- page parser
def ycen(w):
    return (w[1] + w[3]) / 2


def xcen(w):
    return (w[0] + w[2]) / 2


def cluster_y(words, tol):
    words = sorted(words, key=lambda w: (ycen(w), w[0]))
    out, cur, cy = [], [], None
    for w in words:
        c = ycen(w)
        if cy is None or abs(c - cy) <= tol:
            cur.append(w)
            cy = c if cy is None else cy
        else:
            out.append(cur)
            cur, cy = [w], c
    if cur:
        out.append(cur)
    return out


def parse_page(page, log):
    """Return dict(groups=[(label, [col_idx...])], rows=[dict(label, serial, y, vals{col:int|None})], meta)."""
    words = page.get_text("words")
    lines = cluster_y(words, 3.5)
    # column-number line
    colline = None
    for ln in lines:
        toks = [w for w in ln if COLNUM_RE.match(w[4])]
        if len(toks) >= 5 and len(toks) >= 0.8 * len(ln):
            colline = sorted(toks, key=lambda w: w[0])
            break
    if colline is None:
        raise RuntimeError("no column-number line")
    y_col = ycen(colline[0])
    data_cols = colline[2:]                       # (1)=Sl.No, (2)=State/UT
    cx = [xcen(w) for w in data_cols]
    spacing = min(b - a for a, b in zip(cx, cx[1:])) if len(cx) > 1 else 40
    left_edge = cx[0] - spacing / 2
    # measure line (Cases Injured Died) just above the column numbers
    meas_line = None
    for ln in lines:
        if ycen(ln[0]) < y_col and sum(w[4] in ("Cases", "Injured", "Died") for w in ln) >= 3:
            meas_line = ln
    measures = []
    for c in cx:
        w = min(meas_line, key=lambda w: abs(xcen(w) - c))
        measures.append({"Cases": "cases", "Injured": "injured", "Died": "died"}.get(w[4], "?" + w[4]))
    y_meas = ycen(meas_line[0])
    # header-zone top: below last title-ish line
    y_top = 0
    for ln in lines:
        t = " ".join(w[4] for w in sorted(ln, key=lambda w: w[0]))
        if ycen(ln[0]) < y_meas and re.search(r"Table\s*1A|wise\s*\)|during\s+\d{4}|\(Contd|\(Concluded", t):
            y_top = max(y_top, max(w[3] for w in ln))
    # groups of three columns (cases, injured, died)
    groups = []
    i = 0
    while i < len(cx):
        if measures[i:i + 3] == ["cases", "injured", "died"]:
            groups.append([i, i + 1, i + 2]); i += 3
        else:
            groups.append([i]); i += 1
    hdr_words = [w for w in words if y_top < ycen(w) < y_meas - 2 and xcen(w) > left_edge]
    glabels = []
    for g in groups:
        lo, hi = cx[g[0]] - spacing / 2, cx[g[-1]] + spacing / 2
        gw = [w for w in hdr_words if lo <= xcen(w) < hi]
        lab = " ".join(w[4] for l in cluster_y(gw, 2.5) for w in sorted(l, key=lambda w: w[0]))
        glabels.append(re.sub(r"\s+", " ", lab).strip())
    # numeric rows
    below = [w for w in words if ycen(w) > y_col + 3]
    numw = [w for w in below if xcen(w) > left_edge and (NUM_RE.match(w[4]) or w[4] in ("-", "--"))]
    rows = []
    for cl in cluster_y(numw, 2.5):
        vals, clash = {}, []
        for w in cl:
            j = min(range(len(cx)), key=lambda k: abs(xcen(w) - cx[k]))
            if abs(xcen(w) - cx[j]) > spacing * 0.6:
                clash.append(f"token {w[4]} far from any column")
                continue
            v = int(w[4]) if NUM_RE.match(w[4]) else None
            if j in vals:
                clash.append(f"two tokens in column {j}")
            vals[j] = v
        rows.append(dict(y=ycen(cl[0]), vals=vals, clash=clash, label_words=[]))
    # stray numeric tokens (page numbers in the footer etc.) are not table rows
    for r in [r for r in rows if len(r["vals"]) <= 2 and len(cx) > 3]:
        log.append(f"IGNORED  stray numeric line y={r['y']:.1f} values={list(r['vals'].values())} (page number/footnote)")
        rows.remove(r)
    if not rows:
        raise RuntimeError("no numeric rows")
    y_last = max(r["y"] for r in rows)
    # label words
    sections = []
    for w in below:
        if xcen(w) > left_edge or ycen(w) > y_last + 9:
            continue
        rows_sorted = sorted(rows, key=lambda r: abs(r["y"] - ycen(w)))
        r = rows_sorted[0]
        if abs(r["y"] - ycen(w)) > 9:
            sections.append(w)
            continue
        r["label_words"].append(w)
    sl_x = xcen(colline[0])
    for r in rows:
        lw = sorted(r["label_words"], key=lambda w: (round(ycen(w)), w[0]))
        serial = None
        name = []
        for w in lw:
            if serial is None and NUM_RE.match(w[4]) and abs(xcen(w) - sl_x) < 15:
                serial = int(w[4])
            else:
                name.append(w)
        # order wrapped names by text line then x
        name = [w for l in cluster_y(name, 2.0) for w in sorted(l, key=lambda w: w[0])]
        r["label"] = re.sub(r"\s+", " ", " ".join(w[4] for w in name)).strip()
        r["serial"] = serial
    ai = [r["y"] for r in rows if r["label"].upper().startswith("TOTAL (ALL INDIA)")]
    foot = ""
    if ai:
        fl = cluster_y([w for w in words if ycen(w) > ai[0] + 5], 3.0)
        fl = [" ".join(w[4] for w in sorted(l, key=lambda w: w[0])) for l in fl]
        foot = " ".join(t for t in fl if not re.match(r"^(Accidental Deaths|\[?\d+\]?$)", t)).strip()
        foot = foot.replace("\uf0b7", "").replace("\u2022", "").strip()
        for r in [r for r in rows if r["y"] > ai[0] + 1]:
            log.append(f"IGNORED  numeric line below TOTAL (ALL INDIA): '{r['label']}' {list(r['vals'].values())}")
            rows.remove(r)
    sec_text = " ".join(w[4] for w in sections)
    return dict(groups=list(zip(glabels, groups)), measures=measures, rows=rows, ncol=len(cx),
                sections=sec_text, footnote=foot)


def classify_rows(rows):
    """Tag rows as state / ut / total_states / total_uts / total_all_india using printed order."""
    zone = "state"
    out = []
    for r in rows:
        lab = r["label"].upper()
        if lab.startswith("TOTAL (STATES)") or lab == "TOTAL (STATE)":
            r["kind"] = "total_states"; zone = "ut"
        elif lab.startswith("TOTAL (UT"):
            r["kind"] = "total_uts"
        elif lab.startswith("TOTAL (ALL INDIA)"):
            r["kind"] = "total_all_india"
        elif lab.startswith("TOTAL"):
            r["kind"] = "other_total"
        else:
            r["kind"] = zone
        out.append(r)
    return out


# ----------------------------------------------------------------------------------------------- table finder
def page_text(doc, i):
    return re.sub(r"\s+", " ", doc[i].get_text())


def find_pages(doc, year):
    """Return dict table_id -> list of (page_index, printed table number, printed title)."""
    found = defaultdict(list)
    for i in range(len(doc)):
        t = page_text(doc, i)
        if "TOTAL (ALL INDIA)" not in t:
            continue
        m = re.search(r"Table\s*(1A\.\d+)\s*(\((?:Contd|Concluded)[^)]*\))?\s*(.{0,160})", t)
        if not m:
            continue
        num, title = m.group(1), m.group(3)
        title = re.split(r"\(State|\(City|Sl\. ?No", title)[0].strip()
        if num == "1A.2" and "Traffic Accidents" in t:
            found["traffic"].append((i, num, title))
        elif num == "1A.12" and "Railway" in t:
            found["rly_class"].append((i, num, title))
        elif num == "1A.13" and year == 2024 and "Incidents on Railway" in t:
            found["rly_incid"].append((i, num, title))
        elif (num == "1A.13" and year < 2024 and "Railway" in t) or (num == "1A.14" and year == 2024):
            found["rly_cause"].append((i, num, title))
        elif num == "1A.9" and re.search(r"Unmanned\s+Railway\s+Crossing", t) and "STATES" in t:
            found["unmanned"].append((i, num, title))
    return found


# ----------------------------------------------------------------------------------------------- narrative
NUMTXT = r"(?:Zero\s*\(0\)|Nil|\d{1,2}(?:,\s?\d{2})*,\s?\d{3}|\d{1,3})"


def to_int(s):
    s = s.strip()
    if s.startswith("Zero") or s == "Nil":
        return 0
    return int(re.sub(r"[,\s]", "", s))


def narrative(doc, year):
    out = {}
    for i in range(min(40, len(doc))):
        t = page_text(doc, i)
        m = re.search(r"(?i:total of) [\d,\s]+.Traffic Accidents. were reported during the year(.{0,900}?)"
                      r"(It is worth|It is observed|It observed|Maximum number)", t)
        if not m:
            continue
        blk = m.group(1)
        q = "[\u2018\u2019'`]"
        for key, lab in [("railway_cases", r"Railways? Accidents"),
                         ("crossing_cases", r"Railways? Crossing Accidents"),
                         ("track_incidents_cases", r"Incidents on Railway Tracks")]:
            mm = re.search(rf"({NUMTXT})\s*(?:\([\d.]+%\))?\s*{q}{lab}", blk)
            if mm:
                out[key] = to_int(mm.group(1))
        sh = re.search(r"percentage share of deaths.*?due to (.*?) (?:was|were) reported as (.*?)respectively", blk)
        if sh:
            labs = re.findall(rf"{q}([^\u2018\u2019']+){q}", sh.group(1))
            vals = re.findall(rf"\(({NUMTXT}) deaths\)", sh.group(2))
            if len(labs) == len(vals):
                for lb, v in zip(labs, vals):
                    k = ("road" if lb.startswith("Road") else "crossing" if "Crossing" in lb else
                         "track_incidents" if "Incidents" in lb else "railway") + "_deaths"
                    out[k] = to_int(v)
            else:
                out["_share_parse_error"] = f"{labs} vs {vals}"
        out["_page"] = i + 1
        break
    for i in range(min(40, len(doc))):
        t = page_text(doc, i)
        m = re.search(r"[Ff]all from trains?\s*/\s*[Cc]ollision with people (?:on|at) tracks?.{0,3}\s*\(([\d,]+) out of ([\d,]+)\)", t)
        if m:
            out["fall_cases"] = to_int(m.group(1)); out["_fall_page"] = i + 1
            break
    # Figure 1A.x pie chart labels (deaths by classification), where printed as text
    for i in range(100, min(240, len(doc))):
        t = page_text(doc, i)
        m = re.search(r"Fall from train/Collision with people at tracks, (\d+), [\d.]+%", t)
        if m:
            out["figure_fall_deaths"] = int(m.group(1)); out["_fig_page"] = i + 1
            m2 = re.search(r"Explosion/Fire & Others, (\d+), [\d.]+%", t)
            if m2:
                out["figure_explosion_fire_others_deaths"] = int(m2.group(1))
            break
    return out


# ----------------------------------------------------------------------------------------------- main
def main():
    long_rows, log = [], []
    ok = mm = 0
    tables = {}           # (year, tid) -> dict(rowkey -> {(category, measure): value}), plus meta
    pages_used = defaultdict(list)
    narr = {}

    def check(desc, a, b, ctx=""):
        nonlocal ok, mm
        if a is None or b is None:
            log.append(f"MISSING  {desc}: computed={a} printed={b} {ctx}")
            mm += 1
            return False
        if a == b:
            ok += 1
            log.append(f"OK       {desc}: {a}")
            return True
        mm += 1
        log.append(f"MISMATCH {desc}: computed={a} printed={b} diff={a - b} {ctx}")
        return False

    for year, pdf in PDFS.items():
        doc = fitz.open(pdf)
        found = find_pages(doc, year)
        narr[year] = narrative(doc, year)
        for tid, plist in found.items():
            merged = {}       # row order index -> dict
            order = []
            for (pi, num, title) in plist:
                P = parse_page(doc[pi], log)
                if tid == "unmanned" and not any(re.search(r"Unmanned", g[0]) for g in P["groups"]):
                    continue          # other 1A.9 pages (road-accident causes) are not needed
                rows = classify_rows(P["rows"])
                pages_used[year].append((tid, num, pi + 1, title, [g[0] for g in P["groups"]], P["footnote"]))
                for r in rows:
                    if r["clash"]:
                        log.append(f"PARSE    {year} {tid} p{pi+1} row '{r['label']}': {r['clash']}")
                    if len(r["vals"]) != P["ncol"]:
                        miss = [j for j in range(P["ncol"]) if j not in r["vals"]]
                        log.append(f"MISSING  {year} {tid} p{pi+1} row '{r['label']}' columns {miss} unread -> left missing")
                # key rows by (kind, normalised label); serial numbers checked for consistency across pages
                for r in rows:
                    key = (r["kind"], norm_name(r["label"]))
                    if key not in merged:
                        merged[key] = dict(label=r["label"], kind=r["kind"], serial=r["serial"], cells={}, pages=set())
                        order.append(key)
                    for gl, cols in P["groups"]:
                        if tid == "unmanned" and not re.search(r"Unmanned", gl):
                            continue
                        for j in cols:
                            cat = gl if tid != "unmanned" else "Unmanned Railway Crossing Accidents"
                            if (cat, P["measures"][j]) in merged[key]["cells"]:
                                continue
                            merged[key]["cells"][(cat, P["measures"][j])] = r["vals"].get(j)
                    merged[key]["pages"].add(pi + 1)
            tables[(year, tid)] = dict(order=order, rows=merged, num=plist[0][1], title=plist[0][2])

        # ---------------- validation per table
        for tid in ("traffic", "rly_class", "rly_incid", "rly_cause", "unmanned"):
            T = tables.get((year, tid))
            if T is None:
                if not (tid == "rly_incid" and year != 2024):
                    log.append(f"MISSING  {year} table {tid} not found")
                continue
            R = T["rows"]
            states = [k for k in T["order"] if R[k]["kind"] == "state"]
            uts = [k for k in T["order"] if R[k]["kind"] == "ut"]
            tot = {kd: next((k for k in T["order"] if R[k]["kind"] == kd), None)
                   for kd in ("total_states", "total_uts", "total_all_india")}
            log.append(f"--- {year} {tid} (Table {T['num']}): {len(states)} states, {len(uts)} UTs, "
                       f"totals found: {[k for k, v in tot.items() if v]}")
            cells = sorted({c for k in T["order"] for c in R[k]["cells"]})
            for c in cells:
                for grp, tk in ((states, "total_states"), (uts, "total_uts")):
                    if tot[tk] is None:
                        continue
                    vals = [R[k]["cells"].get(c) for k in grp]
                    s = None if any(v is None for v in vals) else sum(vals)
                    check(f"{year} {tid} {c[0]} | {c[1]} sum({tk[6:]}) vs {tk.upper()}", s, R[tot[tk]]["cells"].get(c))
                if all(tot.values()):
                    a, b = R[tot["total_states"]]["cells"].get(c), R[tot["total_uts"]]["cells"].get(c)
                    check(f"{year} {tid} {c[0]} | {c[1]} STATES+UTs vs ALL INDIA",
                          None if a is None or b is None else a + b, R[tot["total_all_india"]]["cells"].get(c))
            # horizontal: categories sum to the Total group
            cats = []
            for c in cells:
                if c[0] not in cats:
                    cats.append(c[0])
            total_cat = next((c for c in cats if re.match(r"^(Total|Grand Total)\b", c) or c.startswith("Total Traffic")), None)
            if total_cat and tid != "unmanned":
                comps = [c for c in cats if c != total_cat]
                for k in T["order"]:
                    for meas in ("cases", "injured", "died"):
                        vals = [R[k]["cells"].get((c, meas)) for c in comps]
                        s = None if any(v is None for v in vals) else sum(vals)
                        check(f"{year} {tid} row '{R[k]['label']}' {meas}: sum({' + '.join(comps)}) vs '{total_cat}'",
                              s, R[k]["cells"].get((total_cat, meas)))
            # long output
            for k in T["order"]:
                r = R[k]
                printed = r["label"]
                if r["kind"] in ("state", "ut"):
                    canon, note = canon_note(year, printed)
                    if canon is None:
                        log.append(f"UNMAPPED {year} {tid} state name '{printed}'")
                else:
                    canon, note = printed.upper(), "printed total row"
                for (cat, meas), v in r["cells"].items():
                    long_rows.append(dict(year=year, state_printed=printed, state_canonical=canon,
                                          table=f"{T['num']}", category=cat, measure=meas, value=v,
                                          page=";".join(str(p) for p in sorted(r["pages"])), notes=note,
                                          table_id=tid, table_title=T["title"], row_type=r["kind"],
                                          serial_no=r["serial"]))

        # ---------------- cross-table checks (state level, all measures)
        def col(tid, catpat, meas):
            T = tables.get((year, tid))
            if T is None:
                return None
            out = {}
            for k in T["order"]:
                r = T["rows"][k]
                v = [val for (c, m), val in r["cells"].items() if m == meas and re.search(catpat, c.rstrip("*"))]
                if v:
                    out[(r["kind"] if r["kind"].startswith("total") else "s", norm_name(r["label"]))] = v[0]
            return out

        def cross(desc, A, B):
            if A is None or B is None:
                log.append(f"MISSING  cross-check {desc}: table absent"); return
            for k in sorted(set(A) | set(B)):
                check(f"{year} CROSS {desc} [{k[1]}]", A.get(k), B.get(k))

        for meas in ("cases", "injured", "died"):
            if year < 2024:
                cross(f"1A.12 Total vs 1A.2 Railway Accidents ({meas})",
                      col("rly_class", r"^Total$", meas), col("traffic", r"^Railway Accidents$", meas))
                cross(f"1A.13 cause Total vs 1A.12 Total ({meas})",
                      col("rly_cause", r"^Total$", meas), col("rly_class", r"^Total$", meas))
            else:
                cross(f"1A.12 Total vs 1A.2 Railway Accidents ({meas})",
                      col("rly_class", r"^Total$", meas), col("traffic", r"^Railway Accidents$", meas))
                cross(f"1A.13 Total vs 1A.2 Incidents on Railway Tracks ({meas})",
                      col("rly_incid", r"^Total$", meas), col("traffic", r"Incidents on Railway", meas))
                a, b = col("rly_class", r"^Total$", meas), col("rly_incid", r"^Total$", meas)
                both = None if a is None or b is None else {
                    k: (None if a.get(k) is None or b.get(k) is None else a[k] + b[k]) for k in set(a) | set(b)}
                cross(f"1A.14 cause Total vs 1A.12+1A.13 Totals ({meas})", col("rly_cause", r"^Total$", meas), both)

        # ---------------- narrative checks
        N = narr[year]
        log.append(f"--- {year} narrative (executive summary p{N.get('_page')}): "
                   f"{ {k: v for k, v in N.items() if not k.startswith('_page')} }")
        tr = tables.get((year, "traffic"))
        if tr:
            ai = next(tr["rows"][k] for k in tr["order"] if tr["rows"][k]["kind"] == "total_all_india")
            def ai_get(pat, meas):
                return next((v for (c, m), v in ai["cells"].items() if m == meas and re.search(pat, c.rstrip("*"))), None)
            pairs = [("railway_cases", r"^Railway Accidents$", "cases"), ("railway_deaths", r"^Railway Accidents$", "died"),
                     ("crossing_cases", r"Crossing", "cases"), ("crossing_deaths", r"Crossing", "died")]
            if year == 2024:
                pairs += [("track_incidents_cases", r"Incidents", "cases"), ("track_incidents_deaths", r"Incidents", "died")]
            for key, pat, meas in pairs:
                if key in N:
                    check(f"{year} NARRATIVE {key} (exec. summary) vs 1A.2 ALL INDIA", N[key], ai_get(pat, meas))
                else:
                    log.append(f"MISSING  {year} narrative value {key} not parsed")
        fall_tid = "rly_incid" if year == 2024 else "rly_class"
        fall_c = col(fall_tid, r"^Fall from Train", "cases")
        fall_d = col(fall_tid, r"^Fall from Train", "died")
        AI = ("total_all_india", "TOTAL (ALL INDIA)")
        if "fall_cases" in N:
            check(f"{year} NARRATIVE fall-from-train cases (exec. summary p{N['_fall_page']}) vs Table ALL INDIA",
                  N["fall_cases"], fall_c.get(AI))
        else:
            log.append(f"NOTE     {year} no fall-from-train '(x out of y)' sentence found in executive summary (not checked)")
        if "figure_fall_deaths" in N:
            check(f"{year} FIGURE (p{N['_fig_page']}) fall-from-train deaths vs Table ALL INDIA",
                  N["figure_fall_deaths"], fall_d.get(AI))
            oth = sum(v.get(AI, 0) for v in (col("rly_class", r"^Explosion/Fire$", "died"),
                                             col("rly_incid", r"^Others$", "died")) if v)
            if "figure_explosion_fire_others_deaths" in N:
                check(f"{year} FIGURE (p{N['_fig_page']}) 'Explosion/Fire & Others' deaths vs Tables 1A.12+1A.13 ALL INDIA",
                      N["figure_explosion_fire_others_deaths"], oth)

    # ---------------- write long
    DATA.mkdir(exist_ok=True)
    fields = ["year", "state_printed", "state_canonical", "table", "category", "measure", "value", "page", "notes",
              "table_id", "table_title", "row_type", "serial_no"]
    with open(DATA / "railway_state_year.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(long_rows)

    # ---------------- wide (year x canonical state, printed units merged to canonical)
    spec = [  # (output prefix, table_id, category regex)
        ("railway_total", "rly_class", r"^Total$"),              # 2024: + rly_incid Total (added below)
        ("fall_from_train_people_on_track", "rly_class", r"^Fall from Train"),
        ("collision", "rly_class", r"^Collisions$"),
        ("derailment", "rly_class", r"^Derailments$"),
        ("explosion_fire", "rly_class", r"^Explosion/Fire$"),
        ("other", "rly_class", r"^Others$"),
        ("railway_crossing", "traffic", r"Railway Crossing"),
        ("unmanned_railway_crossing", "unmanned", r"Unmanned"),
        ("road", "traffic", r"^Road Accidents$"),
        ("traffic_total", "traffic", r"^Total Traffic"),
    ]
    wide = defaultdict(lambda: defaultdict(lambda: None))
    meta = defaultdict(set)
    for r in long_rows:
        if r["row_type"] not in ("state", "ut", "total_all_india"):
            continue
        st = r["state_canonical"] if r["row_type"] != "total_all_india" else "ALL INDIA (printed total)"
        tids = {r["table_id"]}
        for name, tid, pat in spec:
            src_tid = tid
            if r["year"] == 2024 and name in ("fall_from_train_people_on_track", "other"):
                src_tid = "rly_incid"
            if r["table_id"] == src_tid and re.search(pat, r["category"].rstrip("*")) or \
               (r["year"] == 2024 and name == "railway_total" and r["table_id"] == "rly_incid" and r["category"] == "Total"):
                key = (r["year"], st)
                cname = f"{name}_{r['measure']}"
                if r["value"] is None:
                    wide[key][cname] = wide[key][cname]
                    meta[key].add(f"{cname} has unreadable cell")
                else:
                    wide[key][cname] = (wide[key][cname] or 0) + r["value"]
                if r["notes"]:
                    meta[key].add(r["notes"])
    cols = [f"{n}_{m}" for n, _, _ in spec for m in ("died", "cases", "injured")]
    with open(DATA / "railway_state_year_wide.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "state_canonical", "state_panel"] + cols + ["notes"])
        for (y, st) in sorted(wide, key=lambda k: (k[0], str(k[1]))):
            notes = sorted(meta[(y, st)])
            if (y, st) in FLAGS:
                notes.append(FLAGS[(y, st)])
            if y == 2024:
                notes.append("2024: railway_total = 1A.12 'Railway Accidents' (0) + 1A.13 'Incidents on Railway Tracks/In "
                             "Railway Premises'; fall/other from 1A.13")
            w.writerow([y, st, PANEL.get(st, st)] + [wide[(y, st)][c] for c in cols] + [" | ".join(notes)])

    # ---------------- log
    # documented explanations for every mismatch that is a printed inconsistency (values kept as printed)
    EXPLAIN = {
        "2014 NARRATIVE crossing_deaths": "PRINTED INCONSISTENCY in the ADSI 2014 executive summary: it gives "
            "'1.5% (2,547 deaths)' for railway crossing accidents, repeating the CASES figure (2,547); Table 1A.2, "
            "Table 1A(A) narrative (p139: '2,575 deaths') and the cause table all print 2,575 deaths. Table value kept.",
        "2024 FIGURE": "PRINTED INCONSISTENCY in ADSI 2024 Figure 1A.9 (pie chart, p154): labels give Fall-from-train "
            "17,029 and 'Explosion/Fire & Others' 5,384 deaths (sum 22,413 = correct total) whereas Tables 1A.13/1A.14 and "
            "every state row give 16,845 and 5,568. The figure split is not reproducible from the tables; table values kept.",
    }
    for i, line in enumerate(log):
        if line.startswith("MISMATCH"):
            for k, v in EXPLAIN.items():
                if k in line:
                    log[i] = line + "\n         -> " + v
    with open(DATA / "railway_validation_log.txt", "w", encoding="utf-8") as f:
        f.write(f"ADSI railway extraction validation log\nSUMMARY: OK={ok} MISMATCH/MISSING={mm}\n\n")
        f.write("PAGES USED (year, table_id, printed table, pdf page, title, column groups)\n")
        for y in pages_used:
            for p in pages_used[y]:
                f.write(f"  {y} {p[0]:10s} Table {p[1]:6s} p{p[2]:<4d} {p[3][:110]} | groups={p[4]}\n")
                if p[5]:
                    f.write(f"      footnote: {p[5]}\n")
        f.write("\n")
        f.write("\n".join(log) + "\n")
    print(f"OK={ok} MISMATCH/MISSING={mm}; long rows={len(long_rows)}")
    for line in log:
        if not line.startswith("OK"):
            print(line)


if __name__ == "__main__":
    main()
