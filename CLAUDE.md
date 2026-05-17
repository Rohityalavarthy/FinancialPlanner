# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A two-session AI finance agent built as a take-home assignment. The agent converses with a scripted user (Priya Sharma) across two sessions, persisting structured memory between them. It is deliberately framework-free — the agentic loop, memory layer, and tool dispatch are all written by hand.

## How to run

```bash
pip install openai python-dotenv
# Set TOGETHER_API_KEY in .env

# Session 1
# Ensure CURRENT_SESSION = 1 in tools.py (line 4)
python agent.py

# Session 2
# Flip CURRENT_SESSION = 2 in tools.py (line 4)
python agent.py
```

Outputs go to `transcripts/session_<n>.md` and `memory.json`.

## Architecture

### Files and their roles

| File | Role |
|---|---|
| `agent.py` | Entry point, agent loop, tool dispatch, memory-update orchestration |
| `tools.py` | Seed data + four tool implementations — **do not modify** |
| `sessions.md` | Scripted user messages — **do not modify** |
| `memory.py` | `load()`, `save()`, `merge_patch()` for `memory.json` |
| `prompts.py` | Two named prompt constants: `AGENT_SYSTEM_PROMPT`, `MEMORY_UPDATE_PROMPT` |

### Agent loop (`run_turn` in agent.py)

Standard tool-use loop: build messages → call model → if `tool_calls` in response, execute each via `tools.TOOLS[name](**args)` and loop back; if no `tool_calls`, return the reply. Capped at 6 tool-call iterations per user turn.

### Memory update (after each assistant turn)

Two-track hybrid:
1. **Deterministic** — `set_reminder` results are written directly to `memory["reminders_set"]` in Python.
2. **LLM-driven** — a separate model call with `MEMORY_UPDATE_PROMPT` extracts new `commitments`, `budget_targets`, and `notes` as a JSON patch. `merge_patch()` in `memory.py` upserts by `id` (commitments) or `category` (budget_targets).

### Memory schema (`memory.json`)

Deliberately excludes balances, transactions, and bills — those are always re-fetched via tools to avoid stale data. The schema holds: `user_profile`, `commitments`, `budget_targets`, `reminders_set`, `notes`, `last_updated`.

### LLM provider

Together AI via OpenAI-compatible SDK. Model: `meta-llama/Llama-3.3-70B-Instruct-Turbo` (constant at top of `agent.py`). API key: `TOGETHER_API_KEY` from `.env`.

### Session switching

`tools.CURRENT_SESSION` (integer 1 or 2) controls which seed data is returned by all four tools and which date the agent treats as "today". The human must flip this between runs.

## Key constraints

- No agent frameworks (LangChain, etc.) — loop is hand-written.
- Math, filtering, and summing are always code (`sum_by_category` helper), never LLM.
- Total agent code (excluding `tools.py`) must stay under ~300 lines.
- Prompts must remain as named constants in `prompts.py`, not inline strings.
