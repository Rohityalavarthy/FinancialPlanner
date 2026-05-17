# Finance Companion Agent

A two-session AI finance agent built without frameworks. The agent converses with a scripted user (Priya Sharma), persists structured memory between sessions, and demonstrates cross-session learning by connecting a new purchase question in Session 2 to commitments made in Session 1.

---

## How to run

```bash
pip install openai python-dotenv
```

Create a `.env` file with your Together AI key:
```
TOGETHER_API_KEY=your_key_here
```

**Session 1:**
```bash
# Confirm tools.py line 4: CURRENT_SESSION = 1
python agent.py
```

**Session 2:**
```bash
# Change tools.py line 4 to: CURRENT_SESSION = 2
python agent.py
```

Do **not** delete `memory.json` between sessions — Session 2 reads what Session 1 wrote.

Outputs:
- `transcripts/session_1.md` and `transcripts/session_2.md` — full logs of tool calls, replies, and memory writes
- `memory.json` — structured memory persisted to disk

---

## Architecture

### Files

| File | Role |
|---|---|
| `agent.py` | Entry point, agent loop, tool dispatch, financial injection, memory orchestration |
| `memory.py` | `load()`, `save()`, `merge_patch()` for `memory.json` |
| `prompts.py` | Two named prompt constants: `AGENT_SYSTEM_PROMPT`, `MEMORY_UPDATE_PROMPT` |
| `tools.py` | Seed data + four tool implementations — **provided, do not modify** |
| `sessions.md` | Scripted user messages — **provided, do not modify** |

Line count: `agent.py` (217) + `memory.py` (53) = **270 lines** of agent logic. `prompts.py` (90 lines) contains only named string constants.

### Agent loop (`run_turn`)

Standard tool-use loop:
1. Call model with tools and current message history
2. If response contains `tool_calls`: execute each via `tools.TOOLS[name](**args)`, append results, loop back
3. If no `tool_calls`: return the reply text
4. Cap at 6 tool-call iterations per turn

### Tool dispatch (`execute_tool`)

All arithmetic is done in Python here — not delegated to the LLM:

- `get_recent_transactions` → adds `category_totals`, `last_month_totals` (prior calendar month only), and `total_spend`
- `get_upcoming_bills` → adds `bills_total`

After each round of tool calls, `run_turn` injects a `[Pre-computed: ...]` message with `baseline_savings_capacity` and `monthly_savings_target` calculated in Python. The model reads these numbers; it never computes them.

### Memory layer (`memory.py` + `update_memory`)

**Schema** (`memory.json`):
```json
{
  "user_profile":    { "name", "age", "city", "monthly_income_inr", "stated_goal" },
  "commitments":     [ { "id", "description", "amount_inr", "target_date", "status" } ],
  "budget_targets":  [ { "category", "monthly_cap_inr", "rationale" } ],
  "reminders_set":   [ { "reminder_id", "date", "content" } ],
  "notes":           [ "string" ],
  "last_updated":    "ISO timestamp"
}
```

**Deliberately not stored:** balances, transaction lists, bill amounts — anything re-fetchable via tools. Stale numbers in memory are a bug; re-fetching is the fix.

**Update mechanism — two tracks:**
1. **Deterministic (code):** `set_reminder` results are written directly to `reminders_set` without an LLM call.
2. **LLM-driven:** a focused second model call with `MEMORY_UPDATE_PROMPT` extracts new/updated `commitments`, `budget_targets`, and `notes` as a JSON patch. `merge_patch()` upserts by `id` (commitments) or `category` (budget_targets), deduplicating automatically.

### LLM provider

Together AI via OpenAI-compatible SDK. The `base_url` is pointed at `https://api.together.xyz/v1`; the SDK is otherwise unchanged. Model is a single constant at the top of `agent.py` for easy swapping.

---

## Design decisions

### Math in code, judgment in LLM

Every calculation that has a deterministic answer lives in Python: summing bills, totalling category spend, filtering to last month, computing savings capacity, computing monthly savings target. The LLM decides which tool to call, how to frame a trade-off, and what to say — not what numbers to add.

### Memory discipline

Session 2 never reads balances or transactions from memory. It always calls `get_account_balance` and `get_upcoming_bills` fresh — the seed data shows the checking balance dropping ₹25,000 (rent paid) and rent disappearing from upcoming bills between Session 1 and Session 2. If those were stored, Session 2 would quote stale figures.

What memory *does* store: the ₹30,000 house fund commitment and Nov 25 transfer date. Session 2 uses this to proactively connect the MacBook question to the existing plan — without being prompted.

### Per-turn memory updates

Memory is written after every completed assistant turn, not at the end of the session. This means if the session crashes mid-way, progress is not lost. The trade-off is extra LLM calls; the benefit is durability and legibility in the transcript logs.

---

## Prompt design

**`AGENT_SYSTEM_PROMPT`** — the main chat prompt. Key sections:
- *Tool discipline*: hard rules for when to call which tool, and what to use from each result
- *Pre-computed financials*: instructs the model to use injected values for savings capacity and monthly target — not to recompute
- *Behavior*: lead with the answer, walk through the reasoning in prose, name amounts explicitly
- *Evaluating a large purchase*: cash-flow chain from checking balance, savings as gap-filler, required `set_reminder` call

**`MEMORY_UPDATE_PROMPT`** — the memory-extraction prompt. Returns JSON only. Key rules: only write commitments on explicit user confirmation, write the *new* budget cap (not current spend), never store re-fetchable data, always write at least one note if anything financially significant was discussed.
