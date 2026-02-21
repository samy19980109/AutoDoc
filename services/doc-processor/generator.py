"""Documentation generator -- turns a structured code analysis into HTML
documentation for a given doc type.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from common.ai.provider import AIProvider
from common.models.tables import DocType
from prompts import (
    API_REFERENCE_PROMPT,
    API_REFERENCE_SYSTEM,
    ARCHITECTURE_PROMPT,
    ARCHITECTURE_SYSTEM,
    WALKTHROUGH_PROMPT,
    WALKTHROUGH_SYSTEM,
)

logger = logging.getLogger("doc-processor.generator")

# Map each DocType to its (system, prompt_template) pair.
_PROMPT_MAP: Dict[DocType, tuple[str, str]] = {
    DocType.api_reference: (API_REFERENCE_SYSTEM, API_REFERENCE_PROMPT),
    DocType.architecture: (ARCHITECTURE_SYSTEM, ARCHITECTURE_PROMPT),
    DocType.walkthrough: (WALKTHROUGH_SYSTEM, WALKTHROUGH_PROMPT),
}


async def _generate_docs_async(
    analysis: Dict[str, Any],
    doc_type: DocType,
    existing_content: str,
    ai_provider: AIProvider,
) -> str:
    system_prompt, prompt_template = _PROMPT_MAP[doc_type]

    existing_context = ""
    if existing_content and existing_content.strip():
        existing_context = (
            "The page already contains the following human-written content.  "
            "Preserve its intent and do not contradict it:\n\n"
            f"{existing_content}"
        )

    prompt = prompt_template.format(
        analysis_json=json.dumps(analysis, indent=2),
        existing_context=existing_context,
    )

    logger.info("Generating %s documentation", doc_type.value)

    response = await ai_provider.generate(
        prompt=prompt,
        system=system_prompt,
        max_tokens=8192,
    )

    html = response.content.strip()

    # Strip accidental markdown fences.
    if html.startswith("```"):
        html = html.split("\n", 1)[1]
    if html.endswith("```"):
        html = html.rsplit("```", 1)[0]

    logger.info(
        "Generated %s doc (%d chars, %d tokens)",
        doc_type.value,
        len(html),
        response.output_tokens,
    )

    return html.strip()


def generate_docs(
    analysis: Dict[str, Any],
    doc_type: DocType,
    existing_content: str,
    ai_provider: AIProvider,
) -> str:
    """Generate documentation HTML from a code analysis.

    Parameters
    ----------
    analysis:
        Structured analysis dict produced by :func:`analyzer.analyze_code`.
    doc_type:
        The kind of documentation to produce.
    existing_content:
        Any human-written content already on the Confluence page, so the AI
        can avoid contradicting it.
    ai_provider:
        An :class:`AIProvider` instance.

    Returns
    -------
    str
        HTML content ready for insertion between AUTO-DOC markers.
    """
    return asyncio.run(
        _generate_docs_async(analysis, doc_type, existing_content, ai_provider)
    )
