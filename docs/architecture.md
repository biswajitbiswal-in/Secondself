# SecondSelf — System Architecture

> **Source:** Derived from [Problem-statement.md](./Problem-statement.md)  
> **Purpose:** Defines *how* SecondSelf is built — components, data flow, interfaces, and technology choices.

---

## 1. Architecture Overview

SecondSelf is a **personal knowledge pipeline** that turns scattered captures into a self-organizing, queryable second brain. It is not a traditional notes app or a generic chatbot. The system ingests raw information, enriches it with AI, persists it as linked wiki notes, visualizes relationships as a graph, and answers questions via retrieval-augmented generation (RAG).

### 1.1 Design Principles

| Principle | Rationale |
|-----------|-----------|
| **File-first storage** | Notes live as plain files in `raw/` and `wiki/` — easy to inspect, version, and back up |
| **Pipeline stages** | Each week adds one stage; output of stage N is input to stage N+1 |
| **Local-first, free-tier AI** | Embeddings run locally; LLM calls use free APIs (Groq) where possible |
| **Incremental enrichment** | Raw captures are immutable; wiki notes are derived and can be regenerated |
| **Single-user, personal scale** | Optimized for one person's knowledge base (~hundreds to low thousands of notes) |
| **Deployable as one app** | Streamlit bundles graph + Q&A into a single public-facing product |

### 1.2 High-Level System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION LAYER                            │
│  ┌──────────────────────┐    ┌──────────────────────┐                       │
│  │  CLI: capture.py     │    │  Web: app.py         │                       │
│  │  (Week 1)              │    │  (Streamlit, Week 4) │                       │
│  └──────────┬───────────┘    └──────────┬───────────┘                       │
└─────────────┼─────────────────────────────┼─────────────────────────────────┘
              │                             │
              ▼                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING PIPELINE (Python)                        │
│                                                                             │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌─────────────┐   ┌──────┐ │
│  │ capture  │ → │ classify  │ → │  link    │ → │ build_graph │ → │ ask  │ │
│  │ .py      │   │ .py       │   │  .py     │   │ .py         │   │ .py  │ │
│  └──────────┘   └───────────┘   └──────────┘   └─────────────┘   └──────┘ │
│       │               │               │               │              │    │
│       │         Groq LLM        sentence-         JSON export    RAG + LLM │
│       │         (PARA/tags)     transformers                                      │
└───────┼───────────────┼───────────────┼───────────────┼──────────────┼──────┘
        │               │               │               │              │
        ▼               ▼               ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PERSISTENCE LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ raw/         │  │ wiki/        │  │ graph.json   │  │ embeddings/     │ │
│  │ (captures)   │  │ (organized)  │  │ (graph data) │  │ (vectors, opt.) │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VISUALIZATION LAYER (Week 3–4)                      │
│  vis-network / Cytoscape.js embedded in Streamlit via components.html       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Component Map

| Component | File | Week | Responsibility |
|-----------|------|------|----------------|
| Capture | `capture.py` | 1 | Ingest note/link/file → `raw/` with metadata |
| Classify | `classify.py` | 2 | LLM-based PARA categorization, tags, summary |
| Link | `link.py` | 2 | Embedding similarity → auto-link related notes |
| Graph Builder | `build_graph.py` | 3 | Parse wiki links → `graph.json` |
| Q&A Engine | `ask.py` | 4 | Semantic retrieval + LLM synthesis |
| Web App | `app.py` | 4 | Streamlit UI: graph + search bar |
| Config | `config.py` | 0 | Paths, API keys, thresholds (recommended) |
| Pipeline | `pipeline.py` | 4 | Optional orchestrator: classify → link → graph |

### 2.2 Module Dependencies

```
capture.py      → (stdlib only)
classify.py     → groq / openai-compatible client, config
link.py         → sentence-transformers, numpy, classify output
build_graph.py  → wiki/ markdown parser
ask.py          → link embeddings, groq, wiki content
app.py          → ask, build_graph, streamlit, graph JSON
```

**Rule:** Lower layers must not import from higher layers. `app.py` sits at the top; `capture.py` has no upstream dependencies.

---

## 3. Data Architecture

### 3.1 Storage Layout

```
secondself/
├── raw/                          # Immutable captures (Week 1)
│   └── {timestamp}_{uuid}.{ext}  # e.g. 20260724_143022_a1b2c3d4.txt
├── wiki/                           # Organized notes (Week 2+)
│   ├── Projects/
│   ├── Areas/
│   ├── Resources/
│   └── Archives/
├── embeddings/                     # Optional cache (Week 2+)
│   └── {note_id}.npy
├── graph.json                      # Graph export (Week 3)
├── capture.py
├── classify.py
├── link.py
├── build_graph.py
├── ask.py
├── app.py
├── config.py
├── requirements.txt
└── README.md
```

### 3.2 Raw Capture Schema

Each file in `raw/` is a self-describing capture with a YAML frontmatter header (recommended) or sidecar `.meta.json`.

**Format: Markdown with frontmatter (recommended)**

```markdown
---
id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
timestamp: 2026-07-24T14:30:22+05:30
type: note | link | file
source: cli | url | filepath
original_filename: report.pdf
---

Raw content body here...
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID string | Yes | Globally unique capture ID |
| `timestamp` | ISO 8601 | Yes | Capture time (timezone-aware) |
| `type` | enum | Yes | `note`, `link`, or `file` |
| `source` | string | Yes | Origin: CLI text, URL, or file path |
| `original_filename` | string | No | For file captures |
| Body | text/binary ref | Yes | Raw content or extracted text |

**File naming convention:** `{YYYYMMDD}_{HHMMSS}_{short_id}.{ext}`

### 3.3 Wiki Note Schema

Wiki notes are Markdown files organized under PARA folders.

```markdown
---
id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
raw_id: a1b2c3d4-e5f6-7890-abcd-ef1234567890
para: Projects | Areas | Resources | Archives
tags: [python, ml, career]
summary: One-line summary from LLM
created: 2026-07-24T14:30:22+05:30
updated: 2026-07-24T15:00:00+05:30
links: [other-note-id-1, other-note-id-2]
---

# Title (optional, from summary or first line)

Note body with [[wikilinks]] to related notes.

Related: [[other-note-id-1]]
```

| Field | Type | Description |
|-------|------|-------------|
| `para` | enum | PARA category assigned by LLM |
| `tags` | list | LLM-generated tags |
| `summary` | string | One-line summary |
| `links` | list | IDs of auto-linked notes (similarity-based) |
| Body | markdown | Content + optional `[[id]]` wikilinks |

**Path convention:** `wiki/{PARA}/{slug-or-id}.md`

### 3.4 Graph JSON Schema

`graph.json` is the contract between the graph builder and the UI.

```json
{
  "meta": {
    "generated_at": "2026-07-24T16:00:00+05:30",
    "node_count": 42,
    "edge_count": 87
  },
  "nodes": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "label": "One-line summary",
      "para": "Projects",
      "tags": ["python", "ml"],
      "summary": "Full summary text",
      "content_preview": "First 200 chars of body...",
      "content_full": "Full note body for hover popup"
    }
  ],
  "edges": [
    {
      "source": "id-a",
      "target": "id-b",
      "type": "similarity",
      "weight": 0.82
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `nodes[].id` | Matches wiki note `id` |
| `nodes[].label` | Display label on graph |
| `nodes[].content_full` | Shown on hover |
| `edges[].weight` | Cosine similarity (0–1) for auto-links |
| `edges[].type` | `similarity` or `manual` (future) |

### 3.5 Embedding Cache (Optional)

To avoid recomputing embeddings on every query:

```
embeddings/
└── {note_id}.npy          # numpy float32 vector
└── index.json             # { note_id: path, dim, model_name }
```

---

## 4. Processing Pipeline

### 4.1 End-to-End Data Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌───────────┐     ┌─────────┐
│  INPUT  │────▶│   RAW   │────▶│  WIKI   │────▶│   GRAPH   │────▶│   ASK   │
│ note/   │     │  store  │     │  store  │     │   JSON    │     │  answer │
│ link/   │     │         │     │ + links │     │           │     │         │
│ file    │     │         │     │         │     │           │     │         │
└─────────┘     └─────────┘     └─────────┘     └───────────┘     └─────────┘
   Week 1          Week 1          Week 2           Week 3           Week 4
                                  classify          build_graph       ask()
                                  link.py
```

### 4.2 Stage Details

#### Stage 1: Capture (`capture.py`)

```
User input → detect type (note/link/file)
          → generate UUID + timestamp
          → extract/store content (URL fetch, file copy, plain text)
          → write to raw/{timestamp}_{id}.{ext}
          → return capture ID
```

**CLI interface (proposed):**

```bash
python capture.py "My idea about RAG pipelines"
python capture.py --link "https://example.com/article"
python capture.py --file "./documents/report.pdf"
```

#### Stage 2: Classify (`classify.py`)

```
Read raw/ file → build LLM prompt with PARA definitions
              → call Groq (Llama 3)
              → parse JSON: { para, tags, summary }
              → write wiki/{PARA}/{id}.md with frontmatter + body
              → optionally move/archive raw (keep raw immutable)
```

**LLM prompt structure:**

- System: PARA framework definitions + output JSON schema
- User: raw capture content (truncated if needed, e.g. 8K tokens)
- Response: strict JSON `{ "para": "...", "tags": [...], "summary": "..." }`

#### Stage 3: Link (`link.py`)

```
For each new wiki note:
  → compute embedding (sentence-transformers, e.g. all-MiniLM-L6-v2)
  → load existing wiki embeddings
  → cosine similarity vs all existing notes
  → for each match above threshold (default 0.75):
       append link to frontmatter.links
       insert [[related-id]] in markdown body
  → save updated notes + cache embedding
```

**Similarity threshold:** Configurable in `config.py` (recommended default: `0.75`).

#### Stage 4: Graph Build (`build_graph.py`)

```
Scan wiki/**/*.md → parse frontmatter + [[wikilinks]]
                 → build nodes[] from each note
                 → build edges[] from links[] + wikilinks
                 → enrich with para/tags for node styling
                 → write graph.json
```

#### Stage 5: Ask (`ask.py`)

```
User question → embed question
             → cosine similarity vs all note embeddings
             → retrieve top-k notes (default k=5)
             → load full wiki content for top-k
             → build LLM prompt: context + question
             → Groq synthesizes answer with citations
             → return { answer, sources[] }
```

**RAG flow:**

```
Question → Embed → Retrieve top-k wiki notes → LLM synthesize → Answer + sources
```

---

## 5. AI / ML Architecture

### 5.1 Model Choices

| Task | Model / Library | Runtime | Cost |
|------|-----------------|---------|------|
| Classification (PARA, tags, summary) | Llama 3 via Groq API | Cloud | Free tier |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local CPU | Free |
| Answer synthesis | Llama 3 via Groq API | Cloud | Free tier |

### 5.2 LLM Integration Layer

Abstract LLM calls behind a thin client to allow swapping providers:

```python
# config.py
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-8b-8192"

# llm_client.py (recommended helper)
def complete(system: str, user: str) -> str: ...
def classify(content: str) -> dict: ...   # returns {para, tags, summary}
def synthesize(question: str, context: str) -> str: ...
```

### 5.3 Embedding Layer

```python
# embedding.py (recommended helper)
def embed_text(text: str) -> np.ndarray: ...
def embed_note(note_path: Path) -> np.ndarray: ...
def similarity(a: np.ndarray, b: np.ndarray) -> float: ...
def find_similar(query_vec, corpus_vecs, top_k=5) -> list[tuple[id, score]]: ...
```

**Text extraction for embedding:** Use `summary + tags + body` (first N chars) as the embeddable representation.

### 5.4 PARA Framework Mapping

| Category | LLM Definition (prompt context) |
|----------|----------------------------------|
| **Projects** | Active efforts with a deadline or outcome |
| **Areas** | Ongoing responsibilities to maintain |
| **Resources** | Topics of interest for future reference |
| **Archives** | Inactive items from the other three |

---

## 6. Application Layer (Streamlit)

### 6.1 App Structure (`app.py`)

```
┌────────────────────────────────────────────────────────────┐
│  SecondSelf — Your Personal AI Second Brain                │
├────────────────────────────────────────────────────────────┤
│  [ Ask anything about your notes...        ] [ Ask ]       │
│  Answer panel + source citations                           │
├────────────────────────────────────────────────────────────┤
│  Interactive Knowledge Graph (vis-network)                 │
│  • Force-directed layout                                   │
│  • Node color by PARA category                             │
│  • Hover → note preview                                    │
│  • Drag, zoom, pan                                         │
├────────────────────────────────────────────────────────────┤
│  Sidebar: stats, rebuild graph, refresh embeddings         │
└────────────────────────────────────────────────────────────┘
```

### 6.2 Streamlit + Graph Integration

Streamlit does not natively render JS graph libraries. Use `streamlit.components.v1.html()`:

1. `build_graph.py` produces `graph.json`
2. `app.py` reads JSON and injects it into an HTML template
3. Template loads `vis-network` from CDN
4. Bidirectional events (node click) via `postMessage` (optional, Phase 2)

**Recommended graph library:** `vis-network` — simpler API, good force-directed defaults.

### 6.3 Node Styling by PARA

| PARA | Color (example) |
|------|-----------------|
| Projects | `#4CAF50` (green) |
| Areas | `#2196F3` (blue) |
| Resources | `#FF9800` (orange) |
| Archives | `#9E9E9E` (gray) |

---

## 7. Interface Contracts

### 7.1 Public Function Signatures (Proposed)

```python
# capture.py
def capture_note(text: str) -> str: ...           # returns capture id
def capture_link(url: str) -> str: ...
def capture_file(path: str) -> str: ...

# classify.py
def classify_raw(raw_path: Path) -> Path: ...    # returns wiki note path
def classify_all_raw() -> list[Path]: ...

# link.py
def link_note(wiki_path: Path, threshold: float = 0.75) -> list[str]: ...
def link_all_wiki() -> int: ...                   # returns link count

# build_graph.py
def build_graph(wiki_dir: Path, output: Path) -> dict: ...

# ask.py
def ask(question: str, top_k: int = 5) -> dict: ...
# Returns: { "answer": str, "sources": [{"id", "summary", "score"}] }
```

### 7.2 CLI Entry Points

| Command | Action |
|---------|--------|
| `python capture.py "text"` | Capture note |
| `python classify.py --all` | Classify all unprocessed raw |
| `python link.py --all` | Link all wiki notes |
| `python build_graph.py` | Regenerate graph.json |
| `python ask.py "question"` | CLI Q&A |
| `streamlit run app.py` | Launch web app |

---

## 8. Configuration

### 8.1 `config.py` (Recommended)

```python
RAW_DIR = Path("raw")
WIKI_DIR = Path("wiki")
EMBEDDINGS_DIR = Path("embeddings")
GRAPH_PATH = Path("graph.json")

SIMILARITY_THRESHOLD = 0.75
TOP_K_RETRIEVAL = 5
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
GROQ_MODEL = "llama3-8b-8192"
MAX_CONTENT_CHARS = 8000   # truncate for LLM calls
```

### 8.2 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes (Week 2+) | Groq API key for classify + ask |
| `SECONDSELF_DATA_DIR` | No | Override data root for deployment |

**Never commit `.env` or API keys to Git.**

---

## 9. Deployment Architecture

### 9.1 Target Platforms

| Platform | Use Case |
|----------|----------|
| **Local** | Development, capture CLI, embedding compute |
| **Streamlit Cloud** | Primary deployment — free, GitHub-connected |
| **Hugging Face Spaces** | Alternative deployment |

### 9.2 Deployment Topology

```
┌──────────────┐         ┌─────────────────────┐
│   Developer  │──git──▶│  GitHub Repository  │
│   (local)    │         └──────────┬──────────┘
└──────────────┘                    │
                                    │ auto-deploy
                                    ▼
                         ┌─────────────────────┐
                         │  Streamlit Cloud    │
                         │  • app.py           │
                         │  • graph.json       │
                         │  • wiki/ (bundled   │
                         │    or rebuilt)      │
                         │  • GROQ_API_KEY     │
                         │    (secrets)        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         Public URL (read + ask)
```

### 9.3 Deployment Constraints

- **Embeddings at deploy time:** Pre-compute embeddings locally; commit `embeddings/` or regenerate on app startup (slower cold start).
- **Capture on deployed app:** Optional Week 4+ feature — add Streamlit file/text upload that writes to repo or ephemeral storage. Initial scope: deploy is read + ask + graph; capture stays CLI-local.
- **Secrets:** `GROQ_API_KEY` via Streamlit Cloud secrets manager.
- **Resource limits:** Streamlit free tier — keep `sentence-transformers` model loaded once via `@st.cache_resource`.

---

## 10. Security & Privacy

| Concern | Mitigation |
|---------|------------|
| API key exposure | Environment variables only; `.env` in `.gitignore` |
| Personal data in repo | User chooses what to commit; document privacy tradeoffs in README |
| Public deployment | Deployed app exposes your notes — use demo subset or password protect (Streamlit auth optional) |
| URL fetching (link capture) | Validate URLs; timeout; size limits; no SSRF to internal networks |
| File capture | Sanitize filenames; reject executables; size cap (e.g. 10 MB) |
| LLM data leakage | Groq privacy policy applies; don't send secrets in note content |

---

## 11. Error Handling & Observability

### 11.1 Failure Modes

| Stage | Failure | Behavior |
|-------|---------|----------|
| Capture | Invalid file / URL | Return error message; don't write partial capture |
| Classify | LLM timeout / bad JSON | Retry once; log raw response; skip note |
| Link | No similar notes | Normal — note saved without links |
| Graph | Empty wiki | Write empty graph with meta; UI shows empty state |
| Ask | No relevant notes | Return "I couldn't find anything relevant in your notes" |

### 11.2 Logging

Use Python `logging` module with structured messages:

```
INFO  capture: saved raw/a1b2c3d4.txt
INFO  classify: wiki/Projects/a1b2c3d4.md para=Projects tags=3
INFO  link: added 2 links to a1b2c3d4 (scores: 0.81, 0.77)
INFO  ask: retrieved 5 notes, synthesized answer (142 tokens)
```

---

## 12. Testing Strategy

| Layer | Approach |
|-------|----------|
| Capture | Unit tests: UUID uniqueness, timestamp format, file types |
| Classify | Mock LLM; test JSON parsing and wiki file creation |
| Link | Fixed embeddings; assert threshold behavior |
| Graph | Fixture wiki folder → expected nodes/edges count |
| Ask | Mock retrieval + LLM; verify source list |
| E2E | Manual: capture 10+ real items → classify → link → graph → ask |

**Primary validation:** Real personal data, not synthetic test fixtures (per problem statement).

---

## 13. Technology Stack Summary

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| Capture / pipeline | stdlib, `pathlib`, `uuid`, `requests` (URL fetch) |
| LLM | Groq API (`groq` SDK), Llama 3 |
| Embeddings | `sentence-transformers`, `numpy` |
| Markdown | `python-frontmatter` or manual YAML parse |
| Graph UI | `vis-network` (CDN) in Streamlit HTML component |
| Web app | Streamlit |
| Deployment | Streamlit Cloud / Hugging Face Spaces |
| Version control | Git + GitHub |

### 13.1 Core Dependencies (`requirements.txt`)

```
streamlit>=1.28.0
groq>=0.4.0
sentence-transformers>=2.2.0
numpy>=1.24.0
python-frontmatter>=1.0.0
requests>=2.31.0
pyyaml>=6.0
```

---

## 14. Architecture by Week (Build Alignment)

| Week | Architecture Focus | Key Artifacts |
|------|-------------------|---------------|
| **1 — Archivist** | Capture module + raw storage schema | `raw/`, `wiki/`, `capture.py` |
| **2 — Librarian** | LLM classify + embedding link pipeline | `classify.py`, `link.py`, populated `wiki/` |
| **3 — Cartographer** | Graph data model + interactive viz | `build_graph.py`, `graph.json`, HTML graph |
| **4 — Oracle** | RAG ask + Streamlit + deploy | `ask.py`, `app.py`, public URL |

---

## 15. Future Extensions (Out of Scope for v1)

These are not required for the 4-week build but fit the architecture:

- SQLite/vector DB (e.g. Chroma) instead of file-based embeddings
- Incremental graph updates without full rebuild
- Browser extension for one-click capture
- Multi-user auth and isolated knowledge bases
- PDF text extraction via `pymupdf` or `pdfplumber`
- Scheduled re-classification when PARA context changes
- Webhook ingestion (Telegram, email)

---

## 16. Architecture Decision Records (ADRs)

### ADR-001: File-based storage over database

**Decision:** Store captures and wiki notes as files, not SQLite/Postgres.  
**Reason:** Simpler to build, inspect, and version in Week 1–2; sufficient for personal scale.  
**Tradeoff:** Slower similarity search at very large scale (>10K notes).

### ADR-002: Local embeddings, cloud LLM

**Decision:** `sentence-transformers` locally; Groq for generation.  
**Reason:** Free, fast enough, no embedding API costs.  
**Tradeoff:** First embedding load adds ~30s cold start.

### ADR-003: Streamlit as unified UI

**Decision:** Single Streamlit app for graph + Q&A.  
**Reason:** Fastest path to public URL; Python-native.  
**Tradeoff:** Graph interactivity limited vs custom React app.

### ADR-004: Immutable raw, derived wiki

**Decision:** Never mutate `raw/` after capture; all enrichment goes to `wiki/`.  
**Reason:** Audit trail, re-run classify/link without re-capturing.  
**Tradeoff:** Duplicate storage of content.

---

## 17. Glossary

| Term | Definition |
|------|------------|
| **PARA** | Projects, Areas, Resources, Archives — organization framework |
| **RAG** | Retrieval-Augmented Generation — LLM answers grounded in retrieved docs |
| **Capture** | Raw ingestion of note, link, or file |
| **Wiki note** | Classified, tagged, linked markdown file in `wiki/` |
| **Auto-link** | Embedding similarity link between related notes |
| **Graph** | Nodes (notes) + edges (links) exported as JSON |

---

*Next step: Generate [implementation-plan.md](./implementation-plan.md) from this architecture and [Problem-statement.md](./Problem-statement.md).*
