"""Build the illustrated guide (a local PDF that is not kept in git) from the HTML parts and the SVG diagrams.

Usage: python3 docs/guide/build.py   (needs Google Chrome; macOS sips reduces the icon images)
"""

from __future__ import annotations

import base64
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagrams as D  # noqa: E402

OUT_HTML = HERE / "guide.html"
OUT_PDF = HERE.parent / "LetterLens-Guide.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ICON_DIR = HERE.parents[1] / "ios/LetterLens/Resources/Assets.xcassets/AppIcon.appiconset"
ICON_PX = 640  # the 1024 px originals are reduced for the PDF; they stay sharp at the printed size


def icon(name: str) -> str:
    """The app icon as a data URI, reduced with sips (macOS) when it is available."""
    src = ICON_DIR / name
    data = src.read_bytes()
    if shutil.which("sips"):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / name
            done = subprocess.run(["sips", "-Z", str(ICON_PX), str(src), "--out", str(out)], capture_output=True)
            if done.returncode == 0 and out.exists():
                data = out.read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def cover_icon() -> str:
    return f'<img class="app-icon" src="{icon("icon-1024.png")}" alt="LetterLens app icon">'


def icons() -> str:
    cells = [("icon-1024.png", "Light", "the default home screen"),
             ("icon-dark-1024.png", "Dark", "dark home screen (iOS 18+)"),
             ("icon-tinted-1024.png", "Tinted", "tinted home screen (iOS 18+)")]
    out = ['<figure class="icons"><div class="icon-row">']
    for name, label, sub in cells:
        out.append(f'<div class="icon-cell"><img class="app-icon small" src="{icon(name)}" alt="{label} icon">'
                   f'<p><strong>{label}</strong><br>{sub}</p></div>')
    out.append(f'<div class="icon-cell"><div class="logo-tile">{LOGO}</div>'
               '<p><strong>Logo mark</strong><br>header, navigation bar</p></div>')
    out.append("</div><figcaption>Figure 0. The new app icon in its three variants, and the small logo "
               "(drawn from ios/scripts/make_icon.swift and Brand.tsx).</figcaption></figure>")
    return "".join(out)


LOGO = f"""<svg width="96" height="96" viewBox="0 0 48 48" aria-hidden="true">
<rect x="4" y="10" width="32" height="24" rx="3" fill="{D.CARD}" stroke="{D.INK}" stroke-width="2.5"/>
<path d="M5 12l15 11 15-11" fill="none" stroke="{D.INK}" stroke-width="2.5" stroke-linejoin="round"/>
<circle cx="31" cy="29" r="9" fill="{D.MARKER}" fill-opacity="0.9" stroke="{D.INK}" stroke-width="2.5"/>
<path d="M37.5 35.5L44 42" stroke="{D.INK}" stroke-width="3.5" stroke-linecap="round"/></svg>"""

CSS = f"""
@page {{ size: A4; margin: 18mm 17mm 20mm 17mm;
  @bottom-center {{ content: counter(page); font: 9pt -apple-system, Helvetica, sans-serif; color: {D.FAINT}; }}
  @top-right {{ content: "LetterLens guide · 27 November 2026"; font: 8.5pt -apple-system, Helvetica, sans-serif; color: {D.FAINT}; }} }}
@page :first {{ @bottom-center {{ content: none; }} @top-right {{ content: none; }} }}
* {{ box-sizing: border-box; }}
html {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
body {{ margin: 0; color: {D.INK}; font: 10.3pt/1.5 -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif; }}
h1, h2, h3, h4 {{ font-family: "Iowan Old Style", "Palatino", Georgia, serif; line-height: 1.2; color: {D.INK}; }}
section + section {{ break-before: page; }}
h2 {{ font-size: 22pt; margin: 0 0 10pt; border-bottom: 2px solid {D.INK}; padding-bottom: 6pt; }}
h2 .num {{ display: inline-block; background: {D.MARKER}; border-radius: 6px; padding: 0 9px; margin-right: 8px; }}
h3 {{ font-size: 13.5pt; margin: 16pt 0 5pt; break-after: avoid; }}
h4 {{ font-size: 11.5pt; margin: 0 0 4pt; }}
p {{ margin: 0 0 7pt; }}
ul, ol {{ margin: 0 0 8pt; padding-left: 18pt; }}
li {{ margin-bottom: 3pt; }}
code {{ font: 8.8pt "SF Mono", Menlo, Consolas, monospace; background: {D.DEEP}; padding: 0 3px; border-radius: 3px; }}
pre {{ background: #1f2740; color: #f1ece0; border-radius: 8px; padding: 9pt 11pt; margin: 4pt 0 10pt;
  break-inside: avoid; white-space: pre-wrap; }}
pre code {{ background: none; color: inherit; padding: 0; font-size: 8.6pt; line-height: 1.45; }}
table {{ width: 100%; border-collapse: collapse; margin: 4pt 0 12pt; font-size: 9.4pt; break-inside: auto; }}
table.small {{ font-size: 8.8pt; }}
table.tight td {{ padding: 3.6pt 7pt; }}
tr {{ break-inside: avoid; }}
thead {{ display: table-header-group; break-after: avoid; }}
th code {{ background: rgba(255,255,255,0.16); color: inherit; }}
th {{ text-align: left; background: {D.INK}; color: {D.CARD}; padding: 5pt 7pt; font-weight: 600; }}
td {{ padding: 5pt 7pt; border-bottom: 1px solid {D.LINE}; vertical-align: top; }}
tr:nth-child(even) td {{ background: #faf7f0; }}
figure {{ margin: 8pt 0 14pt; break-inside: avoid; }}
figure svg {{ width: 100%; height: auto; display: block; }}
figcaption {{ font-size: 8.8pt; color: {D.SOFT}; text-align: center; margin-top: 4pt; font-style: italic; }}
.summary {{ background: {D.PAPER}; border-left: 5px solid {D.MARKER}; border-radius: 6px; padding: 9pt 12pt;
  margin: 0 0 12pt; font-size: 10.6pt; break-inside: avoid; }}
.summary::before {{ content: "In short  "; font-weight: 800; color: {D.CHECK}; }}
.callout {{ background: {D.OKBG}; border-radius: 8px; padding: 9pt 12pt; color: {D.OK}; font-weight: 600; break-inside: avoid; }}
.note {{ background: {D.BLUEBG}; border-radius: 8px; padding: 9pt 12pt; margin-top: 18pt; }}
.ios {{ background: {D.BLUEBG}; border-radius: 6px; padding: 5pt 9pt; font-size: 9.5pt; color: {D.BLUE}; }}
.concepts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 9pt; }}
.concept {{ border: 1px solid {D.LINE}; border-radius: 8px; padding: 8pt 10pt; break-inside: avoid; background: #fffdf8; }}
.concept p {{ font-size: 9.4pt; }}
.concept .ios {{ margin: 4pt 0 0; font-size: 8.9pt; }}
ol.steps li {{ margin-bottom: 6pt; }}
.cover {{ height: 255mm; display: flex; flex-direction: column; justify-content: center; padding: 0 10mm;
  position: relative; overflow: hidden;
  background: radial-gradient(900px 600px at 0% 0%, {D.DEEP}, transparent 60%),
    radial-gradient(520px 520px at 100% 0%, rgba(255, 226, 122, 0.55), transparent 70%),
    linear-gradient(180deg, #f7f2e8, #e9dec8); border-radius: 14px; }}
.cover h1 {{ font-size: 56pt; margin: 14pt 0 6pt; letter-spacing: -0.01em; }}
.app-icon {{ width: 46mm; height: 46mm; border-radius: 10.4mm; display: block;
  box-shadow: 0 1px 0 rgba(27,37,64,0.06), 0 14px 30px -10px rgba(27,37,64,0.45); }}
.app-icon.small {{ width: 30mm; height: 30mm; border-radius: 6.8mm; margin: 0 auto 6pt; box-shadow: none;
  outline: 1px solid rgba(27,37,64,0.12); outline-offset: -1px; }}
.icon-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10pt; align-items: start; text-align: center;
  background: {D.PAPER}; border-radius: 12px; padding: 14pt 8pt 8pt; }}
.icon-cell p {{ font-size: 8.8pt; color: {D.SOFT}; margin: 0; }}
.icon-cell strong {{ color: {D.INK}; }}
.logo-tile {{ width: 30mm; height: 30mm; border-radius: 6.8mm; margin: 0 auto 6pt; background: {D.CARD};
  border: 1px solid {D.LINE}; display: flex; align-items: center; justify-content: center; }}
.logo-tile svg {{ width: 20mm; height: 20mm; }}
.sw {{ display: inline-block; width: 11pt; height: 11pt; border-radius: 3px; margin-right: 6pt; vertical-align: -2pt;
  border: 1px solid rgba(27,37,64,0.25); }}
.swatches td {{ white-space: nowrap; }}
.swatches td:last-child {{ white-space: normal; }}
.warning {{ background: {D.CHECKBG}; border-left: 5px solid {D.CHECK}; border-radius: 6px; padding: 8pt 12pt;
  margin: 4pt 0 10pt; font-size: 9.8pt; break-inside: avoid; }}
.warning strong {{ color: {D.CHECK}; }}
.adr {{ border: 1px solid {D.LINE}; border-radius: 10px; padding: 9pt 12pt 3pt; margin: 0 0 9pt; background: #fffdf8;
  break-inside: avoid; }}
.adr p {{ font-size: 9.6pt; margin-bottom: 5pt; }}
.adr h4 {{ font-size: 12pt; margin-bottom: 6pt; }}
.adr-id {{ display: inline-block; background: {D.MARKER}; border-radius: 5px; padding: 0 6px; margin-right: 6px;
  font-family: -apple-system, Helvetica, sans-serif; font-size: 9.5pt; font-weight: 800; vertical-align: 1pt; }}
.adr table {{ margin-bottom: 7pt; }}
.toc-cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 18pt; }}
.toc-part {{ font-size: 9pt; font-weight: 800; text-transform: uppercase; letter-spacing: 0.06em; color: {D.CHECK};
  margin: 10pt 0 0; }}
.cover-sub {{ font-size: 17pt; color: {D.SOFT}; font-family: "Iowan Old Style", Georgia, serif; max-width: 140mm; }}
.cover-meta {{ font-size: 10.5pt; color: {D.SOFT}; margin: 18pt 0 22pt; }}
.cover-box {{ background: {D.CARD}; border: 1px solid {D.LINE}; border-radius: 10px; padding: 12pt 16pt; max-width: 150mm; }}
.toc {{ break-before: page; }}
.toc h2 {{ break-before: avoid; }}
.toc-list {{ font-size: 12pt; line-height: 1.75; margin-bottom: 4pt; }}
.toc-list a {{ color: {D.INK}; text-decoration: none; }}
a {{ color: {D.BLUE}; text-decoration: none; }}
"""


def render() -> str:
    parts = [p.read_text(encoding="utf-8") for p in sorted(HERE.glob("0*.html"))]
    body = "\n".join(parts)
    builders = {name: getattr(D, name) for name in dir(D) if callable(getattr(D, name)) and not name.startswith("_")}

    def repl(m: re.Match[str]) -> str:
        name = m.group(1)
        if name == "logo":
            return LOGO
        if name == "cover_icon":
            return cover_icon()
        if name == "icons":
            return icons()
        return builders[name]()

    body = re.sub(r"\[\[(\w+)\]\]", repl, body)
    # Header rows go into <thead>: Chrome then repeats them on the next page and keeps them with a body row.
    body = re.sub(r"(<table[^>]*>)\s*(<tr>\s*<th>.*?</tr>)", r"\1<thead>\2</thead>", body, flags=re.S)
    counter = iter(range(1, 100))
    body = re.sub(r"<figcaption>Figure \d+\.", lambda _m: f"<figcaption>Figure {next(counter)}.", body)
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>LetterLens guide</title>'
            f"<style>{CSS}</style></head><body>{body}</body></html>")


def main() -> None:
    OUT_HTML.write_text(render(), encoding="utf-8")
    subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
         f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()],
        check=True, capture_output=True,
    )
    print(f"wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
