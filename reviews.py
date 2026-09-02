"""Loading and caching of review text snippets used to fill free-text survey fields."""
import os
import json
import hashlib
import logging
import requests

log = logging.getLogger("happymeal.reviews")

REVIEWS_URL = "https://raw.githubusercontent.com/ForgedCore8/happymeal/main/reviews.json"


class ReviewLoadError(Exception):
    """Raised when reviews.json cannot be fetched or parsed."""


def _download(dest_path: str) -> None:
    log.info("Downloading latest reviews.json from GitHub...")
    response = requests.get(REVIEWS_URL, timeout=10)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        f.write(response.content)
    log.debug("Saved reviews.json to %s", dest_path)


def _remote_checksum() -> str:
    response = requests.get(REVIEWS_URL, timeout=10)
    response.raise_for_status()
    return hashlib.md5(response.content).hexdigest()


def _local_checksum(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _needs_update(local_path: str) -> bool:
    if not os.path.exists(local_path):
        return True
    try:
        return _local_checksum(local_path) != _remote_checksum()
    except requests.RequestException as e:
        log.warning("Could not check for reviews.json updates (%s); using local copy.", e)
        return False


def load_reviews(cache_dir: str):
    """
    Load (general, breakfast, lunch) review lists, refreshing the local
    cache from GitHub if missing or outdated.
    """
    local_path = os.path.join(cache_dir, "reviews.json")

    try:
        if _needs_update(local_path):
            _download(local_path)

        with open(local_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        reviews = data["reviews"]
        general = reviews["general"]
        breakfast = reviews["breakfast"]
        lunch = reviews["lunch"]
        log.debug(
            "Loaded %d general, %d breakfast, %d lunch reviews",
            len(general), len(breakfast), len(lunch)
        )
        return general, breakfast, lunch

    except (requests.RequestException, OSError, json.JSONDecodeError, KeyError) as e:
        raise ReviewLoadError(f"Failed to load reviews: {e}") from e
