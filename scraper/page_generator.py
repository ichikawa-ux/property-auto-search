"""Commits updated docs/data/properties.json to the repository."""
import os
import logging
import subprocess

logger = logging.getLogger(__name__)


def commit_and_push():
    """Commit changes to properties.json and push so GitHub Pages redeploys."""
    if not os.path.exists("docs/data/properties.json"):
        logger.info("No properties.json to commit")
        return

    _run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
    _run(["git", "config", "user.name", "github-actions[bot]"])
    _run(["git", "add", "docs/data/properties.json"])

    status = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True
    ).stdout.strip()

    if not status:
        logger.info("No changes to commit")
        return

    _run(["git", "commit", "-m", "chore: update property data [skip ci]"])
    _run(["git", "push"])
    logger.info("Pushed properties.json to repository")


def _run(cmd: list[str]):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result
