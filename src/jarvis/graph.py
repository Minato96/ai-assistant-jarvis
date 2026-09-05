"""The LangGraph: recall memory, run an agent/tools loop, then persist new memories.

Short-term state (this conversation thread) lives in the LangGraph checkpointer.
Long-term state (facts/preferences) lives in Mem0. Structured operational data
(goals/tasks/routines) lives in SQLite, reachable only through the bound tools
below. Recall and remember are fixed graph edges, not LLM judgment calls — the
LLM's only decision is whether/which tool to call, which is what the
agent<->tools loop is for.
"""
from __future__ import annotations

import logging
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from mem0 import Memory

from .config import Settings
from .tools import ALL_TOOLS

logger = logging.getLogger("jarvis.graph")

SYSTEM_PROMPT = """You are Jarvis, a personal AI coach and friend for a final-year \
ECE student juggling academics, a relationship, digital wellbeing, and a longer-term \
ambition in blockchain/AI. Be warm, direct, and concise. Favor autonomy-supportive \
phrasing over nagging: ask rather than assert when a trade-off is close, and surface \
patterns rather than relitigating single instances.

You have tools for goals, tasks, and routine blocks (a real SQLite store, not your \
memory of the conversation). Use them whenever the user asks you to track, list, \
update, or complete something concrete — don't just say you'll remember it in words.

Don't just go along with whatever's proposed. Whenever the user floats something \
that could affect their plans — a new commitment, a schedule change, blowing off \
something, staying up late — check list_tasks, list_goals, and list_routine_blocks \
first, even if they didn't ask you to. If there's a real conflict (an exam \
tomorrow, a deadline that night, a fixed block), push back and name the specific \
thing, don't quietly agree. If they push back with an actual reason (it's genuinely \
low-stakes, this matters more right now), don't fold immediately either — weigh it \
out loud, ask what would make both things work, or flag the risk once more. Either \
way, the call is theirs to make — your job is to make sure they're making it with \
eyes open, not to block it or rubber-stamp it.

You're replying inside Telegram, which uses its own lightweight Markdown, not \
GitHub-style: *word* for bold (single asterisk, not double), _word_ for italics, \
`code` for inline code, and a blank line between paragraphs. Don't use double \
asterisks, headers (#), or tables — they won't render. Use formatting sparingly, \
only where it actually helps (a key term, a short list), not on every message."""


class JarvisState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    memory_context: Optional[str]


def build_graph(settings: Settings, memory: Memory):
    llm = ChatOpenAI(
        model=settings.model_name,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    ).bind_tools(ALL_TOOLS)

    def recall(state: JarvisState) -> dict:
        user_id = state["user_id"]
        last_human = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )

        memory_context = ""
        if last_human is not None:
            try:
                hits = memory.search(
                    query=last_human.content, filters={"user_id": user_id}, top_k=5
                )
                results = hits.get("results", hits) if isinstance(hits, dict) else hits
                memory_context = "\n".join(f"- {r['memory']}" for r in results)
            except Exception:
                logger.exception("Mem0 search failed; continuing without recalled memories")

        return {"memory_context": memory_context}

    def agent(state: JarvisState) -> dict:
        system = SYSTEM_PROMPT
        if state.get("memory_context"):
            system += f"\n\nWhat you remember about the user:\n{state['memory_context']}"

        response = llm.invoke([SystemMessage(content=system), *state["messages"]])
        return {"messages": [response]}

    def remember(state: JarvisState) -> dict:
        user_id = state["user_id"]
        last_human = next(
            (m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)),
            None,
        )
        final_reply = state["messages"][-1]

        payload = []
        if last_human is not None:
            payload.append({"role": "user", "content": last_human.content})
        payload.append({"role": "assistant", "content": final_reply.content})

        try:
            memory.add(payload, user_id=user_id)
        except Exception:
            logger.exception("Mem0 add failed; the reply already went out, so continuing")
        return {}

    graph = StateGraph(JarvisState)
    graph.add_node("recall", recall)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(ALL_TOOLS))
    graph.add_node("remember", remember)

    graph.add_edge(START, "recall")
    graph.add_edge("recall", "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "remember"})
    graph.add_edge("tools", "agent")
    graph.add_edge("remember", END)

    return graph.compile(checkpointer=MemorySaver())
