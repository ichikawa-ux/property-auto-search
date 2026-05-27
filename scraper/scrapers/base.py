import time
import random
import logging
import requests
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MIN_INTERVAL = 30  # seconds between requests


@dataclass
class Property:
    site: str
    property_id: str
    name: str
    address: str
    rent: str
    management_fee: str
    layout: str
    area: str
    age: str
    url: str
    station_access: str = ""
    floor: str = ""
    deposit: str = ""
    key_money: str = ""

    @property
    def unique_id(self) -> str:
        return f"{self.site}:{self.property_id}"

    def to_dict(self) -> dict:
        return {
            "id": self.unique_id,
            "site": self.site,
            "property_id": self.property_id,
            "name": self.name,
            "address": self.address,
            "rent": self.rent,
            "management_fee": self.management_fee,
            "layout": self.layout,
            "area": self.area,
            "age": self.age,
            "url": self.url,
            "station_access": self.station_access,
            "floor": self.floor,
            "deposit": self.deposit,
            "key_money": self.key_money,
        }


class BaseScraper(ABC):
    SITE_NAME = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._last_request_time = 0.0

    def _wait(self):
        elapsed = time.time() - self._last_request_time
        wait = max(0, MIN_INTERVAL - elapsed) + random.uniform(0, 5)
        if wait > 0:
            logger.debug(f"Waiting {wait:.1f}s before next request")
            time.sleep(wait)

    def _get(self, url: str, **kwargs) -> Optional[requests.Response]:
        self._wait()
        try:
            resp = self.session.get(url, timeout=30, **kwargs)
            resp.raise_for_status()
            self._last_request_time = time.time()
            return resp
        except requests.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    @abstractmethod
    def search(self, condition: dict) -> list[Property]:
        """Search for properties matching the given condition."""
        ...

    def build_unique_id(self, raw_id: str) -> str:
        return f"{self.SITE_NAME}:{raw_id}"
