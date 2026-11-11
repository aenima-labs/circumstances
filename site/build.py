# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "jinja2==3.1.6",
#   "markdown-it-py==3.0.0",
#   "mdit-py-plugins==0.4.2",
#   "pygments==2.19.1",
#   "pyyaml==6.0.2",
# ]
# ///
"""Build the Circumstances website from this repository.

    uv run site/build.py                 # writes _site/ for the configured URL
    uv run site/build.py --base /        # for local preview at the server root
    uv run site/build.py --serve         # build for preview and serve on :8000

The documentation is the Markdown under docs/ (plus a few root files), so the
repository and the website never disagree. The build fails on a page missing
from the navigation, a broken internal link, or a missing anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import http.server
import json
import os
import re
import shutil
import socketserver
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.tasklists import tasklists_plugin
from pygments import highlight as pygments_highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent
OUT = ROOT / "_site"

LANG_LABELS = {
    "bash": "Shell",
    "sh": "Shell",
    "console": "Shell",
    "yaml": "YAML",
    "json": "JSON",
    "python": "Python",
    "toml": "TOML",
    "text": "",
    "": "",
}


class BuildError(Exception):
    pass


# ─── Pages ────────────────────────────────────────────────────────────────────


@dataclass
class Page:
    src: str  # repository-relative path, e.g. docs/guides/x.md
    url: str  # site-relative URL, e.g. docs/guides/x/
    section: str
    title: str = ""
    body: str = ""
    description: str = ""
    toc: list[tuple[int, str, str]] = field(default_factory=list)
    anchors: set[str] = field(default_factory=set)
    sections: list[dict[str, str]] = field(default_factory=list)  # for search
    links: list[tuple[str, str]] = field(default_factory=list)  # (url, anchor) to check


def default_url(src: str) -> str:
    path = PurePosixPath(src)
    if path.name == "README.md":
        return f"{path.parent.as_posix()}/" if path.parent.as_posix() != "." else ""
    return f"{path.with_suffix('').as_posix()}/"


def load_pages(config: dict) -> list[Page]:
    pages: list[Page] = []
    for group in config["nav"]:
        for entry in group["pages"]:
            if isinstance(entry, str):
                entry = {"src": entry}
            src = entry["src"]
            if not (ROOT / src).is_file():
                raise BuildError(f"navigation lists a missing file: {src}")
            pages.append(
                Page(
                    src=src,
                    url=entry.get("url", default_url(src)),
                    section=group["section"],
                    title=entry.get("title", ""),
                )
            )
    listed = {page.src for page in pages}
    unlisted = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "docs").rglob("*.md")
        if path.relative_to(ROOT).as_posix() not in listed
    )
    if unlisted:
        raise BuildError("docs missing from site/config.yaml nav: " + ", ".join(unlisted))
    return pages


# ─── Markdown ─────────────────────────────────────────────────────────────────


def slugify(text: str) -> str:
    """GitHub-style heading slug, so links work on github.com and on the site."""
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def inline_text(token: Token) -> str:
    parts: list[str] = []
    for child in token.children or []:
        if child.type in {"text", "code_inline"}:
            parts.append(child.content)
        elif child.type in {"softbreak", "hardbreak"}:
            parts.append(" ")
    return "".join(parts)


def highlight(code: str, lang: str, _attrs: str) -> str:
    lang = (lang or "").strip().lower()
    try:
        lexer = get_lexer_by_name(lang) if lang and lang != "text" else TextLexer()
    except ClassNotFound:
        lexer = TextLexer()
    body = pygments_highlight(code, lexer, HtmlFormatter(nowrap=True))
    label = LANG_LABELS.get(lang, lang.upper())
    shell = " is-shell" if lang in {"bash", "sh", "console"} else ""
    head = f'<span class="code-lang">{html.escape(label)}</span>' if label else "<span></span>"
    return (
        f'<div class="code{shell}"><div class="code-head">{head}'
        '<button class="copy" type="button" aria-label="Copy code">Copy</button></div>'
        f"<pre><code>{body}</code></pre></div>"
    )


class Renderer:
    def __init__(self, config: dict, pages: list[Page], base: str) -> None:
        self.config = config
        self.base = base
        self.by_src = {page.src: page for page in pages}
        self.md = (
            MarkdownIt("commonmark", {"highlight": highlight, "html": False})
            .enable(["table", "strikethrough"])
            .use(tasklists_plugin)
        )
        rules = self.md.renderer.rules
        rules["heading_open"] = self._heading_open
        rules["heading_close"] = self._heading_close
        rules["link_open"] = self._link_open
        rules["table_open"] = lambda *a: '<div class="table-wrap"><table>\n'
        rules["table_close"] = lambda *a: "</table></div>\n"
        self._page: Page | None = None

    # Headings carry ids and a hover anchor.
    def _heading_open(self, tokens, idx, options, env):
        token = tokens[idx]
        anchor = token.attrGet("id")
        return f'<{token.tag} id="{anchor}">'

    def _heading_close(self, tokens, idx, options, env):
        token = tokens[idx]
        opener = tokens[idx - 2]
        anchor = opener.attrGet("id")
        if token.tag == "h1":
            return f"</{token.tag}>\n"
        return (
            f'<a class="anchor" href="#{anchor}" aria-label="Link to this section">#</a>'
            f"</{token.tag}>\n"
        )

    def _link_open(self, tokens, idx, options, env):
        token = tokens[idx]
        href = token.attrGet("href") or ""
        new_href, external = self.resolve_link(href)
        token.attrSet("href", new_href)
        if external:
            token.attrSet("rel", "noopener")
            token.attrJoin("class", "ext")
        return self.md.renderer.renderToken(tokens, idx, options, env)

    def resolve_link(self, href: str) -> tuple[str, bool]:
        parts = urlsplit(href)
        if parts.scheme in {"http", "https", "mailto"}:
            return href, parts.scheme != "mailto"
        if href.startswith("#"):
            assert self._page
            self._page.links.append((self._page.url, href[1:]))
            return href, False
        if not parts.path:
            return href, False
        assert self._page
        target = (PurePosixPath(self._page.src).parent / parts.path).as_posix()
        target = os.path.normpath(target).replace(os.sep, "/")
        if target in self.by_src:
            page = self.by_src[target]
            self._page.links.append((page.url, parts.fragment))
            anchor = f"#{parts.fragment}" if parts.fragment else ""
            return f"{self.base}{page.url}{anchor}", False
        if target.startswith(".."):
            raise BuildError(f"{self._page.src}: link escapes the repository: {href}")
        if not (ROOT / target).exists():
            raise BuildError(f"{self._page.src}: link to a missing file: {href}")
        kind = "tree" if (ROOT / target).is_dir() else "blob"
        repo, branch = self.config["repository"], self.config["branch"]
        anchor = f"#{parts.fragment}" if parts.fragment else ""
        return f"{repo}/{kind}/{branch}/{target}{anchor}", True

    def render(self, page: Page) -> None:
        self._page = page
        source = (ROOT / page.src).read_text()
        tokens = self.md.parse(source)
        seen: dict[str, int] = {}
        section = {"title": "", "anchor": "", "text": []}
        sections: list[dict] = []
        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                text = inline_text(tokens[i + 1])
                slug = slugify(text) or "section"
                if slug in seen:
                    seen[slug] += 1
                    slug = f"{slug}-{seen[slug]}"
                else:
                    seen[slug] = 0
                token.attrSet("id", slug)
                page.anchors.add(slug)
                level = int(token.tag[1])
                if level == 1:
                    page.title = page.title or text
                    section = {"title": "", "anchor": "", "text": []}
                elif level in {2, 3}:
                    page.toc.append((level, slug, text))
                    sections.append(section)
                    section = {"title": text, "anchor": slug, "text": []}
            elif token.type == "inline" and tokens[i - 1].type != "heading_open":
                section["text"].append(inline_text(token))
                if not page.description and tokens[i - 1].type == "paragraph_open":
                    page.description = inline_text(token)
            elif token.type == "fence":
                section["text"].append(token.content)
        sections.append(section)
        page.body = self.md.renderer.render(tokens, self.md.options, {})
        page.sections = [
            {"title": s["title"], "anchor": s["anchor"], "text": " ".join(s["text"])}
            for s in sections
            if s["text"] or s["title"]
        ]
        if not page.title:
            raise BuildError(f"{page.src} has no level-one heading")
        # Strip the H1 from the body; templates render the title themselves.
        page.body = re.sub(r"^\s*<h1[^>]*>.*?</h1>\n", "", page.body, count=1, flags=re.S)
        page.description = re.sub(r"\s+", " ", page.description).strip()[:200]


# ─── Packs ────────────────────────────────────────────────────────────────────


def load_packs() -> list[dict]:
    packs = []
    for manifest in sorted((ROOT / "packs").glob("*/pack.yaml")):
        root = manifest.parent
        meta = yaml.safe_load(manifest.read_text())
        rules = []
        for rule_file in sorted(root.glob("rules/*/rule.yaml")):
            rule = yaml.safe_load(rule_file.read_text())
            cases = []
            for case_file in sorted(rule_file.parent.glob("cases/*/case.yaml")):
                case = yaml.safe_load(case_file.read_text())
                case["path"] = case_file.relative_to(ROOT).as_posix()
                cases.append(case)
            rule["cases"] = cases
            rule["path"] = rule_file.relative_to(ROOT).as_posix()
            rules.append(rule)
        meta["slug"] = root.name
        meta["path"] = root.relative_to(ROOT).as_posix()
        meta["rules"] = rules
        meta["case_count"] = sum(len(rule["cases"]) for rule in rules)
        tiers: set[str] = set()
        for rule in rules:
            tiers.update(e["tier"] for e in rule.get("evaluators", []))
            for case in rule["cases"]:
                tiers.update(e["tier"] for e in case.get("evaluators", []))
        meta["tiers"] = sorted(tiers)
        packs.append(meta)
    order = [
        "grounding",
        "action-integrity",
        "privacy-security",
        "transparency",
        "human-agency",
        "reliability",
        "ai-risk",
    ]
    packs.sort(key=lambda p: order.index(p["slug"]) if p["slug"] in order else 99)
    return packs


# ─── Build ────────────────────────────────────────────────────────────────────


def asset_versions(static: Path) -> dict[str, str]:
    versions = {}
    for path in static.rglob("*"):
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:10]
            versions[path.relative_to(static).as_posix()] = digest
    return versions


def build(base_override: str | None = None) -> Path:
    config = yaml.safe_load((SITE / "config.yaml").read_text())
    site_url = os.environ.get("SITE_URL", config["url"]).rstrip("/") + "/"
    base = base_override if base_override is not None else urlsplit(site_url).path or "/"
    if not base.endswith("/"):
        base += "/"

    pages = load_pages(config)
    renderer = Renderer(config, pages, base)
    for page in pages:
        renderer.render(page)

    by_url = {page.url: page for page in pages}
    problems = []
    for page in pages:
        for url, anchor in page.links:
            target = by_url.get(url)
            if target is None:
                problems.append(f"{page.src}: no page at {url}")
            elif anchor and anchor not in target.anchors:
                problems.append(f"{page.src}: {target.src} has no heading #{anchor}")
    if problems:
        raise BuildError("broken links:\n  " + "\n  ".join(problems))

    nav = []
    for group in config["nav"]:
        nav.append(
            {
                "section": group["section"],
                "pages": [p for p in pages if p.section == group["section"]],
            }
        )

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(SITE / "static", OUT / "static")
    versions = asset_versions(SITE / "static")

    env = Environment(
        loader=FileSystemLoader(SITE / "templates"),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    def asset(path: str) -> str:
        if path not in versions:
            raise BuildError(f"template asks for a missing asset: {path}")
        return f"{base}static/{path}?v={versions[path]}"

    packs = load_packs()
    now = datetime.now(UTC)
    common = {
        "site": config,
        "base": base,
        "site_url": site_url,
        "asset": asset,
        "nav": nav,
        "year": now.year,
        "packs": packs,
        "stats": {
            "packs": len(packs),
            "rules": sum(len(p["rules"]) for p in packs),
            "cases": sum(p["case_count"] for p in packs),
        },
    }

    def write(url: str, template: str, **context) -> None:
        target = OUT / url / "index.html" if url.endswith("/") or url == "" else OUT / url
        target.parent.mkdir(parents=True, exist_ok=True)
        html_text = env.get_template(template).render(**common, **context, url=url)
        target.write_text(html_text)

    write("", "home.html", title=None, description=config["description"])
    for index, page in enumerate(pages):
        prev_page = pages[index - 1] if index > 0 else None
        next_page = pages[index + 1] if index + 1 < len(pages) else None
        template = "packs.html" if page.src == "packs/README.md" else "doc.html"
        write(
            page.url,
            template,
            page=page,
            title=page.title,
            description=page.description,
            prev_page=prev_page,
            next_page=next_page,
            edit_url=f"{config['repository']}/edit/{config['branch']}/{page.src}",
        )
    write(
        "privacy.html",
        "privacy.html",
        title="Privacy and cookies",
        description="What this website collects, why, and how to change your mind.",
    )
    write("404.html", "404.html", title="Not found", description="")

    index = []
    for page in pages:
        for section in page.sections:
            index.append(
                {
                    "page": page.title,
                    "section": section["title"],
                    "group": page.section,
                    "url": f"{base}{page.url}"
                    + (f"#{section['anchor']}" if section["anchor"] else ""),
                    "text": re.sub(r"\s+", " ", section["text"])[:1200],
                }
            )
    (OUT / "search-index.json").write_text(
        json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    )

    urls = [""] + [page.url for page in pages] + ["privacy.html"]
    sitemap = "".join(
        f"  <url><loc>{site_url}{u}</loc><lastmod>{now:%Y-%m-%d}</lastmod></url>\n" for u in urls
    )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{sitemap}</urlset>\n"
    )
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {site_url}sitemap.xml\n")
    (OUT / ".nojekyll").write_text("")
    print(
        f"built {len(pages) + 3} pages into {OUT.relative_to(ROOT)}/ for {site_url} (base {base})"
    )
    return OUT


def serve(port: int) -> None:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as server:
        print(f"serving http://127.0.0.1:{port}/")
        server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--base", help="URL path prefix, e.g. / for local preview")
    parser.add_argument("--serve", action="store_true", help="build for preview and serve")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        build("/" if args.serve and args.base is None else args.base)
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.serve:
        serve(args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
