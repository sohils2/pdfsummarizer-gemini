from __future__ import annotations

from summarizer import PDFSummarizer


class FakeChain:
    """Minimal stand-in for an LCEL chain; no network access."""

    def __init__(self, result="ok", batch_results=None, error=None):
        self.result = result
        self.batch_results = batch_results
        self.error = error

    def invoke(self, inputs):
        if self.error:
            raise self.error
        return self.result

    def batch(self, inputs, config=None, return_exceptions=False):
        if self.batch_results is not None:
            return list(self.batch_results)
        return [self.result for _ in inputs]


def make_summarizer(chunk=None, combine=None, analysis=None, quotes=None) -> PDFSummarizer:
    """Create an instance without the real Gemini client."""
    instance = object.__new__(PDFSummarizer)
    instance.chunk_chain = chunk or FakeChain("chunk summary")
    instance.combine_chain = combine or FakeChain("combined summary")
    instance.analysis_chain = analysis or FakeChain("analysis text")
    instance.quotes_chain = quotes or FakeChain("quote one\nquote two")
    return instance


def test_summarize_chunks_marks_failures_and_combines() -> None:
    summarizer = make_summarizer(
        chunk=FakeChain(batch_results=["summary one", RuntimeError("429 rate limit"), "summary three"]),
        combine=FakeChain("final summary"),
    )

    data = summarizer.summarize_chunks(["a" * 100, "b" * 100, "c" * 100], "brief")

    assert data["total_chunks"] == 3
    assert data["summary_type"] == "brief"
    assert data["combined_summary"] == "final summary"
    assert [item["ok"] for item in data["individual_summaries"]] == [True, False, True]
    assert "429 rate limit" in data["individual_summaries"][1]["summary"]
    assert data["individual_summaries"][1]["summary_length"] == 0


def test_combine_summaries_handles_empty_single_and_failure() -> None:
    summarizer = make_summarizer(combine=FakeChain("merged"))
    good = [{"summary": "one", "ok": True}, {"summary": "two", "ok": True}]

    assert summarizer.combine_summaries([], "detailed") == "No valid summaries were generated."
    assert summarizer.combine_summaries(good[:1], "detailed") == "one"
    assert summarizer.combine_summaries(good, "detailed") == "merged"

    failing = make_summarizer(combine=FakeChain(error=RuntimeError("boom")))
    fallback = failing.combine_summaries(good, "detailed")
    assert fallback.startswith("Combined Summary:")
    assert "Section 1: one" in fallback


def test_analyze_document_structure_reports_errors() -> None:
    assert make_summarizer().analyze_document_structure("text") == {
        "analysis": "analysis text",
        "status": "success",
    }
    failing = make_summarizer(analysis=FakeChain(error=ValueError("bad input")))
    result = failing.analyze_document_structure("text")
    assert result["status"] == "error"
    assert "bad input" in result["analysis"]


def test_extract_key_quotes_cleans_and_limits() -> None:
    response = "1. \"First quote\"\n- Second quote\n• Third quote\n\n" + "\n".join(
        f"{index}. Quote {index}" for index in range(4, 12)
    )
    summarizer = make_summarizer(quotes=FakeChain(response))

    quotes = summarizer.extract_key_quotes("some text")

    assert quotes[:3] == ["First quote", "Second quote", "Third quote"]
    assert len(quotes) == 10
    assert all(not quote.startswith(("1.", "-", "•", '"')) for quote in quotes)
