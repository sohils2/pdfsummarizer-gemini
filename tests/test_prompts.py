from __future__ import annotations

from prompts import ANALYSIS, CHUNK_SUMMARY, COMBINE, QUOTES, STYLES


def test_all_styles_present() -> None:
    assert set(STYLES) == {"brief", "detailed", "bullet_points", "executive"}
    assert all(description.strip() for description in STYLES.values())


def test_template_input_variables() -> None:
    assert set(CHUNK_SUMMARY.input_variables) == {"style", "text"}
    assert set(COMBINE.input_variables) == {"style", "summaries"}
    assert ANALYSIS.input_variables == ["text"]
    assert QUOTES.input_variables == ["text"]


def test_system_persona_is_shared() -> None:
    for template in (CHUNK_SUMMARY, COMBINE, ANALYSIS, QUOTES):
        assert "precise document summarizer" in template.messages[0].prompt.template
