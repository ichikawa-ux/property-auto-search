import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

PROPERTIES_JSON = "docs/data/properties.json"


def load_seen_ids() -> set[str]:
    """Return set of property unique IDs already recorded (from JSON file)."""
    if not os.path.exists(PROPERTIES_JSON):
        return set()
    try:
        with open(PROPERTIES_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return {p["id"] for p in data if "id" in p}
    except (json.JSONDecodeError, KeyError):
        return set()


def save_properties(properties: list, condition_name: str):
    """Append new properties to docs/data/properties.json."""
    if not properties:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _update_json(properties, now, condition_name)


def _update_json(new_properties: list, detected_at: str, condition_name: str):
    """Merge new properties into docs/data/properties.json."""
    existing = []
    if os.path.exists(PROPERTIES_JSON):
        with open(PROPERTIES_JSON, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []

    existing_ids = {p["id"] for p in existing}
    for prop in new_properties:
        d = prop.to_dict()
        d["detected_at"] = detected_at
        d["condition_name"] = condition_name
        if d["id"] not in existing_ids:
            existing.append(d)

    # Keep only last 500 properties in JSON to limit file size
    existing = sorted(existing, key=lambda x: x.get("detected_at", ""), reverse=True)[:500]

    os.makedirs(os.path.dirname(PROPERTIES_JSON), exist_ok=True)
    with open(PROPERTIES_JSON, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info(f"Updated {PROPERTIES_JSON} ({len(existing)} total properties)")
