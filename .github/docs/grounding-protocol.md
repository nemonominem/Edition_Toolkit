# Grounding Protocol

**Grounding** means asking an external LLM (e.g. Monica, Perplexity, Gemini Deep Research) to retrieve or verify online information that GitHub Copilot cannot access directly — recent documents, live sources, historical details requiring web search, etc.

When you (GitHub Copilot) identify a knowledge gap — something that is unclear, thinly sourced, or where additional documentary evidence would strengthen the article — you should proactively flag it and produce a grounding request using the template below.

---

## When to trigger a grounding request

- A claim in the article relies on a source you cannot verify or retrieve
- A historical analogy, actor relationship, or timeline event would benefit from richer documentation
- You suspect a key document, article, or dataset exists but is not in `sources/`
- A factual detail is plausible but not pinned to a specific source
- A section feels thin and you can articulate what evidence would strengthen it

Do not ask for grounding on things already covered by files in `sources/external_original/`, `sources/external_processed/`, or `sources/_grounding/` (already-answered requests).

---

## Grounding request template

When triggering a grounding request, write the request to the file
`sources/_grounding/grounding_YYYY-MM-DD_SLUG.md`
(where SLUG is a short 2–4 word descriptor, e.g. `who-tors-negotiation`, `daszak-lancet-letter`).

The file must follow this structure:

---

```markdown
# Grounding request: [short title]

---
**Answered by:** [Model name — e.g. Monica / Perplexity / Gemini]  
**Date:** [YYYY-MM-DD]  
**Interface / user:** [e.g. Monica web, Perplexity Pro, gillesdemaneuf@…]

---

**Context** (2–4 sentences explaining the gap and why it matters for the article):

[Explain what aspect of the article this supports, what is unclear, and what evidence would help.]

---

## Questions

1. [Specific factual question]

   > **Answer:** *(fill in here — do not repeat the question)*

2. [Specific factual question]

   > **Answer:** *(fill in here)*

3. [Specific factual question]

   > **Answer:** *(fill in here)*

*(add as many Q/Answer blocks as needed — prefer focused, answerable questions over vague ones)*

---

**Open question (always include this last):**  
Given what I am looking for above, what should I have also asked you? Please answer your additional questions.

   > **Answer:** *(fill in here)*

---

## Source guidelines (for the answering LLM)

- Answer directly under each question. Do not repeat or restate the question.
- For each factual claim, provide at least one working, clickable link to a primary or authoritative source (official document, peer-reviewed article, congressional record, credible news outlet with a dateline).
- Prefer primary sources (official WHO documents, FOIA releases, original papers, government reports) over secondary commentary.
- If a source is paywalled, provide the DOI or persistent identifier.
- For each link, include: title, author/organisation, publication date, and URL.
- Do not fabricate links. If you are uncertain whether a URL is live, say so explicitly.
```

---

## After receiving a grounding response

1. The answering LLM fills its answers **directly into the grounding file** under each question — no separate response file.
2. Save the completed file back to `sources/_grounding/` (same filename).
3. Extract any useful PDFs or documents linked in the response and place them in the appropriate `sources/external_original/<category>/` subfolder (or `sources/_import/` if they need processing first), then run extraction.
4. After processing files from `sources/_import/`, **move** them to `sources/external_original/<category>/` (do not copy). `sources/_import/` is a temporary staging area only.
5. Reference the grounding file in the article or notes as appropriate.
6. Do **not** incorporate claims from the grounding response into the article without verifying the links are live and the sources are genuine.
