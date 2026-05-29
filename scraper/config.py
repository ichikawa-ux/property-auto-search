import os
import math
import logging
import requests

logger = logging.getLogger(__name__)

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

# 間取タイプ の表記ゆれ正規化
LAYOUT_TYPE_MAP = {
    "ワンルーム": "1R",
    "k": "K", "K": "K", "K（キッチン）": "K",
    "dk": "DK", "DK": "DK", "DK（ダイニングキッチン）": "DK",
    "sdk": "DK", "SDK": "DK", "SDK（サービスルーム＋DK）": "DK",   # SUUMO上はDKとして検索
    "ldk": "LDK", "LDK": "LDK", "LDK（リビングダイニングキッチン）": "LDK",
    "sldk": "LDK", "SLDK": "LDK", "SLDK（サービスルーム＋LDK）": "LDK",  # SUUMO上はLDKとして検索
}


def _fetch_rows_via_web_app() -> list[dict]:
    """Fetch spreadsheet rows via the Apps Script web app endpoint."""
    url   = os.environ["SHEETS_WEB_APP_URL"].lstrip("﻿").strip()
    token = os.environ.get("SHEETS_WEB_APP_TOKEN", "").lstrip("﻿").strip()
    logger.info("Fetching conditions from Apps Script web app")
    resp = requests.get(url, params={"token": token}, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Web app returned error: {data['error']}")
    return data.get("rows", [])


def _get_float(row: dict, *keys, default: float = 0.0) -> float:
    """Read a float from a row (supports 8.5万円 etc.), trying multiple column name variants."""
    for key in keys:
        val = row.get(key)
        if val:
            try:
                return float(str(val).replace(",", "").replace("万", "").strip())
            except ValueError:
                pass
    return default


def _get_int(row: dict, *keys, default: int = 0) -> int:
    """Read an integer from a row, trying multiple column name variants."""
    v = _get_float(row, *keys, default=float(default))
    return int(v) if v else default


def _collect_areas(row: dict) -> list[str]:
    """
    エリア列を複数のグループ列から収集する。
    新フォーム形式（エリア（都心）等）と旧フォーム形式（エリア）の両方に対応。
    """
    area_columns = [
        "エリア（都心）",
        "エリア（副都心・西部）",
        "エリア（北部・城北）",
        "エリア（東部・下町）",
        "エリア（南部・城南）",
        "エリア",  # 旧フォーム形式・手動入力
    ]
    combined = []
    for col in area_columns:
        val = str(row.get(col, ""))
        for a in val.split(","):
            a = a.strip()
            if a:
                combined.append(a)
    return combined


def _expand_layouts(types_raw: str, rooms_raw: str, legacy_raw: str = "") -> list[str]:
    """
    間取タイプ × 間取部屋数 → 具体的な間取りリスト
    旧フォームの「間取り」列（"1K, 1DK" 等）も引き続きサポート。
    """
    # 旧フォーム形式（直接指定）がある場合はそちらを優先
    if legacy_raw.strip():
        return [l.strip() for l in legacy_raw.split(",") if l.strip()]

    types = [LAYOUT_TYPE_MAP.get(t.strip(), t.strip())
             for t in types_raw.split(",") if t.strip()]
    types = [t for t in types if t]

    if not types:
        return []  # 未指定 = すべて対象

    room_nums = []
    for r in rooms_raw.split(","):
        r = r.strip().replace("室", "").replace("以上", "").strip()
        if r.isdigit():
            room_nums.append(r)

    layouts = []
    for t in types:
        if t == "1R":
            layouts.append("1R")
            continue
        if not room_nums:
            # 部屋数未指定 → 1〜3室 + 4以上
            for n in ["1", "2", "3"]:
                layouts.append(f"{n}{t}")
            layouts.append("4K以上")  # 4室以上の代表
        else:
            for n in room_nums:
                if n == "4":
                    layouts.append("4K以上")
                else:
                    layouts.append(f"{n}{t}")

    # 重複除去・順序保持
    seen = set()
    result = []
    for l in layouts:
        if l not in seen:
            seen.add(l)
            result.append(l)
    return result


def load_conditions() -> list[dict]:
    """
    Load search conditions from Google Sheets via Apps Script web app.
    新フォーム形式（エリアグループ分割・間取タイプ×部屋数）と
    旧フォーム形式（エリア1列・間取り直接指定）の両方に対応。
    """
    rows = _fetch_rows_via_web_app()
    conditions = []

    for i, row in enumerate(rows):
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

        # --- Area（新旧両対応） ---
        areas = _collect_areas(row)
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

        # 手動入力コード列へのフォールバック
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

        # --- Layouts（新旧両対応） ---
        layout_type_raw = str(row.get("間取タイプ", ""))
        room_count_raw  = str(row.get("間取部屋数", ""))
        legacy_layout   = str(row.get("間取り", ""))
        layouts = _expand_layouts(layout_type_raw, room_count_raw, legacy_layout)

        # --- Numeric fields（float対応：8.5万円 OK） ---
        rent_max_f = _get_float(row, "家賃上限_万円", "家賃上限（万円）")
        rent_max   = math.ceil(rent_max_f) if rent_max_f else 0   # SUUMO URLは整数のみ
        walk_max   = _get_int(row, "駅徒歩上限_分", "駅徒歩上限（分）") or None
        age_max    = _get_int(row, "築年数上限_年", "築年数上限（年）") or None
        floor_min  = _get_int(row, "最低階数（階以上）", "階数（階以上）") or None

        # --- Equipment / property conditions ---
        bt_val        = str(row.get("BT別（バストイレ別）", "")).strip()
        washstand_val = str(row.get("独立洗面台", "")).strip()
        pet_val       = str(row.get("ペット", "")).strip()

        bt_required        = bt_val == "必須"
        washstand_required = washstand_val == "必須"
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
            "rent_max_f": rent_max_f,   # 実際の上限（小数）を保持しておく
            "et":      walk_max or 9999999,
            "cn":      age_max,
            "layouts": layouts,
            # HOME'S
            "area_path_homes": homes_paths[0] if homes_paths else "",
            "pricemax": rent_max,
            "walkmax":  walk_max or 0,
            "age":      age_max,
            # AtHome
            "area_path_athome": athome_paths[0] if athome_paths else "",
            "price_max": rent_max,
            "walk_max":  walk_max or 0,
            "age_max":   age_max,
            # Equipment
            "bt_required":        bt_required,
            "washstand_required": washstand_required,
            "pet_option":         pet_option,
            "floor_min":          floor_min,
            # Extra areas
            "_homes_paths":  homes_paths,
            "_athome_paths": athome_paths,
        }
        conditions.append(condition)

    logger.info(f"Loaded {len(conditions)} active conditions")
    return conditions
