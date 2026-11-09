"""State-wise route km, running track km and total track km from Indian Railways Year Books (2016-17, 2018-19, 2024-25).
Reads the page titled 'State-wise Route Kms' by word coordinates (layout text is scrambled), checks that state rows sum
to the printed Total, writes data/state_route_km.csv (as of 31 March of the year after the financial-year start)."""
import os, re, pathlib
import fitz
P = pathlib.Path(__file__).resolve().parents[1]
RAW = pathlib.Path(os.environ.get("RAILWAY_RAW", P / "data_raw")) / "railway"
BOOKS = {"2016-17": "IR_Year_Book_2016-17_ircep.pdf", "2018-19": "IR_Year_Book_2018-19_ircep.pdf", "2024-25": "IR_Year_Book_2024-25_English.pdf"}
num = lambda s: float(s.replace(",", ""))
rows = []
for fy, fn in BOOKS.items():
    doc = fitz.open(RAW / fn)
    pages = [i for i, pg in enumerate(doc) if "State-wise Route Kms" in pg.get_text()]
    assert pages, fy
    words = []
    for i in (pages[0], pages[0] + 1):
        for w in doc[i].get_text("words"):
            words.append((i, (w[1] + w[3]) / 2, w[0], w[4]))
    words.sort()
    lines, cur, key = [], [], None
    for pg, y, x, t in words:
        k = (pg, round(y / 3.5))
        if key is not None and (pg != key[0] or abs(y - key[1]) > 3.5):
            lines.append(cur); cur = []
        cur.append((x, t)); key = (pg, y)
    lines.append(cur)
    got, on = {}, False
    for ln in lines:
        ln.sort(); toks = [t for _, t in ln]
        txt = " ".join(toks)
        if "State/Union" in txt or "States/Union" in txt and "Route" in txt: on = True
        if not on: continue
        nums = [t for t in toks if re.fullmatch(r"[\d,]+", t)]
        name = " ".join(t for t in toks if not re.fullmatch(r"[\d,]+", t)).strip()
        if len(nums) == 3 and name and not name.lower().startswith(("kms", "following")):
            got[name] = [num(n) for n in nums]
            if name == "Total": break
    tot = got.pop("Total")
    s = [sum(v[j] for v in got.values()) for j in range(3)]
    print(fy, len(got), "states; sums", s, "printed", tot, "OK" if s == tot else "MISMATCH")
    for k, v in got.items():
        rows.append(dict(fy=fy, as_of=f"{int(fy[:4]) + 1}-03-31", state_printed=k, route_km=v[0], running_track_km=v[1], total_track_km=v[2]))
import csv
with open(P / "data/state_route_km.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
