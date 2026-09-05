# Roadmap

Living document of what's built, what's next, and ideas raised in conversation that haven't been scoped into concrete work yet. See [ARCHITECTURE.md](ARCHITECTURE.md) for the honest status of each plan component and the end-to-end flow.

## Immediate next step

**The real safety gate (4.5).** Calendar writes currently use a `confirm: bool` two-step as a stopgap — it works, but it's not the safe/ambiguous/dangerous classifier the original plan describes. This is next because it's the natural thing to build now that a real write-tool exists to gate, and because every future write-tool (routine replanning, eventually anything Twilio-adjacent) should sit behind it from day one instead of getting its own bespoke confirm flag.

## Planned, not started

- **Digital wellbeing ingestion (4.4).** Needs: the bot to become an HTTP server (currently pure Telegram long-polling, nothing listening for inbound requests), Tasker/MacroDroid configured on the phone to POST usage events, and — until this moves to an always-on VPS — a tunnel (ngrok or similar) so the phone can actually reach a server running on a laptop. Also: verify Tasker/MacroDroid's actual usage-trigger capabilities in-app before committing to this approach; the original plan flags this as unverified.
- **Proactive nudge engine (4.6).** A scheduled job (not a reaction to a Telegram message) that reads calendar + structured store + Mem0 + accumulated task-outcome data, and makes an LLM judgment call about whether a nudge is warranted. Depends on 4.4 for real usage signal and on the safety gate existing (a nudge is itself a proactive send).
- **Pattern-mining / weekly reflection.** Task-outcome logging (the `focused`/`okay`/`distracted`/`blocked` buttons) started accumulating data as of this session, but nothing reads it yet. The actual ask: notice things like "distracted after a social evening, focused right after a workout" by correlating logged outcomes against what preceded them (routine_blocks/calendar timing), and surface that as a genuine synthesized pattern — not per-instance reactions. This is a periodic look-back job, not a same-turn thing, and it needs real data over real days before there's anything to find.
- **Nudge-effectiveness learning.** A step further than pattern-mining on the user's behavior: the system should also track whether *its own* nudges get acted on, and adjust timing/phrasing accordingly. Ties into the open question below about how much the assistant should own responsibility for planning/nudging failures.
- **Adaptive replanning (4.7) as a standalone flow.** Right now, replanning-style reasoning only happens inside normal conversation (the pushback/scheduling logic already handles "I want to change this plan" reasonably well reactively). The plan describes a more deliberate "something changed, here's how today shifts" flow — not built as its own thing yet.
- **Long/short-term prioritization (4.8), beyond the current prompt-level lean.** The priority ordering (academics > energy/self-care > social/fun) lives in the system prompt today. The plan's original idea of "an editable goals file the assistant reads before close calls" is really the `goals` SQLite table now — worth revisiting whether that's sufficient or whether prioritization needs something richer once the nudge engine exists.

## Explicitly out of scope / deferred (per the original plan)

- **Blockchain RAG subgraph (4.9)** — independent track, doesn't block or get blocked by anything here. Purpose: domain expertise via retrieval for the user's blockchain/AI venture interest, whenever that becomes a priority.
- **Twilio calling (4.10)** — deferred until the safety gate has a track record on lower-stakes tools. An unsupervised phone call is the highest-consequence action this system could take.

## Raised but not scoped yet

- **Diet tracking.** Came up in conversation but isn't in the original v1 plan (which covers digital wellbeing/screen-time, not food logging). Needs its own scoping pass — what data model, what triggers logging, before it's buildable.
- **CI + real test suite.** No `tests/` directory or GitHub Actions exist yet — all verification so far has been manual (`scripts/smoke_test.py`, run by hand). Worth building if a genuine "tests passing" badge is wanted, or just for regression safety as the graph grows more complex. The manual smoke test needs live API keys and can't run in CI as-is; a real suite would need to mock or stub the LLM/Calendar/Telegram calls.
- **LICENSE file.** Repo doesn't have one yet — worth picking one (MIT is the common default for a personal project like this) since it's public.

## Open design question (unresolved — read before building the nudge engine)

The plan's autonomy-supportive design (ask rather than assert, the call is always the user's) sits in tension with a stronger framing raised later: the assistant should own outcomes, and a missed follow-through should be read as the assistant having nudged or planned poorly, not just a user lapse.

Current interpretation, applied so far: the stronger framing shapes how the *system* improves itself over time (get better at timing/phrasing, catch its own planning misses); the original framing still governs actual in-the-moment decisions (the agent asks, pushes back with real directness when it matters, but doesn't override the user's call). This hasn't been explicitly confirmed as the right split — flagged here so it gets settled before the nudge engine is built on top of an assumption.

## Also worth remembering

- **Directness over softness.** Autonomy-supportive phrasing was initially too soft/easy to ignore; the prompt now explicitly says weight/directness matters more than gentleness when something's actually at stake. Keep applying this as new coaching behavior gets added — don't let new features regress back to hedged phrasing.
- **JARVIS persona.** Modeled loosely on Tony Stark's JARVIS — proactive, dry, invested, uses the user's name. Written into the system prompt; keep new features consistent with that voice rather than defaulting to generic assistant tone.
