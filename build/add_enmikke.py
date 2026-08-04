#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Attach えんさがしサポート (enmikke.jp) detail links, matched by name."""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "nurseries_geo.json")

RAW = """
1 ララランド大倉山 https://enmikke.jp/parental/yokohama/facility/detail/2409/
2 聖保育園第二 　https://enmikke.jp/parental/yokohama/facility/detail/2410/
3 明日葉保育園大倉山園 https://enmikke.jp/parental/yokohama/facility/detail/2411/
4 森の樹保育園 https://enmikke.jp/parental/yokohama/facility/detail/2412/
5 おおくらやまえきまえのぞみ保育園 https://enmikke.jp/parental/yokohama/facility/detail/3086/
6 聖保育園 https://enmikke.jp/parental/yokohama/facility/detail/2413/
7 天才キッズクラブ楽学館大倉山園 https://enmikke.jp/parental/yokohama/facility/detail/2416/
8 グローバルキッズ大倉山園 https://enmikke.jp/parental/yokohama/facility/detail/2024/
9 アスク大倉山保育園 https://enmikke.jp/parental/yokohama/facility/detail/1910/
10 太尾保育園　https://enmikke.jp/parental/yokohama/facility/detail/3335/
11 わおわお大倉山保育園 　https://enmikke.jp/parental/yokohama/facility/detail/1940/
12 くっくおさんぽ保育園大倉山 https://enmikke.jp/parental/yokohama/facility/detail/1999/
13 たんぽぽ保育園 https://enmikke.jp/parental/yokohama/facility/detail/2414/
14 大倉山保育園 https://enmikke.jp/parental/yokohama/facility/detail/2407/
15 大曽根コスモス保育園 https://enmikke.jp/parental/yokohama/facility/detail/2408/
16 おおつな保育園 https://enmikke.jp/parental/yokohama/facility/detail/1958/
17 パレット保育園・大倉山 https://enmikke.jp/parental/yokohama/facility/detail/2421/
18 大倉山元気の泉保育園 https://enmikke.jp/parental/yokohama/facility/detail/1929/
19 ぶれすと綱島ほいくえん https://enmikke.jp/parental/yokohama/facility/detail/2422/
20 ぶれすと綱島二階ほいくえん https://enmikke.jp/parental/yokohama/facility/detail/3114/
21 小学館アカデミーつなしま保育園 https://enmikke.jp/parental/yokohama/facility/detail/1996/
22 なあな保育園 https://enmikke.jp/parental/yokohama/facility/detail/1951/
23 ヒューマンアカデミー大倉山保育園 https://enmikke.jp/parental/yokohama/facility/detail/2390/
24 ちいさなたね保育園 https://enmikke.jp/parental/yokohama/facility/detail/2391/
25 スターチャイルド大倉山ナーサリー
26 きゅーぴーるーむ大倉山園 https://enmikke.jp/parental/yokohama/facility/detail/2455/
27 キッズパートナー大倉山 https://enmikke.jp/parental/yokohama/facility/detail/2438/
28 光の園アンティー保育園 https://enmikke.jp/parental/yokohama/facility/detail/2366/
29 リトルスカラー妙蓮寺保育園 https://enmikke.jp/parental/yokohama/facility/detail/2365/
30 グローバルキッズ菊名園 https://enmikke.jp/parental/yokohama/facility/detail/2019/
31 光の園第二保育園 https://enmikke.jp/parental/yokohama/facility/detail/2368/
32 うみのくに保育園きくな https://enmikke.jp/parental/yokohama/facility/detail/2369/
33 まなびの森 菊名こども園 https://enmikke.jp/parental/yokohama/facility/detail/2371/
34 光の園保育園 https://enmikke.jp/parental/yokohama/facility/detail/2393/
35 パレット保育園・妙蓮寺 https://enmikke.jp/parental/yokohama/facility/detail/2423/
36 キディ大倉山・横浜 https://enmikke.jp/parental/yokohama/facility/detail/2417/
37 まめどくれっしゅ https://enmikke.jp/parental/yokohama/facility/detail/2418/
38 パレット保育園・大豆戸 https://enmikke.jp/parental/yokohama/facility/detail/2419/
39 キッズラディ https://enmikke.jp/parental/yokohama/facility/detail/2465/
40 大豆戸どろんこ保育園 https://enmikke.jp/parental/yokohama/facility/detail/2420/
41 ペガサスベビー保育園 https://enmikke.jp/parental/yokohama/facility/detail/2397/
42 聖愛クロス保育園きくな https://enmikke.jp/parental/yokohama/facility/detail/2454/
43 キッズラボ菊名園 https://enmikke.jp/parental/yokohama/facility/detail/1890/
44 Luce陽だまりの家保育園 https://enmikke.jp/parental/yokohama/facility/detail/2445/
"""

def norm(s):
    return re.sub(r"[\s　]+", "", s)

given = []          # (order, name, url|None)
for line in RAW.strip().splitlines():
    m = re.match(r"^\s*(\d+)\s+(.*?)\s*(https?://\S+)?\s*$", line.replace("　", " "))
    if not m:
        sys.exit("unparsed line: " + line)
    given.append((int(m.group(1)), m.group(2).strip(), m.group(3)))

data = json.load(open(PATH, encoding="utf-8"))
by_norm = {norm(d["name"]): d for d in data}
if len(by_norm) != len(data):
    sys.exit("duplicate nursery names — cannot match safely")

seen, problems, applied = set(), [], 0
for order, name, url in given:
    d = by_norm.get(norm(name))
    if d is None:
        problems.append("NO MATCH in data: %s" % name)
        continue
    if d["id"] in seen:
        problems.append("matched twice: %s" % name)
        continue
    seen.add(d["id"])

    # the list is also positional — flag any drift between the two
    idx = int(d["id"].split("_")[1]) + 1
    if idx != order:
        problems.append("order mismatch: list #%d '%s' is data #%d" % (order, name, idx))

    if url:
        if not re.fullmatch(r"https://enmikke\.jp/parental/yokohama/facility/detail/\d+/", url):
            problems.append("unexpected URL shape for %s: %s" % (name, url))
            continue
        d["enmikke"] = url
        applied += 1

missing = [d["name"] for d in data if "enmikke" not in d]
ids = [u.rsplit("/", 2)[-2] for u in (d.get("enmikke") for d in data) if u]
dupes = {i for i in ids if ids.count(i) > 1}

print("given lines   :", len(given))
print("links applied :", applied)
print("no link       :", missing)
print("duplicate ids :", sorted(dupes) or "none")
print("problems      :", problems or "none")

if problems or dupes:
    sys.exit("refusing to write — resolve the above first")

json.dump(data, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nwrote", PATH)
