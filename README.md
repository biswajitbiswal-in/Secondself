# SecondSelf — Personal AI Second Brain

SecondSelf is a personal knowledge pipeline that turns scattered notes, links, and files into a self-organizing, queryable second brain using local vector embeddings and AI LLM categorization.

## 🚀 Features

- **Raw Capture:** One-command ingestion for text notes, web URLs, and files.
- **Auto-Classification:** Intelligent PARA categorization (Projects, Areas, Resources, Archives), tagging, and summarizing via Groq (Llama 3).
- **Auto-Linking:** Local semantic similarity search auto-connects related knowledge.
- **Interactive Graph:** Visual force-directed graph visualization of note relationships.
- **RAG Q&A:** Grounded answers synthesized directly from your personal knowledge base.

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
├── config.py            # Central configuration & paths
├── capture.py           # CLI & ingestion module
├── classify.py          # LLM classification module
├── link.py              # Embedding auto-linking module
├── build_graph.py       # Graph JSON builder
├── ask.py               # RAG Q&A engine
├── app.py               # Streamlit application entry point
├── requirements.txt     # Dependency specifications
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

- **Capture:** `python capture.py "My note content"`
- **Classify:** `python classify.py --all`
- **Link:** `python link.py --all`
- **Build Graph:** `python build_graph.py`
- **Ask CLI:** `python ask.py "What notes do I have about AI?"`
- **Web Interface:** `streamlit run app.py`
