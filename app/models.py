"""Pydantic models for paperplain."""

from pydantic import BaseModel


class ExplainRequest(BaseModel):
    """Request body for the /api/explain endpoint."""

    url: str


class PaperExplanation(BaseModel):
    """Structured explanation of a paper."""

    tldr: str
    the_idea: str
    why_it_matters: str
    whats_missing: str


class PaperMetadata(BaseModel):
    """Metadata about an arxiv paper."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    pdf_url: str


class PaperResponse(BaseModel):
    """Full response for a paper explanation."""

    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    explanation: PaperExplanation
    arxiv_url: str
    created_at: str | None = None


class RecentPaper(BaseModel):
    """Summary for the recent papers list."""

    arxiv_id: str
    title: str
    created_at: str
