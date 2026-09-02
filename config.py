"""Configuration loading for HappyMeal."""
import os
import logging

log = logging.getLogger("happymeal.config")

DEFAULT_CONFIG_TEMPLATE = """\
date=mm/dd # The date being used for the orders. e.g. 12/25 would be Christmas day.
store_number=12345 # this is the number of your mcdonalds store
ks_number=01 # This is the number of the till
auto=False # This determines if HappyMeal generates random orders or uses real orders, Overrides date field. Accepts True/False (case sensitive)
debug=False # Enable verbose debug logging and non-headless troubleshooting output. Accepts True/False (case sensitive)
"""

REQUIRED_KEYS = ("date", "store_number", "ks_number", "auto")
BOOL_KEYS = ("auto", "debug")


class ConfigError(Exception):
    """Raised when config.txt is missing required or well-formed values."""


def ensure_config_exists(path: str) -> bool:
    """
    Create config.txt with default values if it doesn't already exist.

    Returns True if a new file was created (caller should prompt the user
    to edit it and exit), False if a config already exists.
    """
    if os.path.exists(path):
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG_TEMPLATE)
    log.info("Created new config.txt at %s", path)
    return True


def _parse_line(line: str):
    stripped = line.split("#", 1)[0].strip()
    if not stripped:
        return None
    if "=" not in stripped:
        raise ConfigError(f"Malformed config line (missing '='): {line!r}")
    key, value = stripped.split("=", 1)
    return key.strip(), value.strip()


def read_config(path: str) -> dict:
    """Read and validate config.txt, returning a dict of settings."""
    if not os.path.exists(path):
        raise ConfigError(f"{path} does not exist")

    parsed = {}
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            try:
                kv = _parse_line(line)
            except ConfigError as e:
                raise ConfigError(f"{e} (line {lineno})") from e
            if kv:
                key, value = kv
                parsed[key] = value

    missing = [k for k in REQUIRED_KEYS if k not in parsed]
    if missing:
        raise ConfigError(f"config.txt is missing required key(s): {', '.join(missing)}")

    # Normalize booleans but keep string values for backwards compatibility
    # with the rest of the code, which historically compared against "True".
    for key in BOOL_KEYS:
        if key in parsed and parsed[key] not in ("True", "False"):
            raise ConfigError(f"config.txt key '{key}' must be 'True' or 'False', got {parsed[key]!r}")

    parsed.setdefault("debug", "False")

    return parsed


def config_bool(config: dict, key: str, default: bool = False) -> bool:
    """Read a boolean-ish config value safely."""
    return config.get(key, str(default)) == "True"
