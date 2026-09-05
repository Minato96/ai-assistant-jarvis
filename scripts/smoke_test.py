"""One-shot check that config -> Mem0 -> LangGraph -> OpenRouter all wire up.

Usage: uv run python scripts/smoke_test.py "some message"
"""
from __future__ import annotations

import sys

from langchain_core.messages import HumanMessage

from jarvis.config import load_settings
from jarvis.graph import build_graph
from jarvis.memory import build_memory


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else "Hey, quick check that you're online."

    settings = load_settings()
    print(f"Model: {settings.model_name}")

    memory = build_memory(settings)
    graph = build_graph(settings, memory)

    result = graph.invoke(
        {"messages": [HumanMessage(content=text)], "user_id": "smoke_test"},
        config={"configurable": {"thread_id": "smoke_test"}},
    )
    print("Jarvis:", result["messages"][-1].content)


if __name__ == "__main__":
    main()
