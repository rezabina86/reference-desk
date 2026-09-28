#!/usr/bin/env python3
"""Build the knowledge site.

Reads topics/<slug>/topic.json + topics/<slug>/NN-*.md and writes index.html.
Standard library only: no pip install, no network, works offline forever.
"""

import html
import html as html_module
import json
import os
import re
import sys
from datetime import date

ROOT = os.path.dirname(os.path.abspath(__file__))
TOPICS_DIR = os.path.join(ROOT, "topics")
OUT = os.path.join(ROOT, "index.html")
PUBLIC_OUT = os.path.join(ROOT, "docs", "index.html")

# ---------------------------------------------------------------- front matter

def split_front_matter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    meta, key = {}, None
    for line in raw.split("\n"):
        if line.startswith("- ") and key:
            meta.setdefault(key, [])
            if isinstance(meta[key], list):
                meta[key].append(line[2:].strip())
        elif ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            meta[key] = val if val else []
    return meta, body

# ------------------------------------------------------------------- highlight

SWIFT_KEYWORDS = set("""
actor async await func let var if else guard return throw throws rethrows try catch
for in while switch case default break continue fallthrough struct class enum
protocol extension import private public internal fileprivate open static final
init deinit self Self nil true false some any where as is do defer typealias
associatedtype inout mutating nonmutating lazy weak unowned override subscript
get set willSet didSet repeat operator precedencegroup indirect convenience
required dynamic optional throwing consuming borrowing sending nonisolated
""".split())

TOKEN_RE = re.compile(
    r"(//[^\n]*)"                       # 1 comment
    r"|(\"(?:[^\"\\]|\\.)*\")"          # 2 string
    r"|(@[A-Za-z_][A-Za-z0-9_]*)"       # 3 attribute
    r"|(\b\d+(?:\.\d+)?\b)"             # 4 number
    r"|(\b[A-Za-z_][A-Za-z0-9_]*\b)"    # 5 word
)

def highlight_swift(src):
    out, pos = [], 0
    for m in TOKEN_RE.finditer(src):
        out.append(html.escape(src[pos:m.start()]))
        pos = m.end()
        comment, string, attr, num, word = m.group(1, 2, 3, 4, 5)
        if comment:
            out.append('<span class="t-com">%s</span>' % html.escape(comment))
        elif string:
            out.append('<span class="t-str">%s</span>' % html.escape(string))
        elif attr:
            out.append('<span class="t-atr">%s</span>' % html.escape(attr))
        elif num:
            out.append('<span class="t-num">%s</span>' % num)
        elif word:
            if word in SWIFT_KEYWORDS:
                out.append('<span class="t-kw">%s</span>' % word)
            elif word[0].isupper():
                out.append('<span class="t-typ">%s</span>' % word)
            else:
                out.append(html.escape(word))
    out.append(html.escape(src[pos:]))
    return "".join(out)

# ---------------------------------------------------------------------- inline

CODE_SPAN = re.compile(r"`([^`]+)`")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
ITAL = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")

def inline(text):
    slots = []

    def stash(m):
        slots.append('<code>%s</code>' % highlight_swift(m.group(1)))
        return "\x00%d\x00" % (len(slots) - 1)

    text = CODE_SPAN.sub(stash, text)
    text = html.escape(text, quote=False)
    text = LINK.sub(
        lambda m: '<a href="%s" target="_blank" rel="noopener">%s</a>'
                  % (html.escape(m.group(2), quote=True), m.group(1)), text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITAL.sub(r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: slots[int(m.group(1))], text)
    return text

# ----------------------------------------------------------------------- block

HEADING = re.compile(r"^(#{1,4})\s+(.*)$")
BULLET = re.compile(r"^[-*]\s+(.*)$")
NUMBER = re.compile(r"^(\d+)\.\s+(.*)$")

RAW_HTML_LINE = ("<details", "</details", "<summary", "</summary")

def is_break(line):
    return (not line.strip() or line.startswith(("```", ">", "|", "#", ":::"))
            or line.lstrip().startswith(RAW_HTML_LINE)
            or BULLET.match(line) or NUMBER.match(line)
            or line.strip() in ("---", "***"))

def render_table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    if len(cells) >= 2 and all(set(c) <= set("-: ") and c for c in cells[1]):
        head, body = cells[0], cells[2:]
    else:
        head, body = None, cells
    out = ['<div class="scroll"><table>']
    if head:
        out.append("<thead><tr>" + "".join("<th>%s</th>" % inline(c) for c in head) + "</tr></thead>")
    out.append("<tbody>")
    for row in body:
        out.append("<tr>" + "".join("<td>%s</td>" % inline(c) for c in row) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)

# Each topic runs one analogy end to end; its label is styled like the others.
QUOTE_KINDS = (("In the office.", "office", "In the office"),
               ("In the library.", "office", "In the library"),
               ("Under the hood.", "hood", "Under the hood"))

def render_quote(lines):
    body = "\n".join(lines)
    kind, label = "plain", None
    for marker, css, text in QUOTE_KINDS:
        if body.lstrip().startswith("**" + marker + "**"):
            kind, label = css, text
            body = body.lstrip()[len(marker) + 4:].lstrip()
            break
    inner = render_blocks(body)
    head = '<p class="aside-label">%s</p>' % label if label else ""
    return '<blockquote class="aside %s">%s%s</blockquote>' % (kind, head, inner)

def render_blocks(md):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        if line.startswith("```"):
            lang = line[3:].strip() or "text"
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            src = "\n".join(buf)
            if lang in ("diagram", "html"):
                # Raw HTML, emitted untouched: the CSS diagram kit lives in template.html.
                out.append(src)
                continue
            code = highlight_swift(src) if lang in ("swift", "") else html.escape(src)
            out.append('<div class="scroll"><pre data-lang="%s"><code>%s</code></pre></div>'
                       % (html.escape(lang), code))
            continue

        if line.lstrip().startswith(RAW_HTML_LINE):
            out.append(line.strip())
            i += 1
            continue

        if line.startswith(":::") and line[3:].strip():
            label = line[3:].strip()
            i += 1
            buf = []
            while i < len(lines) and lines[i].strip() != ":::":
                buf.append(lines[i])
                i += 1
            i += 1
            out.append('<details class="reveal"><summary>%s</summary><div class="reveal-body">%s</div></details>'
                       % (inline(label), render_blocks("\n".join(buf))))
            continue

        if line.startswith(">"):
            buf = []
            while i < len(lines) and lines[i].startswith(">"):
                buf.append(lines[i][1:].lstrip(" ") if len(lines[i]) > 1 else "")
                i += 1
            out.append(render_quote(buf))
            continue

        if line.startswith("|"):
            buf = []
            while i < len(lines) and lines[i].startswith("|"):
                buf.append(lines[i])
                i += 1
            out.append(render_table(buf))
            continue

        m = HEADING.match(line)
        if m:
            level = len(m.group(1))
            text = inline(m.group(2))
            anchor = re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            out.append('<h%d id="%s">%s</h%d>' % (level, anchor, text, level))
            i += 1
            continue

        if line.strip() in ("---", "***"):
            out.append("<hr>")
            i += 1
            continue

        if BULLET.match(line) or NUMBER.match(line):
            ordered = bool(NUMBER.match(line))
            first_number = NUMBER.match(line).group(1) if ordered else "1"
            items = []
            while i < len(lines):
                m2 = NUMBER.match(lines[i]) if ordered else BULLET.match(lines[i])
                if not m2:
                    break
                text = m2.group(2) if ordered else m2.group(1)
                i += 1
                while i < len(lines) and lines[i].startswith("  ") and lines[i].strip():
                    text += " " + lines[i].strip()
                    i += 1
                items.append("<li>%s</li>" % inline(text))
            if ordered:
                out.append('<ol start="%s">%s</ol>' % (first_number, "".join(items)))
            else:
                out.append("<ul>%s</ul>" % "".join(items))
            continue

        buf = [line]
        i += 1
        while i < len(lines) and not is_break(lines[i]):
            buf.append(lines[i])
            i += 1
        out.append("<p>%s</p>" % inline(" ".join(b.strip() for b in buf)))

    return "".join(out)

# ------------------------------------------------------------------- assembling

def parse_sources(items):
    out = []
    for item in items or []:
        label, _, url = item.partition("|")
        label = html.unescape(label.strip())
        url = url.strip()
        ref = ""
        m = re.match(r"^(SE-\d{4}|WWDC\d{2})\b", label)
        if m:
            ref = m.group(1)
            label = label[m.end():].lstrip(" ·—-").strip()
        out.append({"ref": ref, "label": label, "url": url})
    return out

SCHEDULE_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
HEADING2 = re.compile(r'<h2 id="([^"]+)">(.*?)</h2>', re.S)
TAGS = re.compile(r"<[^>]+>")


def shorten(label, limit=46):
    """A nav-sized label: first clause, then a word boundary."""
    label = label.split(" · ")[0].strip()
    if len(label) <= limit:
        return label
    cut = label[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + "…"


def load_schedule(path):
    """Day number -> (build, label), from the track's markdown table. A build
    is named in full on its first row and abbreviated after, so carry it."""
    out, seen = {}, {}
    if not path or not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = SCHEDULE_ROW.match(line.strip())
            if not m or not m.group(3).strip("- "):
                continue
            build = re.sub(r"\s*\|.*$", "", m.group(2)).strip()
            letter = build.split(" ")[0].strip()
            if " " in build:
                seen[letter] = build
            build = seen.get(letter, build)
            out[m.group(1)] = (build, m.group(3).strip().replace("`", ""))
    return out


def outline_of(html):
    """The h2s of a chapter, for the on-this-page rail."""
    items = []
    for anchor, text in HEADING2.findall(html):
        items.append({"a": anchor, "t": html_module.unescape(TAGS.sub("", text)).strip()})
    return items


SESSION_TITLE = re.compile(r"^#\s+(.*)$")
SESSION_SUBTITLE = re.compile(r"^\*(.+)\*\s*$")
SESSION_MINUTES = re.compile(r"~\s*(\d+)\s*min")


def session_sort_key(name):
    """Setup sessions (day-S1…) first, then numbered days."""
    m = re.match(r"day-S(\d+)", name)
    if m:
        return (0, int(m.group(1)), name)
    m = re.match(r"day-(\d+)", name)
    if m:
        return (1, int(m.group(1)), name)
    return (2, 0, name)


def split_session(text):
    """A session file has no front matter: its H1 is the title and the italic
    line under it is the summary. Both are stripped from the body."""
    lines = text.split("\n")
    title, summary, start = "", "", 0
    for index, line in enumerate(lines[:6]):
        m = SESSION_TITLE.match(line)
        if m and not title:
            title, start = m.group(1).strip().replace("`", ""), index + 1
            continue
        if title and not summary:
            m = SESSION_SUBTITLE.match(line.strip())
            if m:
                summary, start = m.group(1).strip(), index + 1
                break
            if line.strip():
                break
    meta = {"title": title, "summary": summary}
    m = SESSION_MINUTES.search(summary)
    if m:
        meta["minutes"] = m.group(1)
    return meta, "\n".join(lines[start:]).lstrip("\n")


def load_topics():
    topics = []
    if not os.path.isdir(TOPICS_DIR):
        return topics
    for slug in sorted(os.listdir(TOPICS_DIR)):
        folder = os.path.join(TOPICS_DIR, slug)
        meta_path = os.path.join(folder, "topic.json")
        if not os.path.isfile(meta_path):
            continue
        with open(meta_path, encoding="utf-8") as fh:
            topic = json.load(fh)
        topic.setdefault("slug", slug)
        source = topic.pop("source", None)
        session_mode = source is not None
        if session_mode:
            folder = os.path.normpath(os.path.join(ROOT, source))
            if not os.path.isdir(folder):
                print("source folder missing for %s: %s" % (slug, folder), file=sys.stderr)
                continue
        prefix = topic.pop("prefix", "day-")
        schedule = load_schedule(os.path.normpath(os.path.join(ROOT, topic.pop("schedule", ""))) 
                                 if topic.get("schedule") else None)
        setup_labels = topic.pop("setupLabels", {})
        setup_group = topic.pop("setupGroup", "Week 0 · setup")
        if session_mode:
            topic["kind"] = "sessions"
        names = [n for n in os.listdir(folder) if n.endswith(".md")]
        names = [n for n in names if n.startswith(prefix)] if session_mode else names
        names.sort(key=session_sort_key) if session_mode else names.sort()

        chapters, seen = [], set()
        for name in names:
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                raw = fh.read()
            meta, body = split_session(raw) if session_mode else split_front_matter(raw)
            cslug = re.sub(r"^\d+-", "", name[:-3])
            if cslug in seen:
                continue
            seen.add(cslug)
            sources = parse_sources(meta.get("sources"))
            entry = {
                "slug": cslug,
                "title": meta.get("title", cslug.replace("-", " ").title()),
                "summary": meta.get("summary", ""),
                "minutes": meta.get("minutes", ""),
                "sources": sources,
                "html": render_blocks(body),
                "text": re.sub(r"\s+", " ", re.sub(r"[#`*>|\-]", " ", body)).lower()[:24000],
            }
            entry["outline"] = outline_of(entry["html"])
            if session_mode:
                m = re.match(r"day-(S?\d+)", name)
                day = m.group(1) if m else ""
                entry["day"] = day
                if day.startswith("S"):
                    entry["group"] = setup_group
                    entry["short"] = shorten(setup_labels.get(day, entry["title"].split("—", 1)[-1].strip()))
                else:
                    build, label = schedule.get(str(int(day)), ("", entry["title"]))
                    entry["group"] = build
                    entry["short"] = shorten(label)
                    entry["full"] = label
            chapters.append(entry)
        if session_mode and schedule:
            written = {c.get("day", "").lstrip("0") for c in chapters}
            topic["upcoming"] = [
                {"day": n, "group": g, "short": shorten(l), "full": l}
                for n, (g, l) in sorted(schedule.items(), key=lambda kv: int(kv[0]))
                if n not in written
            ]
            topic["total"] = len(schedule)
        topic["chapters"] = chapters
        topic["minutes"] = sum(int(c["minutes"]) for c in chapters if str(c["minutes"]).isdigit())
        all_sources = {}
        for c in chapters:
            for s in c["sources"]:
                all_sources[s["url"]] = s
        topic["sources"] = list(all_sources.values())
        topics.append(topic)
    return topics

# ------------------------------------------------------------------------ page

def build(public=False):
    topics = load_topics()
    if public:
        topics = [t for t in topics if not t.pop("private", False)]
    else:
        for t in topics:
            t.pop("private", None)
    if not topics:
        print("no topics found under topics/", file=sys.stderr)
    data = json.dumps({"topics": topics, "built": date.today().isoformat()},
                      ensure_ascii=False).replace("</", "<\\/")
    with open(os.path.join(ROOT, "template.html"), encoding="utf-8") as fh:
        template = fh.read()
    page = template.replace("__DATA__", data)
    out = PUBLIC_OUT if public else OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(page)
    chapters = sum(len(t["chapters"]) for t in topics)
    print("built %s — %d topic(s), %d chapters, %.0f KB"
          % (os.path.relpath(out, ROOT), len(topics), chapters, len(page) / 1024))

if __name__ == "__main__":
    build(public="--public" in sys.argv)
