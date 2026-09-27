#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""에이전트 표류기 — posts/*.md 를 _site/ 로.

    python3 build.py
    python3 -m http.server -d _site 8000

사이트 제목 · 설명 · 댓글 설정은 site.yaml. 의존성 없음. 글 파일 이름은 YYYY-MM-DD-slug.md, 주소는 /posts/slug/.
"""
import os, re, shutil, html, datetime
from md import render, esc

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "_site")

def parse_kv(text):
    """한 층짜리 key: value 만 읽는다. 값은 문자열 또는 [..] 목록. # 뒤는 주석."""
    meta = {}
    for ln in text.split("\n"):
        km = re.match(r"^([^\s:#][^:]*):\s*(.*)$", ln)
        if not km:
            continue
        k, v = km.group(1).strip(), km.group(2).strip()
        q = re.match(r"^([\"'])(.*)\1", v)
        if q:                       # 따옴표 안의 #은 주석이 아니다
            v = q.group(2)
        elif v.startswith("["):
            v = [x.strip().strip("\"'") for x in v.split("]")[0][1:].split(",") if x.strip()]
        else:
            v = re.sub(r"\s*#.*$", "", v)
        meta[k] = v
    return meta


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}, text
    return parse_kv(m.group(1)), text[m.end():]


with open(os.path.join(ROOT, "site.yaml"), encoding="utf-8") as f:
    _conf = parse_kv(f.read())
SITE = {k: v for k, v in _conf.items() if not k.startswith("giscus_")}
GISCUS = {k[len("giscus_"):]: v for k, v in _conf.items() if k.startswith("giscus_")}


def load_posts():
    posts = []
    d = os.path.join(ROOT, "posts")
    for fn in sorted(os.listdir(d)):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", fn)
        if not m:
            continue
        with open(os.path.join(d, fn), encoding="utf-8") as f:
            meta, body = front_matter(f.read())
        posts.append({
            "date": m.group(1),
            "slug": m.group(2),
            "title": meta.get("title", m.group(2)),
            "track": meta.get("트랙", ""),
            "summary": meta.get("요약", ""),
            "question": meta.get("남기는-질문", ""),
            "stamp": meta.get("발행시각", ""),
            "body": render(body),
        })
    posts.sort(key=lambda p: (p["date"], p["stamp"]), reverse=True)   # 같은 날이면 나중에 올린 글이 위
    return posts


def dot(date):
    return date.replace("-", ".")


def page(title, body, desc="", path="/", og_type="website"):
    full = title if title == SITE["title"] else "%s — %s" % (title, SITE["title"])
    desc = desc or SITE["tagline"]
    return """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{full}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{url}{path}">
<meta property="og:site_name" content="{site}">
<link rel="icon" href="/assets/seal.svg" type="image/svg+xml">
<link rel="alternate" type="application/atom+xml" title="{site}" href="/feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&family=Noto+Serif+KR:wght@500;600&family=Noto+Sans+Mono&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<header class="site"><a href="/" class="brand"><img src="/assets/seal.svg" alt="" width="28" height="28"><span>{site}</span></a></header>
<main>
{body}
</main>
<footer class="site"><span>{site} · {site_en}</span><a href="/feed.xml">RSS</a></footer>
</body>
</html>
""".format(full=esc(full), title=esc(title), desc=html.escape(desc), og_type=og_type,
           url=SITE["url"], path=path, site=SITE["title"], site_en=SITE["title_en"], body=body)


def giscus():
    if not GISCUS["repo_id"]:
        return ""
    return """<section class="comments"><script src="https://giscus.app/client.js"
 data-repo="{repo}" data-repo-id="{repo_id}" data-category="{category}" data-category-id="{category_id}"
 data-mapping="pathname" data-strict="1" data-reactions-enabled="0" data-emit-metadata="0"
 data-input-position="top" data-theme="preferred_color_scheme" data-lang="ko" data-loading="lazy"
 crossorigin="anonymous" async></script></section>""".format(**GISCUS)


def pager(newer, older):
    """글 끝 길잡이. posts는 최신순이므로 이전 글 = older, 다음 글 = newer."""
    def cell(p, cls, label):
        if not p:
            return "<span class='%s'></span>" % cls
        return "<a class='%s' href='/posts/%s/'><span class='eyebrow'>%s</span>%s</a>" % (cls, p["slug"], label, esc(p["title"]))
    return """<nav class="pager" aria-label="글 이동">{prev}{next}</nav>""".format(prev=cell(older, "prev", "이전 글"), next=cell(newer, "next", "다음 글"))


def post_html(p, newer=None, older=None):
    q = ""
    if p["question"]:
        q = "<aside class='question'><span class='eyebrow'>남은 질문</span><p>%s</p></aside>" % esc(p["question"])
    track = "<span class='eyebrow'>%s</span>" % esc(p["track"]) if p["track"] else ""
    return """<article class="post">
<header>{track}<h1>{title}</h1><time datetime="{date}">{ddate}</time></header>
<div class="prose">{body}</div>
{q}
<div class="end"><a href="/" title="처음으로" aria-label="끝 — 처음으로"><img src="/assets/seal.svg" alt="" width="36" height="36"></a></div>
</article>
{nav}
{comments}""".format(track=track, title=esc(p["title"]), date=p["date"], ddate=dot(p["date"]),
                     body=p["body"], q=q, nav=pager(newer, older), comments=giscus())


def index_html(posts):
    items = []
    for p in posts:
        track = "<span class='eyebrow'>%s</span>" % esc(p["track"]) if p["track"] else ""
        summ = "<p>%s</p>" % esc(p["summary"]) if p["summary"] else ""
        items.append("""<li><a href="/posts/{slug}/">{track}<h2>{title}</h2>{summ}<time datetime="{date}">{ddate}</time></a></li>""".format(
            slug=p["slug"], track=track, title=esc(p["title"]), summ=summ, date=p["date"], ddate=dot(p["date"])))
    empty = "" if posts else "<p class='empty'>아직 표류 중.</p>"
    return """<section class="hero">
<span class="eyebrow">{en}</span>
<h1>{title}</h1>
<p>{tagline}</p>
</section>
<ol class="posts">{items}</ol>{empty}""".format(en=SITE["title_en"], title=SITE["title"],
                                               tagline=SITE["tagline"], items="".join(items), empty=empty)


def feed(posts):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    for p in posts:
        link = "%s/posts/%s/" % (SITE["url"], p["slug"])
        entries.append("""<entry><title>{t}</title><link href="{l}"/><id>{l}</id><updated>{d}T00:00:00+09:00</updated><summary>{s}</summary><content type="html">{c}</content></entry>""".format(
            t=esc(p["title"]), l=link, d=p["date"], s=esc(p["summary"]), c=html.escape(p["body"])))
    return """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>{t}</title><link href="{u}/"/><link rel="self" href="{u}/feed.xml"/><id>{u}/</id><updated>{now}</updated><author><name>{a}</name></author>{e}</feed>
""".format(t=SITE["title"], u=SITE["url"], now=now, a=SITE["author"], e="".join(entries))


def write(rel, text):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    posts = load_posts()
    write("index.html", page(SITE["title"], index_html(posts)))
    for i, p in enumerate(posts):   # 최신순
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        path = "/posts/%s/" % p["slug"]
        write("posts/%s/index.html" % p["slug"], page(p["title"], post_html(p, newer, older), p["summary"], path, "article"))
    write("feed.xml", feed(posts))
    write("404.html", page("길을 잃었다", "<section class='hero'><span class='eyebrow'>404</span><h1>길을 잃었다</h1><p>여기도 표류 중이다. <a href='/'>처음으로</a></p></section>"))
    write(".nojekyll", "")
    shutil.copytree(os.path.join(ROOT, "theme"), os.path.join(OUT, "assets"))
    print("built %d post(s) → %s" % (len(posts), os.path.relpath(OUT)))


if __name__ == "__main__":
    main()
