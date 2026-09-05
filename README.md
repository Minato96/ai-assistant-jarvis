# Jarvis

A personal AI assistant over Telegram, built to act as a coach and friend — not just a chatbot that answers questions, but one that tracks real commitments, pushes back when something doesn't add up, and reasons about tradeoffs instead of rubber-stamping whatever's asked.

Built for a single user (no multi-tenant/auth — this is intentionally not a SaaS product) on LangGraph, Mem0, and a provider-agnostic LLM backend.

## What it actually does right now

- **Telegram front door** — talk to it like any other chat. Long-polling bot, per-chat conversation state.
- **Structured tracking** (SQLite) — goals, tasks, and recurring routine blocks, exposed to the model as real tool calls, not vibes. "What's due Thursday" gets an exact answer, not a guess.
- **Google Calendar** — reads your actual schedule and can add/update/delete events. Every write is a two-step confirm (propose → explicit yes → execute) since this is a real side effect on your actual calendar.
- **Long-term memory** (Mem0, running locally — no hosted account needed) — freeform facts and preferences that don't fit a database column ("stressed about the DBMS exam," "prefers concise answers").
- **Judgment, not just retrieval** — the agent checks your actual commitments before agreeing to schedule-affecting requests. Fixed/external things (exams, deadlines, classes) get genuine pushback and negotiation. Self-directed things (a movie, dinner, project time) get scheduling help with no moral judgment attached. It also reasons about physical reality, not just calendar overlaps — a plan that's technically conflict-free but leaves no real time to sleep gets flagged as such.

## What's not built yet

- A real safety gate in front of every write-tool (the calendar confirm-step is a stopgap, not the final design)
- Digital wellbeing / screen-time ingestion
- The proactive nudge engine (scheduled check-ins, pattern-surfacing over time)
- Adaptive replanning as its own flow

This is being built incrementally and in the open — the gaps above are known, not hidden.

## Architecture

Three deliberately separate persistence layers:

- **LangGraph checkpointer** — short-term, per-conversation state
- **Mem0** — long-term freeform memory (vector search)
- **SQLite** — structured operational data (goals/tasks/routines) with real fields

Kept separate on purpose: "what's due Thursday" needs an exact answer, which vector search over freeform memory is the wrong tool for.

The agent itself is a LangGraph tool-calling loop (`agent` ↔ `tools`), not a single LLM call narrating what it did — CRUD operations and calendar actions are real, fixed-path tool executions; the LLM's job is deciding when to call them and how to reason about the results.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env
```

Fill in `.env`:

| Variable | What it is |
|---|---|
| `TELEGRAM_BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `LLM_API_KEY` / `LLM_BASE_URL` / `MODEL_NAME` | Any OpenAI-compatible endpoint (DeepSeek, OpenRouter, etc.) |
| `TIMEZONE` | IANA timezone, e.g. `Asia/Kolkata` |
| `ALLOWED_TELEGRAM_USER_ID` | Locks the bot to one Telegram user (leave blank on first run — the bot logs your ID when it sees a message from an unrecognized sender) |

For Calendar: create a Google Cloud project, enable the Calendar API, create an OAuth Desktop-app client, save the credentials JSON as `data/google_credentials.json`, then run the one-time interactive authorization:

```bash
uv run python scripts/authorize_calendar.py
```

Run the bot:

```bash
uv run jarvis
```

Or sanity-check the graph without Telegram:

```bash
uv run python scripts/smoke_test.py "some message"
```
