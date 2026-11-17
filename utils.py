"""Presentation, export, statistics and key-validation helpers."""

from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from config import api_key_is_present


def format_summary_display(summary_data: dict) -> None:
    """Render statistics, the final summary and the per-chunk summaries."""
    st.subheader("📊 Summary Statistics")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Chunks", summary_data["total_chunks"])
    col2.metric("Successful Summaries", sum(item["ok"] for item in summary_data["individual_summaries"]))
    col3.metric("Summary Type", summary_data["summary_type"].replace("_", " ").title())

    st.subheader("📝 Final Summary")
    st.write(summary_data["combined_summary"])

    with st.expander("View Individual Chunk Summaries"):
        for item in summary_data["individual_summaries"]:
            st.write(f"**Chunk {item['chunk_number']}**" + ("" if item["ok"] else " ⚠ failed"))
            st.write(item["summary"])
            st.write(
                f"*Original length: {item['original_length']} chars, "
                f"Summary length: {item['summary_length']} chars*"
            )
            st.divider()


def export_summary_to_text(summary_data: dict, filename: str = "") -> str:
    """Build the plain-text report; ``filename`` appears in the header."""
    lines = ["PDF Summary Report", "==================", ""]
    if filename:
        lines.append(f"File: {filename}")
    lines += [
        f"Summary Type: {summary_data['summary_type'].replace('_', ' ').title()}",
        f"Total Chunks Processed: {summary_data['total_chunks']}",
        f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "FINAL SUMMARY",
        "=============",
        "",
        summary_data["combined_summary"],
        "",
        "INDIVIDUAL CHUNK SUMMARIES",
        "==========================",
        "",
    ]
    for item in summary_data["individual_summaries"]:
        suffix = "" if item["ok"] else " (FAILED)"
        lines += [f"Chunk {item['chunk_number']}{suffix}:", item["summary"], ""]
    return "\n".join(lines)


def create_summary_dataframe(summary_data: dict) -> pd.DataFrame:
    """One row per chunk with lengths, compression ratio and status."""
    return pd.DataFrame(
        [
            {
                "Chunk": item["chunk_number"],
                "Original Length": item["original_length"],
                "Summary Length": item["summary_length"],
                "Compression Ratio": (
                    round(item["summary_length"] / item["original_length"], 2)
                    if item["original_length"]
                    else 0
                ),
                "Status": "Success" if item["ok"] else "Error",
            }
            for item in summary_data["individual_summaries"]
        ]
    )


def estimate_processing_time(num_chunks: int) -> str:
    """Rough estimate: ~3s per chunk, four in flight, plus ~5s to combine."""
    seconds = int(num_chunks * 3 / 4 + 5)
    return f"~{seconds} seconds" if seconds < 60 else f"~{seconds // 60} min {seconds % 60}s"


def validate_api_key() -> bool:
    """Check the key is present before any LLM call and show it in the sidebar."""
    if not api_key_is_present():
        st.error("❌ GEMINI_API_KEY not found or incomplete. Copy `.env.example` to `.env`, add your key, and restart.")
        st.info("Get a free key at https://aistudio.google.com/apikey")
        return False
    st.sidebar.caption("🔑 Gemini API key loaded")
    return True
