import json
import os
from datetime import datetime, timezone

MEMORY_PATH = "memory.json"

_SEED = {
    "user_profile": {
        "name": "Priya Sharma",
        "age": 28,
        "city": "Bangalore",
        "monthly_income_inr": 120000,
        "stated_goal": "₹15L house down payment in 2 years",
    },
    "commitments": [],
    "budget_targets": [],
    "reminders_set": [],
    "notes": [],
    "last_updated": None,
}

def load() -> dict:
    if os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
            for k, v in _SEED.items()}

def save(memory: dict) -> None:
    memory["last_updated"] = datetime.now(timezone.utc).isoformat()
    with open(MEMORY_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def merge_patch(memory: dict, patch: dict) -> dict:
    for key in ("commitments", "budget_targets"):
        if not patch.get(key):
            continue
        id_field = "id" if key == "commitments" else "category"
        existing = {item[id_field]: i for i, item in enumerate(memory.get(key, []))}
        for item in patch[key]:
            item_id = item.get(id_field)
            if item_id in existing:
                memory[key][existing[item_id]].update(item)
            else:
                memory.setdefault(key, []).append(item)

    if patch.get("notes"):
        seen = set(memory.get("notes", []))
        for note in patch["notes"]:
            if note not in seen:
                memory.setdefault("notes", []).append(note)
                seen.add(note)

    return memory