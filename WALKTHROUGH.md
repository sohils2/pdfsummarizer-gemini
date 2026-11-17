# Walkthrough

A guide to the code for trainers and students.

## 1. What the app does

It reads a PDF, cleans the text, splits long text into token-limited chunks, summarizes each chunk with Gemini, and merges the chunk summaries into one final summary. You can also request a short structure analysis and a list of verbatim quotes, then download a text report and a CSV of chunk statistics.

## 2. Where things are

| File | Responsibility |
|---|---|
| `app.py` | Streamlit UI: sidebar, upload, pipeline calls, results, downloads |
| `config.py` | Reads `.env`, supplies the verified default model and model list |
| `pdf_processor.py` | Metadata, extraction, cleaning, token counting, chunking |
| `prompts.py` | System message, four styles, four `ChatPromptTemplate`s |
| `summarizer.py` | Four LCEL chains and the map/reduce logic |
| `utils.py` | Display helpers, exports, statistics, key check |
| `validate_setup.py` | Phase 0 checks for key, model and tooling |
| `tests/` | Unit tests that do not call the Gemini API |

## 3. How a PDF flows through the app

1. **Upload.** `st.file_uploader` returns an uploaded file object.
2. **Metadata.** `PDFProcessor.get_pdf_metadata()` reads page count, title, author and subject with `pypdf`. No LLM call yet.
3. **Process.** Clicking "Process PDF" calls `process_pdf()`.
4. **Extract.** `extract_text_from_pdf()` reads every page; failed pages are skipped and logged.
5. **Clean.** `clean_text()` removes control characters and extra whitespace while keeping punctuation and paragraph breaks.
6. **Count.** `count_tokens()` uses `tiktoken`'s `cl100k_base` as an approximation of Gemini's tokenizer.
7. **Chunk.** `chunk_text()` splits on sentence endings (`.`, `!`, `?`) and hard-splits any sentence longer than the limit.
8. **Estimate.** `estimate_processing_time()` shows a rough duration.
9. **Analysis (optional).** The first 3000 characters are sent to the analysis chain.
10. **Summarize chunks.** `summarize_chunks()` runs the chunk chain in a batch with `max_concurrency=4`. Each result records an `ok` flag.
11. **Combine.** Failed chunks are dropped. One remaining summary is returned as-is; several are merged by the combine chain.
12. **Quotes (optional).** The first 5000 characters are sent to the quotes chain; list markers and quote marks are stripped from each line.
13. **Store.** Results go into `st.session_state.results` so download clicks do not wipe them.
14. **Display and export.** `display_results()` renders everything and offers TXT/CSV downloads.

## 4. Prompt templates

`prompts.py` has one shared `SYSTEM` message, a `STYLES` dict, and a `_template()` helper that builds each `ChatPromptTemplate`:

| Template | Inputs | Purpose |
|---|---|---|
| `CHUNK_SUMMARY` | `{style}`, `{text}` | Summarize one chunk |
| `COMBINE` | `{style}`, `{summaries}` | Merge the section summaries |
| `ANALYSIS` | `{text}` | Describe type, topics, sections, audience, purpose |
| `QUOTES` | `{text}` | Ask for 5–10 verbatim quotes, one per line |

Each chain in `summarizer.py` has the shape `prompt | llm | parser`, where the parser turns the Gemini message into plain text.

To add a style, add an entry to `STYLES` in `prompts.py` and add its name to the `selectbox` options in `app.py`.

## 5. Model choice

The reference repo defaulted to `gemini-3.1-flash-lite`. During Phase 0 that model returned a transient `503` for a minimal generation request, while `gemini-3.5-flash-lite` and `gemini-flash-lite-latest` both succeeded. `config.py` therefore uses `gemini-3.5-flash-lite` as the default and keeps the others as selectable fallbacks. Run `validate_setup.py` any time to re-check.

## 6. Common problems

- **Scanned PDF:** metadata shows but there is no text; run OCR first.
- **429 rate limit:** wait, shorten the document, or switch models.
- **404 / model unavailable:** change `GEMINI_MODEL` or pick another model in the sidebar.
- **Missing key:** check `.env` next to `app.py`, then restart Streamlit.
