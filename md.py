# -*- coding: utf-8 -*-
"""이 블로그의 글이 실제로 쓰는 마크다운만 다루는 소형 변환기.

의존성 없음. 범용 파서가 아니다. 새 문법을 쓰기 시작하면 여기를 고친다.
원본은 semantic-alignment 리포의 scripts/artifact/md.py.

HTML 주석 중 `SOURCE:` / `VERIFY:` / `검증`으로 시작하는 것은 버리지 않고
「아직 확인 못 한 것」 상자로 본문에 올린다. 모르는 것을 적는 것이 이 블로그의 형식이다.
나머지 주석(편집 메모)은 발행본에서 버린다.
"""
import re, html

def esc(s): return html.escape(s, quote=False)

def inline(s):
    buf = []
    for part in re.split(r"(`[^`]+`)", s):
        if part.startswith("`") and part.endswith("`") and len(part) > 1:
            buf.append("<code>%s</code>" % esc(part[1:-1]))
            continue
        t = esc(part)
        t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r'<img src="\2" alt="\1" loading="lazy">', t)
        t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
        buf.append(t)
    return "".join(buf)

COMMENT = re.compile(r"<!--(.*?)-->", re.S)
FLAG = re.compile(r"^(SOURCE|VERIFY|검증)\s*:?\s*")

def extract_comments(text):
    notes = []
    def sub(m):
        body = m.group(1).strip()
        if not FLAG.match(body):
            return ""
        notes.append(FLAG.sub("", body))
        return "\n@@NOTE%d@@\n" % (len(notes) - 1)
    return COMMENT.sub(sub, text), notes

def slugify(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"\s+", "-", s)

def render(text, _notes=None):
    if _notes is None:
        text, notes = extract_comments(text)
    else:
        notes = _notes
    lines = text.split("\n")
    out, i, n = [], 0, len(lines)

    def flush_table(start):
        j = start
        rows = []
        while j < n and lines[j].strip().startswith("|"):
            rows.append(lines[j].strip()); j += 1
        if len(rows) < 2: return None, start
        cells = lambda r: [c.strip() for c in r.strip("|").split("|")]
        h = ["<div class='tw'><table><thead><tr>"]
        h += ["<th>%s</th>" % inline(c) for c in cells(rows[0])]
        h.append("</tr></thead><tbody>")
        for r in rows[2:]:
            h.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in cells(r)) + "</tr>")
        h.append("</tbody></table></div>")
        return "".join(h), j

    def list_block(start, ordered):
        j = start
        items = []   # [depth, text]
        pat = re.compile(r"^(\s*)(?:[-*]|\d+\.)\s+(.*)$")
        while j < n:
            m = pat.match(lines[j])
            if m:
                items.append([len(m.group(1)) // 2, m.group(2)]); j += 1
            elif lines[j].strip() and lines[j].startswith(("   ", "\t")) and items:
                items[-1][1] += " " + lines[j].strip(); j += 1
            elif not lines[j].strip() and j + 1 < n and pat.match(lines[j + 1]):
                j += 1
            else:
                break
        def build(idx, depth):
            tag = "ol" if (ordered and depth == 0) else "ul"
            h = ["<%s>" % tag]
            while idx < len(items) and items[idx][0] >= depth:
                if items[idx][0] > depth:
                    sub, idx = build(idx, depth + 1)
                    h.append(sub); continue
                h.append("<li>%s" % inline(items[idx][1]))
                idx += 1
                if idx < len(items) and items[idx][0] > depth:
                    sub, idx = build(idx, depth + 1)
                    h.append(sub)
                h.append("</li>")
            h.append("</%s>" % tag)
            return "".join(h), idx
        return build(0, 0)[0], j

    while i < n:
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1; continue
        m = re.match(r"^@@NOTE(\d+)@@$", s)
        if m:
            body = inline(notes[int(m.group(1))]).replace("\n", "<br>")
            out.append("<aside class='unverified'><span class='eyebrow'>아직 확인 못 한 것</span>%s</aside>" % body)
            i += 1; continue
        if s.startswith("```"):
            lang = s[3:].strip()
            j = i + 1; code = []
            while j < n and not lines[j].strip().startswith("```"):
                code.append(lines[j]); j += 1
            cls = " class='language-%s'" % esc(lang) if lang else ""
            out.append("<pre><code%s>%s</code></pre>" % (cls, esc("\n".join(code))))
            i = j + 1; continue
        if re.match(r"^(-{3,}|\*{3,})$", s):
            out.append("<hr>"); i += 1; continue
        hm = re.match(r"^(#{1,6})\s+(.*)$", s)
        if hm:
            lvl = min(len(hm.group(1)) + 1, 6)   # h1은 글 제목 몫
            body = inline(hm.group(2))
            out.append("<h%d id='%s'>%s</h%d>" % (lvl, slugify(body), body, lvl))
            i += 1; continue
        if s.startswith("|"):
            t, j = flush_table(i)
            if t: out.append(t); i = j; continue
        if s.startswith(">"):
            j = i; q = []
            while j < n and lines[j].strip().startswith(">"):
                q.append(re.sub(r"^\s*>\s?", "", lines[j])); j += 1
            out.append("<blockquote>%s</blockquote>" % render("\n".join(q), notes))
            i = j; continue
        lm = re.match(r"^(\s*)(?:([-*])|(\d+)\.)\s+", ln)
        if lm:
            t, j = list_block(i, ordered=bool(lm.group(3)))
            out.append(t); i = j; continue
        j = i; para = []
        while j < n and lines[j].strip() and not re.match(r"^\s*(#{1,6}\s|[-*]\s|\d+\.\s|>|\||```|@@NOTE|-{3,}$)", lines[j]):
            para.append(lines[j].strip()); j += 1
        if para:
            out.append("<p>%s</p>" % inline(" ".join(para)))
            i = j
        else:
            i += 1
    return "".join(out)
