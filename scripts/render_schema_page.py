import html
import pathlib
import re

# reuse the LLD renderer's logic by importing it as a module would be fiddly; inline it
src = pathlib.Path("docs/schema.md").read_text().split("\n")
head = "\n".join(pathlib.Path("docs/pages/locator-lld.html").read_text().split("\n")[0:61])
head = head.replace("<title>Product Locator LLD</title>", "<title>Product Locator Schema</title>")


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


out, i, n = [], 0, len(src)
while i < n and not src[i].startswith("## "):
    i += 1
prose = []


def close_prose():
    if prose:
        out.append('<div class="prose">')
        out.extend(prose)
        out.append("</div>")
        prose.clear()


while i < n:
    line = src[i]
    if line.startswith("## "):
        close_prose()
        m = re.match(r"## (\d+)\.\s+(.*)", line)
        out.append(
            f'<h2><span class="sec">{m.group(1)}</span> &nbsp;{inline(m.group(2))}</h2>'
            if m
            else f"<h2>{inline(line[3:])}</h2>"
        )
        i += 1
    elif line.startswith("### "):
        close_prose()
        txt = inline(line[4:])
        if re.match(r"### [0-9]", line):
            txt = txt.replace(" ", " &nbsp;", 1)
        out.append(f"<h3>{txt}</h3>")
        i += 1
    elif line.startswith("#### "):
        close_prose()
        out.append(f"<h4>{inline(line[5:])}</h4>")
        i += 1
    elif line.startswith("```"):
        close_prose()
        i += 1
        code = []
        while i < n and not src[i].startswith("```"):
            code.append(html.escape(src[i], quote=False))
            i += 1
        i += 1
        out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
    elif line.startswith("|"):
        close_prose()
        rows = []
        while i < n and src[i].startswith("|"):
            rows.append(src[i])
            i += 1
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        has_hdr = len(cells) > 1 and set("".join(cells[1])) <= set("-: ")
        hdr = cells[0] if has_hdr else None
        body = cells[2:] if has_hdr else cells
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
                    ' class="m"'
                    if j == 0 and re.fullmatch(r"`?[A-Z]-?\d+`?|V-\d+|\d+", c.strip("*`| "))
                    else ""
                )
                tds.append(f"<td{cls}>{inline(c)}</td>")
            out.append("    <tr>" + "".join(tds) + "</tr>")
        out.append("  </tbody>\n</table>\n</div>")
    elif re.match(r"^[-*] ", line):
        close_prose()
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
        out.extend(f"  <li>{x}</li>" for x in items)
        out.append("</ul>\n</div>")
    elif re.match(r"^\d+\. ", line):
        close_prose()
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
        out.extend(f"  <li>{x}</li>" for x in items)
        out.append("</ol>\n</div>")
    elif line.startswith("> "):
        close_prose()
        q = []
        while i < n and src[i].startswith(">"):
            q.append(inline(src[i].lstrip(">").strip()))
            i += 1
        out.append('<div class="callout">\n  <p>' + " ".join(q) + "</p>\n</div>")
    elif line.strip() in ("---", ""):
        i += 1
    else:
        para = []
        while (
            i < n
            and src[i].strip()
            and not re.match(r"^(#{2,4} |```|\||[-*] |\d+\. |---|> )", src[i])
        ):
            para.append(src[i].strip())
            i += 1
        prose.append(f"  <p>{inline(' '.join(para))}</p>")
close_prose()

header = """
<div class="wrap">

<header class="prose">
  <div class="eyebrow">Data schema · proof of concept</div>
  <h1>Product Locator Schema</h1>
  <p class="standfirst">The six CSV files that describe one store: columns, types, identifier scheme, referential rules and the forty-seven checks that run before the first search. This is the contract for onboarding a store.</p>
  <div class="meta">
    <span><b>Files</b> six CSVs, one folder per store</span>
    <span><b>Demo store</b> 314 nodes · 352 edge rows · 3 floors</span>
    <span><b>Validation</b> 43 refusals and 5 warnings, checked at load</span>
  </div>
</header>
"""
footer = """
<footer>
  Data schema · proof of concept · companion documents: Requirements, HLD, LLD
</footer>

</div>
"""
doc = head + "\n" + header + "\n" + "\n".join(out) + "\n" + footer
previous = pathlib.Path("docs/pages/locator-schema.html").read_text()
if "<figure>" in previous and "<figure>" not in doc:  # keep the hand-drawn rack figure
    s = previous.index("<figure>")
    e = previous.index("</figure>", s) + len("</figure>")
    tail = previous[max(0, s - 400) : s]
    anchor = next(tail[-k:] for k in range(len(tail), 20, -1) if doc.count(tail[-k:]) == 1)
    at = doc.index(anchor) + len(anchor)
    doc = doc[:at] + previous[s:e] + "\n\n" + doc[at:].lstrip("\n")
pathlib.Path("docs/pages/locator-schema.html").write_text(doc)
print(
    "h2",
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
