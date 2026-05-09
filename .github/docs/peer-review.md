# Peer-Review Protocol for WHO_Compromission.md

## Purpose

This document defines how to conduct a systematic peer-review pass of the article. It is not a checklist of things to polish; it is an adversarial audit designed to find genuine weaknesses before publication. The distinction matters: a polishing pass accepts the article's framing and cleans it up; a peer-review pass interrogates the framing and challenges it.

---

## Review dimensions

Seven dimensions, each with distinct method and tooling. They are not equally weighted — factual accuracy and argumentative integrity are the critical ones.

---

### 1. Factual accuracy

**What is checked:**
- Direct quotes match their source files in the repository (word-for-word, not paraphrased as direct).
- Dates, names, institutional roles, and titles are correct at the time of the relevant event.
- Numerical claims (case counts, funding amounts, vote tallies, batch numbers, page references) are accurate.
- Claims about what a document says are verified against that document.
- URLs cited are live and point to the claimed content.

**Method:**
Systematic footnote-by-footnote audit. For each footnote: locate the source file in `sources/external_processed/` or `sources/external_original/`; verify the quoted passage; verify the attribution. Flag any quote or claim that cannot be cross-checked against a repo source file.

**Tool:** Current session (has direct access to repo source files).

**Output:** List of verified claims, plus any that could not be verified or that diverge from source.

---

### 2. Citation and source quality

**What is checked:**
- Primary sources are used where available (official documents, transcripts, contemporaneous reporting), not secondary summaries of them.
- Secondary sources are used appropriately — to characterise expert opinion or context, not as primary evidence for a factual claim.
- FOIA documents are attributed with sufficient specificity (production batch, line numbers, subpoena reference) to be traceable.
- Congressional testimony is attributed to transcript, not press summary.
- Where the article cites the author's own Medium articles as sources, those are used for context/reconstruction rather than as independent corroboration.

**Method:** Pass through the references section and footnotes with the above criteria. Flag any footnote that uses a secondary source for a primary-evidence claim, or where the source quality does not support the weight the article places on it.

**Tool:** Current session.

---

### 3. Argumentative integrity

**What is checked:**
- Every causal claim is supported by the evidence cited for it, not by evidence for a related but distinct claim.
- The article's four epistemic levels (documented fact → reasonable inference → informed speculation → acknowledged uncertainty) are applied consistently. The article should not present inference as fact.
- Claims of coordination or intent are grounded in documentary evidence, not inferred from outcome alone.
- The article does not use circular reasoning (e.g., treating the outcome as proof of the intent that caused it).
- Analogies (kowtow, proskynesis, tribute logic) are used to illuminate mechanism, not as a substitute for evidence.
- Forward references and structural claims in §1 are actually delivered in §2–§5.

**Method:** Adversarial read: for each major claim, ask "what is the minimum evidence needed to support this, and does the article actually cite it?" Identify claims that would require a defender of the critiqued parties to engage, and check whether the article's evidence would survive that engagement.

**Tool:** **Fresh Claude chat recommended.** A fresh context simulates a reader — and a skeptical one — without editorial capture from the drafting process. Load the article cold and ask it to identify unsupported causal leaps, circular claims, and places where analogy is doing work that evidence should be doing.

---

### 4. Fairness and balance

**What is checked:**
- Are the actors characterised fairly relative to what the documented record shows?
- Does the article distinguish between actors who knowingly acted badly and those who may have been misled, mistaken, or institutionally constrained?
- Does the article attribute malice where incompetence or institutional incentive would be a sufficient explanation?
- Is the counternarrative (natural origin, good-faith WHO engagement, genuine scientific consensus on zoonosis) given accurate representation rather than a straw-man version?
- Does the article acknowledge the genuine scientific uncertainty about origins, or does it imply a settled conclusion that the evidence does not warrant?
- Are there cherry-picked facts — true in isolation, but misleading given what was omitted?

**Method:** Read the article as a defence lawyer for each party named: WHO/Tedros, Farrar, Daszak, Fouchier/Koopmans, China. For each, ask: does the article's characterisation reflect the strongest version of their position, or a weakened one? Flag places where the article is harder on a party than its own evidence supports.

**Tool:** **Fresh Claude chat recommended**, or review by the author. This is the dimension where LLM editorial capture is most damaging — the drafting assistant has been building the argument and is poorly positioned to mount a genuine counter-case.

---

### 5. Tone and register

**What is checked:**
- Consistent with Demaneuf_Medium style throughout (not drifting into legal-brief mode, academic abstraction, or polemical register).
- No passages where the rhetoric outpaces the evidence — where the language is more accusatory than the facts warrant.
- Historical analogies are introduced with stated functional purpose, not used as rhetorical flourish.
- Stand-out quotes are followed by explanation of why they matter (per style guide: "after a strong quote, explain why it matters").
- No ritual throat-clearing, excessive hedging, or caveats that smother strong points.
- Section openings create questions rather than announcing conclusions.
- Closings deliver structural takeaways, not "more research needed."

**Method:** Read-through with the `writing_styles.md` Demaneuf_Medium section open. Flag passages that violate the style's specific anti-patterns.

**Tool:** Current session or fresh chat; either is adequate for style checking.

---

### 6. Readability and progression

**What is checked:**
- Does the argument build coherently for a well-educated reader who is not a specialist in either viriology or WHO governance?
- Is the section sequence logical — does each section set up what follows?
- Are technical terms (TOR, PHEIC, IHR, GoF, FCS, RBD, BSL) introduced before being used, or at least glossed in context?
- Are there sections that assume knowledge the article has not provided?
- Is pacing appropriate — are there stretches that are too dense, or sections that stall before making their point?
- Do the annexes add value without duplicating body content?

**Method:** Cold read as a first-time educated reader. Note anywhere a reader would need to pause because a term is undefined, a reference is unexplained, or the argumentative thread is unclear.

**Tool:** **Fresh Claude chat strongly recommended.** The current session has read every source file and has full context — it cannot simulate a cold reader. A fresh chat with only the article loaded will surface exactly the places where context assumed by the author is not visible to the reader.

---

### 7. Internal consistency

**What is checked:**
- Claims made in §1 (Introduction) are actually delivered and supported in the relevant body sections.
- No contradictions between sections (e.g., a date given differently in two places, an actor's role described inconsistently).
- The Access-Exchange Log (Annex 2) is consistent with body-text descriptions of the same episodes.
- The Actor Summary Table (Annex) characterises actors consistently with how they appear in body text.
- Footnotes do not contradict body-text claims.

**Method:** Targeted cross-check: for each structural claim in §1, locate its body-text delivery; for the annexes, compare entries against their body-text equivalents.

**Tool:** Current session.

---

## On using a fresh LLM context

**Recommendation:** Use a fresh Claude chat (new context, no session history) for dimensions 3, 4, 5, and 6 — the interpretive and argumentative dimensions. Load only the article and the writing style guide. Do not load the source files or session history.

**Why:** The current drafting session has accumulated editorial capture. After building the argument over many sessions, it is poorly positioned to challenge the argument. A fresh context simulates a skeptical reader or a peer-reviewer who has not been part of the drafting process.

**Why not a different LLM:** The primary risk with a different LLM (GPT-4, Gemini) is hallucination on factual claims — it may "find" errors that do not exist, or fail to find ones that do. For an article of this factual density, that is a meaningful risk. The fresh-context approach preserves model consistency while removing editorial capture.

**Why not switch for factual accuracy (dimensions 1–2, 7):** These require cross-referencing against the source files in the repository. The current session has access to those files and can verify quotes directly. A fresh chat would have to take the article's claims on trust.

---

## Execution sequence

Run in this order to avoid duplicate work:

1. **Dimensions 1 + 2 + 7** (factual accuracy, citations, consistency) — current session. These are mechanical and should be done before the interpretive review, so that the interpretive review is not evaluating claims that turn out to be factually wrong.
2. **Dimension 3** (argumentative integrity) — fresh chat. Load article + writing_styles.md. Prompt: "You are a skeptical peer reviewer. Identify claims that outrun their evidence, circular reasoning, and places where analogy substitutes for evidence."
3. **Dimensions 4 + 5** (fairness + tone) — same fresh chat. Prompt: "Read the article as a defence lawyer for each named party. Identify places where the characterisation is harder than the evidence supports."
4. **Dimension 6** (readability) — same or new fresh chat. Prompt: "You are an educated reader with no specialist knowledge of WHO governance or virology. Read the article and note every point where you need context the article has not provided."

---

## Output format

Each dimension produces a set of flags in the following format:

```
[LEVEL] §Section — brief description of issue
Evidence: quote or location
Suggested fix: one sentence
```

**Flag levels:**
- `[RED]` — Must fix before publication. Factual error, unsupported causal claim, serious fairness issue.
- `[AMBER]` — Should fix. Tone drift, unclear transition, over-claimed inference, weak source.
- `[GREEN]` — Note only. Minor style deviation, optional clarification, potential reader confusion.

Flags are collected in a single review report file: `sources/internal_memos/peer-review-report-YYYY-MM-DD.md`.

---

## Success criteria

The article passes peer-review when:
- No `[RED]` flags remain open.
- All direct quotes are verified against a repo source file.
- Every causal claim about intent or coordination is supported by documentary evidence (email, transcript, calendar, FOIA), not inferred from outcome alone.
- The counternarrative (natural origin, good-faith WHO) is represented accurately, not as a straw man.
- A cold-read reviewer (fresh chat, dimension 6) raises no more than three points of genuine reader confusion.
