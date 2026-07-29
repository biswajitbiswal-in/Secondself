# SecondSelf — Phase-Wise Testing Guide

> **Status:** This document contains test commands for completed phases only.
> Last updated: 2026-07-25

---

## How to Use This Guide

Each phase section below contains:
1. **Pre-requisites** — What must be in place before testing
2. **Test commands** — Exact CLI commands to run
3. **Expected output** — What you should see if the phase is working
4. **Verification checks** — Manual checks to confirm functionality

---

## Phase 0 — Foundation (✅ Completed)

**Goal:** Verify the repo scaffold, shared libraries, and directory structure.

### Pre-requisites
- Virtual environment activated: `.venv\Scripts\activate`
- Dependencies installed: `pip install -r requirements.txt`

### Test Commands

```bash
# 0.1 — Verify all directories exist
dir raw
dir wiki
dir wiki\Projects
dir wiki\Areas
dir wiki\Resources
dir wiki\Archives
dir data
dir lib
dir embeddings

# 0.2 — Verify shared library imports work
python -c "from lib import models, storage; print('✓ lib imports OK')"

# 0.3 — Verify specific model dataclasses
python -c "
from lib.models import WikiNote, GraphNode, GraphEdge, AskResult
n = WikiNote(id='test', raw_id='test', para='Resources', summary='test')
print(f'✓ WikiNote created: {n.id} -> {n.para}')
"

# 0.4 — Verify storage layer (read/write index)
python -c "
from lib.storage import load_index, save_index
idx = load_index()
print(f'✓ Index loaded: {len(idx.get(\"raw_processed\", {}))} items processed')
print(f'✓ Embeddings version: {idx.get(\"embeddings_version\")}')
print(f'✓ Last graph build: {idx.get(\"last_graph_build\")}')
"

# 0.5 — Verify config loads with correct paths
python -c "
import config
print(f'✓ BASE_DIR: {config.BASE_DIR}')
print(f'✓ RAW_DIR: {config.RAW_DIR}')
print(f'✓ WIKI_DIR: {config.WIKI_DIR}')
print(f'✓ Embedding model: {config.EMBEDDING_MODEL}')
print(f'✓ Similarity threshold: {config.SIMILARITY_THRESHOLD}')
print(f'✓ PARA categories: {config.PARA_CATEGORIES}')
"
```

### Verification Checklist

- [ ] All 8 directories exist (raw, wiki, wiki/Projects, wiki/Areas, wiki/Resources, wiki/Archives, data, lib)
- [ ] `lib/models.py` imports without errors
- [ ] `lib/storage.py` imports without errors
- [ ] `data/index.json` exists with proper schema
- [ ] `config.py` loads with correct paths

---

## Phase 1 — The Archivist (✅ Completed)

**Goal:** Test the capture pipeline — ingesting notes, URLs, and files into `raw/`.

### Pre-requisites
- Phase 0 verified (all directories exist)
- Virtual environment activated

### Test Commands

```bash
# 1.1 — Capture a text note
python capture.py note "Career goal: transition to ML engineering by Q4"

# 1.2 — Capture a URL link (webpage content)
python capture.py --link "https://huggingface.co/sentence-transformers"

# 1.3 — Capture a local text file
python capture.py --file "README.md"

# 1.4 — Show a specific capture by ID (use the folder name or ID)
python capture.py --show 20260724

# 1.5 — List all raw captures (count folders)
dir raw /b | find /c "."

# Expected: 29+ folders

# 1.6 — Inspect a capture's contents
type raw\20260724_130806_39b80248\metadata.json
type raw\20260724_130806_39b80248\content.md

# 1.7 — Sync/organize raw captures (if any flat files exist)
python capture.py --sync-json

# 1.8 — Test edge case: empty note (should fail gracefully)
python capture.py note ""

# 1.9 — Test edge case: invalid URL
python capture.py --link "not-a-valid-url"

# 1.10 — Test edge case: non-existent file
python capture.py --file "C:\nonexistent\file.pdf"

# 1.11 — Test edge case: large content (binary/executable)
python capture.py --file "C:\Windows\System32\notepad.exe"
```

### Verification Checklist

- [ ] `raw/` contains 29+ folders (one per capture)
- [ ] Each folder has `content.md` + `metadata.json`
- [ ] Metadata includes: id, timestamp, type, source
- [ ] Notes contain the raw text content
- [ ] Links store the fetched webpage content
- [ ] Files store the file contents
- [ ] Edge cases handled gracefully

---

## Phase 2 — The Librarian (✅ Completed)

**Goal:** Test classification and auto-linking.

### Pre-requisites
- Phase 1 complete (raw captures exist)
- `GROQ_API_KEY` set in `.env` file

### Sub-Phase 2.1 — Classification Tests

```bash
# 2.1.1 — Verify LLM connection (Groq API)
python -c "
from lib.llm import classify_content
result = classify_content('Test content about machine learning and AI projects.')
print(f'PARA: {result[\"para\"]}')
print(f'Tags: {result[\"tags\"]}')
print(f'Summary: {result[\"summary\"]}')
"

# 2.1.2 — Run classification on all unprocessed captures
python classify.py

# 2.1.3 — Dry run classification
python classify.py --dry-run

# 2.1.4 — Re-process all captures
python classify.py --reprocess

# 2.1.5 — Verify wiki notes were created
dir wiki\Projects /b
dir wiki\Areas /b
dir wiki\Resources /b
dir wiki\Archives /b

# 2.1.6 — Spot-check a classified note
type wiki\Projects\39b80248.md

# 2.1.7 — Count total wiki notes across all categories
python -c "
from pathlib import Path
import config
count = 0
for para in config.PARA_CATEGORIES:
    pd = config.WIKI_DIR / para
    if pd.exists():
        files = list(pd.glob('*.md'))
        count += len(files)
        print(f'{para}: {len(files)} notes')
print(f'Total: {count} notes')
"

# 2.1.8 — Verify search works on classified notes
python search.py "machine learning"
python search.py "SecondSelf"
python search.py "career"
```

### Sub-Phase 2.2 — Auto-Linking Tests

```bash
# 2.2.1 — Verify embedding model loads
python -c "
from lib.embeddings import embed_text
vec = embed_text('Test embedding')
print(f'Vector shape: {vec.shape}')
print(f'Vector dtype: {vec.dtype}')
print(f'First 5 values: {vec[:5]}')
"

# 2.2.2 — Run auto-linking on all wiki notes
python link.py

# 2.2.3 — Dry run linking
python link.py --dry-run

# 2.2.4 — Re-link all notes
python link.py --reprocess

# 2.2.5 — Link with custom similarity threshold
python link.py --threshold 0.80

# 2.2.6 — Link with looser threshold
python link.py --threshold 0.65

# 2.2.7 — Verify links in wiki notes
findstr "\[\[" wiki\Projects\*.md
findstr "\[\[" wiki\Resources\*.md
findstr "\[\[" wiki\Areas\*.md

# 2.2.8 — Verify frontmatter links
python -c "
from lib.storage import read_wiki_notes
notes = read_wiki_notes()
for n in notes:
    if n.links:
        print(f'{n.id} ({n.para}) → {n.links}')
"

# 2.2.9 — Check embeddings file
python view_embeddings.py --summary
```

### Full Pipeline Test

```bash
# 2.2.10 — Run the complete pipeline (classify + link + graph)
python pipeline.py process

# 2.2.11 — Run pipeline with dry-run flag
python pipeline.py process --dry-run

# 2.2.12 — Run classify-only via pipeline
python pipeline.py classify

# 2.2.13 — Run link-only via pipeline
python pipeline.py link

# 2.2.14 — Count wikilinks present
python -c "
from pathlib import Path
import re, config
total_links = 0
for para in config.PARA_CATEGORIES:
    pd = config.WIKI_DIR / para
    if pd.exists():
        for f in pd.glob('*.md'):
            content = f.read_text()
            links = re.findall(r'\[\[([^\]]+)\]\]', content)
            total_links += len(links)
print(f'Total wikilinks across all notes: {total_links}')
"
```

### Verification Checklist

- [ ] 21+ wiki notes across PARA categories (Projects, Areas, Resources)
- [ ] Each wiki note has YAML frontmatter with: id, raw_id, para, tags, summary, created
- [ ] Notes classified into appropriate PARA categories by LLM
- [ ] Tags are relevant to content
- [ ] Summaries are descriptive one-liners
- [ ] `embeddings.pkl` exists in `data/` folder
- [ ] Wiki notes have `links: [...]` in frontmatter with other note IDs
- [ ] Wiki notes have `[[note-id]]` wikilinks in body content
- [ ] `pipeline.py process` runs end-to-end without errors
- [ ] `view_embeddings.py` shows all notes with vector info

---

## Phase 3 — The Cartographer (✅ Completed)

**
