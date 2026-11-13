# Website

The Circumstances website, published at
[circumstances.aenimalabs.com](https://circumstances.aenimalabs.com/).

It is generated from this repository: the documentation pages are the Markdown
files under [`docs/`](../docs/README.md) plus the root `CONTRIBUTING.md`,
`GOVERNANCE.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`. The pack catalogue is
read from the YAML under [`packs/`](../packs/README.md). Nothing is copied by
hand, so the repository and the site cannot drift apart.

## What's here

| Path | Purpose |
|---|---|
| `build.py` | The generator: a single [uv script](https://docs.astral.sh/uv/guides/scripts/) with pinned dependencies (Jinja2, markdown-it-py, Pygments, PyYAML) |
| `config.yaml` | Site URL, repository, Google Tag Manager id, and the documentation navigation |
| `templates/` | `base.html` (head, consent mode, GTM, header, footer, search), `home.html`, `doc.html`, `packs.html`, `privacy.html`, `404.html` |
| `static/styles.css` | Hand-written CSS in the Ænima Labs palette; light and dark follow the visitor's system setting |
| `static/site.js` | Copy buttons, local search, docs navigation, the home page tabs and trajectory player |
| `static/consent.js` | The cookie banner shared with aenimalabs.com and kodama.house |
| `static/fonts/` | Self-hosted Space Grotesk, DM Sans, and Playfair Display (SIL Open Font License) |
| `og.svg`, `og.py` | Source and renderer for `static/og.png`, the 1200×630 link preview |
| `banner.py` | Renders the README banners in `.github/assets/` (light and dark) |

## Preview

```bash
uv run site/build.py --serve        # http://127.0.0.1:8000
```

`--serve` builds with the URL prefix `/` so links work at the server root.
Rebuild after editing; there is no watcher.

## Build

```bash
uv run site/build.py                # writes _site/ for the configured URL
```

The build fails, on purpose, when:

- a Markdown file under `docs/` is not listed in `config.yaml` `nav`;
- a relative link points at a file that does not exist;
- a link points at a heading anchor that does not exist on the target page;
- a page has no level-one heading.

Relative links between Markdown files become site URLs. Links to other
repository files (source, schemas, `LICENSE`) become GitHub links. Heading
anchors use GitHub's slug rules, so the same links work on github.com.

## Add a documentation page

1. Write `docs/<section>/<page>.md` with one `# Title`.
2. Add it to `nav` in `config.yaml` under the right section.
3. Link it from [`docs/README.md`](../docs/README.md) so the repository index
   stays complete.
4. Run `uv run site/build.py` and fix anything it reports.

## Deploying

[`.github/workflows/pages.yml`](../.github/workflows/pages.yml) builds the site
on every pull request that touches docs, packs, or the site (which checks links
before merge), and deploys `_site/` to GitHub Pages on every push to `main`.

Repository settings must have **Pages → Build and deployment → Source** set to
**GitHub Actions**, and **Custom domain** set to `circumstances.aenimalabs.com`
with **Enforce HTTPS** on. A workflow deploy ignores a `CNAME` file, so the
domain lives only in that setting.

DNS for `aenimalabs.com` is in Route 53. `circumstances.aenimalabs.com` is a
`CNAME` to `aenima-labs.github.io`. The `aenimalabs.com` domain is verified for
the `aenima-labs` GitHub organization (the `_github-pages-challenge-aenima-labs`
TXT record), so no other repository can claim the subdomain.

To move the site to another address, change `url` in `config.yaml`, the Pages
custom domain, and the DNS record. All internal links are generated from `url`,
so nothing else changes. A `url` with a path, such as
`https://aenima-labs.github.io/circumstances/`, also works: every link gets
that prefix.

## Analytics and privacy

The site uses the same consent setup as aenimalabs.com and kodama.house:

- Google Consent Mode defaults every storage type to `denied` in the page head.
- Google Tag Manager (`gtm_id` in `config.yaml`) loads, but Google Analytics
  only runs after the visitor accepts in the banner (`static/consent.js`).
- The answer is kept in `localStorage` under `consent` for 12 months. Any
  element with `data-cookie-settings` (the footer's "Cookie settings") reopens
  the banner.
- `templates/privacy.html` explains all of this to visitors. Update it when
  anything above changes.

Search runs entirely in the browser over `search-index.json`; no query leaves
the page. Fonts are self-hosted, so nothing is requested from Google Fonts.

## Regenerate the link-preview image

```bash
sed -E '/<text|<\/text>/d' site/og.svg > /tmp/og-bg.svg
rsvg-convert -w 1200 -h 630 /tmp/og-bg.svg -o /tmp/og-bg.png
uv run site/og.py /tmp/og-bg.png
```
