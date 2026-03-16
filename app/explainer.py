"""Claude API-based paper explanation generation."""

import json
import logging
import os

import anthropic

from app.models import PaperExplanation, PaperMetadata

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert science communicator who makes complex research accessible \
to smart, curious people who are NOT specialists. Think: explaining a paper \
to a bright friend over coffee.

Your job is to produce a layered explanation of an academic paper. You will \
receive the paper's metadata and its full text converted to markdown.

Respond with a JSON object containing exactly these four keys:

1. "tldr" — A single paragraph (3-5 sentences). No jargon. A curious teenager \
should understand the gist. Start with what the researchers did, then why it matters.

2. "the_idea" — 2-4 paragraphs. What the researchers actually did and why. \
Use analogies and concrete examples. Explain technical concepts inline when \
you must use them. Structure: problem → approach → key insight → result.

3. "why_it_matters" — 1-2 paragraphs. Practical implications. Who benefits? \
What could this enable in 2-5 years? Connect to things readers care about.

4. "whats_missing" — 1-2 paragraphs. Honest assessment of limitations, open \
questions, and what the paper doesn't address. Be fair but candid.

Rules:
- Write for a smart but non-technical reader. Avoid acronyms unless you define them.
- Use concrete analogies. Abstract → concrete, always.
- Be accurate. Don't overstate claims or implications.
- Be engaging. This should feel like a good blog post, not a textbook summary.
- Output valid JSON only. No markdown code fences, no preamble.\
"""


def _get_client() -> anthropic.Anthropic:
    """Create an Anthropic client, reading the API key from the environment."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. "
            "Set it in your environment or in a .env file."
        )
    return anthropic.Anthropic(api_key=api_key)


def _build_user_message(metadata: PaperMetadata, markdown: str) -> str:
    """Build the user message containing paper metadata and content."""
    # Truncate very long papers to stay within context limits
    max_chars = 80_000
    if len(markdown) > max_chars:
        markdown = markdown[:max_chars] + "\n\n[... content truncated for length ...]"

    return f"""\
Paper: {metadata.title}
Authors: {', '.join(metadata.authors)}
Categories: {', '.join(metadata.categories)}

Abstract:
{metadata.abstract}

Full paper text (converted from PDF):
{markdown}
"""


async def generate_explanation(
    metadata: PaperMetadata, markdown: str
) -> PaperExplanation:
    """Generate a layered explanation of a paper using Claude."""
    client = _get_client()

    user_message = _build_user_message(metadata, markdown)

    logger.info("Sending paper '%s' to Claude for explanation...", metadata.title)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = message.content[0].text.strip()

    # Parse the JSON response
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response if it's wrapped in code fences
        import re

        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise RuntimeError("Claude returned an invalid response format.")

    return PaperExplanation(
        tldr=data.get("tldr", ""),
        the_idea=data.get("the_idea", ""),
        why_it_matters=data.get("why_it_matters", ""),
        whats_missing=data.get("whats_missing", ""),
    )
