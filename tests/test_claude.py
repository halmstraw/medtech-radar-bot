"""
tests/test_claude.py

Tests for the Claude API integration.

Two modes:
  - Unit tests (no API key needed): test JSON parsing logic with mocked responses
  - Integration test (API key needed): test actual Claude API call

Run unit tests only:
    pytest tests/test_claude.py -v -m "not integration"

Run integration test (requires ANTHROPIC_API_KEY):
    pytest tests/test_claude.py -v -m integration
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "function"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_claude_response(text_content: str) -> dict:
    """Reproduce the JSON extraction logic from claude.py so we can test it."""
    start = text_content.find("{")
    end = text_content.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")
    clean = text_content[start:end]
    return json.loads(clean)


VALID_QUADRANTS = {"tools", "platforms", "languages-frameworks", "techniques"}
VALID_RINGS = {"adopt", "trial", "assess", "hold"}

EXPECTED_KEYS = {"title", "quadrant", "ring", "tags", "reasoning", "description", "entry_markdown"}


def assert_valid_recommendation(result: dict):
    """Assert that a recommendation dict has the expected structure."""
    missing = EXPECTED_KEYS - result.keys()
    assert not missing, f"Missing keys: {missing}"
    assert result["quadrant"] in VALID_QUADRANTS, f"Invalid quadrant: {result['quadrant']}"
    assert result["ring"] in VALID_RINGS, f"Invalid ring: {result['ring']}"
    assert isinstance(result["tags"], list), "tags must be a list"
    assert len(result["tags"]) > 0, "tags must not be empty"
    assert isinstance(result["title"], str) and result["title"], "title must be non-empty string"
    assert isinstance(result["reasoning"], str) and result["reasoning"], "reasoning must be non-empty"
    assert isinstance(result["description"], str) and result["description"], "description must be non-empty"
    assert "---" in result["entry_markdown"], "entry_markdown must contain frontmatter"


# ---------------------------------------------------------------------------
# Unit tests — JSON parsing (no API key needed)
# ---------------------------------------------------------------------------

class TestJsonParsing:
    """Test the JSON extraction logic against various Claude response shapes."""

    def test_clean_json(self):
        raw = '{"title": "Temporal", "quadrant": "platforms", "ring": "assess", "tags": ["infrastructure"], "reasoning": "r", "description": "d", "entry_markdown": "---\\ntitle: \\"Temporal\\"\\n---\\n\\nd"}'
        result = parse_claude_response(raw)
        assert result["title"] == "Temporal"

    def test_leading_newline(self):
        """Claude often returns a newline before the JSON object."""
        raw = '\n{"title": "Temporal", "quadrant": "platforms", "ring": "assess", "tags": ["infrastructure"], "reasoning": "r", "description": "d", "entry_markdown": "---"}'
        result = parse_claude_response(raw)
        assert result["title"] == "Temporal"

    def test_leading_whitespace(self):
        raw = '   \n\n  {"title": "Temporal", "quadrant": "platforms", "ring": "assess", "tags": ["infrastructure"], "reasoning": "r", "description": "d", "entry_markdown": "---"}'
        result = parse_claude_response(raw)
        assert result["title"] == "Temporal"

    def test_markdown_fences(self):
        raw = '```json\n{"title": "Temporal", "quadrant": "platforms", "ring": "assess", "tags": ["infrastructure"], "reasoning": "r", "description": "d", "entry_markdown": "---"}\n```'
        result = parse_claude_response(raw)
        assert result["title"] == "Temporal"

    def test_preamble_text(self):
        raw = 'Here is my recommendation:\n\n{"title": "Temporal", "quadrant": "platforms", "ring": "assess", "tags": ["infrastructure"], "reasoning": "r", "description": "d", "entry_markdown": "---"}'
        result = parse_claude_response(raw)
        assert result["title"] == "Temporal"

    def test_trailing_text(self):
        raw = '{"title": "Temporal", "quadrant": "platforms", "ring": "assess", "tags": ["infrastructure"], "reasoning": "r", "description": "d", "entry_markdown": "---"}\n\nLet me know if you want changes.'
        result = parse_claude_response(raw)
        assert result["title"] == "Temporal"

    def test_no_json_raises(self):
        with pytest.raises(ValueError, match="No JSON object found"):
            parse_claude_response("I cannot recommend this technology.")

    def test_invalid_json_raises(self):
        """Truncated JSON with a closing brace should raise JSONDecodeError."""
        with pytest.raises(json.JSONDecodeError):
            parse_claude_response('{"title": "broken", }')  # malformed but has braces

    def test_assistant_prefill_response(self):
        """Simulate the assistant prefill pattern — response starts mid-object."""
        prefill = "{"
        continuation = '"title": "Temporal", "quadrant": "platforms", "ring": "assess", "tags": ["infrastructure"], "reasoning": "r", "description": "d", "entry_markdown": "---"}'
        full = prefill + continuation
        result = parse_claude_response(full)
        assert result["title"] == "Temporal"


# ---------------------------------------------------------------------------
# Integration test — real Claude API call
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestClaudeIntegration:
    """
    Real API call to Claude. Requires ANTHROPIC_API_KEY environment variable.

    Run with:
        ANTHROPIC_API_KEY=sk-ant-... pytest tests/test_claude.py -v -m integration
    """

    def test_recommendation_structure(self):
        """Claude returns a valid recommendation for a known technology."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        from radar_bot.claude import research_and_recommend

        result = research_and_recommend(
            suggestion="Temporal workflow orchestration engine",
            radar_context="Existing tools include GitHub Actions, MLflow, TestRail.",
        )

        print(f"\nClaude returned: {json.dumps(result, indent=2)}")
        assert_valid_recommendation(result)

    def test_recommendation_for_known_tool(self):
        """Claude correctly identifies an already-adopted tool."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        from radar_bot.claude import research_and_recommend

        result = research_and_recommend(
            suggestion="GitHub Actions for CI/CD pipelines",
            radar_context="No existing entries.",
        )

        print(f"\nClaude returned: {json.dumps(result, indent=2)}")
        assert_valid_recommendation(result)
        assert result["quadrant"] == "tools"
