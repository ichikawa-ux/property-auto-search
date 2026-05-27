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
        """
        condition keys:
          ta: prefecture code (e.g. "13" for Tokyo)
          sc: list of city codes (e.g. ["13101", "13102"])
          km: max rent in 10000 yen (e.g. 15)
          layouts: list of layout names (e.g. ["1K", "1DK"])
          et: max walk minutes (e.g. 10)
          cn: max building age in years (e.g. 20)
        """
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

            next_link = soup.select_one("li.pagination-parts a[href*='pn=']")
            current_page_el = soup.select_one("li.pagination-parts.is-active")
            if not next_link or (current_page_el and int(current_page_el.text.strip()) >= page):
                # Try another pagination pattern
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

        # --- 設備・条件 ---
        # ⚠ bc の値はSUUMOの検索フォームHTMLを確認して調整してください
        # （bc=09: バス・トイレ別, bc=11: 独立洗面台 は推定値です）
        bc_codes = []
        if condition.get("bt_required"):
            bc_codes.append("09")   # バス・トイレ別
        if condition.get("washstand_required"):
            bc_codes.append("11")   # 独立洗面台
        if bc_codes:
            params["bc"] = bc_codes

        pet = condition.get("pet_option", "")
        if pet == "可相談":
            params["pe"] = "1"   # ペット可・相談可（SUUMOはpe=1で両方含む）

        if condition.get("floor_min"):
            params["ff"] = str(condition["floor_min"])   # 何階以上

        return params

    def _parse_list(self, soup: BeautifulSoup) -> list[Property]:
        properties = []

        # Primary selector: property cards with jnc_ links
        prop_links = soup.select('a[href*="/chintai/jnc_"]')
        seen_ids = set()

        for link in prop_links:
            href = link.get("href", "")
            m = re.search(r"jnc_(\d+)", href)
            if not m:
                continue
            prop_id = m.group(1)
            if prop_id in seen_ids:
                continue
            seen_ids.add(prop_id)

            # Walk up to find the property container
            container = link
            for _ in range(8):
                container = container.parent
                if container is None:
                    break
                if container.name in ("li", "div") and len(container.text) > 50:
                    break

            prop = self._extract_from_container(container, prop_id, href)
            if prop:
                properties.append(prop)

        return properties

    def _extract_from_container(self, container, prop_id: str, href: str) -> Property | None:
        try:
            text = container.get_text(separator="\n") if container else ""
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            name = ""
            h3 = container.find("h3") if container else None
            if h3:
                name = h3.get_text(strip=True)
                # Remove prefix like "賃貸マンション "
                name = re.sub(r"^(賃貸|分譲)\S+\s+", "", name)

            address = ""
            rent = ""
            layout = ""
            area = ""
            age = ""
            station = ""

            for line in lines:
                if re.search(r"東京都|大阪府|[都道府県]", line) and not address:
                    address = line
                elif re.match(r"\d+\.?\d*万円", line) and not rent:
                    rent = line
                elif re.match(r"\d+[KDL]+R?", line) and not layout:
                    layout = line
                elif re.search(r"\d+\.?\d*m²", line) and not area:
                    area = line
                elif re.search(r"築\d+年", line) and not age:
                    age = line
                elif re.search(r"駅\s*歩\d+分|徒歩\d+分", line) and not station:
                    station = line

            url = f"https://suumo.jp{href}" if href.startswith("/") else href

            return Property(
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
            )
        except Exception as e:
            logger.warning(f"Failed to extract SUUMO property {prop_id}: {e}")
            return None
