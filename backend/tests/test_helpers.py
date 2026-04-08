"""Tests for pipeline helper functions (e.g. _strip_fences)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.pipeline import _strip_fences


# ---------------------------------------------------------------------------
# _strip_fences: ```html fences
# ---------------------------------------------------------------------------


class TestStripFencesHtml:
    def test_html_fence_basic(self):
        text = "```html\n<div>hello</div>\n```"
        assert _strip_fences(text) == "<div>hello</div>"

    def test_html_fence_multiline(self):
        text = "```html\n<html>\n<body>\n<h1>Hi</h1>\n</body>\n</html>\n```"
        result = _strip_fences(text)
        assert "<html>" in result
        assert "<h1>Hi</h1>" in result
        assert "```" not in result

    def test_html_fence_with_preamble(self):
        text = "Here is the code:\n\n```html\n<div>content</div>\n```"
        assert _strip_fences(text) == "<div>content</div>"

    def test_html_fence_with_long_preamble(self):
        text = (
            "Sure! I'll build that for you.\n"
            "Here is the complete HTML:\n\n"
            "```html\n<p>result</p>\n```"
        )
        assert _strip_fences(text) == "<p>result</p>"


# ---------------------------------------------------------------------------
# _strip_fences: ```json fences
# ---------------------------------------------------------------------------


class TestStripFencesJson:
    def test_json_fence(self):
        # _strip_fences only has explicit handling for ```html fences.
        # For ```json, the generic fence path picks it up but includes the language tag.
        text = '```json\n{"key": "value"}\n```'
        result = _strip_fences(text)
        assert '{"key": "value"}' in result
        assert "```" not in result

    def test_json_fence_with_preamble(self):
        text = 'Here is the JSON:\n```json\n{"a": 1}\n```'
        result = _strip_fences(text)
        assert '"a": 1' in result
        assert "```" not in result


# ---------------------------------------------------------------------------
# _strip_fences: generic ``` fences
# ---------------------------------------------------------------------------


class TestStripFencesGeneric:
    def test_generic_fence(self):
        text = "```\nsome code\n```"
        assert _strip_fences(text) == "some code"

    def test_generic_fence_with_preamble(self):
        text = "Output:\n```\nresult here\n```"
        assert _strip_fences(text) == "result here"


# ---------------------------------------------------------------------------
# _strip_fences: no fences / edge cases
# ---------------------------------------------------------------------------


class TestStripFencesEdgeCases:
    def test_no_fences(self):
        text = "<div>just plain html</div>"
        assert _strip_fences(text) == "<div>just plain html</div>"

    def test_empty_string(self):
        assert _strip_fences("") == ""

    def test_whitespace_only(self):
        assert _strip_fences("   \n  ") == ""

    def test_just_triple_backtick(self):
        result = _strip_fences("```")
        # After the opening ```, there's nothing, so empty or minimal
        assert "```" not in result or result == ""

    def test_unclosed_fence_html(self):
        text = "```html\n<div>no closing fence"
        result = _strip_fences(text)
        assert "<div>no closing fence" in result
        assert "```" not in result

    def test_unclosed_fence_generic(self):
        text = "```\nno closing fence"
        result = _strip_fences(text)
        assert "no closing fence" in result

    def test_fence_with_extra_whitespace(self):
        text = "  ```html\n  <p>padded</p>\n  ```  "
        result = _strip_fences(text)
        assert "<p>padded</p>" in result

    def test_preserves_inner_backticks(self):
        """Fenced code that contains inline backticks should keep them."""
        text = "```html\n<code>`inline`</code>\n```"
        result = _strip_fences(text)
        assert "`inline`" in result
