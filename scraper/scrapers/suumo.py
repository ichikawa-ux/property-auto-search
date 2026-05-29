import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlencode
from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE_URL = "https://suumo.jp/jj/chintai/ichiran/FR301FC001/"

# Room type codes for SUUMO
LAYOUT_CODES = {
    "1R": "01", "1K": "02", "1DK": "03", "1LDK": "04",
    "2K": "05", "2DK": "06", "2LDK": "07",
    "3K": "08", "3DK": "09", "3LDK": "10", "4K以上": "11",
}


class SuumoScraper(BaseScraper):
    SITE_NAME = "suumo"

    def search(self, condition: dict) -> list[Property]:
        params = self._build_params(condition)
        properties = []
        page = 1

        while True:
            params["pn"] = page
            url = BASE_URL + "?" + urlencode(params, doseq=True)
            logger.info(f"SUUMO: fetching page {page} — {url}")

            resp = self._get(url)
            if resp is None:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            page_props = self._parse_list(soup)

            if not page_props:
                break

            properties.extend(page_props)

            # Pagination: check if there's a next page
            # Try class-based first, fall back to link scan
            next_link = soup.select_one("li.pagination-parts a[href*='pn=']")
            current_page_el = soup.select_one("li.pagination-parts.is-active")
            if not next_link or (current_page_el and current_page_el.text.strip().isdigit()
                                  and int(current_page_el.text.strip()) >= page):
                all_pages = soup.select("div.pagination ol li a")
                page_nums = [int(a.text.strip()) for a in all_pages if a.text.strip().isdigit()]
                if page >= max(page_nums, default=page):
                    break

            page += 1
            if page > 20:  # Safety cap
                break

        return properties

    def _build_params(self, condition: dict) -> dict:
        params: dict = {
            "ar": "030",
            "bs": "040",
            "ta": condition.get("ta", "13"),
            "kb": "1",
            "km": str(condition.get("km", "9999")),
            "et": str(condition.get("et", "9999999")),
            "mb": "0",
            "mt": "9999999",
            "shkr1": "03",
            "shkr2": "03",
            "shkr3": "03",
            "shkr4": "03",
        }

        for sc in condition.get("sc", []):
            params.setdefault("sc", [])
            if isinstance(params["sc"], list):
                params["sc"].append(str(sc))
            else:
                params["sc"] = [params["sc"], str(sc)]

        for layout in condition.get("layouts", []):
            code = LAYOUT_CODES.get(layout)
            if code:
                params.setdefault("md", [])
                if isinstance(params["md"], list):
                    params["md"].append(code)
                else:
                    params["md"] = [params["md"], code]

        if condition.get("cn"):
            params["cn"] = str(condition["cn"])

        bc_codes = []
        if condition.get("bt_required"):
            bc_codes.append("09")
        if condition.get("washstand_required"):
            bc_codes.append("11")
        if bc_codes:
            params["bc"] = bc_codes

        pet = condition.get("pet_option", "")
        if pet == "可相談":
            params["pe"] = "1"

        if condition.get("floor_min"):
            params["ff"] = str(condition["floor_min"])

        return params

    def _parse_list(self, soup: BeautifulSoup) -> list[Property]:
        properties = []
        seen_ids = set()

        for link in soup.select('a[href*="/chintai/jnc_"]'):
            href = link.get("href", "")
            m = re.search(r"jnc_(\d+)", href)
            if not m:
                continue
            prop_id = m.group(1)
            if prop_id in seen_ids:
                continue
            seen_ids.add(prop_id)

            url = f"https://suumo.jp{href}" if href.startswith("/") else href

            # ── 部屋レベル：trから家賃・間取り・面積を取得 ──────────────
            row = link
            while row and row.name != "tr":
                row = row.parent

            rent = layout = area = ""
            if row:
                for line in [l.strip() for l in row.get_text("\n").splitlines() if l.strip()]:
                    if re.search(r"\d+\.?\d*万円", line) and not rent:
                        m2 = re.search(r"\d+\.?\d*万円", line)
                        rent = m2.group() if m2 else line
                    elif re.match(r"^\d+[KDLkdl]+R?$|^ワンルーム$|^1R$", line) and not layout:
                        layout = line
                    elif re.search(r"\d+\.?\d*m[²2㎡]", line) and not area:
                        m2 = re.search(r"\d+\.?\d*m[²2㎡]", line)
                        area = m2.group() if m2 else line

            # ── 建物レベル：trの上位から住所・駅・築年数・物件名を取得 ──
            section = row
            for _ in range(20):
                if section is None:
                    break
                section = section.parent
                if section is None:
                    break
                txt = section.get_text()
                # 住所と駅情報の両方を含む大きな要素を探す
                if (len(txt) > 150
                        and re.search(r"[都道府県].{2,6}[市区町村]", txt)
                        and re.search(r"歩\d+分|徒歩\d+分", txt)):
                    break

            name = address = station = age = ""
            if section:
                lines = [l.strip() for l in section.get_text("\n").splitlines() if l.strip()]
                addr_idx = None
                for i, line in enumerate(lines):
                    if not address and re.search(r"[都道府県].{1,6}[市区町村]", line):
                        address = line
                        addr_idx = i
                    elif not station and re.search(r"歩\d+分|徒歩\d+分", line):
                        station = line
                    elif not age and re.search(r"築\d+年", line):
                        age = line

                # 物件名：住所より前の行から探す
                if addr_idx is not None:
                    for j in range(max(0, addr_idx - 4), addr_idx):
                        candidate = lines[j]
                        if (len(candidate) > 2
                                and not re.search(r"[市区町村]\d|歩\d+分|万円|\d+m|築\d", candidate)
                                and not re.match(r"^\d+$", candidate)):
                            name = candidate
                            break

            properties.append(Property(
                site=self.SITE_NAME,
                property_id=prop_id,
                name=name or f"物件_{prop_id}",
                address=address,
                rent=rent,
                management_fee="",
                layout=layout,
                area=area,
                age=age,
                url=url,
                station_access=station,
            ))

        return properties
