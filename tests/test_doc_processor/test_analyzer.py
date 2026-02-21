"""Tests for services/doc-processor/analyzer.py"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from common.ai.provider import AIResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ANALYSIS = {
    "summary": "A utility library for string manipulation.",
    "functions": [
        {
            "name": "capitalize_words",
            "file": "utils.py",
            "signature": "def capitalize_words(text: str) -> str",
            "description": "Capitalizes each word.",
            "params": [{"name": "text", "type": "str", "description": "Input text"}],
            "returns": "Capitalized string.",
        }
    ],
    "classes": [],
    "api_endpoints": [],
    "dependencies": [{"name": "re", "purpose": "Regular expression support"}],
    "architecture_patterns": ["Utility module pattern"],
}


def _make_ai_response(content: str) -> AIResponse:
    return AIResponse(content=content, model="test-model", input_tokens=100, output_tokens=200)


@pytest.fixture
def mock_ai_provider():
    provider = MagicMock()
    provider.generate = AsyncMock()
    return provider


@pytest.fixture
def sample_files():
    return {"utils.py": "def capitalize_words(text):\n    return text.title()\n"}


# ---------------------------------------------------------------------------
# Successful analysis
# ---------------------------------------------------------------------------


class TestAnalyzeCodeSuccess:
    """Test the happy-path for analyze_code."""

    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_PROMPT", "{file_contents}")
    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_SYSTEM", "system")
    def test_returns_parsed_json(self, mock_ai_provider, sample_files):
        from services_doc_processor.analyzer import analyze_code

        mock_ai_provider.generate.return_value = _make_ai_response(
            json.dumps(SAMPLE_ANALYSIS)
        )

        result = analyze_code(sample_files, mock_ai_provider)

        assert result["summary"] == SAMPLE_ANALYSIS["summary"]
        assert len(result["functions"]) == 1
        assert result["functions"][0]["name"] == "capitalize_words"
        mock_ai_provider.generate.assert_awaited_once()

    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_PROMPT", "{file_contents}")
    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_SYSTEM", "system")
    def test_provider_receives_formatted_files(self, mock_ai_provider, sample_files):
        from services_doc_processor.analyzer import analyze_code

        mock_ai_provider.generate.return_value = _make_ai_response(
            json.dumps(SAMPLE_ANALYSIS)
        )

        analyze_code(sample_files, mock_ai_provider)

        call_kwargs = mock_ai_provider.generate.call_args
        prompt_arg = call_kwargs.kwargs.get("prompt") or call_kwargs[1].get("prompt", call_kwargs[0][0] if call_kwargs[0] else "")
        # The formatted prompt should contain the file path marker
        assert "utils.py" in prompt_arg


# ---------------------------------------------------------------------------
# Markdown-fenced AI responses
# ---------------------------------------------------------------------------


class TestMarkdownFenceStripping:
    """The analyzer should strip accidental markdown code fences from AI output."""

    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_PROMPT", "{file_contents}")
    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_SYSTEM", "system")
    def test_strips_triple_backtick_json_fence(self, mock_ai_provider, sample_files):
        from services_doc_processor.analyzer import analyze_code

        fenced = "```json\n" + json.dumps(SAMPLE_ANALYSIS) + "\n```"
        mock_ai_provider.generate.return_value = _make_ai_response(fenced)

        result = analyze_code(sample_files, mock_ai_provider)
        assert result["summary"] == SAMPLE_ANALYSIS["summary"]

    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_PROMPT", "{file_contents}")
    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_SYSTEM", "system")
    def test_strips_plain_backtick_fence(self, mock_ai_provider, sample_files):
        from services_doc_processor.analyzer import analyze_code

        fenced = "```\n" + json.dumps(SAMPLE_ANALYSIS) + "\n```"
        mock_ai_provider.generate.return_value = _make_ai_response(fenced)

        result = analyze_code(sample_files, mock_ai_provider)
        assert "functions" in result


# ---------------------------------------------------------------------------
# JSON parsing errors
# ---------------------------------------------------------------------------


class TestAnalyzeCodeErrors:
    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_PROMPT", "{file_contents}")
    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_SYSTEM", "system")
    def test_invalid_json_raises(self, mock_ai_provider, sample_files):
        from services_doc_processor.analyzer import analyze_code

        mock_ai_provider.generate.return_value = _make_ai_response(
            "This is not JSON at all"
        )

        with pytest.raises(json.JSONDecodeError):
            analyze_code(sample_files, mock_ai_provider)

    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_PROMPT", "{file_contents}")
    @patch("services_doc_processor.analyzer.CODE_ANALYSIS_SYSTEM", "system")
    def test_empty_response_raises(self, mock_ai_provider, sample_files):
        from services_doc_processor.analyzer import analyze_code

        mock_ai_provider.generate.return_value = _make_ai_response("")

        with pytest.raises(json.JSONDecodeError):
            analyze_code(sample_files, mock_ai_provider)


# ---------------------------------------------------------------------------
# _format_file_contents helper
# ---------------------------------------------------------------------------


class TestFormatFileContents:
    def test_single_file(self):
        from services_doc_processor.analyzer import _format_file_contents

        result = _format_file_contents({"app.py": "print('hi')"})
        assert "=== app.py ===" in result
        assert "print('hi')" in result

    def test_multiple_files(self):
        from services_doc_processor.analyzer import _format_file_contents

        files = {"a.py": "aaa", "b.py": "bbb"}
        result = _format_file_contents(files)
        assert "=== a.py ===" in result
        assert "=== b.py ===" in result
        assert "aaa" in result
        assert "bbb" in result
