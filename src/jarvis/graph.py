"""The LangGraph skeleton: retrieve relevant memories, respond, then persist new ones.

Short-term state (this conversation thread) lives in the LangGraph checkpointer.
Long-term state (facts/preferences) lives in Mem0. Keeping them separate is
deliberate — see the project's persistence-model notes.
"""
from __future__ import annotations

import logging
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from mem0 import Memory

from .config import Settings

logger = logging.getLogger("jarvis.graph")

SYSTEM_PROMPT = """You are Jarvis, a personal AI coach and friend for a final-year \
ECE student juggling academics, a relationship, digital wellbeing, and a longer-term \
ambition in blockchain/AI. Be warm, direct, and concise. Favor autonomy-supportive \
phrasing over nagging: ask rather than assert when a trade-off is close, and surface \
patterns rather than relitigating single instances.

You're replying inside Telegram, which uses its own lightweight Markdown, not \
GitHub-style: *word* for bold (single asterisk, not double), _word_ for italics, \
`code` for inline code, and a blank line between paragraphs. Don't use double \
asterisks, headers (#), or tables — they won't render. Use formatting sparingly, \
only where it actually helps (a key term, a short list), not on every message."""


class JarvisState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str


def build_graph(settings: Settings, memory: Memory):
    llm = ChatOpenAI(
        model=settings.model_name,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    def respond(state: JarvisState) -> dict:
        user_id = state["user_id"]
        last_human = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )

        memories_text = ""
        if last_human is not None:
            try:
                hits = memory.search(
                    query=last_human.content, filters={"user_id": user_id}, top_k=5
                )
                results = hits.get("results", hits) if isinstance(hits, dict) else hits
                memories_text = "\n".join(f"- {r['memory']}" for r in results)
            except Exception:
                logger.exception("Mem0 search failed; continuing without recalled memories")

        system = SYSTEM_PROMPT
        if memories_text:
            system += f"\n\nWhat you remember about the user:\n{memories_text}"

        response = llm.invoke([SystemMessage(content=system), *state["messages"]])
        return {"messages": [response]}

    def remember(state: JarvisState) -> dict:
        user_id = state["user_id"]
        recent = state["messages"][-2:]
        payload = [
            {
                "role": "user" if isinstance(m, HumanMessage) else "assistant",
                "content": m.content,
            }
            for m in recent
        ]
        try:
            memory.add(payload, user_id=user_id)
        except Exception:
            logger.exception("Mem0 add failed; the reply already went out, so continuing")
        return {}

    graph = StateGraph(JarvisState)
    graph.add_node("respond", respond)
    graph.add_node("remember", remember)
    graph.add_edge(START, "respond")
    graph.add_edge("respond", "remember")
    graph.add_edge("remember", END)

    return graph.compile(checkpointer=MemorySaver())
