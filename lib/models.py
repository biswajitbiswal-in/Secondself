"""
Shared dataclasses for SecondSelf.

These models are used across all phases and represent the core data types
in the system: raw captures, wiki notes, graph entities, and Q&A results.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CaptureMeta:
    """Metadata for a raw capture stored in raw/{id}/meta.json."""
    id: str
    timestamp: str
    type: str  # 'note' | 'link' | 'file'
    source: str  # 'cli' | 'stdin' | 'filepath'
    original_filename: Optional[str] = None
    content_hash: Optional[str] = None


@dataclass
class CaptureResult:
    """Return value from a capture operation."""
    id: str
    path: str
    type: str  # 'note' | 'link' | 'file'


@dataclass
class WikiNote:
    """A processed wiki note stored in wiki/{para}/{id}.md."""
    id: str
    raw_id: str
    para: str  # 'Projects' | 'Areas' | 'Resources' | 'Archives'
    tags: list = field(default_factory=list)
    summary: str = ""
    created: str = ""
    links: list = field(default_factory=list)
    body: str = ""
    source_url: str = ""  # Original source URL (for link/web captures)


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: str
    label: str
    para: str
    tags: list = field(default_factory=list)
    summary: str = ""
    content_preview: str = ""
    group: str = ""


@dataclass
class GraphEdge:
    """An edge in the knowledge graph."""
    source: str
    target: str
    weight: float = 1.0
    type: str = "semantic"  # 'semantic' | 'explicit'


@dataclass
class AskResult:
    """Result from a Q&A query to the RAG engine."""
    answer: str
    sources: list = field(default_factory=list)  # list of dicts with id, summary, relevance_score, para

