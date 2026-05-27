import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urljoin
from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE_URL = "https://www.athome.co.jp/chintai/{area}/list/"


class AtHomeScraper(BaseScraper):
    SITE_NAME = "athome"

    def search(self, condition: dict) -> list[Property]:
        """
        condition keys:
          area_path: URL path segment (e.g. "tokyo/shinjuku")
          price_max: max rent in 10000 yen
          layouts: list of layout names
          walk_max: max walk minutes
          age_max: max building age in years
        """
        area_path = condition.get("area_path", "tokyo")
        base = BASE_URL.format(area=area_path)
        params = self._build_params(condition)
        properties = []
        page = 1

        while True:
            params["page"] = page
            url = base + "?" + urlencode(params, doseq=True)
            logger.info(f"AtHome: fetching page {page} — {url}")

            resp = self._get(url)
            if resp is None:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            page_props = self._parse_list(soup)

            if not page_props:
                break

            properties.extend(page_props)

            if not self._has_next_page(soup, page):
                break
            page += 1
            if page > 20:
                break

        return properties

    def _build_params(self, condition: dict) -> dict:
        params: dict = {}
        if condition.get("price_max"):
            params["PR"] = f"0-{condition['price_max']}0000"
        if condition.get("walk_max"):
            params["TW"] = str(condition["walk_max"])
        if condition.get("age_max"):
            params["AGE"] = str(condition["age_max"])

        layout_map = {
            "1R": "01", "1K": "02", "1DK": "03", "1LDK": "04",
            "2K": "05", "2DK": "06", "2LDK": "07",
            "3K": "08", "3DK": "09", "3LDK": "10",
        }
        for l in condition.get("layouts", []):
            code = layout_map.get(l)
            if code:
                params.setdefault("TA", [])
                params["TA"].append(code)

        # --- 設備・条件 ---
        # ⚠ アットホームのパラメータはサイトのフォームHTMLを確認して調整してください
        if condition.get("bt_required"):
            params["BT"] = "1"    # バス・トイレ別
        if condition.get("washstand_required"):
            params["WB"] = "1"    # 独立洗面台（推定パラメータ）

        pet = condition.get("pet_option", "")
        if pet == "可相談":
            # アットホーム: PET=1(可) と PET=2(相談可) を配列で両方同時検索
            # ⚠ コードはアットホームのフォームを確認して調整してください
            params["PET"] = ["1", "2"]

        if condition.get("floor_min"):
            params["FL"] = str(condition["floor_min"])   # 何階以上

        return params

    def _parse_list(self, soup: BeautifulSoup) -> list[Property]:
        properties = []
        seen_ids = set()

        # AtHome property links: /chintai/[numeric_id]/
        prop_links = soup.select('a[href*="/chintai/"]')

        for link in prop_links:
            href = link.get("href", "")
            m = re.search(r"/chintai/(\d{8,})/", href)
            if not m:
                continue
            prop_id = m.group(1)
            if prop_id in seen_ids:
                continue
            seen_ids.add(prop_id)

            container = link
            for _ in range(8):
                container = container.parent
                if container is None:
                    break
                text_len = len(container.get_text()) if container else 0
                if container.name in ("tr", "li", "div", "article") and text_len > 50:
                    break

            prop = self._extract_from_container(container, prop_id, href)
            if prop:
                properties.append(prop)

        return properties

    def _has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        next_link = soup.select_one("a.next, a[rel='next']")
        if next_link:
            return True
        all_pages = [
            int(a.text.strip()) for a in soup.select(".pagination a, .pager a")
            if a.text.strip().isdigit()
        ]
        return current_page < max(all_pages, default=current_page)

    def _extract_from_container(self, container, prop_id: str, href: str) -> Property | None:
        try:
            text = container.get_text(separator="\n") if container else ""
            lines = [l.strip() for l in text.splitlines() if l.strip()]

            name = ""
            address = ""
            rent = ""
            layout = ""
            area = ""
            age = ""
            station = ""

            for line in lines:
                if not name and re.search(r"(マンション|アパート|ハイツ|コーポ|ハウス|レジデンス|荘|寮)", line):
                    name = line
                elif re.search(r"[都道府県区市]", line) and not address and len(line) > 5:
                    address = line
                elif re.match(r"\d+\.?\d*万円", line) and not rent:
                    rent = line
                elif re.search(r"\d+\.?\d*m²", line) and not area:
                    area = line
                elif re.search(r"\d+[KDL]+R?", line) and not layout:
                    layout = line
                elif re.search(r"築\d+年", line) and not age:
                    age = line
                elif re.search(r"徒歩\d+分|駅.*\d+分", line) and not station:
                    station = line

            url = urljoin("https://www.athome.co.jp", href)

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
            logger.warning(f"Failed to extract AtHome property {prop_id}: {e}")
            return None
