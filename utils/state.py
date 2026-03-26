"""Save and load system state so agents remember where they left off."""

import json
from pathlib import Path

STATE_FILE = "state/system_state.json"
Path("state").mkdir(exist_ok=True)

def save_state(data: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_state() -> dict:
    if Path(STATE_FILE).exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}
