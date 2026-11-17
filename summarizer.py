"""LangChain chains that call Gemini for summaries, analysis and quotes."""

from __future__ import annotations

import re

from langchain_core.runnables import RunnableLambda
from langchain_google_genai import ChatGoogleGenerativeAI

from config import get_api_key, get_model
from prompts import ANALYSIS, CHUNK_SUMMARY, COMBINE, QUOTES, STYLES


class PDFSummarizer:
    """Thin wrapper around four LCEL chains: chunk, combine, analysis, quotes."""

    def __init__(self, model: str | None = None) -> None:
        api_key = get_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is missing. Copy .env.example to .env and set it.")

        self.model = model or get_model()
        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            google_api_key=api_key,
        )
        # Gemini responses can expose .text as a list of blocks; str() flattens it.
        parser = RunnableLambda(lambda message: str(message.text))
        self.chunk_chain = CHUNK_SUMMARY | self.llm | parser
        self.combine_chain = COMBINE | self.llm | parser
        self.analysis_chain = ANALYSIS | self.llm | parser
        self.quotes_chain = QUOTES | self.llm | parser

    @staticmethod
    def _style(summary_type: str) -> str:
        return STYLES.get(summary_type, STYLES["detailed"])

    def summarize_text(self, text: str, summary_type: str = "detailed") -> str:
        """Summarize a single piece of text (useful for small documents)."""
        return self.chunk_chain.invoke({"style": self._style(summary_type), "text": text})

    def summarize_chunks(self, chunks: list[str], summary_type: str = "detailed") -> dict:
        """Summarize chunks concurrently, then reduce them into one summary."""
        style = self._style(summary_type)
        inputs = [{"style": style, "text": chunk} for chunk in chunks]
        results = self.chunk_chain.batch(
            inputs,
            config={"max_concurrency": 4},
            return_exceptions=True,
        )

        summaries: list[dict] = []
        for index, (chunk, result) in enumerate(zip(chunks, results), start=1):
            ok = not isinstance(result, Exception)
            summary = result if ok else f"Error processing chunk: {result}"
            summaries.append(
                {
                    "chunk_number": index,
                    "summary": summary,
                    "ok": ok,
                    "original_length": len(chunk),
                    "summary_length": len(summary) if ok else 0,
                }
            )

        return {
            "individual_summaries": summaries,
            "combined_summary": self.combine_summaries(summaries, summary_type),
            "total_chunks": len(chunks),
            "summary_type": summary_type,
        }

    def combine_summaries(self, chunk_summaries: list[dict], summary_type: str) -> str:
        """Merge successful chunk summaries; degrade gracefully on failure."""
        valid = [item["summary"] for item in chunk_summaries if item.get("ok")]
        if not valid:
            return "No valid summaries were generated."
        if len(valid) == 1:
            return valid[0]

        sections = "\n\n".join(
            f"Section {index}: {summary}" for index, summary in enumerate(valid, start=1)
        )
        try:
            return self.combine_chain.invoke(
                {"style": self._style(summary_type), "summaries": sections}
            )
        except Exception:  # noqa: BLE001 - keep the section summaries instead of failing
            return f"Combined Summary:\n\n{sections}"

    def analyze_document_structure(self, text: str) -> dict:
        """Return a status-tagged structure analysis of the first 3000 chars."""
        try:
            analysis = self.analysis_chain.invoke({"text": text[:3000]})
            return {"analysis": analysis, "status": "success"}
        except Exception as exc:  # noqa: BLE001
            return {"analysis": f"Error analyzing document: {exc}", "status": "error"}

    def extract_key_quotes(self, text: str) -> list[str]:
        """Return up to ten cleaned quotes from the supplied text."""
        response = self.quotes_chain.invoke({"text": text})
        lines = (
            re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", line).strip(' \t"“”')
            for line in response.splitlines()
        )
        return [line for line in lines if line][:10]
