import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import tools
import memory as mem
from prompts import AGENT_SYSTEM_PROMPT, MEMORY_UPDATE_PROMPT

load_dotenv()

MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
MAX_TOOL_ITERATIONS = 6
SESSION_DATES = {1: "2025-11-03", 2: "2025-11-06"}
MONTHLY_INCOME = 120_000
GOAL_AMOUNT = 1_500_000
GOAL_DATE = datetime(2027, 11, 1)

TOOL_SCHEMAS = [
    {"type": "function", "function": {"name": "get_recent_transactions",
        "description": "Returns transactions with pre-computed category_totals. Pass days=35 for prior calendar month.",
        "parameters": {"type": "object", "properties": {"days": {"type": "integer"}}, "required": ["days"]}}},
    {"type": "function", "function": {"name": "get_account_balance",
        "description": "Returns current balances: checking, savings, house_fund, mutual_funds.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "get_upcoming_bills",
        "description": "Returns scheduled bill payments due within the look-ahead window.",
        "parameters": {"type": "object", "properties": {"days": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {"name": "set_reminder",
        "description": "Sets a reminder for Priya on a specific date.",
        "parameters": {"type": "object", "required": ["date", "content"],
            "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}, "content": {"type": "string"}}}}},
]

def months_remaining(today: str) -> int:
    today_dt = datetime.strptime(today, "%Y-%m-%d")
    return (GOAL_DATE.year - today_dt.year) * 12 + (GOAL_DATE.month - today_dt.month)

def sum_by_category(txns, category, start=None, end=None):
    return sum(t["amount_inr"] for t in txns if t["category"] == category
               and (not start or t["date"] >= start) and (not end or t["date"] <= end))

def execute_tool(tc) -> dict | list:
    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
    result = tools.TOOLS[tc.function.name](**args)
    if tc.function.name == "get_recent_transactions":
        totals = defaultdict(int)
        last_month_totals = defaultdict(int)
        today_str = SESSION_DATES[tools.CURRENT_SESSION]
        this_month_start = today_str[:8] + "01"  # YYYY-MM-01
        for t in result:
            totals[t["category"]] += t["amount_inr"]
            if t["date"] < this_month_start:
                last_month_totals[t["category"]] += t["amount_inr"]
        total_spend = sum(totals.values())
        return {"transactions": result, "category_totals": dict(totals),
                "last_month_totals": dict(last_month_totals), "total_spend": total_spend, "count": len(result)}
    if tc.function.name == "get_upcoming_bills":
        return {"bills": result, "bills_total": sum(b["amount_inr"] for b in result), "count": len(result)}
    return result

def log(lines: list, text: str) -> None:
    lines.append(text)
    print(text)

def run_turn(client, messages: list, transcript: list, months_rem: int) -> tuple[str, list]:
    tool_calls_log = []
    tc_data = {}  # accumulates key financials across tool calls in this turn

    for _ in range(MAX_TOOL_ITERATIONS):
        msg = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS, tool_choice="auto"
        ).choices[0].message

        if msg.tool_calls:
            messages.append({
                "role": "assistant", "content": msg.content or "",
                "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
            })
            if not tool_calls_log:
                log(transcript, "**Assistant thinking / tool calls:**")
            for tc in msg.tool_calls:
                result = execute_tool(tc)
                args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                if isinstance(result, dict) and "category_totals" in result:
                    tc_data["total_spend"] = result["total_spend"]
                    tc_data["food_delivery"] = result["category_totals"].get("food_delivery", 0)
                    summary = f"returned {result['count']} txns | totals: {result['category_totals']} | total_spend: ₹{result['total_spend']:,}"
                elif isinstance(result, dict) and "bills_total" in result:
                    tc_data["bills_total"] = result["bills_total"]
                    summary = f"returned {result['count']} bills | total: ₹{result['bills_total']:,} | {result['bills']}"
                elif isinstance(result, dict) and "house_fund" in result:
                    tc_data["house_fund"] = result["house_fund"]
                    tc_data["savings"] = result["savings"]
                    summary = str(result)[:200]
                elif isinstance(result, list):
                    summary = f"returned {len(result)} items: {result}"
                else:
                    summary = str(result)[:120]
                log(transcript, f"- TOOL CALL: {tc.function.name}({tc.function.arguments})\n  → {summary}")
                tool_calls_log.append({
                    "name": tc.function.name, "args": args,
                    "result": result if tc.function.name == "set_reminder" else None,
                })
                messages.append({"role": "tool", "tool_call_id": tc.id,
                                 "content": json.dumps(result, ensure_ascii=False)})

            parts = []
            if "bills_total" in tc_data and "total_spend" in tc_data:
                sc = MONTHLY_INCOME - tc_data["bills_total"] - tc_data["total_spend"]
                parts.append(f"baseline_savings_capacity = ₹{MONTHLY_INCOME:,} − ₹{tc_data['bills_total']:,} − ₹{tc_data['total_spend']:,} = ₹{sc:,}")
            if "house_fund" in tc_data and "savings" in tc_data:
                mt = round((GOAL_AMOUNT - tc_data["house_fund"] - tc_data["savings"]) / months_rem)
                parts.append(f"monthly_savings_target = (₹{GOAL_AMOUNT:,} − ₹{tc_data['house_fund']:,} − ₹{tc_data['savings']:,}) / {months_rem} = ₹{mt:,}")
            if parts:
                messages.append({"role": "user", "content": "[Pre-computed: " + "; ".join(parts) + "]"})
        else:
            reply = msg.content or ""
            messages.append({"role": "assistant", "content": reply})
            log(transcript, f"\n**Assistant reply:**\n{reply}\n")
            return reply, tool_calls_log

    log(transcript, "**WARNING: tool-call cap (6) reached.**")
    return "", tool_calls_log

def update_memory(client, memory: dict, session_num: int,
                  user_msg: str, reply: str, tool_calls_log: list, transcript: list) -> None:
    for tc in tool_calls_log:
        if tc["name"] == "set_reminder" and isinstance(tc.get("result"), dict):
            r = tc["result"]
            entry = {"reminder_id": r["reminder_id"], "date": tc["args"]["date"], "content": tc["args"]["content"]}
            if entry["reminder_id"] not in [x["reminder_id"] for x in memory.get("reminders_set", [])]:
                memory.setdefault("reminders_set", []).append(entry)
                log(transcript, f"- reminder recorded: {entry['reminder_id']} on {entry['date']}")

    tool_summary = json.dumps([{"name": tc["name"], "args": tc["args"]} for tc in tool_calls_log])
    prompt = (
        MEMORY_UPDATE_PROMPT
        + f"\n\nSession: {session_num}\nUser: {user_msg}\nAssistant: {reply}\n"
        + f"Tools called: {tool_summary}\nCurrent memory:\n{json.dumps(memory, indent=2, ensure_ascii=False)}"
    )
    try:
        raw = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0
        ).choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE).strip()
        patch = json.loads(raw)
        if patch:
            mem.merge_patch(memory, patch)
            for key, items in patch.items():
                if items:
                    log(transcript, f"- memory [{key}]: {len(items) if isinstance(items, list) else 1} item(s)")
    except Exception as e:
        print(f"  Memory update skipped: {e}")
    mem.save(memory)

def load_sessions() -> dict:
    content = Path("sessions.md").read_text(encoding="utf-8")
    sessions, current, messages = {}, None, []
    for line in content.splitlines():
        m = re.match(r"^## Session (\d+)", line)
        if m:
            if current is not None:
                sessions[current] = messages
            current, messages = int(m.group(1)), []
        elif current is not None and re.match(r"^\d+\.", line):
            msg = re.sub(r"^\d+\.\s*", "", line).strip()
            if msg:
                messages.append(msg)
    if current is not None:
        sessions[current] = messages
    return sessions

def build_system(today: str, memory: dict, months_rem: int) -> str:
    mem_str = json.dumps(memory, indent=2, ensure_ascii=False)
    return (AGENT_SYSTEM_PROMPT
            .replace("{today}", today)
            .replace("{memory}", mem_str)
            .replace("{months_remaining}", str(months_rem)))

def main():
    client = OpenAI(api_key=os.environ["TOGETHER_API_KEY"], base_url="https://api.together.xyz/v1")
    session_num = tools.CURRENT_SESSION
    today = SESSION_DATES[session_num]
    months_rem = months_remaining(today)
    print(f"=== Session {session_num} — {today} ===\n")

    memory = mem.load()
    user_messages = load_sessions()[session_num]
    Path("transcripts").mkdir(exist_ok=True)

    transcript = [
        f"# Session {session_num} — {today}\n",
        "## Memory at start",
        f"```json\n{json.dumps(memory, indent=2, ensure_ascii=False)}\n```",
        "\n---\n",
    ]
    messages = [{"role": "system", "content": build_system(today, memory, months_rem)}]

    for turn_num, user_msg in enumerate(user_messages, 1):
        log(transcript, f"### User turn {turn_num}")
        log(transcript, f"> {user_msg}\n")
        messages[0] = {"role": "system", "content": build_system(today, memory, months_rem)}
        messages.append({"role": "user", "content": user_msg})
        reply, tool_calls_log = run_turn(client, messages, transcript, months_rem)
        log(transcript, "\n**Memory writes:**")
        update_memory(client, memory, session_num, user_msg, reply, tool_calls_log, transcript)
        transcript.append("\n---\n")

    out = f"transcripts/session_{session_num}.md"
    Path(out).write_text("\n".join(transcript), encoding="utf-8")
    print(f"\nTranscript → {out}\nMemory     → memory.json")

if __name__ == "__main__":
    main()