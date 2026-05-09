## Core environment

- Python 3.11+
- `requests`
- `beautifulsoup4`
- `pypdf`
- `pillow`
- `pytesseract`

## System dependency

- `tesseract`
  - Needed for OCR when extracting text from screenshots or embedded document images.
  - On macOS, install with Homebrew: `brew install tesseract`

## What each one is for

- `requests`
  - Fetching simple web pages or downloads when direct browser access is not practical.
- `beautifulsoup4`
  - Extracting readable text from saved HTML or lightly structured pages.
- `pypdf`
  - Extracting text from saved PDF sources.
- `pillow`
  - Basic image handling before OCR.
- `pytesseract`
  - Running OCR from Python against screenshots and document images.

## Deliberate non-requirements

Avoid adding large frameworks or extra dependencies unless the task clearly needs them. In most cases, this repo should stay lean and rely on:

- built-in Markdown editing,
- shell tools,
- the minimal Python stack above,
- and direct source reading whenever possible.

## Practical rule

If a task can be done cleanly without installing anything new, do that. If installation is needed, prefer the smallest widely used library that fits the repo's research-and-writing workflow.
