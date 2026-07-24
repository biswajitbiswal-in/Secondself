# SecondSelf — Phase-Wise Implementation Plan

> **Sources:** [Problem-statement.md](./Problem-statement.md) · [architecture.md](./architecture.md)  
> **Purpose:** Step-by-step execution plan from zero to deployed product.

---

## Plan Overview

| Phase | Name | Maps To | Goal |
|-------|------|---------|------|
| **0** | Setup | Pre-Week 1 | Scaffold repo, config, dependencies, folders |
| **1** | Capture Pipeline | Week 1 — The Archivist | One command saves anything to `raw/` |
| **2** | Auto-Classify | Week 2.1 — The Librarian | LLM assigns PARA, tags, summary |
| **3** | Auto-Link | Week 2.2 — The Librarian | Embeddings + similarity linking |
| **4** | Graph Builder & Viz | Week 3 — The Cartographer | `graph.json` + interactive graph |
| **5** | Ask + Streamlit App | Week 4 — The Oracle | RAG Q&A + unified UI |
| **6** | Local Module Testing | — | Unit/integration tests per module |
| **7** | End-to-End Local Testing | — | Full pipeline on real personal data |
| **8** | Deployment | Week 4.2 | Streamlit Cloud / HF Spaces + public URL |
| **9** | Production Validation | Final deliverables | Live smoke tests, README, GitHub |

### Pipeline Dependency Chain

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8 → Phase 9
           raw/      wiki/     links     graph.json   app.py
```

**Rule:** Do not start Phase N until Phase N−1 acceptance criteria pass.

---

## Phase 0 — Setup

**Goal:** Create a runnable project skeleton with configuration, dependencies, and folder structure.

**Duration estimate:** 1–2 hours

### Tasks

- [ ] **0.1** Initialize Git repository and create `.gitignore`
- [ ] **0.2** Create directory structure:

  ```
  secondself/
  ├── raw/
  ├── wiki/
  │   ├── Projects/
  │   ├── Areas/
  │   ├── Resources/
  │   └── Archives/
  ├── embeddings/
  ├── templates/          # HTML graph template (Phase 4)
  └── docs/                 # optional: move planning docs here
  ```

- [ ] **0.3** Create `requirements.txt`:

  ```
  streamlit>=1.28.0
  groq>=0.4.0
  sentence-transformers>=2.2.0
  numpy>=1.24.0
  python-frontmatter>=1.0.0
  requests>=2.31.0
  pyyaml>=6.0
  ```

- [ ] **0.4** Create `config.py` with paths and constants (from architecture §8.1)
- [ ] **0.5** Create `.env.example`:

  ```
  GROQ_API_KEY=your_groq_api_key_here
  ```

- [ ] **0.6** Set up Python virtual environment and install dependencies:

  ```bash
  python -m venv .venv
  .venv\Scripts\activate        # Windows
  pip install -r requirements.txt
  ```

- [ ] **0.7** Register for a free [Groq API key](https://console.groq.com/) (needed from Phase 2)
- [ ] **0.8** Add placeholder module files with docstrings:
  - `capture.py`, `classify.py`, `link.py`, `build_graph.py`, `ask.py`, `app.py`
- [ ] **0.9** Create stub `README.md` with project name and setup steps

### Deliverables

| Artifact | Description |
|----------|-------------|
| Repo scaffold | All folders and stub files exist |
| `config.py` | Central paths, thresholds, model names |
| `requirements.txt` | Pinned minimum versions |
| `.gitignore` | Excludes `.venv/`, `.env`, `__pycache__/`, `*.pyc` |
| Working venv | `pip install -r requirements.txt` succeeds |

### Acceptance Criteria

- [ ] `raw/`, `wiki/` (with 4 PARA subfolders), `embeddings/` exist
- [ ] Virtual environment activates and imports `streamlit`, `groq`, `sentence_transformers` without error
- [ ] `config.py` loads without error
- [ ] `.env` is gitignored; `.env.example` is committed

### Verification Command

```bash
python -c "import config; print('Setup OK')"
```

---

## Phase 1 — Capture Pipeline

**Goal:** Ship the capture pipeline — one command saves notes, links, and files to `raw/` with timestamp + unique ID.

**Maps to:** Week 1 — The Archivist  
**Duration estimate:** 4–6 hours

### Tasks

- [ ] **1.1** Implement core helpers in `capture.py`:
  - `generate_id()` → UUID4 string
  - `generate_timestamp()` → ISO 8601, timezone-aware
  - `build_filename(id, timestamp, ext)` → `{YYYYMMDD}_{HHMMSS}_{short_id}.{ext}`
  - `write_capture(content, metadata)` → write markdown with YAML frontmatter

- [ ] **1.2** Implement capture functions:
  - `capture_note(text: str) -> str`
  - `capture_link(url: str) -> str` — fetch URL with `requests`, timeout 10s, size limit
  - `capture_file(path: str) -> str` — copy/read file, reject executables, cap at 10 MB

- [ ] **1.3** Define raw capture schema (architecture §3.2):

  ```yaml
  id, timestamp, type, source, original_filename (optional)
  ```

- [ ] **1.4** Add CLI with `argparse`:

  ```bash
  python capture.py "My idea about RAG"
  python capture.py --link "https://example.com/article"
  python capture.py --file "./documents/report.pdf"
  ```

- [ ] **1.5** Add basic logging (`logging.info` on each successful capture)
- [ ] **1.6** Capture 10+ real items from your own scattered notes, links, and files

### Deliverables

| Artifact | Description |
|----------|-------------|
| `capture.py` | Working CLI + library functions |
| `raw/` | 10+ real captured items with valid frontmatter |

### Acceptance Criteria

- [ ] One command captures a **note**, a **link**, AND a **file**
- [ ] Every capture has a **timestamp** + **unique ID** in frontmatter
- [ ] Filenames follow `{YYYYMMDD}_{HHMMSS}_{short_id}.{ext}` convention
- [ ] Invalid URLs and oversized files fail gracefully with error messages
- [ ] 10+ real items in `raw/` (not synthetic test data)

### Verification Commands

```bash
python capture.py "Learning plan for SecondSelf project"
python capture.py --link "https://python.org"
python capture.py --file "README.md"
dir raw\
```

### Badge

🏅 **The Archivist**

---

## Phase 2 — Auto-Classify (PARA)

**Goal:** Send raw captures to Groq (Llama 3) and produce organized wiki notes with PARA category, tags, and summary.

**Maps to:** Week 2.1 — The Librarian  
**Duration estimate:** 6–8 hours  
**Depends on:** Phase 1

### Tasks

- [ ] **2.1** Create `llm_client.py` helper:
  - `complete(system, user) -> str`
  - Load `GROQ_API_KEY` from environment
  - Handle timeouts and retries (1 retry on failure)

- [ ] **2.2** Write classification prompt with PARA definitions (architecture §5.4):
  - System prompt: PARA framework + strict JSON output schema
  - User prompt: raw capture content (truncate to `MAX_CONTENT_CHARS`)

- [ ] **2.3** Implement `classify_raw(raw_path: Path) -> Path` in `classify.py`:
  - Read raw file + frontmatter
  - Call LLM → parse JSON `{ "para", "tags", "summary" }`
  - Validate `para` is one of: Projects, Areas, Resources, Archives
  - Write wiki note to `wiki/{PARA}/{id}.md`

- [ ] **2.4** Define wiki note schema (architecture §3.3):

  ```yaml
  id, raw_id, para, tags, summary, created, updated, links: []
  ```

- [ ] **2.5** Implement `classify_all_raw() -> list[Path]`:
  - Scan `raw/` for unclassified captures (no matching wiki note)
  - Process each; log success/failure

- [ ] **2.6** Add CLI:

  ```bash
  python classify.py --file raw/20260724_143022_a1b2c3d4.txt
  python classify.py --all
  ```

- [ ] **2.7** Run classification on all Phase 1 captures

### Deliverables

| Artifact | Description |
|----------|-------------|
| `llm_client.py` | Groq wrapper with retry logic |
| `classify.py` | Single + batch classification |
| `wiki/` | Organized notes under PARA folders |

### Acceptance Criteria

- [ ] Any raw capture → **category + tags + summary** automatically
- [ ] PARA categorization places files in correct subfolder
- [ ] Invalid LLM JSON is retried once, then skipped with log entry
- [ ] Raw files remain **immutable** (not deleted or modified)
- [ ] All 10+ raw captures classified into `wiki/`

### Verification Commands

```bash
set GROQ_API_KEY=your_key_here
python classify.py --all
dir wiki\Projects
dir wiki\Resources
```

### Badge

🏅 **The Librarian** (partial — completed with Phase 3)

---

## Phase 3 — Auto-Link (Embeddings)

**Goal:** Compute embeddings for wiki notes and auto-link related content above a similarity threshold.

**Maps to:** Week 2.2 — The Librarian  
**Duration estimate:** 6–8 hours  
**Depends on:** Phase 2

### Tasks

- [ ] **3.1** Create `embedding.py` helper:
  - `load_model()` — cache `all-MiniLM-L6-v2` singleton
  - `embed_text(text: str) -> np.ndarray`
  - `embed_note(note_path: Path) -> np.ndarray` — use `summary + tags + body[:N]`
  - `cosine_similarity(a, b) -> float`
  - `find_similar(query_vec, corpus, top_k) -> list[tuple[id, score]]`

- [ ] **3.2** Implement embedding cache in `embeddings/`:
  - Save `{note_id}.npy` per note
  - Maintain `embeddings/index.json` with metadata

- [ ] **3.3** Implement `link_note(wiki_path, threshold=0.75) -> list[str]` in `link.py`:
  - Compute embedding for target note
  - Compare against all other wiki note embeddings
  - For matches ≥ threshold: update `links` in frontmatter + insert `[[related-id]]` in body

- [ ] **3.4** Implement `link_all_wiki() -> int`:
  - Process all wiki notes; return total links created

- [ ] **3.5** Add CLI:

  ```bash
  python link.py --file wiki/Projects/abc123.md
  python link.py --all
  ```

- [ ] **3.6** Capture 5+ additional real items, classify, and link — reach **15+ total wiki notes**

### Deliverables

| Artifact | Description |
|----------|-------------|
| `embedding.py` | Model loading, embed, similarity search |
| `link.py` | Auto-linking pipeline |
| `embeddings/` | Cached vectors for all wiki notes |
| `wiki/` | 15+ notes with cross-links in frontmatter and body |

### Acceptance Criteria

- [ ] Embeddings computed per wiki note and cached to disk
- [ ] Related notes auto-linked when similarity ≥ `SIMILARITY_THRESHOLD` (default 0.75)
- [ ] No manual tagging required — links appear automatically
- [ ] Notes with no similar matches save cleanly (no errors)
- [ ] **15+ real items** in organized, linked `wiki/`

### Verification Commands

```bash
python link.py --all
python -c "import frontmatter; print(frontmatter.load(open('wiki/Projects/your-note.md')).metadata.get('links'))"
```

### Badge

🏅 **The Librarian** (complete)

---

## Phase 4 — Graph Builder & Interactive Visualization

**Goal:** Convert linked wiki notes into `graph.json` and render an interactive force-directed graph.

**Maps to:** Week 3 — The Cartographer  
**Duration estimate:** 8–10 hours  
**Depends on:** Phase 3

### Tasks

#### 4A — Graph Data Model

- [ ] **4.1** Implement `build_graph(wiki_dir, output) -> dict` in `build_graph.py`:
  - Scan `wiki/**/*.md`
  - Parse frontmatter + `[[wikilinks]]` in body
  - Build `nodes[]` with: id, label, para, tags, summary, content_preview, content_full
  - Build `edges[]` with: source, target, type, weight
  - Write `graph.json` with meta block (generated_at, node_count, edge_count)

- [ ] **4.2** Add CLI:

  ```bash
  python build_graph.py
  python build_graph.py --output graph.json
  ```

- [ ] **4.3** Validate JSON against schema (architecture §3.4)

#### 4B — Interactive Graph

- [ ] **4.4** Create `templates/graph.html`:
  - Load `vis-network` from CDN
  - Accept graph JSON injected by Python
  - Force-directed layout with physics
  - Node colors by PARA (architecture §6.3)
  - Hover tooltip showing `content_full`
  - Drag, zoom, pan enabled

- [ ] **4.5** Create standalone test script `render_graph.py` (optional):
  - Opens graph in browser via simple HTTP server for quick testing before Streamlit

- [ ] **4.6** Verify graph renders correctly with your real wiki data

### Deliverables

| Artifact | Description |
|----------|-------------|
| `build_graph.py` | Wiki → JSON converter |
| `graph.json` | Exported graph from real notes |
| `templates/graph.html` | vis-network interactive renderer |

### Acceptance Criteria

- [ ] Script builds nodes + edges and exports clean JSON
- [ ] Interactive force-directed graph renders from JSON
- [ ] Hover reveals note content
- [ ] Drag + zoom work
- [ ] Built from **real notes**, not dummy data
- [ ] Empty wiki produces valid empty graph (not a crash)

### Verification Commands

```bash
python build_graph.py
python -c "import json; g=json.load(open('graph.json')); print(g['meta'])"
streamlit run render_graph.py   # if standalone test script created
```

### Badge

🏅 **The Cartographer**

---

## Phase 5 — Ask (RAG) + Streamlit App

**Goal:** Build retrieval-augmented Q&A and assemble graph + search into one Streamlit app.

**Maps to:** Week 4 — The Oracle  
**Duration estimate:** 10–12 hours  
**Depends on:** Phase 4

### Tasks

#### 5A — RAG Q&A Engine

- [ ] **5.1** Implement `ask(question, top_k=5) -> dict` in `ask.py`:
  - Embed the question
  - Load all cached note embeddings from `embeddings/`
  - Retrieve top-k notes by cosine similarity
  - Load full wiki content for retrieved notes
  - Build LLM prompt: system (answer from context only) + user (context + question)
  - Return `{ "answer": str, "sources": [{"id", "summary", "score"}] }`

- [ ] **5.2** Handle edge cases:
  - No relevant notes → return friendly fallback message
  - Low similarity scores → mention low confidence

- [ ] **5.3** Add CLI:

  ```bash
  python ask.py "What have I captured about machine learning?"
  ```

- [ ] **5.4** Test 5+ real questions against your own notes

#### 5B — Streamlit App

- [ ] **5.5** Implement `app.py`:
  - **Header:** "SecondSelf — Your Personal AI Second Brain"
  - **Search bar:** text input + Ask button → calls `ask()`
  - **Answer panel:** synthesized answer + source citations
  - **Graph section:** embed `templates/graph.html` via `st.components.v1.html()`
  - **Sidebar:** node/edge counts, PARA legend, "Rebuild Graph" button

- [ ] **5.6** Cache expensive resources:

  ```python
  @st.cache_resource
  def load_embedding_model(): ...

  @st.cache_data
  def load_graph_json(): ...
  ```

- [ ] **5.7** Optional: create `pipeline.py` orchestrator:

  ```bash
  python pipeline.py --classify --link --graph
  ```

- [ ] **5.8** Run locally:

  ```bash
  streamlit run app.py
  ```

### Deliverables

| Artifact | Description |
|----------|-------------|
| `ask.py` | RAG Q&A with source citations |
| `app.py` | Unified Streamlit UI (graph + search) |
| `pipeline.py` | Optional batch orchestrator |

### Acceptance Criteria

- [ ] `ask()` returns answers synthesized from your own notes (retrieval + LLM)
- [ ] Sources list shows which notes were used
- [ ] One Streamlit app contains **both** the graph and the search bar
- [ ] Graph and Q&A work together in the same session
- [ ] App runs locally without errors on real data

### Verification Commands

```bash
python ask.py "Summarize my project ideas"
streamlit run app.py
```

### Badge

🏅 **The Oracle** (partial — completed with Phase 8–9)

---

## Phase 6 — Local Module Testing

**Goal:** Verify each module in isolation with targeted tests before full integration.

**Duration estimate:** 4–6 hours  
**Depends on:** Phase 5

### Tasks

- [ ] **6.1** Create `tests/` directory and install `pytest` (add to dev requirements)
- [ ] **6.2** **Capture tests** (`tests/test_capture.py`):
  - UUID uniqueness across multiple captures
  - Timestamp is valid ISO 8601
  - Note, link, and file capture types produce correct frontmatter
  - Invalid file path raises clear error

- [ ] **6.3** **Classify tests** (`tests/test_classify.py`):
  - Mock Groq response → verify wiki file created in correct PARA folder
  - Invalid JSON from LLM → retry then skip
  - Tags and summary written to frontmatter

- [ ] **6.4** **Link tests** (`tests/test_link.py`):
  - Fixed embedding vectors → verify threshold behavior
  - Similar notes get linked; dissimilar notes do not
  - `links` array updated in frontmatter

- [ ] **6.5** **Graph tests** (`tests/test_build_graph.py`):
  - Fixture wiki folder → expected node and edge counts
  - Wikilinks in body become edges
  - Empty wiki → valid empty graph JSON

- [ ] **6.6** **Ask tests** (`tests/test_ask.py`):
  - Mock retrieval + mock LLM → verify answer structure
  - No matches → fallback message returned
  - Sources list populated correctly

- [ ] **6.7** Run full test suite:

  ```bash
  pytest tests/ -v
  ```

### Deliverables

| Artifact | Description |
|----------|-------------|
| `tests/` | Unit tests for all pipeline modules |
| Test results | All tests passing locally |

### Acceptance Criteria

- [ ] Each module has at least 3 meaningful tests
- [ ] LLM and embedding calls are mocked in unit tests (no API cost)
- [ ] `pytest tests/ -v` passes with 0 failures
- [ ] Tests cover happy path + at least one failure/edge path per module

### Verification Command

```bash
pytest tests/ -v --tb=short
```

---

## Phase 7 — End-to-End Local Testing

**Goal:** Run the complete pipeline on real personal data and validate the full user journey locally.

**Duration estimate:** 3–4 hours  
**Depends on:** Phase 6

### Tasks

- [ ] **7.1** **Fresh pipeline run** — execute in order:

  ```bash
  python capture.py "New idea captured during E2E test"
  python capture.py --link "https://a-real-article-youve-read.com"
  python classify.py --all
  python link.py --all
  python build_graph.py
  python ask.py "What topics have I been exploring?"
  streamlit run app.py
  ```

- [ ] **7.2** **Capture → Classify → Link → Graph → Ask checklist:**

  | Step | Check |
  |------|-------|
  | Capture | New item appears in `raw/` with ID + timestamp |
  | Classify | Wiki note created in correct PARA folder |
  | Link | Related notes cross-linked automatically |
  | Graph | New node visible in interactive graph |
  | Ask | Question returns answer grounded in your notes |

- [ ] **7.3** Test edge cases manually (see `edge-case.md` when available):
  - Empty question submitted in Streamlit
  - Very long note capture
  - Duplicate URL capture
  - Question with no matching notes

- [ ] **7.4** Verify data counts:
  - 15+ items in `wiki/`
  - `graph.json` node_count matches wiki note count
  - Embeddings exist for every wiki note

- [ ] **7.5** Document any bugs found; fix before deployment

### Deliverables

| Artifact | Description |
|----------|-------------|
| E2E test log | Checklist with pass/fail for each step |
| Bug fixes | All blockers resolved before Phase 8 |

### Acceptance Criteria

- [ ] Full pipeline works: **capture → classify → link → graph → ask**
- [ ] Streamlit app loads graph and returns real answers
- [ ] No crashes on empty states or missing data
- [ ] All 4 weekly milestone acceptance criteria from Problem-statement.md pass locally

### Verification

Manual walkthrough — record results in a checklist or commit message before deploying.

---

## Phase 8 — Deployment

**Goal:** Deploy the Streamlit app to a public URL with secrets configured.

**Maps to:** Week 4.2 — UI, Deployment, Public URL  
**Duration estimate:** 3–5 hours  
**Depends on:** Phase 7

### Tasks

- [ ] **8.1** Prepare repo for deployment:
  - Ensure `app.py` is the Streamlit entry point
  - Add `.streamlit/config.toml` (theme, layout)
  - Pre-build `graph.json` and commit (or rebuild on startup)
  - Pre-compute `embeddings/` and commit (faster cold start)

- [ ] **8.2** Write production `README.md`:
  - Project description and demo screenshot
  - Setup instructions (venv, env vars, CLI usage)
  - Architecture diagram (link to `architecture.md`)
  - Public demo URL
  - Privacy note: deployed app exposes your notes

- [ ] **8.3** Push to GitHub (public repo)

- [ ] **8.4** Deploy to **Streamlit Cloud** (primary):
  1. Connect GitHub repo at [share.streamlit.io](https://share.streamlit.io)
  2. Set main file: `app.py`
  3. Add secret: `GROQ_API_KEY`
  4. Deploy and wait for build

- [ ] **8.5** Alternative: deploy to **Hugging Face Spaces** (optional backup)

- [ ] **8.6** Verify deployed app loads within reasonable time (< 60s cold start)

### Deliverables

| Artifact | Description |
|----------|-------------|
| Public GitHub repo | Clean README + setup instructions |
| Live URL | Streamlit Cloud or HF Spaces public link |
| Secrets configured | `GROQ_API_KEY` in platform secrets manager |

### Acceptance Criteria

- [ ] App accessible at a **public URL** anyone can open
- [ ] Interactive graph renders on deployed app
- [ ] Ask bar returns answers (not API key errors)
- [ ] No secrets exposed in repo or logs
- [ ] README documents setup and usage

### Verification

Open public URL in incognito browser → ask a question → confirm graph loads.

### Badge

🏅 **The Oracle** (complete)

---

## Phase 9 — Production Validation & Final Deliverables

**Goal:** Final round of testing on the live deployment and confirm all project deliverables.

**Duration estimate:** 2–3 hours  
**Depends on:** Phase 8

### Tasks

- [ ] **9.1** **Production smoke tests** (on live URL):

  | Test | Expected |
  |------|----------|
  | Page loads | App renders without 500 error |
  | Graph visible | Nodes and edges display; drag/zoom work |
  | Hover works | Note content appears on node hover |
  | Ask works | Question returns synthesized answer |
  | Sources shown | Answer cites relevant notes |
  | Empty question | Graceful validation message |
  | Mobile view | Layout usable on smaller screens |

- [ ] **9.2** **End-to-end on production:**
  - Confirm full flow works in deployed environment
  - Note any differences from local behavior; fix and redeploy

- [ ] **9.3** **Final deliverables checklist** (from Problem-statement.md):

  - [ ] Public GitHub repo with clean README + setup instructions
  - [ ] Live deployed URL — interactive graph + ask-your-brain search
  - [ ] End-to-end flow verified: capture → classify → link → graph → ask
  - [ ] All 4 weekly milestones complete

- [ ] **9.4** Tag release (optional):

  ```bash
  git tag -a v1.0.0 -m "SecondSelf v1.0 — initial public release"
  git push origin v1.0.0
  ```

- [ ] **9.5** Update README with final demo URL and badge list

### Deliverables

| Artifact | Description |
|----------|-------------|
| Smoke test report | All production tests passing |
| `v1.0.0` tag | Optional release marker |
| Complete README | Demo URL, badges, architecture link |

### Acceptance Criteria

- [ ] All production smoke tests pass
- [ ] Full pipeline verified end to end (locally for capture; deployed for graph + ask)
- [ ] All 4 badges earned: Archivist, Librarian, Cartographer, Oracle
- [ ] Project ready to share publicly

---

## Master Checklist — All Phases

Use this as a single progress tracker:

| Phase | Status | Key Output |
|-------|--------|------------|
| 0 — Setup | [ ] | Repo scaffold, venv, config |
| 1 — Capture | [ ] | `capture.py`, 10+ raw items |
| 2 — Classify | [ ] | `classify.py`, wiki notes with PARA |
| 3 — Auto-Link | [ ] | `link.py`, 15+ linked wiki notes |
| 4 — Graph | [ ] | `graph.json`, interactive graph |
| 5 — Ask + App | [ ] | `ask.py`, `app.py` running locally |
| 6 — Module Tests | [ ] | `pytest` passing |
| 7 — E2E Local | [ ] | Full pipeline on real data |
| 8 — Deploy | [ ] | Public URL live |
| 9 — Production | [ ] | All final deliverables complete |

---

## File Creation Order

Build files in this sequence to avoid dependency issues:

```
1.  config.py
2.  capture.py
3.  llm_client.py
4.  classify.py
5.  embedding.py
6.  link.py
7.  build_graph.py
8.  templates/graph.html
9.  ask.py
10. app.py
11. pipeline.py          (optional)
12. tests/test_*.py
13. README.md             (finalize in Phase 8)
```

---

## Environment & Secrets Reference

| Variable | Phases | Where to Set |
|----------|--------|--------------|
| `GROQ_API_KEY` | 2, 3, 5, 8, 9 | `.env` locally; Streamlit secrets in production |
| `SECONDSELF_DATA_DIR` | 8+ | Optional override for deployment data root |

---

## Risk Register

| Risk | Phase | Mitigation |
|------|-------|------------|
| Groq rate limits | 2, 5 | Batch with delays; retry with backoff |
| Slow embedding cold start | 3, 5, 8 | Cache model with `@st.cache_resource`; pre-compute embeddings |
| LLM returns invalid JSON | 2 | Retry once; strict prompt; JSON parse with fallback |
| Streamlit graph not rendering | 4, 5 | Test HTML template standalone first |
| Public repo exposes personal notes | 8, 9 | Use demo subset; document privacy in README |
| Large file capture | 1 | 10 MB cap; reject binaries |

---

## Next Steps After This Plan

1. Generate **`edge-case.md`** — corner scenarios for each phase
2. **Implement Phase 0** — scaffold the repo
3. Work through Phases 1–9 sequentially, checking acceptance criteria before moving on

---

*Generated from [architecture.md](./architecture.md) and [Problem-statement.md](./Problem-statement.md).*
