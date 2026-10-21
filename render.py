"""Server-side rendering for the knowledge site.

build.py loads the topics; this module turns them into page markup. It is the
only place that writes the reading views (home, part pages, day-session index,
chapters), so the single-file build and the one-page-per-chapter build show
the same thing. The page's script keeps the parts that need a browser: the
sidebar, the on-this-page outline, search, diagrams and copy buttons.
"""

import html
import json
import re

SITE = "The iOS Interview Field Guide"
SHORT = "Field Guide"
SEO_SUFFIX = "iOS Interview Field Guide"
SITE_ROOT = "https://reza-bina.com/"
PUBLIC_BASE = "https://reza-bina.com/notes/"
OG_IMAGE = "https://reza-bina.com/og/notes.png"
PERSON_ID = SITE_ROOT + "#person"
WEBSITE_ID = SITE_ROOT + "#website"
HOME_DESCRIPTION = (
    "Every round of a senior iOS interview loop, worked through from the interviewer's side: "
    "live coding, code review, mobile system design, algorithms, Swift concurrency and ARC. Free to read."
)

NUMBERED = re.compile(r"^(\d+) · (.*)$")
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


# ------------------------------------------------------------------ helpers

def esc(value):
    return html.escape(str(value), quote=True)


def pad(n):
    return "%02d" % n


def split_title(c):
    m = NUMBERED.match(c["title"])
    return (m.group(1), m.group(2)) if m else ("", c["title"])


def is_method(n):
    """'00 · How the round works' is the method, not a problem."""
    return bool(re.fullmatch(r"0+", n))


def groups_of(t):
    groups, by = [], {}
    for i, c in enumerate(t["chapters"]):
        g = c.get("group")
        if not g:
            continue
        if g not in by:
            by[g] = {"name": g, "items": []}
            groups.append(by[g])
        by[g]["items"].append((c, i))
    return groups or None


def problem_count(group):
    return sum(1 for c, _ in group["items"] if split_title(c)[0] and not is_method(split_title(c)[0]))


def topic_count(t):
    gs = groups_of(t)
    return sum(problem_count(g) for g in gs) if gs else len(t["chapters"])


def count_label(t):
    if groups_of(t):
        return "%d %s" % (topic_count(t), t.get("unit") or "problems")
    return "%d %s" % (len(t["chapters"]), t.get("unit") or "chapters")


def parts(topics):
    """Parts are the reference topics in order; the private day sessions are not a part."""
    return [t for t in topics if t.get("kind") != "sessions"]


def part_of(topics, t):
    ps = parts(topics)
    return "Part " + ROMAN[ps.index(t) + 1] if t in ps else ""


def ch_num(t, c, i):
    """A chapter's number: the one in its title ('03 · Chat client'), else its position."""
    n, title = split_title(c)
    if n:
        return n, title
    numbered = any(split_title(x)[0] for x in t["chapters"])
    return ("·" if numbered else pad(i + 1)), c["title"]


def chapter_of(t, c, idx):
    """'Chapter 02 of 16' uses the number in the title when the topic numbers its titles."""
    numbered = [x for x in t["chapters"] if split_title(x)[0] and not is_method(split_title(x)[0])]
    if not numbered:
        return "Chapter %s of %s" % (pad(idx + 1), pad(len(t["chapters"])))
    n = split_title(c)[0]
    return "Chapter %s of %s" % (n, pad(len(numbered))) if n and not is_method(n) else "Start here"


def minutes(value):
    return "%s min" % value if str(value).strip() else ""


class Links:
    """Hash routes in the single-file build, real paths in the page build."""

    def __init__(self, base=None):
        self.base = base  # None: single file, hash routing

    def home(self):
        return self.base if self.base is not None else "#/"

    def topic(self, t):
        return (self.base + t["slug"] + "/") if self.base is not None else "#/" + t["slug"]

    def chapter(self, t, c):
        if self.base is not None:
            return self.base + t["slug"] + "/" + c["slug"] + "/"
        return "#/" + t["slug"] + "/" + c["slug"]


# -------------------------------------------------------------------- views

def home_view(topics, links, built):
    ps = parts(topics)
    pages = sum(len(t["chapters"]) for t in ps)
    prog = "".join(
        '<a class="fg-prog" href="%s">%s<span>%d written · %d planned</span></a>'
        % (esc(links.topic(t)), esc(t["title"]), len(t["chapters"]), t.get("total") or len(t["chapters"]))
        for t in topics if t.get("kind") == "sessions"
    )
    contents = "".join(_part_card(topics, t, links) for t in ps)
    return (
        '<header class="fg-title"><div class="fg-bar"></div>'
        "<h1>The iOS Interview<br>Field Guide</h1>"
        '<p class="fg-sub">Every round of a senior iOS loop, worked through from the interviewer’s chair.</p>'
        '<p class="fg-by">Reza Bina · Berlin · %d pages, free to read</p>%s</header>'
        '<section class="fg-contents"><h2>Contents</h2><div class="fg-parts">%s</div></section>'
        '<footer class="fg-foot">Every claim about how something works carries its source, linked where it is used.'
        '<span class="meta">Updated %s · <a href="https://reza-bina.com">reza-bina.com</a></span></footer>'
        % (pages, prog, contents, esc(built))
    )


def _part_card(topics, t, links):
    gs = groups_of(t)
    if gs and len(gs) >= 4:
        rows = []
        for i, g in enumerate(gs[:4]):
            n = problem_count(g)
            rows.append(
                '<li><a href="%s"><span class="n">%s</span><span class="t">%s</span><span class="lead"></span>'
                '<span class="m">%s</span></a></li>'
                % (esc(links.chapter(t, g["items"][0][0])), pad(i + 1), esc(g["name"]),
                   ("%d %s" % (n, "problem" if n == 1 else "problems")) if n else "start")
            )
    else:
        rows = []
        for i, c in enumerate(t["chapters"][:4]):
            n, title = ch_num(t, c, i)
            rows.append(
                '<li><a href="%s"><span class="n">%s</span><span class="t">%s</span><span class="lead"></span>'
                '<span class="m">%s</span></a></li>'
                % (esc(links.chapter(t, c)), esc(n), esc(title), esc(minutes(c.get("minutes", ""))))
            )
    return (
        '<section class="fg-part"><a class="fg-ph" href="%s"><span class="fg-pn">%s</span>'
        '<span class="fg-pt">%s</span><span class="fg-pc">%s</span></a>'
        '<p class="fg-tag">%s</p><ol class="fg-toc">%s</ol>'
        '<a class="fg-all" href="%s">All %s →</a></section>'
        % (esc(links.topic(t)), part_of(topics, t), esc(t["title"]), count_label(t),
           esc(t.get("tagline", "")), "".join(rows), esc(links.topic(t)), count_label(t))
    )


def _chapter_row(t, c, i, links, number=None, title=None, primer=False):
    n, plain = (number, title) if number is not None else ch_num(t, c, i)
    return (
        '<li><a class="%s" href="%s"><span class="num">%s</span><span class="ch-t">%s</span>'
        '<span class="ch-m">%s</span><span class="ch-s">%s</span></a></li>'
        % ("primer" if primer else "", esc(links.chapter(t, c)), esc(n), esc(plain),
           esc(minutes(c.get("minutes", ""))), esc(c.get("summary", "")))
    )


def topic_view(topics, t, links):
    head = '<p class="ix-part">%s</p>' % part_of(topics, t)
    gs = groups_of(t)
    if gs:
        body = "".join(
            '<section class="ix-group"><h3>%s</h3><ul class="chapters">%s</ul></section>'
            % (esc(g["name"]), "".join(
                _chapter_row(t, c, i, links, number=split_title(c)[0], title=split_title(c)[1],
                             primer=not split_title(c)[0])
                for c, i in g["items"]))
            for g in gs
        )
        meta = "%s · %d groups" % (count_label(t), sum(1 for g in gs if problem_count(g)))
        return (head + '<div class="ix-head"><h1>%s</h1><span class="meta">%s</span></div>'
                '<p class="ix-lede">%s</p>%s' % (esc(t["title"]), meta, esc(t.get("summary", "")), body))
    rows = "".join(_chapter_row(t, c, i, links) for i, c in enumerate(t["chapters"]))
    return (head + '<div class="ix-head"><h1>%s</h1><span class="meta">%d chapters · %s min</span></div>'
            '<p class="ix-lede">%s</p><ul class="chapters">%s</ul>'
            % (esc(t["title"]), len(t["chapters"]), t.get("minutes", 0), esc(t.get("summary", "")), rows))


def session_view(t, links):
    groups, by = [], {}
    for c in t["chapters"]:
        if c["group"] not in by:
            by[c["group"]] = []
            groups.append(c["group"])
        by[c["group"]].append(
            '<a class="card" href="%s"><span class="n">DAY %s</span><b>%s</b>'
            '<span class="s">%s · reading, code, questions</span></a>'
            % (esc(links.chapter(t, c)), esc(c["day"].lstrip("0")), esc(c.get("short") or c["title"]),
               esc(minutes(c.get("minutes", ""))))
        )
    for u in t.get("upcoming", []):
        if u["group"] not in by:
            by[u["group"]] = []
            groups.append(u["group"])
        by[u["group"]].append(
            '<div class="card next"><span class="n">DAY %s</span><b>%s</b><span class="s">not written yet</span></div>'
            % (esc(u["day"]), esc(u["short"]))
        )
    done = len(t["chapters"])
    return (
        '<div class="ix-head"><h1>%s</h1><span class="meta">%d written · %d planned · %s min</span></div>'
        '<p class="ix-lede">%s</p>%s'
        % (esc(t["title"]), done, t.get("total") or done, t.get("minutes", 0), esc(t.get("summary", "")),
           "".join('<section class="build"><h3>%s</h3><div class="cards">%s</div></section>'
                   % (esc(g), "".join(by[g])) for g in groups))
    )


def chapter_view(topics, t, c, idx, links):
    chs = t["chapters"]
    prev = chs[idx - 1] if idx > 0 else None
    nxt = chs[idx + 1] if idx + 1 < len(chs) else None
    srcs = ""
    if c.get("sources"):
        srcs = '<section class="sources"><h2>Sources for this chapter</h2><div class="src">%s</div></section>' % "".join(
            '<a href="%s" target="_blank" rel="noopener"><span class="s-r">%s</span>'
            '<span class="s-l">%s<span class="s-u">%s</span></span></a>'
            % (esc(s["url"]), esc(s["ref"]), esc(s["label"]), esc(s["url"]))
            for s in c["sources"]
        )
    pager = '<nav class="pager">%s%s</nav>' % (
        ('<a href="%s"><span class="dir">Previous</span><span class="nm">%s</span></a>'
         % (esc(links.chapter(t, prev)), esc(prev["title"]))) if prev else "",
        ('<a class="next" href="%s"><span class="dir">Next</span><span class="nm">%s</span></a>'
         % (esc(links.chapter(t, nxt)), esc(nxt["title"]))) if nxt else "",
    )

    prog = ""
    if t.get("kind") == "sessions" and c.get("day") and not c["day"].startswith("S"):
        n, total = int(c["day"]), t.get("total") or len(chs)
        slice_at = size = 0
        for x in chs + t.get("upcoming", []):
            if x["group"] == c["group"]:
                size += 1
                if str(int(x["day"])) == str(n):
                    slice_at = size
        prog = ('<div class="prog"><span class="lb">%s%s</span><span class="bar"><i style="width:%d%%"></i></span>'
                '<span class="lb">Day %d of %d</span></div>'
                % (esc(c["group"]), (" · slice %d of %d" % (slice_at, size)) if slice_at else "",
                   round(n / total * 100), n, total))

    part = part_of(topics, t)
    n = split_title(c)[0]
    if c.get("group"):
        where = esc(c["group"]) + ((" · %s of %d" % (n, topic_count(t))) if n and not is_method(n) else "")
    else:
        where = chapter_of(t, c, idx)
    eyebrow = (
        '<div class="eyebrow">%s<a href="%s">%s</a><span class="dot"></span>%s<span class="dot"></span>%s</div>'
        % (('<a class="part" href="%s">%s</a><span class="dot"></span>' % (esc(links.topic(t)), part)) if part else "",
           esc(links.topic(t)), esc(t["title"]), where, esc(minutes(c.get("minutes", ""))))
    )
    return (
        "<article>%s%s<h1 class=\"title\">%s</h1><p class=\"lede\">%s</p>%s%s%s</article>"
        % (prog, eyebrow, esc(c["title"]), esc(c.get("summary", "")), c["html"], srcs, pager)
    )


# --------------------------------------------------------------- page heads

def plain_title(c):
    return split_title(c)[1]


def clip(text, limit=158):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:—-") + "…"


def _jsonld(graph):
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False)
    return '<script type="application/ld+json">%s</script>' % data.replace("</", "<\\/")


def _breadcrumbs(items):
    return {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }


PERSON = {"@type": "Person", "@id": PERSON_ID, "name": "Reza Bina", "url": SITE_ROOT}


def page_head(title, description, url, kind="website", published=None, modified=None, graph=None):
    """Title, description, canonical, Open Graph, Twitter and JSON-LD for one public page."""
    tags = [
        "<title>%s</title>" % esc(title),
        '<meta name="description" content="%s">' % esc(description),
        '<link rel="canonical" href="%s">' % esc(url),
        '<meta name="author" content="Reza Bina">',
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg">',
        '<meta property="og:type" content="%s">' % kind,
        '<meta property="og:site_name" content="%s">' % SITE,
        '<meta property="og:title" content="%s">' % esc(title),
        '<meta property="og:description" content="%s">' % esc(description),
        '<meta property="og:url" content="%s">' % esc(url),
        '<meta property="og:image" content="%s">' % OG_IMAGE,
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:locale" content="en_GB">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:title" content="%s">' % esc(title),
        '<meta name="twitter:description" content="%s">' % esc(description),
        '<meta name="twitter:image" content="%s">' % OG_IMAGE,
    ]
    if published:
        tags.append('<meta property="article:published_time" content="%s">' % published)
    if modified:
        tags.append('<meta property="article:modified_time" content="%s">' % modified)
    if graph:
        tags.append(_jsonld([PERSON] + graph))
    return "\n".join(tags)


def home_head(topics):
    graph = [{
        "@type": "CollectionPage",
        "@id": PUBLIC_BASE + "#page",
        "url": PUBLIC_BASE,
        "name": SITE,
        "description": HOME_DESCRIPTION,
        "inLanguage": "en",
        "isPartOf": {"@id": WEBSITE_ID},
        "author": {"@id": PERSON_ID},
        "publisher": {"@id": PERSON_ID},
        "hasPart": [
            {"@type": "CollectionPage", "@id": PUBLIC_BASE + t["slug"] + "/#page", "name": t["title"],
             "url": PUBLIC_BASE + t["slug"] + "/"}
            for t in parts(topics)
        ],
    }]
    return page_head(SITE, HOME_DESCRIPTION, PUBLIC_BASE, graph=graph)


def topic_head(topics, t):
    url = PUBLIC_BASE + t["slug"] + "/"
    title = "%s — %s" % (t["title"], SITE)
    description = clip(t.get("summary", ""))
    graph = [
        {"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": t["title"],
         "description": description, "inLanguage": "en",
         "isPartOf": {"@id": PUBLIC_BASE + "#page"}, "author": {"@id": PERSON_ID}},
        _breadcrumbs([(SITE, PUBLIC_BASE), (t["title"], url)]),
    ]
    return page_head(title, description, url, graph=graph)


def chapter_head(topics, t, c):
    url = PUBLIC_BASE + t["slug"] + "/" + c["slug"] + "/"
    name = plain_title(c)
    title = "%s — %s | %s" % (name, t["title"], SEO_SUFFIX)
    description = c.get("summary", "").strip()
    if len(description) < 90 and t.get("tagline"):
        # A one-line prompt is a thin snippet; the part's tagline says what kind of answer follows.
        description = (description + " " + t["tagline"].rstrip(".") + ".").strip()
    description = clip(description) or clip(t.get("summary", ""))
    article = {
        "@type": "TechArticle", "@id": url + "#article", "url": url, "mainEntityOfPage": url,
        "headline": name[:110], "description": description, "inLanguage": "en",
        "author": {"@id": PERSON_ID}, "publisher": {"@id": PERSON_ID},
        "isPartOf": {"@id": PUBLIC_BASE + t["slug"] + "/#page"}, "image": OG_IMAGE,
    }
    if c.get("published"):
        article["datePublished"] = c["published"]
    if c.get("modified"):
        article["dateModified"] = c["modified"]
    graph = [article, _breadcrumbs([(SITE, PUBLIC_BASE), (t["title"], PUBLIC_BASE + t["slug"] + "/"), (name, url)])]
    return page_head(title, description, url, kind="article",
                     published=c.get("published"), modified=c.get("modified"), graph=graph)


def mirror_head():
    """The single-file copies (the local private build, the GitHub Pages mirror) stay out of search:
    reza-bina.com/notes is the one indexed home."""
    return "\n".join([
        "<title>%s</title>" % SITE,
        '<meta name="robots" content="noindex">',
        '<link rel="canonical" href="%s">' % PUBLIC_BASE,
    ])


def sitemap(entries):
    rows = "".join(
        "<url><loc>%s</loc>%s</url>" % (esc(url), ("<lastmod>%s</lastmod>" % lastmod) if lastmod else "")
        for url, lastmod in entries
    )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">%s</urlset>\n' % rows)
