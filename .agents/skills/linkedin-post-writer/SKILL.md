---
name: linkedin-post-writer
description: Write a complete, grounded LinkedIn post about a developer's GitHub project from repo context (README, commits, releases, notes) following the user's profile.yaml voice. Use whenever drafting, revising, or regenerating a LinkedIn post draft for human approval. Never publishes.
---

# LinkedIn Post Writer

Produces **drafts only**. Publishing is a separate, approval-gated step handled by the app.

## Inputs
- `ProjectContext`: repo, description, README excerpt, languages, topics, recent commits, releases, homepage, local notes
- `profile.yaml`: tone, audience, hashtags, banned phrases, length range, CTA styles, example past posts
- Optional: `instruction` (e.g., "more technical", "focus on the mobile side")

## Process
1. **Extract facts.** List what the project does, who it's for, the stack, notable decisions, challenges, and real results from the context. Discard anything not in the context.
2. **Pick an angle** (one per variant):
   - Problem → solution
   - A technical challenge and how I solved it
   - A lesson learned
   - Build-in-public milestone
3. **Write the hook** (first 1–2 lines, visible before "see more"): a concrete problem, surprising detail, or outcome. No "Excited to announce".
4. **Body:** what it does → how it's built (stack, 1–2 decisions) → the hardest part or learning.
5. **CTA:** one soft ask (link to repo/demo, feedback request on a specific thing). Not engagement bait.
6. **Hashtags:** 3–5, from `profile.yaml` + project topics.
7. **Claims list:** for each factual statement, cite the source (README / commit sha / notes).
8. **Self-check** against the rules below before output.

## Rules
- First person, plain language, specific nouns over adjectives.
- 900–1,500 chars (hard max 3,000). Short paragraphs, blank lines between.
- Max 2 emojis. No banned phrases from `profile.yaml`.
- No fabricated numbers, users, results, or employers. If a number isn't in context, don't use it.
- No "production-ready / scalable / blazing fast" unless stated in context.
- Link to repo/demo if provided.
- 2–3 variants must differ in hook and angle.

## Output format (strict JSON)
```json
{
  "variants": [
    {
      "angle": "problem-solution",
      "text": "Full post text with \n line breaks",
      "hashtags": ["#python", "#buildinpublic"],
      "claims": [
        {"claim": "Uses SQLite for state", "source": "README:Architecture"},
        {"claim": "Added offline sync", "source": "commit a1b2c3d"}
      ],
      "warnings": []
    }
  ],
  "missing_context": ["No README screenshots", "No result metrics provided"]
}
```
If context is too thin to write a grounded post, return `variants: []` and list what's needed in `missing_context`.

## Example (shape only)
```
Most habit apps break the moment you lose signal.

I built Momentum, an offline-first Flutter app where everything works without a connection and syncs when you're back.

Stack: Flutter, Clean Architecture, local-first storage.

Hardest part: conflict resolution when the same task is edited on two devices. I ended up with last-write-wins plus a per-field merge for notes.

Repo: <link>

#flutter #offlinefirst #buildinpublic
```
(Example is illustrative; always derive content from the real context.)
