#!/usr/bin/env python3
"""Build static HTML site from content/papers/*.json."""

import json
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

CONTENT_DIR = Path("content/papers")
SITE_DIR = Path("docs")
PAPERS_DIR = SITE_DIR / "papers"
BASE_URL = "https://tashfeenm.github.io/paperplain"
REPO_URL = "https://github.com/tashfeenm/paperplain"


def escape(text: str) -> str:
    return html.escape(text)


def truncate_at_sentence(text: str, max_len: int = 300) -> str:
    """Truncate text at the nearest sentence boundary before max_len."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    # Find last sentence-ending punctuation
    last_period = max(truncated.rfind(". "), truncated.rfind(".) "))
    if last_period > max_len // 2:
        return truncated[: last_period + 1]
    # Fallback: find last space
    last_space = truncated.rfind(" ")
    if last_space > max_len // 2:
        return truncated[:last_space] + "..."
    return truncated + "..."


def text_to_paragraphs(text: str, indent: int = 20) -> str:
    pad = " " * indent
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"{pad}<p>{escape(p)}</p>" for p in paragraphs)


def og_description(text: str) -> str:
    """Clean text for use in meta description (single line, max 200 chars)."""
    clean = text.replace("\n", " ").strip()
    if len(clean) > 200:
        clean = clean[:197] + "..."
    return escape(clean)


FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#2563eb"/>
  <text x="16" y="22" font-family="system-ui,sans-serif" font-size="18" font-weight="700"
        fill="white" text-anchor="middle">pp</text>
</svg>"""


HEAD_COMMON = """\
    <link rel="icon" type="image/svg+xml" href="{favicon_path}favicon.svg">"""


def build_paper_page(paper: dict, prev_paper: dict | None, next_paper: dict | None) -> str:
    arxiv_id = paper["arxiv_id"]
    title = escape(paper["title"])
    authors = escape(", ".join(paper["authors"]))
    arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
    category = escape(paper.get("category", ""))
    published = escape(paper.get("published_date", ""))
    explained = paper.get("explained_date", "")
    ex = paper["explanation"]
    page_url = f"{BASE_URL}/papers/{arxiv_id}.html"
    desc = og_description(ex["tldr"])

    # Prev/next navigation
    nav_items = []
    if prev_paper:
        pid = prev_paper["arxiv_id"]
        ptitle = escape(prev_paper["title"])
        nav_items.append(
            f'            <a href="{pid}.html" class="nav-prev" title="{ptitle}">&larr; Previous</a>'
        )
    else:
        nav_items.append('            <span class="nav-prev"></span>')
    if next_paper:
        nid = next_paper["arxiv_id"]
        ntitle = escape(next_paper["title"])
        nav_items.append(
            f'            <a href="{nid}.html" class="nav-next" title="{ntitle}">Next &rarr;</a>'
        )
    else:
        nav_items.append('            <span class="nav-next"></span>')
    nav_html = "\n".join(nav_items)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — paperplain</title>
    <meta name="description" content="{desc}">
    <meta property="og:title" content="{title} — paperplain">
    <meta property="og:description" content="{desc}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{page_url}">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title} — paperplain">
    <meta name="twitter:description" content="{desc}">
    <link rel="canonical" href="{page_url}">
{HEAD_COMMON.format(favicon_path="../")}
    <link rel="stylesheet" href="../style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Merriweather:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
    <header>
        <div class="container">
            <a href="../index.html" class="logo-link">
                <h1 class="logo">paper<span class="logo-accent">plain</span></h1>
            </a>
            <p class="tagline">arxiv papers, explained for humans</p>
        </div>
    </header>

    <main class="container">
        <div class="top-nav">
            <a href="../index.html">&larr; All papers</a>
        </div>

        <article class="result-section">
            <div class="paper-header">
                <div class="paper-meta">
                    <span class="category-tag">{category}</span>
                    <span class="paper-date">{published}</span>
                </div>
                <h2 class="paper-title">{title}</h2>
                <p class="paper-authors">{authors}</p>
                <a href="{arxiv_url}" target="_blank" rel="noopener" class="paper-link">
                    View original paper on arxiv &nearr;
                </a>
            </div>

            <nav class="section-toc" aria-label="Sections">
                <a href="#tldr">TL;DR</a>
                <a href="#the-idea">The Idea</a>
                <a href="#why-it-matters">Why It Matters</a>
                <a href="#whats-missing">What's Missing</a>
            </nav>

            <div class="explanation">
                <section id="tldr" class="explanation-block">
                    <h3 class="section-label">TL;DR</h3>
                    <div class="section-content tldr-content">
{text_to_paragraphs(ex["tldr"])}
                    </div>
                </section>

                <section id="the-idea" class="explanation-block">
                    <h3 class="section-label">The Idea</h3>
                    <div class="section-content">
{text_to_paragraphs(ex["the_idea"])}
                    </div>
                </section>

                <section id="why-it-matters" class="explanation-block">
                    <h3 class="section-label">Why It Matters</h3>
                    <div class="section-content">
{text_to_paragraphs(ex["why_it_matters"])}
                    </div>
                </section>

                <section id="whats-missing" class="explanation-block">
                    <h3 class="section-label">What's Missing</h3>
                    <div class="section-content">
{text_to_paragraphs(ex["whats_missing"])}
                    </div>
                </section>
            </div>
        </article>

        <div class="paper-footer-meta">
            <p>Explained {escape(explained)} using Claude Opus.
            Found an error? <a href="{REPO_URL}/issues/new?title=Error+in+{arxiv_id}&labels=correction" target="_blank" rel="noopener">Report it</a>.</p>
        </div>

        <nav class="prev-next-nav" aria-label="Paper navigation">
{nav_html}
        </nav>
    </main>

    <footer>
        <div class="container">
            <p class="disclaimer">
                Generated by <a href="https://www.anthropic.com" target="_blank" rel="noopener">Claude</a>, reviewed by an AI council. May contain errors.
                Always refer to the <a href="{arxiv_url}" target="_blank" rel="noopener">original paper</a>.
            </p>
            <p class="credits">
                <a href="{REPO_URL}" target="_blank" rel="noopener">GitHub</a> &middot;
                <a href="../feed.xml">RSS</a> &middot;
                Built with <a href="https://ds4sd.github.io/docling/" target="_blank" rel="noopener">Docling</a>
                + <a href="https://www.anthropic.com" target="_blank" rel="noopener">Claude</a>
            </p>
        </div>
    </footer>
</body>
</html>"""


def build_index_page(papers: list[dict]) -> str:
    cards = []
    for p in papers:
        arxiv_id = escape(p["arxiv_id"])
        title = escape(p["title"])
        authors = escape(", ".join(p["authors"][:3]))
        if len(p["authors"]) > 3:
            authors += f" + {len(p['authors']) - 3} more"
        tldr = truncate_at_sentence(p["explanation"]["tldr"])
        tldr_escaped = escape(tldr)
        category = escape(p.get("category", ""))
        published = escape(p.get("published_date", ""))

        cards.append(f"""
            <a href="papers/{arxiv_id}.html" class="paper-card">
                <div class="card-meta">
                    <span class="category-tag">{category}</span>
                    <span class="card-date">{published}</span>
                </div>
                <h3 class="card-title">{title}</h3>
                <p class="card-authors">{authors}</p>
                <p class="card-tldr">{tldr_escaped}</p>
            </a>""")

    cards_html = "\n".join(cards)
    index_url = f"{BASE_URL}/"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>paperplain — arxiv papers, explained</title>
    <meta name="description" content="Complex research papers explained in plain language. Generated by Claude, reviewed by an AI council.">
    <meta property="og:title" content="paperplain — arxiv papers, explained">
    <meta property="og:description" content="Complex research papers explained in plain language. Generated by Claude, reviewed by an AI council.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{index_url}">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="paperplain — arxiv papers, explained">
    <meta name="twitter:description" content="Complex research papers explained in plain language. Generated by Claude, reviewed by an AI council.">
    <link rel="canonical" href="{index_url}">
    <link rel="alternate" type="application/rss+xml" title="paperplain" href="{BASE_URL}/feed.xml">
{HEAD_COMMON.format(favicon_path="")}
    <link rel="stylesheet" href="style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Merriweather:wght@400;700&display=swap" rel="stylesheet">
</head>
<body>
    <header>
        <div class="container">
            <a href="index.html" class="logo-link">
                <h1 class="logo">paper<span class="logo-accent">plain</span></h1>
            </a>
            <p class="tagline">arxiv papers, explained for humans</p>
        </div>
    </header>

    <main class="container">
        <section class="how-it-works">
            <h2>How it works</h2>
            <p>Papers are converted from PDF using <a href="https://ds4sd.github.io/docling/" target="_blank" rel="noopener">Docling</a>,
            explained by <a href="https://www.anthropic.com" target="_blank" rel="noopener">Claude</a>,
            then cross-checked by multiple AI models for factual accuracy, logical consistency, and completeness.
            The full pipeline is <a href="{REPO_URL}" target="_blank" rel="noopener">open source</a>.</p>
        </section>

        <section class="papers-grid">
{cards_html}
        </section>
    </main>

    <footer>
        <div class="container">
            <p class="disclaimer">
                Generated by <a href="https://www.anthropic.com" target="_blank" rel="noopener">Claude</a>,
                reviewed by an AI council.
                May contain errors. Always refer to the
                <a href="https://arxiv.org" target="_blank" rel="noopener">original papers</a>.
            </p>
            <p class="credits">
                <a href="{REPO_URL}" target="_blank" rel="noopener">GitHub</a> &middot;
                <a href="feed.xml">RSS</a> &middot;
                Built with <a href="https://ds4sd.github.io/docling/" target="_blank" rel="noopener">Docling</a>
                + <a href="https://www.anthropic.com" target="_blank" rel="noopener">Claude</a>
            </p>
        </div>
    </footer>
</body>
</html>"""


def build_rss_feed(papers: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for p in papers:
        title = escape(p["title"])
        arxiv_id = p["arxiv_id"]
        link = f"{BASE_URL}/papers/{arxiv_id}.html"
        desc = escape(p["explanation"]["tldr"])
        items.append(f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid>{link}</guid>
      <description>{desc}</description>
    </item>""")
    items_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>paperplain</title>
    <link>{BASE_URL}/</link>
    <description>arxiv papers, explained for humans</description>
    <lastBuildDate>{now}</lastBuildDate>
    <atom:link href="{BASE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>"""


def main():
    if not CONTENT_DIR.exists():
        print("No content/papers/ directory found.")
        sys.exit(1)

    json_files = sorted(CONTENT_DIR.glob("*.json"))
    if not json_files:
        print("No paper JSON files found in content/papers/.")
        sys.exit(1)

    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    papers = []
    for f in json_files:
        paper = json.loads(f.read_text())
        papers.append(paper)

    # Build paper pages with prev/next navigation
    for i, paper in enumerate(papers):
        prev_paper = papers[i - 1] if i > 0 else None
        next_paper = papers[i + 1] if i < len(papers) - 1 else None
        page_html = build_paper_page(paper, prev_paper, next_paper)
        out_path = PAPERS_DIR / f"{paper['arxiv_id']}.html"
        out_path.write_text(page_html)
        print(f"  Built {out_path}")

    # Build index
    index_html = build_index_page(papers)
    (SITE_DIR / "index.html").write_text(index_html)
    print(f"  Built {SITE_DIR / 'index.html'}")

    # Build RSS feed
    rss = build_rss_feed(papers)
    (SITE_DIR / "feed.xml").write_text(rss)
    print(f"  Built {SITE_DIR / 'feed.xml'}")

    # Write favicon
    (SITE_DIR / "favicon.svg").write_text(FAVICON_SVG.strip())
    print(f"  Built {SITE_DIR / 'favicon.svg'}")

    print(f"\nDone. {len(papers)} papers built. Serve with: python -m http.server -d docs")


if __name__ == "__main__":
    main()
