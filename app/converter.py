"""PDF to Markdown conversion using Docling."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def pdf_to_markdown(pdf_path: Path) -> str:
    """Convert a PDF file to Markdown using Docling.

    Returns the markdown text, or raises an exception on failure.
    """
    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(pdf_path))
        markdown = result.document.export_to_markdown()

        if not markdown or not markdown.strip():
            raise ValueError("Docling produced empty output for this PDF.")

        return markdown

    except ImportError:
        raise RuntimeError(
            "Docling is not installed. Install it with: pip install docling"
        )
    except Exception as e:
        logger.exception("Failed to convert PDF to markdown")
        raise RuntimeError(
            f"Failed to convert PDF to readable text: {e}"
        ) from e
    finally:
        # Clean up the temp PDF
        try:
            pdf_path.unlink(missing_ok=True)
        except OSError:
            pass
