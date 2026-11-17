# 📄 PDF AI Summarizer

A Streamlit app that summarizes PDF documents with **Google Gemini** through **LangChain**. Upload a PDF, choose a summary style, and get a final summary plus optional structure analysis and key quotes.

> Built from the architecture of [niti007/pdfsummarizer-gemini](https://github.com/niti007/pdfsummarizer-gemini), with verified model defaults, environment validation, and unit tests.

## Features

- Extracts and cleans PDF text, then splits it into token-limited chunks (map/reduce).
- Four summary styles: `brief`, `detailed`, `bullet_points`, `executive`.
- Optional document-structure analysis and verbatim key-quote extraction.
- Per-chunk statistics, TXT report export, and CSV statistics export.
- Results survive Streamlit reruns (download clicks do not clear them).
- `validate_setup.py` checks the API key, working model, and Git tooling before you start.

## Setup (Windows)

Requires Python 3.10+ (tested with 3.12).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt   # only for running tests
copy .env.example .env
```

Edit `.env` and set `GEMINI_API_KEY` to a key from <https://aistudio.google.com/apikey>.
`GEMINI_MODEL` defaults to `gemini-3.5-flash-lite`, which was verified against a live key.

Validate everything with:

```powershell
.\.venv\Scripts\python.exe validate_setup.py
```

## Run

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Open the URL Streamlit prints (usually <http://localhost:8501>).

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Project structure

```text
app.py             Streamlit UI (settings, upload, results, downloads)
pdf_processor.py   PDF extraction, cleaning, token counting, chunking
summarizer.py      Gemini/LangChain chains (chunk, combine, analysis, quotes)
prompts.py         ChatPromptTemplates and summary styles
utils.py           Display, export, statistics and key checks
config.py          Environment/config defaults (no secrets in code)
validate_setup.py  Phase 0 verification script
tests/             Unit tests for processor, prompts and summarizer
.env.example       Environment template
```

## How it works

```text
PDF → extract text → clean → chunk by tokens
                                  │
                  ┌───────────────┼───────────────┐
                  ▼               ▼               ▼
             summary 1       summary 2   ...   summary N      (map)
                  └───────────────┼───────────────┘
                                  ▼
                        combine → final summary                (reduce)
```

## Troubleshooting

- **No extractable text**: the PDF is likely scanned images. Run OCR first.
- **429 / rate limits**: wait and retry, use a shorter document, or pick another model in the sidebar.
- **404 / model unavailable**: change `GEMINI_MODEL` in `.env` or choose another model in the sidebar.
- **API key errors**: confirm `.env` sits next to `app.py` and restart after editing it.

## Repository

https://github.com/sohils2/pdfsummarizer-gemini
