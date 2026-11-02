# PM2.3.1 — Recall preview matching and visibility repair

**Release:** `v0.7.3-pm23-recallfix1` from operator-installed `v0.7.3-pm23-optin-recall1`.

## Operator report

Scout and Original recall switches worked, but the Recall preview did not return useful matches and reported a generic “No matching memories” message. This did not establish a publishing/agent failure. It was both a **UI ambiguity** and a strict retrieval limitation:

- The preview searches approved **active Memory Manager notes**, **not** historical Scout replies or original Moltbook posts. Channel selection controls **which generator may use a matching memory**. The user-facing copy did not explain this.
- The original tokenizer omitted terms under four letters, including **AI**, **RF**, and **3D**, and discarded single-keyword body matches with a fixed threshold of two. It also did not normalize obvious singular/plural variations.
- The UI made it impossible to distinguish an empty eligible-memory table, archived/excluded-only notes, disabled recall, overly generic queries, and genuinely unrelated topics.

## Focused remedy

- Tokenizer now retains meaningful 2+ character technical topics while filtering generic short English function words; normalizes simple plural forms (`memories` → `memory`, `replies` → `reply`). This is still a deterministic local keyword matcher, **not semantic/embedding recall**.
- Title matches can yield a result with one meaningful token; a single-term topic may match the memory body. Multiword topics still require a title hit or two distinct body hits. No unrelated fallback notes are ever selected.
- A new read-only inventory shows the count of eligible verified active notes, archived/excluded notes, and integrity-ineligible records. No history, source URLs or excluded memory text is displayed.
- When results are empty, the page explains **why** and shows clickable examples built from up to six eligible existing memory titles. Clicking a title populates the search; it does not change settings or trigger Bob's generation.
- The preview explicitly says it retrieves saved accepted memories, not Moltbook Scout/original post archives.
- The existing 3-record and 1,350-character contextual payload limits, active-only/source_kind/digest checks, optional channel permissions, and read-only producer behavior remain intact. Also ensure marker neutralization still occurs when the bounded JSON context is shortened.
- **No memory data/schema, publishing, Scout/original producer, SOUL.md, identity, Gateway, model, or automatically scheduled task changes.** Only `bob_memory_recall.py` is installed; Activity Manager restarts to pick up the new UI.

## Single-command operator acceptance

1. In OpenClawLab, run `bobctl update` and approve `v0.7.3-pm23-recallfix1` from `v0.7.3-pm23-optin-recall1` by typing `UPDATE`.
2. Open **Bob's Mind → Recall**. It now explicitly explains that it searches accepted memories. Verify the **Eligible active memories** count. If zero, add or approve a harmless note in **Bob's Mind → Memory**, e.g. title `Local AI memory interests`, content `Bob wants to explore local AI agents and long-term memory.`.
3. Enable the Scout channel if disabled. Click one of the new **Try a saved memory title** links. Its matching active memory should appear under **Matching active notes**. Try just `AI` or `memory` from the note title.
4. Select Original; only if you want this channel to influence possible public original drafts, enable it independently. The same title-based preview should then work there too. With Original disabled, the page should explicitly say it is disabled.
5. Try an unrelated search like `penguin icebergs`, which should give an accurate no-match reason and **no unrelated fallback**.
6. Archive/exclude your test note and refresh; its text must stop appearing. Restore it if desired.
7. Check prior Memory/Suggestions/AI ideas pages remain functional. No Moltbook post is sent by any of these tests.

## Safety note

Turning a channel on can influence the text of a draft that might later be published under already-configured review/automatic-publishing rules. Review eligible notes for private or sensitive content first. Nothing in this patch changes publication authority or enables recall if it was previously disabled.
