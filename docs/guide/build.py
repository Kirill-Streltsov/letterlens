"""Build docs/LetterLens-Guide.pdf from the HTML parts and the SVG diagrams.

Usage: python3 docs/guide/build.py   (needs Google Chrome)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import diagrams as D  # noqa: E402

OUT_HTML = HERE / "guide.html"
OUT_PDF = HERE.parent / "LetterLens-Guide.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

LOGO = f"""<svg width="96" height="96" viewBox="0 0 48 48" aria-hidden="true">
<rect x="4" y="10" width="32" height="24" rx="3" fill="{D.CARD}" stroke="{D.INK}" stroke-width="2.5"/>
<path d="M5 12l15 11 15-11" fill="none" stroke="{D.INK}" stroke-width="2.5" stroke-linejoin="round"/>
<circle cx="31" cy="29" r="9" fill="{D.MARKER}" fill-opacity="0.9" stroke="{D.INK}" stroke-width="2.5"/>
<path d="M37.5 35.5L44 42" stroke="{D.INK}" stroke-width="3.5" stroke-linecap="round"/></svg>"""

CSS = f"""
@page {{ size: A4; margin: 18mm 17mm 20mm 17mm;
  @bottom-center {{ content: counter(page); font: 9pt -apple-system, Helvetica, sans-serif; color: {D.FAINT}; }}
  @top-right {{ content: "LetterLens guide"; font: 8.5pt -apple-system, Helvetica, sans-serif; color: {D.FAINT}; }} }}
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
tr {{ break-inside: avoid; }}
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
.cover {{ height: 255mm; display: flex; flex-direction: column; justify-content: center; padding: 0 8mm;
  background: radial-gradient(800px 500px at 10% 0%, {D.DEEP}, transparent 60%), {D.PAPER}; border-radius: 12px; }}
.cover h1 {{ font-size: 54pt; margin: 10pt 0 6pt; }}
.cover-sub {{ font-size: 17pt; color: {D.SOFT}; font-family: "Iowan Old Style", Georgia, serif; max-width: 140mm; }}
.cover-meta {{ font-size: 10.5pt; color: {D.SOFT}; margin: 18pt 0 22pt; }}
.cover-box {{ background: {D.CARD}; border: 1px solid {D.LINE}; border-radius: 10px; padding: 12pt 16pt; max-width: 150mm; }}
.toc {{ break-before: page; }}
.toc h2 {{ break-before: avoid; }}
.toc-list {{ font-size: 12.5pt; line-height: 1.9; }}
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
        return builders[name]()

    body = re.sub(r"\[\[(\w+)\]\]", repl, body)
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
