#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Join the nursery list to chome-level coordinates (geolonia / ABR derived)."""
import json, re, unicodedata, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
# The original page that holds the RAW_DATA array of nurseries.
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "source.html")
CHOME = os.path.join(HERE, "kohoku_chome.json")

if not os.path.exists(SRC):
    sys.exit("source not found: %s\nusage: python3 build_geo.py <original.html>" % SRC)

# ---- pull RAW_DATA out of the original file -------------------------------
html = open(SRC, encoding="utf-8").read()
m = re.search(r"const RAW_DATA = (\[.*?\]);\n", html, re.S)
raw = json.loads(m.group(1))
print("nurseries:", len(raw))

chome = json.load(open(CHOME, encoding="utf-8"))
COORD = {c["town"]: (c["lat"], c["lng"]) for c in chome}

KAN = "〇一二三四五六七八九"
def num_to_kan(n):
    n = int(n)
    if n < 1 or n > 99:
        return None
    if n < 10:
        return KAN[n]
    if n < 20:
        return "十" + (KAN[n % 10] if n % 10 else "")
    return KAN[n // 10] + "十" + (KAN[n % 10] if n % 10 else "")

def normalize(addr):
    """full-width -> half-width, strip postal code / prefecture / city / ward."""
    s = unicodedata.normalize("NFKC", addr)
    s = s.replace("−", "-").replace("－", "-").replace("ー", "-").replace("―", "-")
    s = re.sub(r"〒?\s*\d{3}-?\d{4}", "", s)
    s = re.sub(r"^\s*神奈川県", "", s)
    s = re.sub(r"^\s*横浜市", "", s)
    s = re.sub(r"^\s*港北区", "", s)
    return s.strip()

def town_of(addr):
    """Return (town_key_in_dataset, precision) or (None, None)."""
    s = normalize(addr)

    # 1) explicit "N丁目" or kanji "三丁目"
    mm = re.match(r"^([^\d]+?)(\d+)丁目", s)
    if mm:
        k = num_to_kan(mm.group(2))
        if k:
            return mm.group(1) + k + "丁目", "chome"
    mm = re.match(r"^([^\d]+?)([〇一二三四五六七八九十]+)丁目", s)
    if mm:
        return mm.group(1) + mm.group(2) + "丁目", "chome"

    # 2) "大倉山1-10-12" style -> first number is the chome
    mm = re.match(r"^(\D+?)(\d+)-", s)
    if mm:
        k = num_to_kan(mm.group(2))
        if k:
            cand = mm.group(1) + k + "丁目"
            if cand in COORD:
                return cand, "chome"

    # 3) town with no chome subdivision (師岡町298, 大豆戸町943, 錦が丘19-18)
    mm = re.match(r"^(\D+?)\d", s)
    if mm and mm.group(1) in COORD:
        return mm.group(1), "town"

    # 4) whole remainder is a town name
    for t in COORD:
        if s.startswith(t):
            return t, "town"
    return None, None

out, misses = [], []
for i, d in enumerate(raw):
    t, prec = town_of(d["address"])
    rec = dict(d)
    rec["id"] = "hk_%d" % i
    if t and t in COORD:
        rec["lat"], rec["lng"] = COORD[t]
        rec["town"], rec["prec"] = t, prec
    else:
        rec["lat"] = rec["lng"] = None
        rec["town"], rec["prec"] = None, None
        misses.append((d["name"], d["address"], normalize(d["address"])))
    out.append(rec)

print("\n--- resolved ---")
for r in out:
    print("%-28s %-10s %-6s %s" % (r["name"][:28], r["town"] or "MISS", r["prec"] or "-", r["address"][:44]))

print("\nmissed:", len(misses))
for x in misses:
    print("  ", x)

# co-location report
from collections import Counter
cnt = Counter(r["town"] for r in out if r["town"])
print("\n--- towns with multiple nurseries ---")
for t, c in cnt.most_common():
    if c > 1:
        print("  %-14s %d" % (t, c))

json.dump(out, open(os.path.join(HERE, "nurseries_geo.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote nurseries_geo.json")
