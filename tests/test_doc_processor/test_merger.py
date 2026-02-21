"""Tests for services/doc-processor/merger.py"""

import pytest


# We import directly since merger.py has no external dependencies beyond stdlib.
from services_doc_processor.merger import merge_content, _wrap_section


# ---------------------------------------------------------------------------
# _wrap_section helper
# ---------------------------------------------------------------------------


class TestWrapSection:
    def test_wraps_content_with_markers(self):
        result = _wrap_section("overview", "<p>Hello</p>")
        assert '<!-- AUTO-DOC:START section="overview" -->' in result
        assert "<p>Hello</p>" in result
        assert "<!-- AUTO-DOC:END -->" in result

    def test_section_name_in_start_marker(self):
        result = _wrap_section("api_ref", "content")
        assert 'section="api_ref"' in result


# ---------------------------------------------------------------------------
# merge_content - no existing content
# ---------------------------------------------------------------------------


class TestMergeNoExistingContent:
    """When existing_html is empty/blank, new sections are simply concatenated."""

    def test_empty_string(self):
        result = merge_content("", {"overview": "<p>Overview</p>"})
        assert '<!-- AUTO-DOC:START section="overview" -->' in result
        assert "<p>Overview</p>" in result
        assert "<!-- AUTO-DOC:END -->" in result

    def test_none_like_empty(self):
        # Passing only whitespace should behave like empty
        result = merge_content("   ", {"s1": "content1"})
        assert 'section="s1"' in result

    def test_multiple_sections_no_existing(self):
        sections = {"overview": "<p>OV</p>", "api": "<p>API</p>"}
        result = merge_content("", sections)
        assert 'section="overview"' in result
        assert 'section="api"' in result
        # Sections separated by double newline
        assert "\n\n" in result


# ---------------------------------------------------------------------------
# merge_content - replacing existing AUTO-DOC sections
# ---------------------------------------------------------------------------


class TestMergeReplaceExisting:
    """Existing AUTO-DOC markers should have their content replaced."""

    def test_replace_single_section(self):
        existing = (
            '<h1>My Page</h1>\n'
            '<!-- AUTO-DOC:START section="overview" -->\n'
            '<p>Old overview</p>\n'
            '<!-- AUTO-DOC:END -->\n'
            '<p>Human-written note</p>'
        )
        result = merge_content(existing, {"overview": "<p>New overview</p>"})

        assert "<p>New overview</p>" in result
        assert "<p>Old overview</p>" not in result
        # Human content preserved
        assert "<h1>My Page</h1>" in result
        assert "<p>Human-written note</p>" in result

    def test_human_content_outside_markers_untouched(self):
        existing = (
            '<p>Before</p>\n'
            '<!-- AUTO-DOC:START section="s1" -->\n'
            'OLD\n'
            '<!-- AUTO-DOC:END -->\n'
            '<p>After</p>'
        )
        result = merge_content(existing, {"s1": "NEW"})
        assert "<p>Before</p>" in result
        assert "<p>After</p>" in result
        assert "NEW" in result
        assert "OLD" not in result


# ---------------------------------------------------------------------------
# merge_content - multiple sections
# ---------------------------------------------------------------------------


class TestMergeMultipleSections:
    def test_replace_two_existing_sections(self):
        existing = (
            '<!-- AUTO-DOC:START section="a" -->\nold-a\n<!-- AUTO-DOC:END -->\n'
            'HUMAN\n'
            '<!-- AUTO-DOC:START section="b" -->\nold-b\n<!-- AUTO-DOC:END -->'
        )
        result = merge_content(existing, {"a": "new-a", "b": "new-b"})
        assert "new-a" in result
        assert "new-b" in result
        assert "old-a" not in result
        assert "old-b" not in result
        assert "HUMAN" in result

    def test_append_new_section_when_not_in_existing(self):
        existing = (
            '<!-- AUTO-DOC:START section="a" -->\ncontent-a\n<!-- AUTO-DOC:END -->'
        )
        result = merge_content(existing, {"a": "updated-a", "b": "brand-new-b"})
        assert "updated-a" in result
        assert 'section="b"' in result
        assert "brand-new-b" in result

    def test_section_in_existing_but_not_in_new_stays(self):
        existing = (
            '<!-- AUTO-DOC:START section="keep" -->\nkeep-content\n<!-- AUTO-DOC:END -->'
        )
        # We pass a different section; the existing one should remain.
        result = merge_content(existing, {"other": "other-content"})
        assert "keep-content" in result
        assert 'section="other"' in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestMergeEdgeCases:
    def test_empty_new_sections_returns_existing(self):
        existing = "<p>Hello</p>"
        result = merge_content(existing, {})
        assert result == existing

    def test_malformed_start_marker_no_end(self):
        """If the end marker is missing, the section is not replaced but new
        content is appended."""
        existing = '<!-- AUTO-DOC:START section="broken" -->\nno end marker here'
        result = merge_content(existing, {"broken": "fixed"})
        # Because end marker is missing, the replacement cannot happen.
        # The section should be appended instead.
        assert "no end marker here" in result
        # The new content should still appear (appended)
        assert "fixed" in result

    def test_empty_section_content(self):
        result = merge_content("", {"empty": ""})
        assert 'section="empty"' in result
        # Even empty content gets markers
        assert "<!-- AUTO-DOC:END -->" in result
