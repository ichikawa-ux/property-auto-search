import os
import json
import logging
from datetime import datetime
import gspread
from .config import get_sheets_client, SHEET_PROPERTIES

logger = logging.getLogger(__name__)

PROPERTIES_JSON = "docs/data/properties.json"

# Column order in the Google Sheets property data sheet
COLUMNS = [
    "物件ID", "サイト", "物件名", "住所", "家賃", "管理費",
    "間取り", "面積", "築年数", "URL", "検知日時", "担当者名",
]


def load_seen_ids() -> set[str]:
    """Return set of property unique IDs already recorded."""
    client = get_sheets_client()
    sheet_id = os.environ["GOOGLE_SHEETS_ID"]
    wb = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(wb, SHEET_PROPERTIES)
    rows = ws.get_all_values()
    if len(rows) < 2:
        return set()
    return {row[0] for row in rows[1:] if row}


def save_properties(properties: list, condition_name: str):
    """Append new properties to Google Sheets and update the JSON file."""
    if not properties:
        return

    client = get_sheets_client()
    sheet_id = os.environ["GOOGLE_SHEETS_ID"]
    wb = client.open_by_key(sheet_id)
    ws = _get_or_create_sheet(wb, SHEET_PROPERTIES)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows_to_add = []
    for p in properties:
        rows_to_add.append([
            p.unique_id,
            p.site,
            p.name,
            p.address,
            p.rent,
            p.management_fee,
            p.layout,
            p.area,
            p.age,
            p.url,
            now,
            condition_name,
        ])

    ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")
    logger.info(f"Saved {len(rows_to_add)} properties to Sheets")

    _update_json(properties, now, condition_name)


def _get_or_create_sheet(wb: gspread.Spreadsheet, name: str) -> gspread.Worksheet:
    try:
        return wb.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(title=name, rows=1000, cols=20)
        ws.append_row(COLUMNS)
        return ws


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
