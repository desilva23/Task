import html
import pathlib
import re

src = pathlib.Path("docs/lld.md").read_text().split("\n")
page = pathlib.Path("docs/pages/locator-lld.html").read_text().split("\n")
head = "\n".join(page[0:61])  # <title> .. </style>


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


out, i, n = [], 0, len(src)
# skip the markdown title block; the page carries its own header
while i < n and not src[i].startswith("## "):
    i += 1


def close_prose(buf):
    if buf:
        out.append('<div class="prose">')
        out.extend(buf)
        out.append("</div>")
        buf.clear()


prose = []
while i < n:
    line = src[i]
    if line.startswith("## "):
        close_prose(prose)
        m = re.match(r"## (\d+)\.\s+(.*)", line)
        out.append(
            f'<h2><span class="sec">{m.group(1)}</span> &nbsp;{inline(m.group(2))}</h2>'
            if m
            else f"<h2>{inline(line[3:])}</h2>"
        )
        i += 1
    elif line.startswith("### "):
        close_prose(prose)
        out.append(
            f"<h3>{inline(line[4:]).replace(' ', ' &nbsp;', 1) if re.match(r'### [0-9]', line) else inline(line[4:])}</h3>"
        )
        i += 1
    elif line.startswith("#### "):
        close_prose(prose)
        out.append(f"<h4>{inline(line[5:])}</h4>")
        i += 1
    elif line.startswith("```"):
        close_prose(prose)
        i += 1
        code = []
        while i < n and not src[i].startswith("```"):
            code.append(html.escape(src[i], quote=False))
            i += 1
        i += 1
        out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
    elif line.startswith("|"):
        close_prose(prose)
        rows = []
        while i < n and src[i].startswith("|"):
            rows.append(src[i])
            i += 1
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        body = cells[2:] if len(cells) > 1 and set(cells[1][0]) <= set("-: ") else cells
        hdr = cells[0] if body is not cells else None
        out.append('<div class="tablewrap">\n<table>')
        if hdr:
            out.append(
                "  <thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in hdr) + "</tr></thead>"
            )
        out.append("  <tbody>")
        for r in body:
            tds = []
            for j, c in enumerate(r):
                cls = (
                    ' class="id"'
                    if j == 0 and re.fullmatch(r"`?[A-Z]{2,4}-?\d*`?|\d+", c.strip("*` "))
                    else ""
                )
                tds.append(f"<td{cls}>{inline(c)}</td>")
            out.append("    <tr>" + "".join(tds) + "</tr>")
        out.append("  </tbody>\n</table>\n</div>")
    elif re.match(r"^[-*] ", line):
        close_prose(prose)
        items = []
        while i < n and (
            re.match(r"^[-*] ", src[i]) or (src[i].startswith("  ") and src[i].strip() and items)
        ):
            if re.match(r"^[-*] ", src[i]):
                items.append(inline(src[i][2:]))
            else:
                items[-1] += " " + inline(src[i].strip())
            i += 1
        out.append('<div class="prose">\n<ul>')
        out.extend(f"  <li>{it}</li>" for it in items)
        out.append("</ul>\n</div>")
    elif re.match(r"^\d+\. ", line):
        close_prose(prose)
        items = []
        while i < n and (
            re.match(r"^\d+\. ", src[i]) or (src[i].startswith("   ") and src[i].strip() and items)
        ):
            if re.match(r"^\d+\. ", src[i]):
                items.append(inline(re.sub(r"^\d+\. ", "", src[i])))
            else:
                items[-1] += " " + inline(src[i].strip())
            i += 1
        out.append('<div class="prose">\n<ol>')
        out.extend(f"  <li>{it}</li>" for it in items)
        out.append("</ol>\n</div>")
    elif line.strip() == "---":
        i += 1
    elif line.strip() == "":
        i += 1
    else:
        para = []
        while (
            i < n and src[i].strip() and not re.match(r"^(#{2,4} |```|\||[-*] |\d+\. |---)", src[i])
        ):
            para.append(src[i].strip())
            i += 1
        prose.append(f"  <p>{inline(' '.join(para))}</p>")
close_prose(prose)

header = """
<div class="wrap">

<header class="prose">
  <div class="eyebrow">Low-level design · proof of concept</div>
  <h1>Product Locator LLD</h1>
  <p class="standfirst">Module layout, graph state, node contracts, algorithms and thresholds for the in-store product finder. Read after the HLD; the data formats live in the Schema document.</p>
  <div class="meta">
    <span><b>Stack</b> Python · LangGraph · Streamlit, in-process</span>
    <span><b>Nodes</b> 11, of which 3 call a model</span>
    <span><b>No HTTP layer</b> the page calls the graph directly</span>
  </div>
</header>
"""
footer = """
<footer>
  Low-level design · proof of concept · companion documents: Requirements, HLD, Schema
</footer>

</div>
"""
doc = head + "\n" + header + "\n" + "\n".join(out) + "\n" + footer
pathlib.Path("docs/pages/locator-lld.html").write_text(doc)
print(
    "sections",
    doc.count("<h2"),
    "| tables",
    doc.count("<table>"),
    doc.count("</table>"),
    "| pre",
    doc.count("<pre>"),
    doc.count("</pre>"),
    "| divs",
    doc.count("<div"),
    doc.count("</div>"),
)
