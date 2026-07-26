#!/usr/bin/env python3
"""Validate TOEIC content sources in content/ and splice them into english.html.

Vocab sources per level: content/vocab-<lv>.json (full entries, order preserved)
plus content/vocab-<lv>-ext-*.json batches (terse entries, sorted by filename).
Entry fields: w, p, m, cat required; ex/exKo optional (paired); rel optional
list of {w, k, m} with k in 파생/동의/반의/숙어.

STRICT=1 enforces the book-scale minimums (>=1000 headwords/level,
>=5000 total learning items, 60 grammar and 40 listening per level).
"""
import glob, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(REPO, "content")
HTML = os.path.join(REPO, "english.html")
STRICT = os.environ.get("STRICT", "0") == "1"

errors = []
def err(msg): errors.append(msg)

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def no_html(s, where, allow_b=False):
    t = s
    if allow_b:
        t = t.replace("<b>", "").replace("</b>", "")
    if "<" in t or ">" in t:
        err(f"{where}: unexpected HTML: {s[:60]!r}")

REL_KINDS = {"파생", "동의", "반의", "숙어"}
POS = {"명사", "동사", "형용사", "부사", "구동사", "숙어", "전치사", "접속사"}
CATS = {"채용·인사", "회의", "계약·법무", "마케팅", "재무·회계", "출장·여행", "배송·주문", "시설·사무"}

def check_why(why, choices, where, allow_missing=True):
    """보기별 정오답 이유 배열 검증. 통과하면 리스트, 없으면 None."""
    if why is None:
        if not allow_missing: err(f"{where}: why 누락")
        return None
    if not isinstance(why, list) or len(why) != len(choices):
        err(f"{where}: why 길이가 보기 수({len(choices)})와 다름"); return None
    for i, t in enumerate(why):
        if not isinstance(t, str) or len(t.strip()) < 4:
            err(f"{where}.why[{i}]: 너무 짧거나 문자열이 아님"); return None
        no_html(t, f"{where}.why[{i}]")
    return [t.strip() for t in why]

# ---- vocab ----
vocab = []
seen_w = {}
rel_total = 0
for lv in (1, 2, 3):
    files = [os.path.join(CONTENT, f"vocab-{lv}.json")] + \
            sorted(glob.glob(os.path.join(CONTENT, f"vocab-{lv}-ext-*.json")))
    lv_count = 0
    for path in files:
        name = os.path.basename(path)
        data = load(path)["words"]
        for i, v in enumerate(data):
            where = f"{name}[{i}]({v.get('w')})"
            for k in ("w", "p", "m", "cat"):
                if not v.get(k): err(f"{where}: missing {k}")
            if v.get("p") and v["p"] not in POS: err(f"{where}: bad pos {v['p']}")
            if v.get("cat") and v["cat"] not in CATS: err(f"{where}: bad cat {v['cat']}")
            w = (v.get("w") or "").strip().lower()
            if not w: continue
            if w in seen_w: err(f"{where}: duplicate word (also in {seen_w[w]})")
            seen_w[w] = name
            entry = {"w": w, "p": v["p"], "m": v["m"], "lv": lv, "cat": v["cat"]}
            if STRICT and not (v.get("ex") and v.get("exKo")):
                err(f"{where}: missing ex/exKo (모든 표제어는 예문 필수)")
            if v.get("ex") or v.get("exKo"):
                if not (v.get("ex") and v.get("exKo")):
                    err(f"{where}: ex/exKo must both be present")
                else:
                    if "<b>" not in v["ex"]: err(f"{where}: ex missing <b>")
                    no_html(v["ex"], where + ".ex", allow_b=True)
                    no_html(v["exKo"], where + ".exKo")
                    entry["ex"] = v["ex"]; entry["exKo"] = v["exKo"]
            if v.get("ety"):
                no_html(v["ety"], where + ".ety"); entry["ety"] = v["ety"].strip()
            if v.get("mnem"):
                no_html(v["mnem"], where + ".mnem"); entry["mnem"] = v["mnem"].strip()
            no_html(v["m"], where + ".m")
            rel = v.get("rel") or []
            for j, r in enumerate(rel):
                rw = f"{where}.rel[{j}]"
                if not (r.get("w") and r.get("k") and r.get("m")): err(f"{rw}: needs w/k/m")
                elif r["k"] not in REL_KINDS: err(f"{rw}: bad kind {r['k']}")
                else:
                    no_html(r["w"], rw); no_html(r["m"], rw)
            if rel:
                entry["rel"] = [{"w": r["w"], "k": r["k"], "m": r["m"]} for r in rel]
                rel_total += len(rel)
            vocab.append(entry)
            lv_count += 1
    print(f"vocab lv{lv}: {lv_count} headwords ({len(files)} files)")
    if STRICT and lv_count < 1000: err(f"vocab lv{lv}: {lv_count} < 1000 headwords")

total_items = len(vocab) + rel_total
print(f"vocab total: {len(vocab)} headwords + {rel_total} rel = {total_items} learning items")
if STRICT and total_items < 5000: err(f"total learning items {total_items} < 5000")

carry = ["appointment","available","order","refund","reservation","schedule","vacation",
         "luggage","exchange","recommend","negotiate","opportunity","temporary","manage",
         "improve","confident","decision","suggest","quality","experience"]
missing_carry = [w for w in carry if w not in seen_w]
if missing_carry: err(f"carryover words missing: {missing_carry}")

# ---- grammar ----
G_TYPES = {"품사", "시제·형태", "전치사·접속사", "어휘"}
grammar = []
seen_gq = set()
for lv in (1, 2, 3):
    files = [os.path.join(CONTENT, f"grammar-{lv}.json")] + \
            sorted(glob.glob(os.path.join(CONTENT, f"grammar-{lv}-ext-*.json")))
    data = []
    for path in files:
        data.extend(load(path)["items"])
    print(f"grammar lv{lv}: {len(data)} items ({len(files)} files)")
    if STRICT and len(data) < 330: err(f"grammar-{lv}: {len(data)} < 330")
    counts = {}
    for i, g in enumerate(data):
        where = f"grammar-{lv}[{i}]"
        if g["type"] not in G_TYPES: err(f"{where}: bad type {g['type']}")
        counts[g["type"]] = counts.get(g["type"], 0) + 1
        if len(re.findall(r"_{2,}", g["q"])) != 1: err(f"{where}: blank count != 1")
        if len(g["choices"]) != 4: err(f"{where}: choices != 4")
        if not (0 <= g["a"] <= 3): err(f"{where}: a out of range")
        if len(set(g["choices"])) != 4: err(f"{where}: duplicate choices")
        no_html(g["q"], where + ".q")
        qkey = g["q"].strip().lower()
        if qkey in seen_gq: err(f"{where}: duplicate sentence: {g['q'][:50]!r}")
        seen_gq.add(qkey)
        for c in g["choices"]: no_html(c, where + ".choice")
        no_html(g["transKo"], where); no_html(g["exKo"], where)
        g_why = check_why(g.get("why"), g["choices"], where)
        g_entry = {"id": f"g{lv}{i+1:02d}", "lv": lv, "type": g["type"], "q": g["q"],
                   "choices": g["choices"], "a": g["a"], "transKo": g["transKo"], "exKo": g["exKo"]}
        if g_why: g_entry["why"] = g_why
        grammar.append(g_entry)
    print(f"  type mix: {counts}")

# ---- reading ----
R_KINDS = {"이메일", "공지", "광고", "기사", "문자메시지"}
Q_TYPES = {"주제·목적", "세부사항", "추론", "동의어"}
reading = []
seen_rt = set()
for lv in (1, 2, 3):
    files = [os.path.join(CONTENT, f"reading-{lv}.json")] + \
            sorted(glob.glob(os.path.join(CONTENT, f"reading-{lv}-ext-*.json")))
    data = []
    for path in files:
        data.extend(load(path)["passages"])
    print(f"reading lv{lv}: {len(data)} passages ({len(files)} files)")
    if STRICT and len(data) < 110: err(f"reading-{lv}: {len(data)} < 110 passages")
    for i, r in enumerate(data):
        where = f"reading-{lv}[{i}]"
        if r["kind"] not in R_KINDS: err(f"{where}: bad kind")
        tkey = r["title"].strip()
        if tkey in seen_rt: err(f"{where}: duplicate title: {tkey!r}")
        seen_rt.add(tkey)
        no_html(r["passage"], where + ".passage")
        if not (2 <= len(r["questions"]) <= 3): err(f"{where}: question count")
        qs = []
        for qi, q in enumerate(r["questions"]):
            qw = f"{where}.q{qi}"
            if q["type"] not in Q_TYPES: err(f"{qw}: bad type")
            if len(q["choices"]) != 4: err(f"{qw}: choices != 4")
            if not (0 <= q["a"] <= 3): err(f"{qw}: a out of range")
            if len(set(q["choices"])) != 4: err(f"{qw}: duplicate choices")
            no_html(q["q"], qw); no_html(q["exKo"], qw)
            for c in q["choices"]: no_html(c, qw + ".choice")
            q_entry = {"q": q["q"], "type": q["type"], "choices": q["choices"], "a": q["a"], "exKo": q["exKo"]}
            r_why = check_why(q.get("why"), q["choices"], qw)
            if r_why: q_entry["why"] = r_why
            if q.get("ev"):
                no_html(q["ev"], qw + ".ev")
                norm = lambda t: " ".join(t.split())
                if norm(q["ev"]) not in norm(r["passage"]):
                    err(f"{qw}.ev: 근거 문장이 지문에 없음")
                else:
                    q_entry["ev"] = norm(q["ev"])
            qs.append(q_entry)
        reading.append({"id": f"r{lv}{i+1:02d}", "lv": lv, "kind": r["kind"], "title": r["title"],
                        "passage": r["passage"], "questions": qs})

# ---- listening ----
L_TYPES = {"Who", "What", "When", "Where", "Why", "How", "일반의문문", "평서문"}
listening = []
for lv in (1, 2, 3):
    files = [os.path.join(CONTENT, f"listening-{lv}.json")] + \
            sorted(glob.glob(os.path.join(CONTENT, f"listening-{lv}-ext-*.json")))
    data = []
    for path in files:
        data.extend(load(path)["items"])
    print(f"listening lv{lv}: {len(data)} items ({len(files)} files)")
    if STRICT and len(data) < 40: err(f"listening-{lv}: {len(data)} < 40")
    for i, l in enumerate(data):
        where = f"listening-{lv}[{i}]"
        if l["qType"] not in L_TYPES: err(f"{where}: bad qType")
        if len(l["choices"]) != 3: err(f"{where}: choices != 3")
        if not (0 <= l["a"] <= 2): err(f"{where}: a out of range")
        if len(set(l["choices"])) != 3: err(f"{where}: duplicate choices")
        no_html(l["q"], where); no_html(l["exKo"], where)
        for c in l["choices"]: no_html(c, where + ".choice")
        l_entry = {"id": f"l{lv}{i+1:02d}", "lv": lv, "qType": l["qType"], "q": l["q"],
                   "choices": l["choices"], "a": l["a"], "exKo": l["exKo"]}
        l_why = check_why(l.get("why"), l["choices"], where)
        if l_why: l_entry["why"] = l_why
        if l.get("transKo"):
            no_html(l["transKo"], where + ".transKo"); l_entry["transKo"] = l["transKo"].strip()
        listening.append(l_entry)

if errors:
    print(f"\n== {len(errors)} VALIDATION ERRORS ==")
    for e in errors[:60]: print(" -", e)
    if len(errors) > 60: print(f" ... and {len(errors)-60} more")
    sys.exit(1)

ety_n = sum(1 for v in vocab if v.get("ety"))
mnem_n = sum(1 for v in vocab if v.get("mnem"))
gw_n = sum(1 for g in grammar if g.get("why"))
rw_n = sum(1 for r in reading for q in r["questions"] if q.get("why"))
rev_n = sum(1 for r in reading for q in r["questions"] if q.get("ev"))
lw_n = sum(1 for l in listening if l.get("why"))
print(f"해설 강화: 어원 {ety_n} · 연상 {mnem_n} · 구문why {gw_n} · 독해why {rw_n} · 독해근거 {rev_n} · 듣기why {lw_n}")
print(f"\nTotals: vocab={len(vocab)} (+{rel_total} rel) grammar={len(grammar)} reading={len(reading)} listening={len(listening)}")

def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

block = (
    "/*__DATA_START__*/\n"
    f"const VOCAB = {js(vocab)};\n"
    f"const GRAMMAR = {js(grammar)};\n"
    f"const READING = {js(reading)};\n"
    f"const LISTENING = {js(listening)};\n"
    "/*__DATA_END__*/"
)

with open(HTML, encoding="utf-8") as f:
    html = f.read()
new_html, n = re.subn(r"/\*__DATA_START__\*/.*?/\*__DATA_END__\*/", lambda m: block, html, flags=re.S)
if n != 1:
    print(f"ERROR: data marker match count = {n}")
    sys.exit(1)
with open(HTML, "w", encoding="utf-8") as f:
    f.write(new_html)
print(f"Spliced into english.html ({len(new_html)//1024} KB){' [STRICT]' if STRICT else ''}")
