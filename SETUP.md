# Setup (fresh machine)

This assumes you're setting up on a new OS install with nothing but this repo cloned from GitHub. No secrets or personal data live in the repo — `data/` and `.env` are gitignored, so if you have a backup of them from a previous machine, restoring it (step 5) skips most of the re-setup below.

## 1. System prerequisites (Fedora)

```bash
sudo dnf install git python3.12
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your shell (or `source ~/.bashrc`) so `uv` is on your `PATH`.

One thing that's actually *easier* on a real desktop Fedora install than it was in WSL: Google Calendar's one-time OAuth step (§6 below) opens a browser automatically. WSL had no browser installed at all, which meant copy-pasting the auth URL into a Windows browser by hand. Fedora Workstation ships Firefox by default, so this should just work.

## 2. Clone and install

```bash
git clone https://github.com/Minato96/ai-assistant-jarvis.git
cd ai-assistant-jarvis
uv sync
```

If `uv sync` ever tries to pull a CUDA build of torch (multi-GB download, several `nvidia-*` packages) instead of the small CPU-only one, something's wrong with the `[tool.uv.sources]` override in `pyproject.toml` — it should already force the CPU index, but if this machine has an NVIDIA GPU, double check `uv.lock` resolves `torch` from `download.pytorch.org/whl/cpu`, not plain `pypi.org`.

## 3. Restore your data backup (if you made one)

If you backed up `data/` and `.env` before wiping the old machine:

```bash
tar -xzf /path/to/jarvis-data-backup-YYYYMMDD.tar.gz -C .
```

That restores your tasks/goals/routines (SQLite), Mem0's memory store, your Google Calendar OAuth token, and `.env` — skip straight to step 7 (running the bot).

**No backup?** Continue with the steps below — you'll rebuild `.env` from scratch and Mem0/tasks start empty. Calendar can't be skipped either way; OAuth tokens don't transfer across a full OS wipe if you didn't back up `data/google_token.json`.

## 4. Create `.env`

```bash
cp .env.example .env
```

Fill in:

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram — `/newbot`, or `/token` if you still have the same bot |
| `LLM_API_KEY` | Your LLM provider's key (DeepSeek platform or OpenRouter) |
| `LLM_BASE_URL` | `https://api.deepseek.com` (DeepSeek direct) or `https://openrouter.ai/api/v1` (OpenRouter) |
| `MODEL_NAME` | Exact model slug for whichever provider you're using — verify at the provider's docs, don't guess |
| `TIMEZONE` | IANA timezone, e.g. `Asia/Kolkata` |
| `ALLOWED_TELEGRAM_USER_ID` | Leave blank on first run — see step 8 |

## 5. Google Calendar setup

If you restored `data/google_credentials.json` and `data/google_token.json` from a backup, skip this entirely — the calendar tools will just work.

Otherwise, from scratch:

1. [console.cloud.google.com](https://console.cloud.google.com) → new project
2. **APIs & Services → Library** → enable "Google Calendar API"
3. **APIs & Services → OAuth consent screen** → External → add your own email under **Test users**
4. **APIs & Services → Credentials** → Create Credentials → OAuth client ID → **Desktop app**
5. Download the JSON, save as `data/google_credentials.json`
6. Run the one-time interactive authorization:

```bash
uv run python scripts/authorize_calendar.py
```

## 6. Sanity-check before going live

```bash
uv run python scripts/smoke_test.py "Hey, quick check that you're online."
```

This exercises the LLM, Mem0, and the tool-calling loop without touching Telegram — confirm it replies sensibly before moving on.

## 7. Run the bot

```bash
uv run jarvis
```

## 8. Lock the bot to yourself

On first run with `ALLOWED_TELEGRAM_USER_ID` blank, the bot logs a warning with your numeric Telegram user ID the first time it sees a message from anyone. Message the bot once, copy that ID from the log, set it in `.env`, restart. Until you do this, anyone who finds the bot's username can talk to it.

See [ARCHITECTURE.md](ARCHITECTURE.md) for how everything actually fits together, and [ROADMAP.md](ROADMAP.md) for what's built vs. planned.
