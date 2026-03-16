"""FastAPI application for paperplain."""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import arxiv, cache, converter, explainer
from app.models import ExplainRequest, PaperResponse, RecentPaper

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the database on startup."""
    # Ensure the data directory exists
    Path("data").mkdir(exist_ok=True)
    logger.info("paperplain is ready")
    yield


app = FastAPI(
    title="paperplain",
    description="Layman-friendly explanations of arxiv papers",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """Serve the main page."""
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.post("/api/explain", response_model=PaperResponse)
async def explain_paper(request: ExplainRequest):
    """Accept an arxiv URL/ID, fetch the paper, and return an explanation."""
    # Parse the arxiv ID
    try:
        arxiv_id = arxiv.parse_arxiv_id(request.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check cache first
    cached = cache.get(arxiv_id)
    if cached is not None:
        logger.info("Cache hit for %s", arxiv_id)
        return cached

    # Fetch metadata
    try:
        metadata = await arxiv.fetch_metadata(arxiv_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to fetch arxiv metadata")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch paper metadata from arxiv: {e}",
        )

    # Download PDF
    try:
        pdf_path = await arxiv.download_pdf(metadata.pdf_url)
    except Exception as e:
        logger.exception("Failed to download PDF")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to download paper PDF: {e}",
        )

    # Convert PDF to markdown
    try:
        markdown = converter.pdf_to_markdown(pdf_path)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Generate explanation
    try:
        explanation = await explainer.generate_explanation(metadata, markdown)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate explanation")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate explanation: {e}",
        )

    # Build response and cache it
    paper_response = PaperResponse(
        arxiv_id=metadata.arxiv_id,
        title=metadata.title,
        authors=metadata.authors,
        abstract=metadata.abstract,
        explanation=explanation,
        arxiv_url=f"https://arxiv.org/abs/{metadata.arxiv_id}",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    cache.put(paper_response)
    logger.info("Generated and cached explanation for %s", arxiv_id)

    return paper_response


@app.get("/api/paper/{arxiv_id}", response_model=PaperResponse)
async def get_paper(arxiv_id: str):
    """Get a cached paper explanation."""
    paper = cache.get(arxiv_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail=f"Paper {arxiv_id} not found. Try explaining it first.",
        )
    return paper


@app.get("/api/recent", response_model=list[RecentPaper])
async def get_recent():
    """List recently explained papers."""
    return cache.list_recent()
