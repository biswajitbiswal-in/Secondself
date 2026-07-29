
# SecondSelf — Personal AI Second Brain

SecondSelf is a personal knowledge pipeline that turns scattered notes, links, and files into a self-organizing, queryable second brain using local vector embeddings and AI LLM categorization.

## 🚀 Features

- **Raw Capture:** One-command ingestion for text notes, web URLs, and files.
- **Auto-Classification:** Intelligent PARA categorization (Projects, Areas, Resources, Archives), tagging, and summarizing via Groq (Llama 3).
- **Auto-Linking:** Local semantic similarity search auto-connects related knowledge.
- **Interactive Graph:** Visual force-directed graph visualization of note relationships.
- **RAG Q&A:** Grounded answers synthesized directly from your personal knowledge base.
- **Streamlit Web App:** Unified UI with ask bar, knowledge graph, capture, and pipeline control.

---

## 📁 Repository Structure

```
secondself/
├── raw/                 # Raw capture store (Phase 1)
├── wiki/                # Organized notes store (Phase 2)
│   ├── Projects/
│   ├── Areas/
│   ├── Resources/
│   └── Archives/
├── embeddings/          # Cached embedding vectors (Phase 3)
├── templates/           # HTML templates for graph visualization (Phase 4)
├── docs/                # Architecture & implementation documentation
├── data/                # Graph JSON, indices, persistence
├── static/              # Static assets (graph.html for vis-network)
├── lib/                 # Shared libraries (models, storage, LLM, embeddings)
├── config.py            # Central configuration & paths
├── capture.py           # CLI & ingestion module
├── classify.py          # LLM classification module
├── link.py              # Embedding auto-linking module
├── build_graph.py       # Graph JSON builder
├── ask.py               # RAG Q&A engine
├── app.py               # Streamlit application entry point
├── pipeline.py          # Orchestration script
├── search.py            # Keyword search across wiki notes
├── requirements.txt     # Dependency specifications
├── .env.example         # Environment variable template
└── README.md            # Project documentation
```

---

## ⚙️ Quick Start Setup

### 1. Environment & Dependencies

Create and activate a virtual environment, then install dependencies:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Credentials

Copy `.env.example` to `.env` and set your Groq API key:

```bash
copy .env.example .env
```

Edit `.env`:
```env
GROQ_API_KEY=your_actual_groq_api_key
```

### 3. Verify Setup

Run the setup verification check:

```bash
python -c "import config; print('Setup OK')"
```

---

## 📖 Usage Overview

### CLI Commands

```bash
# Capture a note, link, or file
python capture.py "My note content"
python capture.py "https://example.com/article"
python capture.py ./documents/notes.md

# Classify raw captures into wiki notes
python classify.py

# Auto-link related notes
python link.py

# Build the knowledge graph
python build_graph.py

# Ask questions via CLI
python ask.py "What are my career goals?"
python ask.py "What ML resources have I saved?"

# Full pipeline
python pipeline.py process

# Keyword search
python search.py "machine learning"
```

### 🌐 Web Interface (Streamlit App)

The Streamlit app provides a unified UI for all SecondSelf features:

```bash
streamlit run app.py
```

#### App Layout

```
┌────────────────────────────────────────────────────────────┐
│  🧠 SecondSelf — Personal AI Second Brain                  │
├────────────────────────────────────────────────────────────┤
│  Ask Your Brain: [___________________________] [🔍 Ask]    │
│  + Retrieval options (top-k, threshold)                    │
│  Answer panel with source citations                        │
├────────────────────────────────────────────────────────────┤
│  Knowledge Graph (vis-network) — interactive               │
│  • Hover for tooltips (summary, tags, preview)             │
│  • Click for full detail modal                             │
│  • Filter by PARA category                                 │
│  • Search by label, tag, or summary                        │
├────────────────────────────────────────────────────────────┤
│  Sidebar:                                                  │
│  ├─ Quick Capture (Note / Link / File)                     │
│  ├─ Pipeline Control (Process All / Refresh Graph / Steps) │
│  └─ Stats (Notes, Embeddings, Graph, PARA breakdown)       │
└────────────────────────────────────────────────────────────┘
```

#### Sidebar Features

| Feature | Description |
|---------|-------------|
| **Quick Capture** | Capture notes, URLs, or uploaded files directly from the UI |
| **Process All** | Run classify + link + build graph in one click |
| **Refresh Graph** | Rebuild the knowledge graph from wiki notes |
| **Individual Steps** | Classify, Link, or Build Graph separately |
| **Stats Panel** | See note counts, embedding status, graph sizes, PARA breakdown |

#### Main Panel Features

| Feature | Description |
|---------|-------------|
| **Ask Bar** | Type questions in plain English, get answers from your notes |
| **Retrieval Options** | Adjust top-K and relevance threshold |
| **Answer Display** | Synthesized answer with numbered source citations |
| **Source Cards** | Each source shows ID, summary, category, relevance score |
| **Knowledge Graph** | Interactive vis-network with force-directed layout |
| **Node Details** | Click any node to see full info in a modal |

#### Keyboard Shortcuts (in graph)

| Key | Action |
|-----|--------|
| `Ctrl+F` / `Cmd+F` | Focus search input |
| `Esc` | Close modal / upload panel |
| Scroll | Zoom in/out on graph |
| Drag | Pan around graph |
| Click node | Show detail modal |

---

## 🔄 Pipeline

The full pipeline can be run in one command:

```bash
# Full pipeline: classify → link → build graph
python pipeline.py process

# Or step by step:
python pipeline.py classify
python pipeline.py link
python pipeline.py graph
python pipeline.py ask "Your question here"
```

---

## 🧠 Architecture Overview

```
                   ┌──────────────┐
                   │  capture.py  │
                   │  (Phase 1)   │
                   └──────┬───────┘
                          ▼
                   ┌──────────────┐
                   │  raw/        │
                   │  captures    │
                   └──────┬───────┘
                          ▼
              ┌───────────────────────┐
              │    classify.py        │
              │  (Phase 2 — Sub 2.1)  │
              │  lib/llm.py (Groq)    │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │    wiki/ notes        │
              │  (PARA organized)     │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │    link.py            │
              │  (Phase 2 — Sub 2.2)  │
              │  lib/embeddings.py    │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  build_graph.py       │
              │  (Phase 3)            │
              │  data/graph.json      │
              │  static/graph.html    │
              └───────────┬───────────┘
                          ▼
              ┌───────────────────────┐
              │  ask.py + app.py      │
              │  (Phase 4)            │
              │  RAG + Streamlit UI   │
              └───────────────────────┘
```

---

## 📚 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `streamlit` | >=1.28 | Web application framework |
| `groq` | >=0.4 | Groq Cloud LLM API |
| `sentence-transformers` | >=2.2 | Local embedding generation |
| `numpy` | >=1.24 | Vector operations |
| `python-frontmatter` | >=1.0 | YAML frontmatter parsing |
| `requests` | >=2.31 | HTTP client for URL capture |
| `beautifulsoup4` | >=4.x | HTML text extraction |
| `pypdf` | >=4.0 | PDF text extraction |
| `pyyaml` | >=6.0 | YAML serialization |
| `python-dotenv` | >=1.0 | Environment variable loading |

---

## 🔧 Configuration

Key settings in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `SIMILARITY_THRESHOLD` | 0.75 | Auto-link similarity threshold |
| `TOP_K_RETRIEVAL` | 5 | Number of notes for RAG context |
| `EMBEDDING_MODEL` | all-MiniLM-L6-v2 | sentence-transformers model |
| `GROQ_MODEL` | llama-3.1-8b-instant | LLM for classification & synthesis |
| `MAX_CONTENT_CHARS` | 8000 | Max chars for LLM processing |

---

## 📊 Project Status

| Phase | Name | Badge | Status |
|-------|------|-------|--------|
| 1 | The Archivist | 🏅 | Complete |
| 2 | The Librarian | 🏅 | Complete |
| 3 | The Cartographer | 🏅 | Complete |
| 4 | The Oracle | 🏅 | Complete |

---

## 🚀 Deployment

SecondSelf is designed to be deployed on **Streamlit Community Cloud** for a public demo.

### Live Demo

> 🔗 **[https://secondself-<your-username>.streamlit.app](https://secondself-<your-username>.streamlit.app)**

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| **GitHub account** | Streamlit Cloud deploys from a connected repo |
| **Public repo** | Required for free Community Cloud tier |
| **Groq API key** | [console.groq.com](https://console.groq.com/) — free tier is sufficient |
| **Python 3.11+** | Recommended |

### Deploy Steps

1. **Push to GitHub** — ensure the repo is public
2. **Go to [share.streamlit.io](https://share.streamlit.io)** → Sign in with GitHub
3. **Click "New app"** → select repo, branch (`main`), main file: `app.py`
4. **Click "Deploy"** — Streamlit installs deps from `requirements.txt`
5. **Configure secrets** — In app dashboard → Settings → Secrets, add:
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   ```
6. **Wait for build** (~2-5 min for first build with PyTorch/sentence-transformers)

### Deployment Considerations

| Concern | Strategy |
|---------|----------|
| **Cold starts** | Embedding model loads on first Ask (~30-60s); accept for demo |
| **Ephemeral storage** | Captures and pipeline writes reset on container restart |
| **Public notes** | `wiki/` content is visible to anyone with the URL |
| **API key** | Set via Streamlit Secrets; never commit `.env` |
| **Fast first Ask** | Commit `data/embeddings.pkl` for pre-computed vectors |

### Files to Commit for Deploy

```
app.py               # Streamlit entry point
requirements.txt     # Python dependencies
lib/                 # Shared code
static/              # Graph HTML template
wiki/                # Demo knowledge base
data/graph.json      # Pre-built graph
data/index.json      # Pipeline state
data/embeddings.pkl  # Pre-computed vectors (force-add with -f)
.streamlit/config.toml  # Streamlit configuration
runtime.txt          # Python version pin
```

### Updating

```bash
python pipeline.py process   # Refresh pipeline
python build_graph.py        # Rebuild graph
git add wiki/ data/graph.json data/index.json
git add -f data/embeddings.pkl
git commit -m "Refresh demo data"
git push                    # Auto-redeploys on Streamlit Cloud
```

See [docs/deployement_plan.md](./docs/deployement_plan.md) for the full deployment checklist and troubleshooting guide.

---
