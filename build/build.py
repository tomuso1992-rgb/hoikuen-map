#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Inject data into the template; emit the artifact body and a standalone page."""
import json, io, os

HERE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()

nur = json.load(open(os.path.join(HERE, "nurseries_geo.json"), encoding="utf-8"))
chome = json.load(open(os.path.join(HERE, "kohoku_chome.json"), encoding="utf-8"))

KEEP = ["id", "name", "address", "tel", "url", "enmikke", "hours", "parking",
        "capacity", "staff", "cap0", "apply0", "policy",
        "lat", "lng", "town", "prec"]

def clean(d):
    o = {}
    for k in KEEP:
        v = d.get(k)
        if v is None:
            continue
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        o[k] = v
    return o

nur_out = [clean(d) for d in nur]
chome_out = [{"town": c["town"], "lat": round(c["lat"], 6), "lng": round(c["lng"], 6)}
             for c in chome]

nj = json.dumps(nur_out, ensure_ascii=False, separators=(",", ":"))
cj = json.dumps(chome_out, ensure_ascii=False, separators=(",", ":"))

body = tpl.replace("/*__NURSERIES__*/[]", nj).replace("/*__CHOME__*/[]", cj)

# 1) artifact body — no doctype/html/head/body wrapper
art = os.path.join(HERE, "artifact.html")
open(art, "w", encoding="utf-8").write(body)

# 2) standalone page for the repo / download
standalone = (
    '<!DOCTYPE html>\n<html lang="ja">\n<head>\n'
    '<meta charset="UTF-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="color-scheme" content="light dark">\n'
    '<meta name="description" content="横浜市港北区・大倉山・菊名エリアの認可保育園 0歳児クラス 倍率マップ">\n'
    + body.split("</style>")[0] + "</style>\n</head>\n<body>\n"
    + "</style>".join(body.split("</style>")[1:]).lstrip()
    + "\n</body>\n</html>\n"
)
sa = os.path.join(HERE, "hoikuen-map.html")
open(sa, "w", encoding="utf-8").write(standalone)

print("nurseries:", len(nur_out), "chome:", len(chome_out))
print("artifact.html      %6.1f KB" % (os.path.getsize(art) / 1024))
print("hoikuen-map.html   %6.1f KB" % (os.path.getsize(sa) / 1024))
assert "__NURSERIES__" not in body and "__CHOME__" not in body, "placeholder left in output"
print("ok")
