import re
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urljoin
from .base import BaseScraper, Property

logger = logging.getLogger(__name__)

BASE_URL = "https://www.homes.co.jp/chintai/{area}/list/"


class HomesScraper(BaseScraper):
    SITE_NAME = "homes"

    def search(self, condition: dict) -> list[Property]:
        """
        condition keys:
          area_path: URL path segment (e.g. "tokyo/shinjuku-city")
          pricemax: max rent in 10000 yen
          layouts: list of layout names (e.g. ["1K", "1DK"])
          walkmax: max walk minutes
          age: max building age in years
        """
        area_path = condition.get("area_path", "tokyo")
        base = BASE_URL.format(area=area_path)
        params = self._build_params(condition)
        properties = []
        page = 1

        while True:
            params["page"] = page
            url = base + "?" + urlencode(params, doseq=True)
            logger.info(f"HOME'S: fetching page {page} — {url}")

            resp = self._get(url)
            if resp is None:
                break

            soup = BeautifulSoup(resp.text, "lxml")
            page_props = self._parse_list(soup, base)

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
        if condition.get("pricemax"):
            params["pricemax"] = str(condition["pricemax"])
        if condition.get("walkmax"):
            params["walkmax"] = str(condition["walkmax"])
        if condition.get("age"):
            params["age"] = str(condition["age"])

        layout_map = {
            "1R": "1", "1K": "2", "1DK": "3", "1LDK": "4",
            "2K": "5", "2DK": "6", "2LDK": "7",
            "3K": "8", "3DK": "9", "3LDK": "10",
        }
        codes = [layout_map[l] for l in condition.get("layouts", []) if l in layout_map]
        if codes:
            params["floorplancd"] = codes

        # --- 設備・条件 ---
        # ⚠ HOME'Sの設備コードはサイトのフォームHTMLを確認して調整してください
        kkt = []
        if condition.get("bt_required"):
            kkt.append("22")   # バス・トイレ別（推定コード）
        if condition.get("washstand_required"):
            kkt.append("23")   # 独立洗面台（推定コード）
        if kkt:
            params["kkt_cd"] = kkt

        pet = condition.get("pet_option", "")
        if pet == "可相談":
            # HOME'S: pet=1(可) と pet=2(相談可) を配列で渡して両方同時検索
            # ⚠ コードはHOME'Sのフォームを確認して調整してください
            params["pet"] = ["1", "2"]

        if condition.get("floor_min"):
            params["floorfrom"] = str(condition["floor_min"])

        return params

    def _parse_list(self, soup: BeautifulSoup, base_url: str) -> list[Property]:
        properties = []
        seen_ids = set()

        # HOME'S property links contain /chintai/room/ or /chintai/[hash]/
        prop_links = soup.select('a[href*="/chintai/room/"], a[href*="/chintai/bukken/"]')
        if not prop_links:
            prop_links = soup.select('a[href*="/chintai/"]')

        for link in prop_links:
            href = link.get("href", "")
            # Extract hash-style ID
            m = re.search(r"/chintai/(?:room/|bukken/)?([a-f0-9]{20,})", href)
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
                if container.name in ("li", "div", "article") and len(container.get_text()) > 50:
                    break

            prop = self._extract_from_container(container, prop_id, href)
            if prop:
                properties.append(prop)

        return properties

    def _has_next_page(self, soup: BeautifulSoup, current_page: int) -> bool:
        next_link = soup.select_one("a.pagination-next, a[rel='next']")
        if next_link:
            return True
        all_pages = [
            int(a.text.strip()) for a in soup.select(".pagination a")
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
            mgmt_fee = ""
            layout = ""
            area = ""
            age = ""
            station = ""

            for line in lines:
                if not name and re.search(r"(マンション|アパート|ハイツ|コーポ|ハウス|レジデンス)", line):
                    name = line
                elif re.search(r"[都道府県]", line) and not address:
                    address = line
                elif re.match(r"\d+\.?\d*万円", line) and not rent:
                    rent = line
                elif re.search(r"\d+\.?\d*m²", line) and not area:
                    area = line
                elif re.search(r"\d+[KDL]+R?", line) and not layout:
                    layout = line
                elif re.search(r"築\d+年", line) and not age:
                    age = line
                elif re.search(r"徒歩\d+分|駅.*歩\d+分", line) and not station:
                    station = line

            url = urljoin("https://www.homes.co.jp", href)

            return Property(
                site=self.SITE_NAME,
                property_id=prop_id,
                name=name or f"物件_{prop_id[:8]}",
                address=address,
                rent=rent,
                management_fee=mgmt_fee,
                layout=layout,
                area=area,
                age=age,
                url=url,
                station_access=station,
            )
        except Exception as e:
            logger.warning(f"Failed to extract HOME'S property {prop_id}: {e}")
            return None
