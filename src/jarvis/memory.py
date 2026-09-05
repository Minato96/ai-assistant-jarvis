"""Long-term memory (Mem0): freeform facts/preferences pulled out of conversation.

Local vector store (Chroma) + local embedder — no Mem0 account needed. Torch
is pinned to the CPU-only wheel index (see pyproject.toml) since this only
ever embeds short chat snippets; the CUDA build would be pure dead weight.
Mem0's own fact-extraction step uses an LLM, routed through the same
provider-agnostic endpoint as the main chat model.
"""
from __future__ import annotations

from pathlib import Path

from mem0 import Memory

from .config import Settings

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def build_memory(settings: Settings) -> Memory:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    config = {
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "jarvis_memory",
                "path": str(DATA_DIR / "mem0_chroma"),
            },
        },
        "embedder": {
            "provider": "huggingface",
            "config": {"model": "sentence-transformers/all-MiniLM-L6-v2"},
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": settings.model_name,
                "api_key": settings.llm_api_key,
                "openai_base_url": settings.llm_base_url,
            },
        },
    }
    return Memory.from_config(config)
