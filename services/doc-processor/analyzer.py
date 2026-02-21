"""Code analysis module -- sends source files to an AI provider and returns
a structured analysis result.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from common.ai.provider import AIProvider
from prompts import CODE_ANALYSIS_PROMPT, CODE_ANALYSIS_SYSTEM

logger = logging.getLogger("doc-processor.analyzer")


def _format_file_contents(file_contents: Dict[str, str]) -> str:
    """Format a dict of {filepath: source} into a prompt-friendly block."""
    parts: list[str] = []
    for path, source in file_contents.items():
        parts.append(f"=== {path} ===\n{source}")
    return "\n\n".join(parts)


async def _analyze_code_async(
    file_contents: Dict[str, str],
    ai_provider: AIProvider,
) -> Dict[str, Any]:
    """Async implementation of code analysis."""
    formatted = _format_file_contents(file_contents)
    prompt = CODE_ANALYSIS_PROMPT.format(file_contents=formatted)

    logger.info("Sending %d files for analysis (%d chars)", len(file_contents), len(formatted))

    response = await ai_provider.generate(
        prompt=prompt,
        system=CODE_ANALYSIS_SYSTEM,
        max_tokens=4096,
    )

    # Parse the JSON response, stripping any accidental markdown fences.
    raw = (response.content or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    def _default_analysis() -> Dict[str, Any]:
        return {
            "summary": "AI returned non-JSON analysis output; using fallback structure.",
            "functions": [],
            "classes": [],
            "api_endpoints": [],
            "dependencies": [],
            "architecture_patterns": [],
        }

    def _extract_json_object(text: str) -> str:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start : end + 1]
        return text

    if not raw:
        logger.error("AI analysis response was empty; using fallback analysis")
        analysis = _default_analysis()
    else:
        try:
            analysis = json.loads(raw)
        except json.JSONDecodeError:
            candidate = _extract_json_object(raw)
            try:
                analysis = json.loads(candidate)
            except json.JSONDecodeError:
                logger.error(
                    "Failed to parse AI analysis JSON. Sample output: %r",
                    raw[:1000],
                )
                analysis = _default_analysis()

    logger.info(
        "Analysis complete: %d functions, %d classes, %d endpoints",
        len(analysis.get("functions", [])),
        len(analysis.get("classes", [])),
        len(analysis.get("api_endpoints", [])),
    )

    return analysis


def analyze_code(
    file_contents: Dict[str, str],
    ai_provider: AIProvider,
) -> Dict[str, Any]:
    """Analyze source code using an AI provider.

    Parameters
    ----------
    file_contents:
        Mapping of ``relative/file/path`` to source-code string.
    ai_provider:
        An :class:`AIProvider` instance.

    Returns
    -------
    dict
        Structured analysis with keys: ``summary``, ``functions``,
        ``classes``, ``api_endpoints``, ``dependencies``,
        ``architecture_patterns``.
    """
    import asyncio

    return asyncio.run(_analyze_code_async(file_contents, ai_provider))
