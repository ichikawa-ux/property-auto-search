#!/usr/bin/env python3
"""Entry point for the real estate property monitor."""
import logging
import sys
from collections import defaultdict

from .config import load_conditions
from .storage import load_seen_ids, save_properties
from .notifier import send_notification
from .page_generator import commit_and_push
from .scrapers.suumo import SuumoScraper
from .scrapers.homes import HomesScraper
from .scrapers.athome import AtHomeScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

SCRAPER_MAP = {
    "suumo": SuumoScraper,
    "homes": HomesScraper,
    "athome": AtHomeScraper,
}


def run():
    logger.info("=== 不動産物件監視 開始 ===")

    conditions = load_conditions()
    if not conditions:
        logger.warning("No active conditions found. Exiting.")
        return

    seen_ids = load_seen_ids()
    logger.info(f"Already seen: {len(seen_ids)} properties")

    scraper_instances: dict[str, object] = {}
    new_by_condition: dict[str, dict] = defaultdict(lambda: {"props": [], "email": ""})

    for condition in conditions:
        logger.info(f"Processing condition: {condition['name']} — sites: {condition['sites']}")

        for site_name in condition["sites"]:
            scraper_cls = SCRAPER_MAP.get(site_name)
            if not scraper_cls:
                logger.warning(f"Unknown site: {site_name}")
                continue

            if site_name not in scraper_instances:
                scraper_instances[site_name] = scraper_cls()
            scraper = scraper_instances[site_name]

            site_condition = _build_site_condition(condition, site_name)
            try:
                found = scraper.search(site_condition)
            except Exception as e:
                logger.error(f"Scraper error ({site_name}): {e}", exc_info=True)
                continue

            new_props = [p for p in found if p.unique_id not in seen_ids]
            logger.info(f"  {site_name}: {len(found)} found, {len(new_props)} new")

            if new_props:
                cond_key = condition["id"] or condition["name"]
                new_by_condition[cond_key]["props"].extend(new_props)
                new_by_condition[cond_key]["email"] = condition["email"]
                new_by_condition[cond_key]["name"] = condition["name"]

                for p in new_props:
                    seen_ids.add(p.unique_id)

    total_new = sum(len(v["props"]) for v in new_by_condition.values())
    logger.info(f"Total new properties: {total_new}")

    for cond_key, data in new_by_condition.items():
        props = data["props"]
        email = data["email"]
        name = data.get("name", cond_key)

        save_properties(props, name)

        if email and props:
            try:
                send_notification(email, props, name)
            except Exception as e:
                logger.error(f"Failed to send notification to {email}: {e}", exc_info=True)

    if total_new > 0:
        commit_and_push()

    logger.info("=== 完了 ===")


def _build_site_condition(condition: dict, site: str) -> dict:
    """Build site-specific condition dict from unified condition."""
    # Equipment conditions are shared across all sites
    equipment = {
        "bt_required":        condition.get("bt_required", False),
        "washstand_required": condition.get("washstand_required", False),
        "pet_option":         condition.get("pet_option", ""),
        "floor_min":          condition.get("floor_min"),
    }
    if site == "suumo":
        return {
            "ta": condition.get("ta", "13"),
            "sc": condition.get("sc", []),
            "km": condition.get("km", 0),
            "et": condition.get("et", 9999999),
            "cn": condition.get("cn"),
            "layouts": condition.get("layouts", []),
            **equipment,
        }
    elif site == "homes":
        return {
            "area_path": condition.get("area_path_homes", ""),
            "pricemax": condition.get("pricemax", 0),
            "walkmax": condition.get("walkmax", 0),
            "age": condition.get("age"),
            "layouts": condition.get("layouts", []),
            **equipment,
        }
    elif site == "athome":
        return {
            "area_path": condition.get("area_path_athome", ""),
            "price_max": condition.get("price_max", 0),
            "walk_max": condition.get("walk_max", 0),
            "age_max": condition.get("age_max"),
            "layouts": condition.get("layouts", []),
            **equipment,
        }
    return condition


if __name__ == "__main__":
    run()
