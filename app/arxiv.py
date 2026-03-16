"""Arxiv metadata fetching and PDF download."""

import re
import tempfile
from pathlib import Path
from xml.etree import ElementTree

import httpx

from app.models import PaperMetadata

ARXIV_ID_PATTERN = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?")
ARXIV_API_URL = "https://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def parse_arxiv_id(url_or_id: str) -> str:
    """Extract an arxiv paper ID from a URL or raw ID string.

    Handles formats like:
        - 2408.09869
        - 2408.09869v2
        - https://arxiv.org/abs/2408.09869
        - https://arxiv.org/pdf/2408.09869
        - https://arxiv.org/abs/2408.09869v1
    """
    url_or_id = url_or_id.strip()
    match = ARXIV_ID_PATTERN.search(url_or_id)
    if match:
        return match.group(1)
    raise ValueError(
        f"Could not parse arxiv ID from: {url_or_id}. "
        "Please provide a valid arxiv URL or paper ID (e.g., 2408.09869)."
    )


async def fetch_metadata(arxiv_id: str) -> PaperMetadata:
    """Fetch paper metadata from the arxiv API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            ARXIV_API_URL, params={"id_list": arxiv_id}
        )
        response.raise_for_status()

    root = ElementTree.fromstring(response.text)
    entry = root.find(f"{ATOM_NS}entry")
    if entry is None:
        raise ValueError(f"Paper {arxiv_id} not found on arxiv.")

    # Check for arxiv error
    title_el = entry.find(f"{ATOM_NS}title")
    if title_el is not None and title_el.text and "Error" in title_el.text:
        raise ValueError(f"Arxiv API error: {title_el.text.strip()}")

    title = (title_el.text or "").strip().replace("\n", " ")

    authors = []
    for author_el in entry.findall(f"{ATOM_NS}author"):
        name_el = author_el.find(f"{ATOM_NS}name")
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    abstract_el = entry.find(f"{ATOM_NS}summary")
    abstract = (abstract_el.text or "").strip() if abstract_el is not None else ""

    categories = []
    for cat_el in entry.findall(f"{ARXIV_NS}primary_category"):
        term = cat_el.get("term")
        if term:
            categories.append(term)
    for cat_el in entry.findall(f"{ATOM_NS}category"):
        term = cat_el.get("term")
        if term and term not in categories:
            categories.append(term)

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

    return PaperMetadata(
        arxiv_id=arxiv_id,
        title=title,
        authors=authors,
        abstract=abstract,
        categories=categories,
        pdf_url=pdf_url,
    )


async def download_pdf(pdf_url: str) -> Path:
    """Download a PDF to a temporary file and return the path."""
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        response = await client.get(pdf_url)
        response.raise_for_status()

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(response.content)
    tmp.close()
    return Path(tmp.name)
