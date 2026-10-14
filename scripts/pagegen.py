"""Render a design document's markdown into its published page (docs/pages/*.html).

The markdown is the source of truth; the pages are generated so they cannot drift from it
(CLAUDE.md, "Published pages"). Each page keeps its own <head> and styles — everything before
``<div class="wrap">`` in the current file — and gets a header written by its script. Hand-drawn
figures live in docs/pages/figures/ and are placed by section: either instead of the section's
first code block (the ASCII sketch they draw properly) or at the end of the section.
"""

import html
import pathlib
import re

FIGURES = pathlib.Path("docs/pages/figures")


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def _close_prose(out, buf):
    if buf:
        out.append('<div class="prose">')
        out.extend(buf)
        out.append("</div>")
        buf.clear()


def body(md: str, figures: dict[str, tuple[str, str]] | None = None) -> str:
    """``figures``: section heading line → (figure file stem, "replace" or "end")."""
    src = md.split("\n")
    figures = dict(figures or {})
    out, i, n = [], 0, len(src)
    while i < n and not src[i].startswith("## "):  # the page carries its own title block
        i += 1
    pending: list[str] = []  # figures waiting for the end of their section

    def figure(stem):
        return (FIGURES / f"{stem}.html").read_text().rstrip("\n")

    prose = []
    section = None
    while i < n:
        line = src[i]
        if re.match(r"^#{2,3} ", line):
            _close_prose(out, prose)
            out.extend(pending)
            pending.clear()
            section = line
            if figures.get(section, ("", ""))[1] == "end":
                pending.append(figure(figures.pop(section)[0]))
        if line.startswith("## "):
            _close_prose(out, prose)
            m = re.match(r"## (\d+)\.\s+(.*)", line)
            out.append(
                f'<h2><span class="sec">{m.group(1)}</span> &nbsp;{inline(m.group(2))}</h2>'
                if m
                else f"<h2>{inline(line[3:])}</h2>"
            )
            i += 1
        elif line.startswith("### "):
            _close_prose(out, prose)
            out.append(
                f"<h3>{inline(line[4:]).replace(' ', ' &nbsp;', 1) if re.match(r'### [0-9]', line) else inline(line[4:])}</h3>"
            )
            i += 1
        elif line.startswith("#### "):
            _close_prose(out, prose)
            out.append(f"<h4>{inline(line[5:])}</h4>")
            i += 1
        elif line.startswith("```"):
            _close_prose(out, prose)
            i += 1
            code = []
            while i < n and not src[i].startswith("```"):
                code.append(html.escape(src[i], quote=False))
                i += 1
            i += 1
            if figures.get(section, ("", ""))[1] == "replace":
                out.append(figure(figures.pop(section)[0]))  # the drawing, not its ASCII sketch
            else:
                out.append("<pre><code>" + "\n".join(code) + "</code></pre>")
        elif line.startswith("|"):
            _close_prose(out, prose)
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
                    "  <thead><tr>"
                    + "".join(f"<th>{inline(c)}</th>" for c in hdr)
                    + "</tr></thead>"
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
            _close_prose(out, prose)
            items = []
            while i < n and (
                re.match(r"^[-*] ", src[i])
                or (src[i].startswith("  ") and src[i].strip() and items)
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
            _close_prose(out, prose)
            items = []
            while i < n and (
                re.match(r"^\d+\. ", src[i])
                or (src[i].startswith("   ") and src[i].strip() and items)
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
                i < n
                and src[i].strip()
                and not re.match(r"^(#{2,4} |```|\||[-*] |\d+\. |---)", src[i])
            ):
                para.append(src[i].strip())
                i += 1
            prose.append(f"  <p>{inline(' '.join(para))}</p>")
    _close_prose(out, prose)
    out.extend(pending)
    assert not figures, f"figures with no section to go in: {figures}"
    return "\n".join(out)


def write(page: str, md: str, header: str, footer: str, figures=None) -> None:
    path = pathlib.Path(page)
    head = path.read_text().split('<div class="wrap">')[0].rstrip("\n")
    doc = (head + '\n\n<div class="wrap">\n' + header + "\n" + body(md, figures) + "\n"
           + footer + "\n</div>\n")  # fmt: skip
    path.write_text(doc)
    print(path.name, "| sections", doc.count("<h2"), "| tables", doc.count("<table>"),
          doc.count("</table>"), "| figures", doc.count("<figure>"), "| divs", doc.count("<div"),
          doc.count("</div>"))  # fmt: skip
