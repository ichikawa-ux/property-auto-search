import os
import json
import logging
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

SHEET_CONDITIONS = "検索条件"
SHEET_PROPERTIES = "物件データ"

# Normalize site names from Google Forms checkboxes to internal IDs
SITE_NAME_MAP = {
    "suumo": "suumo",
    "home's": "homes",
    "homes": "homes",
    "lifull home's": "homes",
    "アットホーム": "athome",
    "athome": "athome",
    "at home": "athome",
}

# Area name → scraper codes (Tokyo 23 wards)
# Add more cities here if needed
AREA_LOOKUP: dict[str, dict] = {
    "千代田区": {"ta": "13", "sc": ["13101"], "homes": "tokyo/chiyoda-city",    "athome": "tokyo/chiyoda"},
    "中央区":   {"ta": "13", "sc": ["13102"], "homes": "tokyo/chuo-city",       "athome": "tokyo/chuo"},
    "港区":     {"ta": "13", "sc": ["13103"], "homes": "tokyo/minato-city",     "athome": "tokyo/minato"},
    "新宿区":   {"ta": "13", "sc": ["13104"], "homes": "tokyo/shinjuku-city",   "athome": "tokyo/shinjuku"},
    "文京区":   {"ta": "13", "sc": ["13105"], "homes": "tokyo/bunkyo-city",     "athome": "tokyo/bunkyo"},
    "台東区":   {"ta": "13", "sc": ["13106"], "homes": "tokyo/taito-city",      "athome": "tokyo/taito"},
    "墨田区":   {"ta": "13", "sc": ["13107"], "homes": "tokyo/sumida-city",     "athome": "tokyo/sumida"},
    "江東区":   {"ta": "13", "sc": ["13108"], "homes": "tokyo/koto-city",       "athome": "tokyo/koto"},
    "品川区":   {"ta": "13", "sc": ["13109"], "homes": "tokyo/shinagawa-city",  "athome": "tokyo/shinagawa"},
    "目黒区":   {"ta": "13", "sc": ["13110"], "homes": "tokyo/meguro-city",     "athome": "tokyo/meguro"},
    "大田区":   {"ta": "13", "sc": ["13111"], "homes": "tokyo/ota-city",        "athome": "tokyo/ota"},
    "世田谷区": {"ta": "13", "sc": ["13112"], "homes": "tokyo/setagaya-city",   "athome": "tokyo/setagaya"},
    "渋谷区":   {"ta": "13", "sc": ["13113"], "homes": "tokyo/shibuya-city",    "athome": "tokyo/shibuya"},
    "中野区":   {"ta": "13", "sc": ["13114"], "homes": "tokyo/nakano-city",     "athome": "tokyo/nakano"},
    "杉並区":   {"ta": "13", "sc": ["13115"], "homes": "tokyo/suginami-city",   "athome": "tokyo/suginami"},
    "豊島区":   {"ta": "13", "sc": ["13116"], "homes": "tokyo/toshima-city",    "athome": "tokyo/toshima"},
    "北区":     {"ta": "13", "sc": ["13117"], "homes": "tokyo/kita-city",       "athome": "tokyo/kita"},
    "荒川区":   {"ta": "13", "sc": ["13118"], "homes": "tokyo/arakawa-city",    "athome": "tokyo/arakawa"},
    "板橋区":   {"ta": "13", "sc": ["13119"], "homes": "tokyo/itabashi-city",   "athome": "tokyo/itabashi"},
    "練馬区":   {"ta": "13", "sc": ["13120"], "homes": "tokyo/nerima-city",     "athome": "tokyo/nerima"},
    "足立区":   {"ta": "13", "sc": ["13121"], "homes": "tokyo/adachi-city",     "athome": "tokyo/adachi"},
    "葛飾区":   {"ta": "13", "sc": ["13122"], "homes": "tokyo/katsushika-city", "athome": "tokyo/katsushika"},
    "江戸川区": {"ta": "13", "sc": ["13123"], "homes": "tokyo/edogawa-city",    "athome": "tokyo/edogawa"},
}


def get_sheets_client() -> gspread.Client:
    creds_json = os.environ["GOOGLE_CREDENTIALS_JSON"].lstrip("﻿")  # strip UTF-8 BOM if present
    creds_info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.Client(auth=creds)


def _get_int(row: dict, *keys, default: int = 0) -> int:
    """Read an integer from a row, trying multiple column name variants."""
    for key in keys:
        val = row.get(key)
        if val:
            try:
                return int(str(val).replace(",", "").replace("万", "").strip())
            except ValueError:
                pass
    return default


def load_conditions() -> list[dict]:
    """
    Load search conditions from Google Sheets.
    Supports both:
      - Manual spreadsheet entry (original format)
      - Google Forms responses (エリア column with ward names, no 有効 column)
    """
    client = get_sheets_client()
    sheet_id = os.environ["GOOGLE_SHEETS_ID"]
    logger.info(f"Opening spreadsheet: {sheet_id}")
    try:
        wb = client.open_by_key(sheet_id)
    except Exception as e:
        resp = getattr(e, 'response', None)
        body = resp.text if resp is not None else "no response"
        logger.error(f"Failed to open spreadsheet: {e} | response body: {body}")
        raise
    ws = wb.worksheet(SHEET_CONDITIONS)
    rows = ws.get_all_records()
    conditions = []

    for i, row in enumerate(rows):
        # "有効" defaults to TRUE when column is absent (all Google Forms entries are active)
        if str(row.get("有効", "TRUE")).upper() == "FALSE":
            continue

        # --- Sites ---
        sites_raw = str(row.get("サイト", ""))
        sites = []
        for s in sites_raw.split(","):
            normalized = SITE_NAME_MAP.get(s.strip().lower())
            if normalized:
                sites.append(normalized)
        if not sites:
            sites = ["suumo", "homes", "athome"]

        # --- Area: resolve from ward names (Google Forms) or explicit codes (manual) ---
        areas_raw = str(row.get("エリア", ""))
        areas = [a.strip() for a in areas_raw.split(",") if a.strip()]

        sc_codes: list[str] = []
        homes_paths: list[str] = []
        athome_paths: list[str] = []
        ta = str(row.get("都道府県コード_SUUMO", "13") or "13")

        for area in areas:
            info = AREA_LOOKUP.get(area)
            if info:
                ta = info["ta"]
                sc_codes.extend(info["sc"])
                if info["homes"] not in homes_paths:
                    homes_paths.append(info["homes"])
                if info["athome"] not in athome_paths:
                    athome_paths.append(info["athome"])

        # Fall back to explicit code columns (for manually entered rows)
        if not sc_codes:
            sc_raw = str(row.get("SUUMOエリアコード", ""))
            sc_codes = [c.strip() for c in sc_raw.split(",") if c.strip()]
        if not homes_paths:
            p = str(row.get("HOMESエリアパス", ""))
            if p:
                homes_paths = [p]
        if not athome_paths:
            p = str(row.get("アットホームエリアパス", ""))
            if p:
                athome_paths = [p]

        # --- Layouts ---
        layouts_raw = str(row.get("間取り", ""))
        layouts = [l.strip() for l in layouts_raw.split(",") if l.strip()]

        # --- Numeric fields (handle both 家賃上限_万円 and 家賃上限（万円）) ---
        rent_max  = _get_int(row, "家賃上限_万円",  "家賃上限（万円）")
        walk_max  = _get_int(row, "駅徒歩上限_分",  "駅徒歩上限（分）") or None
        age_max   = _get_int(row, "築年数上限_年",  "築年数上限（年）") or None
        floor_min = _get_int(row, "最低階数（階以上）", "階数（階以上）") or None

        # --- Equipment / property conditions ---
        bt_val        = str(row.get("BT別（バストイレ別）", "")).strip()
        washstand_val = str(row.get("独立洗面台", "")).strip()
        pet_val       = str(row.get("ペット", "")).strip()

        bt_required        = bt_val == "必須"
        washstand_required = washstand_val == "必須"
        # "可・相談可を含む" → 両方同時検索、"不可のみ" → 不可フィルタ、それ以外 → 問わない
        if pet_val in ("可・相談可を含む", "可相談"):
            pet_option = "可相談"
        elif pet_val == "不可のみ":
            pet_option = "不可"
        else:
            pet_option = ""

        row_id = str(row.get("ID", "") or row.get("タイムスタンプ", "") or str(i + 1))
        email  = str(row.get("メールアドレス", "")).strip()
        if not email:
            continue

        condition = {
            "id":    row_id,
            "name":  str(row.get("担当者名", "")),
            "email": email,
            "sites": sites,
            # SUUMO
            "ta":      ta,
            "sc":      sc_codes,
            "km":      rent_max,
            "et":      walk_max or 9999999,
            "cn":      age_max,
            "layouts": layouts,
            # HOME'S (first area only — each site supports one path at a time)
            "area_path_homes": homes_paths[0] if homes_paths else "",
            "pricemax": rent_max,
            "walkmax":  walk_max or 0,
            "age":      age_max,
            # AtHome
            "area_path_athome": athome_paths[0] if athome_paths else "",
            "price_max": rent_max,
            "walk_max":  walk_max or 0,
            "age_max":   age_max,
            # Equipment conditions (shared across all sites)
            "bt_required":        bt_required,
            "washstand_required": washstand_required,
            "pet_option":         pet_option,
            "floor_min":          floor_min,
            # Extra areas for HOME'S / AtHome (if multiple wards selected)
            "_homes_paths":  homes_paths,
            "_athome_paths": athome_paths,
        }
        conditions.append(condition)

    logger.info(f"Loaded {len(conditions)} active conditions")
    return conditions
