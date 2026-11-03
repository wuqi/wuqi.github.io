#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export a Typecho SQLite database into a Hugo content tree."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import re
import shutil
import sqlite3
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

TZ = timezone(timedelta(hours=8))

DEFAULT_DB = r"E:\typcho2.tar\domains\diphda.info\public_html\usr\5312b1ffc6830.db"
DEFAULT_UPLOADS = r"E:\typcho2.tar\domains\diphda.info\public_html\usr\uploads"
DEFAULT_THEME = r"E:\typcho2.tar\domains\diphda.info\public_html\usr\themes\jianshu"
DEFAULT_PROJECT = r"E:\diphda-blog"


def yaml_str(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_list(values) -> str:
    return "[" + ", ".join(yaml_str(str(v)) for v in values) + "]"


def ts(value: int) -> datetime:
    return datetime.fromtimestamp(int(value), TZ)


def iso(value: int) -> str:
    return ts(value).isoformat()


def rewrite_links(text: str) -> str:
    text = re.sub(r"https?://(?:www\.)?diphda\.info", "", text)
    text = text.replace("/index.php/archives/", "/archives/")
    text = text.replace("/index.php/category/", "/category/")
    text = text.replace("/index.php/tag/", "/tag/")
    text = text.replace("/index.php/author/", "/author/")
    text = text.replace("/index.php/attachment/", "/attachment/")
    text = text.replace("/index.php/feed/", "/feed/")
    text = text.replace("/index.php/", "/")
    return text


def plain_text(markdown_text: str) -> str:
    s = re.sub(r"```.*?```", "", markdown_text, flags=re.S)
    s = re.sub(r"~~~.*?~~~", "", s, flags=re.S)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"^\s{0,3}[#>\-+*]+\s*", "", s, flags=re.M)
    s = re.sub(r"[`*_~]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def make_excerpt(markdown_text: str) -> str:
    excerpt = markdown_text.split("<!--more-->")[0]
    text = plain_text(excerpt) or plain_text(markdown_text)
    if len(text) > 100:
        return text[:100] + "..."
    return text


def first_image(markdown_text: str) -> str:
    m = re.search(r"!\[[^\]]*\]\(\s*([^)\s]+)", markdown_text)
    if not m:
        m = re.search(r"<img[^>]+src=[\"']([^\"']+)", markdown_text, re.I)
    if not m:
        return ""
    url = rewrite_links(m.group(1))
    return url.split("?")[0]


def ordinal(n: int) -> str:
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def comment_date(value: int) -> str:
    dt = ts(value)
    return f"{dt:%B} {dt.day}{ordinal(dt.day)}, {dt:%Y} at {dt:%I:%M %p}".replace(
        "AM", "am"
    ).replace("PM", "pm")


def comment_paragraphs(text: str) -> str:
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not parts:
        return ""
    return "".join("<p>%s</p>" % escape(p).replace("\n", "<br>") for p in parts)


def gravatar(mail: str) -> str:
    digest = hashlib.md5((mail or "").strip().lower().encode("utf-8")).hexdigest()
    return f"https://cravatar.cn/avatar/{digest}?s=32&r=X"


def render_comment(comment, children_by_parent) -> str:
    coid = comment["coid"]
    author = escape(comment["author"] or "匿名")
    cite = author
    if comment["url"]:
        cite = '<a href="%s" rel="external nofollow">%s</a>' % (
            escape(comment["url"]),
            author,
        )
    avatar = gravatar(comment["mail"])
    content = comment_paragraphs(comment["text"])
    child_html = ""
    children = children_by_parent.get(coid) or []
    if children:
        child_html = (
            '<div class="comment-children" itemprop="discusses"><ol class="comment-list">'
            + "".join(render_comment(c, children_by_parent) for c in children)
            + "</ol></div>"
        )
    level_class = "comment-child" if comment["parent"] else "comment-parent"
    return (
        '<li itemscope itemtype="http://schema.org/UserComments" id="comment-%s" '
        'class="comment-body %s">'
        '<div class="comment-meta">'
        '<div class="comment-meta-author" itemprop="creator" itemscope '
        'itemtype="http://schema.org/Person">'
        '<span itemprop="image"><img class="avatar" loading="lazy" src="%s" '
        'alt="%s" width="32" height="32" onerror="this.src=\'/img/avatar.png\'" /></span>'
        '<cite class="fn" itemprop="name">%s</cite></div>'
        '<div class="comment-meta-time"><a href="#comment-%s">'
        '<time itemprop="commentTime" datetime="%s">%s</time></a></div>'
        "</div>"
        '<div class="comment-content" itemprop="commentText">%s</div>'
        "%s</li>"
    ) % (
        coid,
        level_class,
        avatar,
        author,
        cite,
        coid,
        iso(comment["created"]),
        comment_date(comment["created"]),
        content,
        child_html,
    )


def build_comments(rows):
    comments = []
    for row in rows:
        comments.append(
            {
                "coid": row["coid"],
                "cid": row["cid"],
                "author": row["author"],
                "mail": row["mail"],
                "url": row["url"],
                "created": row["created"],
                "text": row["text"],
                "parent": row["parent"] or 0,
                "status": row["status"],
            }
        )
    by_cid = {}
    for c in comments:
        by_cid.setdefault(c["cid"], []).append(c)
    result = {}
    for cid, items in by_cid.items():
        children_by_parent = {}
        roots = []
        for item in items:
            if item["parent"]:
                children_by_parent.setdefault(item["parent"], []).append(item)
            else:
                roots.append(item)
        html = (
            '<ol class="comment-list">'
            + "".join(render_comment(c, children_by_parent) for c in roots)
            + "</ol>"
        )
        result[str(cid)] = {"count": len(items), "html": html}
    return result


def write_redirect(project: Path, path: str, target: str) -> None:
    out = project / "static" / path.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    target_html = escape(target)
    out.write_text(
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        f"<title>Redirecting to {target_html}</title>\n"
        f"<link rel=\"canonical\" href=\"{target_html}\">\n"
        f"<meta http-equiv=\"refresh\" content=\"0; url={target_html}\">\n"
        f"<script>location.replace({json.dumps(target)});</script>\n"
        "</head>\n<body>\n"
        f"<p>正在跳转到 <a href=\"{target_html}\">{target_html}</a>…</p>\n"
        "</body>\n</html>\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--uploads", default=DEFAULT_UPLOADS)
    parser.add_argument("--theme-src", default=DEFAULT_THEME)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    args = parser.parse_args()

    project = Path(args.project)
    content = project / "content"
    data = project / "data"
    static = project / "static"
    for p in (content, data, static):
        p.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    options = {r["name"]: r["value"] for r in cur.execute("select name,value from typecho_options")}
    site_title = options.get("title", "")
    site_desc = options.get("description", "")

    metas = {r["mid"]: r for r in cur.execute("select * from typecho_metas")}
    rels = list(cur.execute("select cid,mid from typecho_relationships"))
    rel_by_cid = {}
    for r in rels:
        rel_by_cid.setdefault(r["cid"], []).append(r["mid"])

    posts = list(
        cur.execute(
            "select * from typecho_contents where type='post' and status='publish' order by created asc"
        )
    )
    pages = list(
        cur.execute(
            "select * from typecho_contents where type='page' and status='publish' order by created asc"
        )
    )

    comments = build_comments(
        list(cur.execute("select * from typecho_comments where status='approved'"))
    )
    (data / "legacy_comments.json").write_text(
        json.dumps(comments, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Headers for the sidebar cover image
    header_files = sorted(
        p.name
        for p in Path(args.theme_src, "img").glob("header*")
        if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif")
    )
    header_list = "[" + ", ".join(yaml_str("/img/" + n) for n in header_files) + "]"
    (data / "headers.toml").write_text(
        "headers = %s\n" % header_list, encoding="utf-8"
    )

    # Copy uploads
    dest_uploads = static / "usr" / "uploads"
    if dest_uploads.exists():
        shutil.rmtree(dest_uploads)
    shutil.copytree(args.uploads, dest_uploads)
    print("copied uploads ->", dest_uploads)

    posts_dir = content / "posts"
    pages_dir = content / "pages"
    if posts_dir.exists():
        shutil.rmtree(posts_dir)
    if pages_dir.exists():
        shutil.rmtree(pages_dir)
    posts_dir.mkdir(parents=True)
    pages_dir.mkdir(parents=True)

    search_entries = []
    category_counts = {}
    tag_counts = {}

    for post in posts:
        cid = post["cid"]
        raw = (post["text"] or "").replace("<!--markdown-->", "", 1)
        body = rewrite_links(raw)
        mids = rel_by_cid.get(cid, [])
        cats = [metas[m]["slug"] for m in mids if metas[m]["type"] == "category"]
        tags = [metas[m]["slug"] for m in mids if metas[m]["type"] == "tag"]
        if not cats:
            cats = ["default"]
        for c in cats:
            category_counts[c] = category_counts.get(c, 0) + 1
        for t in tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1

        title = post["title"] or "(无标题)"
        url = f"/archives/{cid}/"
        aliases = [f"/index.php/archives/{cid}/"]
        fm = [
            "---",
            f"title: {yaml_str(title)}",
            f"date: {iso(post['created'])}",
            f"lastmod: {iso(post['modified'] or post['created'])}",
            f"url: {yaml_str(url)}",
            f"slug: {yaml_str(str(post['slug'] or cid))}",
            f"cid: {cid}",
            f"author: {yaml_str('wuqi')}",
            f"views: {int(post['views'] or 0)}",
            f"comments_count: {int(post['commentsNum'] or 0)}",
            f"excerpt: {yaml_str(make_excerpt(raw))}",
            f"thumb: {yaml_str(first_image(raw))}",
            f"categories: {yaml_list(cats)}",
            f"tags: {yaml_list(tags)}",
            f"aliases: {yaml_list(aliases)}",
            "---",
            "",
            body.strip(),
            "",
        ]
        (posts_dir / f"{cid}.md").write_text("\n".join(fm), encoding="utf-8")

        search_entries.append(
            {
                "title": title,
                "url": url,
                "date": iso(post["created"])[:10],
                "categories": [metas[m]["name"] for m in mids if metas[m]["type"] == "category"],
                "tags": [metas[m]["name"] for m in mids if metas[m]["type"] == "tag"],
                "text": plain_text(raw),
            }
        )

    for page in pages:
        raw = (page["text"] or "").replace("<!--markdown-->", "", 1)
        body = rewrite_links(raw)
        slug = page["slug"] or str(page["cid"])
        title = page["title"] or "(无标题)"
        url = f"/{slug}.html"
        aliases = [f"/index.php/{slug}.html"]
        fm = [
            "---",
            f"title: {yaml_str(title)}",
            f"date: {iso(page['created'])}",
            f"lastmod: {iso(page['modified'] or page['created'])}",
            f"url: {yaml_str(url)}",
            f"slug: {yaml_str(slug)}",
            f"cid: {page['cid']}",
            f"aliases: {yaml_list(aliases)}",
            "---",
            "",
            body.strip(),
            "",
        ]
        (pages_dir / f"{slug}.md").write_text("\n".join(fm), encoding="utf-8")

    search_entries.sort(key=lambda x: x["date"], reverse=True)
    (static / "search-index.json").write_text(
        json.dumps(search_entries, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print("wrote", len(posts), "posts,", len(pages), "pages")

    # Taxonomy term pages (term key = old slug so URLs are preserved)
    for taxonomy, plural in (("category", "categories"), ("tag", "tags")):
        base = content / plural
        if base.exists():
            shutil.rmtree(base)
        for mid, meta in metas.items():
            if meta["type"] != taxonomy:
                continue
            slug = meta["slug"]
            term_dir = base / slug
            term_dir.mkdir(parents=True, exist_ok=True)
            fm = [
                "---",
                f"title: {yaml_str(meta['name'])}",
                f"slug: {yaml_str(slug)}",
                f"url: {yaml_str(f'/{taxonomy}/{slug}/')}",
                f"aliases: {yaml_list([f'/index.php/{taxonomy}/{slug}/'])}",
                "---",
                "",
            ]
            (term_dir / "_index.md").write_text("\n".join(fm), encoding="utf-8")

    # Home page front matter
    (content / "_index.md").write_text(
        "\n".join(
            [
                "---",
                f"title: {yaml_str(site_title)}",
                f"description: {yaml_str(site_desc)}",
                'aliases: ["/index.php/"]',
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Search page
    search_dir = content / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    (search_dir / "_index.md").write_text(
        "\n".join(
            [
                "---",
                'title: "搜索"',
                'layout: "search"',
                'url: "/search/"',
                "---",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Static redirects for old pagination/feed/author URLs
    total_pages = math.ceil(len(posts) / 5)
    write_redirect(project, "/feed", "/index.xml")
    write_redirect(project, "/index.php/feed", "/index.xml")
    write_redirect(project, "/index.php/feed/rss", "/index.xml")
    write_redirect(project, "/index.php/feed/atom", "/index.xml")
    write_redirect(project, "/author/1", "/")
    write_redirect(project, "/index.php/author/1", "/")
    write_redirect(project, "/index.php/page/1", "/")
    write_redirect(project, "/index.php/author/1/1", "/")
    for n in range(2, total_pages + 1):
        write_redirect(project, f"/index.php/page/{n}", f"/page/{n}/")
        write_redirect(project, f"/index.php/author/1/{n}", f"/page/{n}/")
    for slug, count in category_counts.items():
        write_redirect(project, f"/index.php/category/{slug}/1", f"/category/{slug}/")
        for n in range(2, math.ceil(count / 5) + 1):
            write_redirect(
                project, f"/index.php/category/{slug}/{n}", f"/category/{slug}/page/{n}/"
            )
    for slug, count in tag_counts.items():
        write_redirect(project, f"/index.php/tag/{slug}/1", f"/tag/{slug}/")
        for n in range(2, math.ceil(count / 5) + 1):
            write_redirect(project, f"/index.php/tag/{slug}/{n}", f"/tag/{slug}/page/{n}/")
    for cid in comments.keys():
        write_redirect(
            project, f"/index.php/archives/{cid}/comment-page-1", f"/archives/{cid}/#comments"
        )

    # CNAME and nojekyll
    (static / "CNAME").write_text("diphda.info\n", encoding="utf-8")
    (static / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
