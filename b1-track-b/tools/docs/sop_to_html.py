import os, sys, markdown, re
src, out = sys.argv[1], sys.argv[2]
md = open(src, encoding="utf-8").read()
# Python-Markdown needs a blank line before a list that follows a paragraph line.
lines, prev = [], ""
in_code = False
for ln in md.split("\n"):
    if ln.startswith("```"):
        in_code = not in_code
    is_item = bool(re.match(r"^(\s*[-*]|\d+\.) ", ln))
    if not in_code and is_item and prev.strip() and not re.match(r"^(\s*[-*]|\d+\.) ", prev) \
            and not prev.startswith("|"):
        lines.append("")
    lines.append(ln); prev = ln
md = "\n".join(lines)
body = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
FOOTER = os.environ.get("DOC_FOOTER", "B1 Version-Aware Retrieval · Track B SOP")
SUBTITLE = os.environ.get("DOC_SUBTITLE", "Standard operating procedure and runbook: build, test and recreate the B1 experiment")
TAG = os.environ.get("DOC_TAG", "Version 2 · 2026-10-18 · Steps 2–6 complete, Step 7 next · every command in Appendix A")
css = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm;
  @bottom-center { content: "__FOOTER__ · page " counter(page) " of " counter(pages); font: 8pt Helvetica; color: #6b7280; } }
body { font-family: -apple-system, Helvetica, Arial, sans-serif; font-size: 9.6pt; line-height: 1.45; color: #1f2a37; }
.cover { background: #1f2a37; color: #fff; padding: 22px 26px; border-radius: 10px; margin-bottom: 18px; }
.flow { margin: 10px 0 6px; }
.lane { display:flex; align-items:center; gap:6px; margin: 8px 0; flex-wrap: nowrap; }
.lane .lbl { flex: 0 0 58px; font-weight:700; font-size:8.5pt; color:#0b6e61; }
.box { flex: 1 1 0; overflow-wrap:anywhere; border:1.5px solid #9aa7b4; background:#f7f9fb; border-radius:7px; padding:6px 8px; font-size:8.3pt; text-align:center; min-width:58px; }
.box small { display:block; color:#6b7280; font-size:7.2pt; }
.box.src { background:#eef2f5; }
.box.new { background:#fff4e8; border:2px solid #e8833a; color:#8a4510; font-weight:700; }
.box.meta { background:#e6f6f3; border-color:#0f9d8a; }
.arr { color:#6b7280; font-size:12pt; flex: 0 0 auto; }
.legend { font-size:8pt; color:#6b7280; margin-top:4px; }
.cover h1 { margin: 0 0 6px; font-size: 22pt; color: #fff; border: 0; }
.cover p { margin: 2px 0; color: #cbd5e1; font-size: 10.5pt; }
.cover .tag { display:inline-block; margin-top:10px; background:#0f9d8a; color:#fff; padding:3px 10px; border-radius:12px; font-size:9pt; }
h1 { font-size: 17pt; color: #1f2a37; }
h2 { font-size: 14pt; color: #0b6e61; margin-top: 22px; page-break-after: avoid; break-before: page; }
h2:first-of-type { break-before: auto; }
h3 { font-size: 11.5pt; color: #1f2a37; margin-top: 18px; padding: 5px 9px; background: #eef2f5; border-radius: 5px; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 12px; font-size: 8.4pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th { background: #1f2a37; color: #fff; text-align: left; padding: 4px 6px; }
td { border-bottom: 1px solid #d8dee4; padding: 4px 6px; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fb; }
code { font-family: "Courier New", Courier, monospace; font-weight: 600; font-size: 8.2pt; background: #eef2f5; padding: 0 3px; border-radius: 3px; overflow-wrap: anywhere; }
pre { background: #0f1720; color: #e5e7eb; padding: 9px 11px; border-radius: 6px; white-space: pre-wrap; word-break: break-word; page-break-inside: avoid; }
pre code { background: none; color: inherit; font-size: 7.9pt; padding: 0; }
strong { color: #111827; }
hr { border: 0; border-top: 1px solid #d8dee4; margin: 16px 0; }
"""
# Drop empty table header rows (the SOP's key/value table has a blank header)
body = re.sub(r"<thead>\s*<tr>\s*(<th></th>\s*)+</tr>\s*</thead>", "", body)
# Replace the ASCII flow diagram with a drawn one
FLOW = open(sys.argv[3], encoding="utf-8").read() if len(sys.argv) > 3 else ""
body = re.sub(r"(<h2>2\. The flow</h2>\s*)<pre>.*?</pre>", lambda m: m.group(1) + FLOW, body, count=1, flags=re.S)
# Replace the SOP's own H1 + metadata table with a cover block
m = re.search(r"<h1>(.*?)</h1>", body)
title = m.group(1) if m else "SOP"
body = body.replace(m.group(0), "", 1) if m else body
cover = f"""<div class="cover"><h1>{title}</h1>
<p>{SUBTITLE}</p>
<p>Modern AI Pro · Level 2 · Track B · RAG Design · Owner: Shreenath Shetty</p>
<span class="tag">{TAG}</span></div>"""
css = css.replace("__FOOTER__", FOOTER)
if os.environ.get("DOC_H2_BREAK", "1") == "0":
    css += "\nh2 { break-before: auto !important; margin-top: 26px; }\n"
open(out, "w", encoding="utf-8").write(f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{css}</style></head><body>{cover}{body}</body></html>")
