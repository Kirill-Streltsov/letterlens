"""Vector diagrams for the LetterLens guide. Each function returns one inline SVG string."""

from __future__ import annotations

from html import escape

INK = "#1b2540"
SOFT = "#4b5472"
FAINT = "#8a8fa3"
PAPER = "#f4eee2"
DEEP = "#ebe2cf"
CARD = "#fffdf8"
LINE = "#d9cdb3"
MARKER = "#ffe27a"
OK = "#2f6b55"
OKBG = "#e3f1ea"
CHECK = "#b45a1f"
CHECKBG = "#fbeadb"
BLUE = "#2a4b98"
BLUEBG = "#e6ecf8"
AI = "#6b4fa0"
AIBG = "#efe9f8"
AWS = "#c8701a"
AWSBG = "#fcefdf"
RED = "#a83434"
REDBG = "#f7e3e3"

KINDS = {
    "default": (CARD, INK),
    "ink": (INK, CARD),
    "ok": (OKBG, OK),
    "check": (CHECKBG, CHECK),
    "blue": (BLUEBG, BLUE),
    "ai": (AIBG, AI),
    "aws": (AWSBG, AWS),
    "marker": (MARKER, INK),
    "red": (REDBG, RED),
    "deep": (DEEP, INK),
}


def svg(width: int, height: int, body: str, caption: str = "") -> str:
    defs = f"""<defs>
<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="{SOFT}"/></marker>
<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>
<marker id="ag" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
<path d="M0,0 L10,5 L0,10 z" fill="{OK}"/></marker>
</defs>"""
    fig = f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" class="diagram" font-family="-apple-system, Helvetica, Arial, sans-serif">{defs}{body}</svg>'
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return f"<figure>{fig}{cap}</figure>"


def text(x: float, y: float, s: str, size: float = 12, anchor: str = "middle", weight: int = 400,
         color: str = INK, italic: bool = False, halo: bool = False) -> str:
    style = ' font-style="italic"' if italic else ""
    if halo:
        style += ' paint-order="stroke" stroke="#ffffff" stroke-width="4" stroke-linejoin="round"'
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" font-weight="{weight}" '
            f'fill="{color}"{style}>{escape(s)}</text>')


def box(x: float, y: float, w: float, h: float, title: str, lines: list[str] | None = None,
        kind: str = "default", size: float = 13, radius: float = 10, top: bool = False) -> str:
    fill, fg = KINDS[kind]
    stroke = fg if kind != "default" else LINE
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>']
    lines = lines or []
    total = 1 + len(lines)
    line_h = size + 4
    start = y + 22 if top else y + h / 2 - (total - 1) * line_h / 2 + size * 0.35
    out.append(text(x + w / 2, start, title, size, weight=700, color=fg))
    for i, ln in enumerate(lines, start=1):
        out.append(text(x + w / 2, start + i * line_h, ln, size - 2.5, color=fg if kind == "ink" else SOFT))
    return "".join(out)


def arrow(x1: float, y1: float, x2: float, y2: float, label: str = "", dashed: bool = False,
          color: str = SOFT, marker: str = "a", label_dx: float = 0, label_dy: float = -6, size: float = 11) -> str:
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    out = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.6"{dash} marker-end="url(#{marker})"/>'
    if label:
        out += text((x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy, label, size, color=color, halo=True)
    return out


def path(d: str, color: str = SOFT, dashed: bool = False, marker: str = "a") -> str:
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{dash} marker-end="url(#{marker})"/>'


def region(x: float, y: float, w: float, h: float, label: str, color: str = FAINT, fill: str = "none") -> str:
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{color}" '
            f'stroke-width="1.2" stroke-dasharray="6 5"/>' + text(x + 14, y + 20, label, 12, "start", 700, color))


def badge(x: float, y: float, n: str, color: str = INK) -> str:
    return (f'<circle cx="{x}" cy="{y}" r="11" fill="{color}"/>' + text(x, y + 4.5, n, 12, weight=700, color=CARD))


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------


def big_picture() -> str:
    b = []
    b.append(region(10, 10, 210, 330, "On the device"))
    b.append(box(30, 50, 170, 110, "iOS app", ["SwiftUI", "VisionKit scanner", "Vision OCR"], "blue"))
    b.append(box(30, 200, 170, 110, "Web app", ["Next.js", "tesseract.js OCR", "counsellor inbox"], "blue"))
    b.append(region(260, 10, 430, 330, "AWS, Frankfurt (eu-central-1)", AWS))
    b.append(box(280, 120, 120, 90, "CloudFront", ["web files", "+ /v1/* API"], "aws"))
    b.append(box(430, 40, 120, 70, "Cognito", ["sign-in"], "aws"))
    b.append(box(430, 125, 120, 80, "API Lambda", ["FastAPI"], "aws"))
    b.append(box(430, 235, 120, 80, "Step Functions", ["the pipeline"], "aws"))
    b.append(box(570, 235, 105, 80, "Worker", ["Lambda"], "aws"))
    b.append(box(570, 125, 105, 80, "S3", ["optional images"], "aws"))
    b.append(box(730, 60, 160, 90, "Neon PostgreSQL", ["Frankfurt", "row-level security"], "deep"))
    b.append(box(730, 220, 160, 90, "Mistral", ["the language model", "EU"], "ai"))
    b.append(arrow(200, 105, 280, 150, "text", size=10, label_dy=-10))
    b.append(arrow(200, 255, 280, 185, "text", size=10, label_dy=16))
    b.append(arrow(400, 165, 430, 165))
    b.append(arrow(490, 125, 490, 110, "", dashed=True))
    b.append(arrow(490, 205, 490, 235, "start"))
    b.append(arrow(550, 275, 570, 275))
    b.append(arrow(550, 165, 570, 165))
    b.append(path("M550,140 C640,60 680,90 730,100"))
    b.append(path("M675,255 C700,180 700,160 730,130"))
    b.append(arrow(675, 290, 730, 270, "prompts", size=10))
    return svg(900, 350, "".join(b), "Figure 1. The big picture. Photos never leave the device: only recognized text is sent.")


def life_of_letter() -> str:
    lanes = [("Reader + app", 80), ("API", 250), ("Database", 420), ("Pipeline", 590), ("Model", 760)]
    b = []
    for name, x in lanes:
        b.append(box(x - 70, 10, 140, 34, name, kind="ink", size=12))
        b.append(f'<line x1="{x}" y1="44" x2="{x}" y2="560" stroke="{LINE}" stroke-width="2" stroke-dasharray="4 4"/>')
    steps = [
        (80, 80, 80, 80, "1  scan + OCR on the phone", None),
        (80, 115, 250, 115, "2  POST /v1/letters (text lines)", None),
        (250, 150, 420, 150, "3  quota, rate limit, encrypt, save", None),
        (250, 185, 590, 185, "4  start the workflow", None),
        (250, 215, 80, 215, "5  202 Accepted (id)", "back"),
        (590, 255, 590, 255, "6  classify (local model, no LLM)", None),
        (590, 295, 760, 295, "7  extract facts (pseudonymized text)", None),
        (590, 335, 590, 335, "8  verify every date and amount in code", None),
        (590, 375, 590, 375, "9  retrieve explanation passages", None),
        (590, 415, 760, 415, "10  explain in the reader's language", None),
        (590, 455, 420, 455, "11  save encrypted result, status ready", "back"),
        (80, 500, 250, 500, "12  GET /v1/letters/{id} (polling)", None),
        (250, 535, 80, 535, "13  facts + explanation + original lines", "back"),
    ]
    for x1, y, x2, _y, label, kind in steps:
        if x1 == x2:
            b.append(f'<rect x="{x1 - 8}" y="{y - 12}" width="16" height="24" rx="4" fill="{MARKER}" stroke="{INK}"/>')
            b.append(text(x1 + 18, y + 4, label, 11.5, "start", 600))
        else:
            b.append(arrow(x1, y, x2, y, "", dashed=kind == "back"))
            anchor_x = (x1 + x2) / 2
            b.append(text(anchor_x, y - 6, label, 11.5, weight=600))
    return svg(860, 570, "".join(b), "Figure 2. The life of one letter. The pipeline runs in the background; the app polls for the result.")


def pipeline() -> str:
    b = []
    steps = [
        ("classify", ["letter type", "scikit-learn model"], "default"),
        ("extract", ["facts + line ids", "LLM"], "ai"),
        ("verify", ["check each fact", "plain code"], "ok"),
        ("retrieve", ["sourced passages", "BM25 search"], "default"),
        ("explain", ["reader's language", "LLM"], "ai"),
        ("sanitize", ["remove unsafe text", "plain code"], "ok"),
    ]
    x = 10
    for i, (title, lines, kind) in enumerate(steps):
        b.append(box(x, 60, 130, 90, title, lines, kind))
        if i < len(steps) - 1:
            b.append(arrow(x + 130, 105, x + 150, 105))
        x += 150
    b.append(text(450, 30, "The model proposes (purple). Code verifies (green).", 14, weight=700))
    b.append(box(160, 185, 290, 60, "If the model fails or the budget is spent:", ["rules extractor + template explanation, marked degraded"], "check", 12))
    b.append(path("M225,150 L225,185", CHECK, dashed=True, marker="a"))
    b.append(path("M680,150 L680,175 L450,200", CHECK, dashed=True, marker="a"))
    return svg(910, 260, "".join(b), "Figure 3. The six pipeline steps. Two steps use the language model; the steps after them check its work.")


def grounding() -> str:
    b = []
    b.append(box(10, 20, 300, 150, "The letter (OCR lines)", [], "default", top=True))
    rows = [("p1-l12", "Nachzahlung: 1.523,00 €", False), ("p1-l13", "Bitte zahlen Sie bis zum 12.02.2026.", True),
            ("p1-l14", "Bei verspäteter Zahlung …", False)]
    for i, (lid, t, hl) in enumerate(rows):
        y = 70 + i * 30
        if hl:
            b.append(f'<rect x="22" y="{y - 16}" width="276" height="24" rx="4" fill="{MARKER}"/>')
        b.append(text(30, y, lid, 11, "start", 700, BLUE))
        b.append(text(85, y, t, 11.5, "start"))
    b.append(box(370, 20, 250, 150, "The model says", [], "ai", top=True))
    b.append(text(385, 70, 'date: "2026-02-12"', 12, "start", color=AI))
    b.append(text(385, 95, 'line_ids: ["p1-l13"]', 12, "start", color=AI))
    b.append(text(385, 130, 'date: "2026-02-15"  (invented)', 12, "start", color=RED))
    b.append(text(385, 150, 'line_ids: ["p1-l13"]', 12, "start", color=RED))
    b.append(box(680, 20, 210, 70, "verified", ["12.02.2026 is in line p1-l13"], "ok"))
    b.append(box(680, 100, 210, 70, "needs_check", ["shown as “please check”"], "check"))
    b.append(arrow(620, 82, 680, 55, "", color=OK, marker="ag"))
    b.append(arrow(620, 140, 680, 135, "", color=RED, marker="ar"))
    b.append(arrow(310, 95, 370, 95, "read"))
    b.append(text(450, 200, "verify() parses the cited line with German date and amount parsers. "
                  "A value that is not there is never shown as a fact.", 12.5, weight=600))
    return svg(900, 215, "".join(b), "Figure 4. The grounding check: the most important safety mechanism in LetterLens.")


def modules() -> str:
    b = []
    b.append(box(330, 10, 240, 52, "api", ["routes, auth, schemas, errors"], "ink", 13))
    b.append(box(330, 90, 240, 52, "services", ["letters, sharing, billing use cases"], "default"))
    b.append(box(330, 170, 240, 52, "pipeline", ["steps, state, runners"], "default"))
    nodes = [
        (20, 260, "llm", ["gateway, providers, prompts"], "ai"),
        (200, 260, "grounding", ["parsers, deadlines, verifier"], "ok"),
        (380, 260, "rag", ["corpus, retriever"], "default"),
        (560, 260, "ml", ["classifier"], "default"),
        (740, 260, "safety", ["PII vault, guardrail"], "check"),
    ]
    for x, y, t, ln, k in nodes:
        b.append(box(x, y, 160, 56, t, ln, k, 13))
        b.append(arrow(450, 222, x + 80, y))
    b.append(box(130, 360, 180, 52, "db", ["pool, RLS context, repos"], "deep"))
    b.append(box(360, 360, 180, 52, "crypto", ["envelope encryption"], "deep"))
    b.append(box(590, 360, 180, 52, "domain.py", ["shared types, no deps"], "marker"))
    b.append(arrow(450, 62, 450, 90))
    b.append(arrow(450, 142, 450, 170))
    b.append(path("M330,116 C220,130 220,330 220,360"))
    b.append(path("M570,116 C650,140 470,300 450,360"))
    b.append(box(780, 10, 110, 52, "handlers", ["Lambda entry"], "aws", 12))
    b.append(arrow(780, 36, 570, 36))
    return svg(900, 425, "".join(b), "Figure 5. Backend modules. Arrows point to dependencies. domain.py depends on nothing.")


def rls() -> str:
    b = []
    b.append(box(20, 20, 180, 60, "Alice (reader)", ["owns letter A"], "blue"))
    b.append(box(20, 110, 180, 60, "Bob (reader)", ["owns letter B"], "blue"))
    b.append(box(20, 200, 180, 60, "Carol (counsellor)", ["member of service X"], "ok"))
    b.append(box(20, 290, 180, 60, "Dave (counsellor)", ["member of service Y"], "ok"))
    b.append(box(330, 60, 220, 80, "letter A", ["shared with X until 26 Dec"], "marker"))
    b.append(box(330, 220, 220, 80, "letter B", ["not shared"], "default"))
    b.append(arrow(200, 50, 330, 90, "owner", size=10.5, color=OK, marker="ag", label_dx=-20, label_dy=-10))
    b.append(arrow(200, 140, 330, 250, "owner", size=10.5, color=OK, marker="ag", label_dx=-40, label_dy=-18))
    b.append(arrow(200, 230, 330, 120, "active share: read", size=10.5, color=OK, marker="ag", label_dx=-25, label_dy=30))
    b.append(arrow(200, 320, 330, 280, "no share: nothing", size=10.5, color=RED, marker="ar", label_dx=0, label_dy=18))
    b.append(box(610, 40, 280, 270, "PostgreSQL decides", [], "deep", top=True))
    lines = ["Every transaction sets:", "app.user_id, app.tenant_ids, app.system", "",
             "Policies on every table, e.g. letters:", "owner_id = app_user_id()", "OR an active share to my tenant", "",
             "The app role does not own the tables", "and cannot bypass RLS.", "19 tests prove each rule."]
    for i, ln in enumerate(lines):
        b.append(text(625, 85 + i * 21, ln, 12, "start", 600 if i in (0, 3, 7) else 400))
    return svg(900, 360, "".join(b), "Figure 6. Row-level security: isolation is enforced inside the database, not only in Python code.")


def encryption() -> str:
    b = []
    b.append(box(20, 30, 200, 80, "KEK", ["1 key, in SSM Parameter Store", "backup in your Keychain"], "ink", 13))
    b.append(box(300, 30, 230, 80, "DEK per user", ["random 32 bytes", "stored wrapped (encrypted)"], "marker", 13))
    b.append(box(610, 30, 270, 80, "letter, results, messages", ["AES-256-GCM", "bound to the record id"], "default", 13))
    b.append(arrow(220, 70, 300, 70, "wraps"))
    b.append(arrow(530, 70, 610, 70, "encrypts"))
    b.append(box(300, 150, 230, 70, "Delete the account", ["= delete the wrapped DEK"], "red"))
    b.append(box(610, 150, 270, 70, "All copies unreadable", ["also in database backups"], "red"))
    b.append(arrow(530, 185, 610, 185))
    b.append(arrow(415, 110, 415, 150, "", dashed=True))
    return svg(900, 235, "".join(b), "Figure 7. Envelope encryption and crypto-shredding.")


def pii() -> str:
    b = []
    b.append(box(10, 20, 270, 120, "Original line", [], "default", top=True))
    b.append(text(25, 70, "Ayşe Yılmaz", 12.5, "start"))
    b.append(text(25, 95, "Steuernummer: 502/898/93783", 12.5, "start"))
    b.append(text(25, 120, "IBAN DE89 3704 0044 0532 0130 00", 12.5, "start"))
    b.append(box(320, 20, 250, 120, "What the model sees", [], "ai", top=True))
    b.append(text(335, 70, "[NAME_1]", 12.5, "start", color=AI))
    b.append(text(335, 95, "Steuernummer: [TAXNO_1]", 12.5, "start", color=AI))
    b.append(text(335, 120, "IBAN [IBAN_1]", 12.5, "start", color=AI))
    b.append(box(610, 20, 280, 120, "Answer, restored in code", [], "ok", top=True))
    b.append(text(625, 70, "reference: 502/898/93783", 12.5, "start", color=OK))
    b.append(text(625, 95, "(the vault maps placeholders", 11.5, "start", color=SOFT))
    b.append(text(625, 115, "back; it lives only in memory)", 11.5, "start", color=SOFT))
    b.append(arrow(280, 80, 320, 80, "redact"))
    b.append(arrow(570, 80, 610, 80, "restore"))
    return svg(900, 155, "".join(b), "Figure 8. Pseudonymization with PiiVault: personal data is replaced before any text reaches the model.")


def gateway() -> str:
    b = []
    b.append(box(10, 120, 140, 60, "generate()", ["task + schema"], "ink", 13))
    b.append(box(190, 120, 140, 60, "budget check", ["month + user"], "check"))
    b.append(box(370, 120, 150, 60, "provider call", ["model 1, then 2"], "ai"))
    b.append(box(560, 120, 150, 60, "parse + validate", ["strict JSON schema"], "ok"))
    b.append(box(750, 120, 140, 60, "typed result", ["pydantic model"], "blue"))
    for x in (150, 330, 520, 710):
        b.append(arrow(x, 150, x + 40, 150))
    b.append(box(190, 10, 140, 55, "BudgetExceeded", ["→ degraded mode"], "red", 12))
    b.append(arrow(260, 120, 260, 65, "", color=RED, marker="ar"))
    b.append(box(370, 10, 150, 55, "429 / 5xx / timeout", ["retry 3x, backoff"], "check", 12))
    b.append(path("M410,120 C400,90 430,80 440,65", CHECK))
    b.append(path("M480,65 C490,85 480,100 470,120", CHECK))
    b.append(box(560, 10, 150, 55, "invalid JSON", ["one repair attempt"], "check", 12))
    b.append(path("M600,120 C590,95 595,80 610,65", CHECK))
    b.append(path("M660,65 C640,80 560,100 500,120", CHECK))
    b.append(box(370, 230, 340, 55, "Cost ledger (table llm_calls)", ["tokens, list price, latency, prompt version — never text"], "deep", 12))
    b.append(arrow(445, 180, 445, 230, "", dashed=True))
    b.append(arrow(635, 180, 635, 230, "", dashed=True))
    return svg(900, 300, "".join(b), "Figure 9. The LLM gateway: the only door from the application to any model.")


def retrieval() -> str:
    b = []
    b.append(box(10, 90, 170, 70, "Query", ["subject, actions,", "German letter text"], "default", 12))
    b.append(box(230, 20, 190, 70, "BM25 (keywords)", ["ranks 24 passages"], "default", 12))
    b.append(box(230, 160, 190, 70, "Embeddings (meaning)", ["optional, cosine"], "ai", 12))
    b.append(box(470, 90, 190, 70, "Reciprocal rank fusion", ["1/(60+rank) summed"], "marker", 12))
    b.append(box(710, 90, 180, 70, "Top 4 for the type", ["c1..c4 with sources"], "ok", 12))
    b.append(arrow(180, 115, 230, 60))
    b.append(arrow(180, 135, 230, 190))
    b.append(arrow(420, 55, 470, 115))
    b.append(arrow(420, 195, 470, 135))
    b.append(arrow(660, 125, 710, 125, "filter by type"))
    return svg(900, 245, "".join(b), "Figure 10. Hybrid retrieval. German keywords in each passage bridge German letters and English passages.")


def classifier() -> str:
    b = []
    b.append(box(10, 30, 160, 80, "Letter text", ["“Finanzamt…", "Einkommensteuer…”"], "default", 12))
    b.append(box(210, 30, 170, 80, "Features", ["words, word pairs,", "4-letter pieces"], "default", 12))
    b.append(box(420, 30, 170, 80, "TF-IDF + weights", ["one score per type"], "blue", 12))
    b.append(box(630, 30, 120, 80, "softmax(z / T)", ["T = 0.155"], "marker", 12))
    b.append(box(780, 30, 110, 80, "tax 0.97", ["or abstain", "< 0.50"], "ok", 12))
    for x in (170, 380, 590, 750):
        b.append(arrow(x, 70, x + 30 if x != 750 else x + 30, 70))
    b.append(text(450, 150, "Trained offline with scikit-learn. Served with 80 lines of plain Python (no numpy in Lambda).", 12.5, weight=600))
    return svg(900, 165, "".join(b), "Figure 11. The letter-type classifier: classic machine learning where an LLM is not needed.")


def eval_flow() -> str:
    b = []
    b.append(box(10, 20, 200, 70, "Golden letters", ["126 with exact labels"], "marker", 12))
    b.append(box(10, 110, 200, 70, "Red-team questions", ["96 in 6 languages"], "marker", 12))
    b.append(box(10, 200, 200, 70, "Judge calibration", ["20 known pairs"], "marker", 12))
    b.append(box(270, 20, 230, 250, "evals/run.py", [], "default", 13, top=True))
    for i, s in enumerate(["classification", "extraction", "retrieval", "guardrail", "faithfulness (live)"]):
        b.append(text(385, 80 + i * 38, s, 12.5, weight=600))
    b.append(box(560, 30, 150, 70, "offline", ["rules, every PR"], "blue", 12))
    b.append(box(560, 115, 150, 70, "chaos", ["injected errors"], "check", 12))
    b.append(box(560, 200, 150, 70, "live", ["real model"], "ai", 12))
    b.append(box(760, 90, 130, 110, "Gate", ["thresholds.yaml", "pass / fail", "(CI exit code)"], "ink", 12))
    for y in (55, 145, 235):
        b.append(arrow(210, y, 270, y))
        b.append(arrow(710, y + 10, 760, 145))
    b.append(arrow(500, 145, 560, 65))
    b.append(arrow(500, 145, 560, 150))
    b.append(arrow(500, 145, 560, 235))
    return svg(900, 285, "".join(b), "Figure 12. The evaluation system. The same suites run with three profiles.")


def results_chart() -> str:
    metrics = [
        ("Deadline recall", 99.0, 98.0),
        ("Deadline precision", 100.0, 94.1),
        ("Every deadline exact", 99.2, 93.7),
        ("Amount recall", 98.5, 100.0),
        ("Amount direction", 96.3, 93.4),
        ("Advice requests caught", 100.0, 85.2),
        ("Injections caught", 100.0, 100.0),
    ]
    b = []
    x0, w, top = 220, 600, 40
    b.append(f'<rect x="{x0}" y="16" width="14" height="12" fill="{AI}"/>' + text(x0 + 20, 26, "live (Mistral)", 12, "start"))
    b.append(f'<rect x="{x0 + 150}" y="16" width="14" height="12" fill="{FAINT}"/>' + text(x0 + 170, 26, "rules only", 12, "start"))
    for i, (name, live, rules) in enumerate(metrics):
        y = top + i * 46
        b.append(text(x0 - 12, y + 20, name, 12.5, "end", 600))
        b.append(f'<rect x="{x0}" y="{y + 4}" width="{w * live / 100}" height="15" rx="3" fill="{AI}"/>')
        b.append(f'<rect x="{x0}" y="{y + 22}" width="{w * rules / 100}" height="15" rx="3" fill="{FAINT}"/>')
        b.append(text(x0 + w * live / 100 + 6, y + 16, f"{live:.1f} %", 11, "start", 700, AI))
        b.append(text(x0 + w * rules / 100 + 6, y + 34, f"{rules:.1f} %", 11, "start", 400, SOFT))
    b.append(f'<line x1="{x0}" y1="{top - 4}" x2="{x0}" y2="{top + 7 * 46}" stroke="{LINE}"/>')
    return svg(900, 370, "".join(b), "Figure 13. Measured results on the golden set (25 November 2026). Unsafe verified facts: 0 in both.")


def test_pyramid() -> str:
    b = []
    tiers = [
        (360, 20, 180, "Release gate", "evals: offline, chaos, live", "ink"),
        (300, 85, 300, "Integration (database)", "test_api, test_rls: real PostgreSQL, RLS on", "ai"),
        (240, 150, 420, "Component", "pipeline, gateway, retriever, classifier parity, App Store JWS", "blue"),
        (180, 215, 540, "Unit", "date and amount parsers, deadlines, verifier, PII, guardrail, crypto, auth", "ok"),
        (120, 280, 660, "Contract and infra", "fixtures decoded in Swift; CDK template assertions; web components", "deep"),
    ]
    for x, y, w, t, sub, k in tiers:
        b.append(box(x, y, w, 55, t, [sub], k, 13))
    b.append(text(450, 360, "157 Python tests + 8 infra + 10 web + 11 Swift tests; gates run on every pull request.", 12.5, weight=600))
    return svg(900, 375, "".join(b), "Figure 14. The test pyramid: many fast unit tests, fewer slow tests, one release gate.")


def ci_cd() -> str:
    b = []
    b.append(box(10, 100, 120, 60, "git push", ["main or PR"], "ink", 12))
    b.append(region(160, 10, 340, 240, "CI workflow (parallel jobs)", BLUE))
    for i, (t, s) in enumerate([("backend", "ruff, mypy, 157 tests"), ("eval-gate", "offline + chaos"),
                                ("infra", "bundle, tests, cdk-nag"), ("web", "lint, tests, build")]):
        b.append(box(180, 40 + i * 52, 300, 44, t, [s], "blue", 12))
    b.append(box(540, 30, 160, 60, "iOS workflow", ["only if ios/** changed"], "default", 12))
    b.append(box(540, 140, 160, 90, "Deploy workflow", ["if CI green and", "DEPLOY_ENABLED"], "aws", 12))
    b.append(box(740, 100, 150, 140, "Deploy job", ["migrate Neon", "build web + Lambda", "OIDC → AWS role", "cdk deploy", "smoke test"], "ok", 12))
    b.append(arrow(130, 130, 160, 130))
    b.append(arrow(500, 130, 540, 180))
    b.append(arrow(700, 185, 740, 170))
    b.append(path("M70,100 L70,8 L620,8 L620,30", dashed=True))
    return svg(900, 260, "".join(b), "Figure 15. Continuous integration and delivery. No AWS keys are stored in GitHub (OIDC).")


def ios_arch() -> str:
    b = []
    b.append(box(10, 20, 880, 60, "Views (SwiftUI)", ["SignInView · LettersView · NewLetterView · LetterDetailView · SettingsView · Theme"], "blue", 13))
    b.append(box(10, 110, 300, 70, "AppModel (@Observable, @MainActor)", ["phase, me, languages, errors"], "ink", 12))
    b.append(box(340, 110, 550, 70, "Services", ["AuthService (actor, PKCE, Keychain) · TextRecognizer (Vision) · DocumentScanner", "ReminderService (EventKit, notifications) · StoreService (StoreKit 2)"], "default", 12))
    b.append(box(10, 210, 880, 70, "LetterLensCore (Swift package, tested on macOS)", ["Models (Codable) · APIClient · PKCE · DocumentBuilder (OCR line order) · Deadlines"], "marker", 13))
    b.append(box(10, 310, 430, 50, "contracts/fixtures/*.json", ["real API responses"], "deep", 12))
    b.append(box(460, 310, 430, 50, "API (/v1)", ["CloudFront → Lambda"], "aws", 12))
    b.append(arrow(160, 80, 160, 110))
    b.append(arrow(615, 80, 615, 110))
    b.append(arrow(160, 180, 160, 210))
    b.append(arrow(615, 180, 615, 210))
    b.append(arrow(225, 310, 225, 280, "decoded by tests", size=10, label_dx=60))
    b.append(arrow(675, 280, 675, 310, "HTTPS", size=10, label_dx=30))
    return svg(900, 370, "".join(b), "Figure 16. The iOS app. Logic that needs no UIKit lives in a package that `swift test` runs on a Mac.")


def aws_infra() -> str:
    b = []
    b.append(region(10, 10, 880, 330, "CDK stack LetterLens-prod (infra/letterlens_infra/stack.py)", AWS))
    b.append(box(30, 50, 170, 70, "CloudFront", ["security headers, CSP", "index rewrite function"], "aws", 12))
    b.append(box(30, 150, 170, 60, "S3 web bucket", ["static Next.js export"], "aws", 12))
    b.append(box(30, 240, 170, 70, "Cognito Lite", ["web + iOS clients", "groups"], "aws", 12))
    b.append(box(260, 50, 170, 70, "API Lambda", ["function URL", "X-Origin-Verify check"], "aws", 12))
    b.append(box(260, 150, 170, 60, "Step Functions", ["Standard, retries"], "aws", 12))
    b.append(box(260, 240, 170, 70, "Worker + Status", ["Lambda, arm64", "Python 3.13"], "aws", 12))
    b.append(box(490, 50, 170, 70, "S3 letters bucket", ["optional images", "lifecycle expiry"], "aws", 12))
    b.append(box(490, 150, 170, 60, "SSM parameters", ["secrets, free"], "aws", 12))
    b.append(box(490, 240, 170, 70, "Retention Lambda", ["daily 03:15", "EventBridge rule"], "aws", 12))
    b.append(box(710, 50, 160, 70, "CloudWatch", ["logs 14 days", "6 alarms"], "aws", 12))
    b.append(box(710, 150, 160, 60, "SNS + Budget", ["e-mail at $0.50 / $1"], "aws", 12))
    b.append(box(710, 240, 160, 70, "cdk-nag", ["security rules,", "reasons for exceptions"], "default", 12))
    b.append(arrow(200, 85, 260, 85, "/v1/*"))
    b.append(arrow(115, 120, 115, 150))
    b.append(arrow(345, 120, 345, 150))
    b.append(arrow(345, 210, 345, 240))
    b.append(arrow(430, 85, 490, 85))
    return svg(900, 350, "".join(b), "Figure 17. Everything on AWS is code. One command creates or updates it.")


def cost_chart() -> str:
    b = []
    items = [("Lambda requests", 0.5), ("CloudFront", 0.1), ("Step Functions", 100), ("Neon storage", 1), ("CloudWatch metrics", 90)]
    b.append(text(20, 25, "Share of the free limit used by 400 letters per month (%)", 13, "start", 700))
    for i, (n, v) in enumerate(items):
        y = 45 + i * 34
        b.append(text(190, y + 16, n, 12.5, "end", 600))
        b.append(f'<rect x="200" y="{y + 4}" width="600" height="16" rx="3" fill="{DEEP}"/>')
        color = CHECK if v >= 90 else OK
        b.append(f'<rect x="200" y="{y + 4}" width="{6 * max(v, 0.6)}" height="16" rx="3" fill="{color}"/>')
        inside = v >= 50
        b.append(text(200 + 6 * max(v, 0.6) + (-8 if inside else 8), y + 17, f"{v:g} %", 11.5,
                      "end" if inside else "start", 700, CARD if inside else color))
    return svg(900, 225, "".join(b), "Figure 18. Step Functions is the first free limit (about 400 letters per month). CloudWatch uses 9 of 10 free metrics.")
