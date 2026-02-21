"""Smart-merge engine that preserves human-written content outside AUTO-DOC markers.

Markers follow the format:
    <!-- AUTO-DOC:START section="section_name" -->
    ... auto-generated content ...
    <!-- AUTO-DOC:END -->

Content outside markers is never modified.
"""

from __future__ import annotations

import re
from typing import Dict

_MARKER_START_RE = re.compile(
    r'<!-- AUTO-DOC:START section="(?P<section>[^"]+)" -->'
)
_MARKER_END = "<!-- AUTO-DOC:END -->"


def _wrap_section(section_name: str, html_content: str) -> str:
    """Wrap *html_content* with AUTO-DOC markers for *section_name*."""
    return (
        f'<!-- AUTO-DOC:START section="{section_name}" -->\n'
        f"{html_content}\n"
        f"{_MARKER_END}"
    )


def merge_content(existing_html: str, new_sections: Dict[str, str]) -> str:
    """Merge *new_sections* into *existing_html* preserving human-written content.

    Parameters
    ----------
    existing_html:
        The current page body (may be empty or contain AUTO-DOC markers).
    new_sections:
        Mapping of ``section_name`` to HTML content.  Each entry will be
        placed inside matching AUTO-DOC markers.

    Returns
    -------
    str
        The merged HTML with updated auto-generated sections and all
        human-written content intact.
    """
    if not existing_html or not existing_html.strip():
        # No existing content -- just concatenate wrapped sections.
        parts = [
            _wrap_section(name, content)
            for name, content in new_sections.items()
        ]
        return "\n\n".join(parts)

    result = existing_html
    replaced_sections: set[str] = set()

    # Replace content inside existing markers.
    for match in _MARKER_START_RE.finditer(existing_html):
        section_name = match.group("section")
        if section_name not in new_sections:
            continue

        start_tag = match.group(0)
        start_idx = result.find(start_tag)
        if start_idx == -1:
            continue

        end_idx = result.find(_MARKER_END, start_idx + len(start_tag))
        if end_idx == -1:
            continue

        before = result[:start_idx]
        after = result[end_idx + len(_MARKER_END):]
        replacement = _wrap_section(section_name, new_sections[section_name])
        result = before + replacement + after
        replaced_sections.add(section_name)

    # Append sections that had no existing markers.
    new_parts: list[str] = []
    for name, content in new_sections.items():
        if name not in replaced_sections:
            new_parts.append(_wrap_section(name, content))

    if new_parts:
        result = result.rstrip() + "\n\n" + "\n\n".join(new_parts)

    return result
