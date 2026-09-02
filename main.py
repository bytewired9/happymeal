#!/usr/bin/env python3
"""HappyMeal - McDonald's customer survey filler-outer-inator."""
import os
import sys
import argparse
import logging

import requests
from colorama import Fore, Style, init as colorama_init

from config import ensure_config_exists, read_config, config_bool, ConfigError
from reviews import load_reviews, ReviewLoadError
from survey import build_driver, run_survey, SurveyError
from prompts import generate_survey_data

VERSION = "1.2.0"
LATEST_RELEASE_URL = "https://api.github.com/repos/ForgedCore8/happymeal/releases/latest"

CWD = os.getcwd()
CONFIG_PATH = os.path.join(CWD, "config.txt")
LOG_PATH = os.path.join(CWD, "happymeal.log")
VALIDATION_CODES_PATH = os.path.join(CWD, "validation_codes.txt")


def setup_logging(debug: bool) -> logging.Logger:
    """Configure root + module logging. Debug mode logs to console and file at DEBUG level."""
    level = logging.DEBUG if debug else logging.INFO
    handlers = [logging.StreamHandler(sys.stdout)]
    if debug:
        handlers.append(logging.FileHandler(LOG_PATH, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s" if debug else "%(message)s",
        handlers=handlers,
        force=True,
    )
    log = logging.getLogger("happymeal")
    if debug:
        log.debug("Debug logging enabled. Full log at %s", LOG_PATH)
    return log


def print_logo():
    print(
        Fore.YELLOW
        + """              &&&&&     &&&&&
            &&&&&&&&& &&&&&&&&&
           &&      $&&&      &&X
      ++++++++++++++++++++++++++++++
     ++++++++++++++++++++++++++++++++
     ++++++++++++++++++++++++++++++++
    ++++++++++++++++++++++++++++++++++
    $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    &&&&&$ x&&&&&&&&&&&&&&&&&&x $&&&&&
    &&&&&&x   x&&&&&&&&&&&&X   x&&&&&&
    &&&&&&&&$                X&&&&&&&&
    &&&&&&&&&&&&:        .$&&&&&&&&&&&
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
    &&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&
          """
        + Style.RESET_ALL
    )


def check_for_update(log: logging.Logger):
    try:
        response = requests.get(LATEST_RELEASE_URL, timeout=10)
        response.raise_for_status()
        latest = response.json().get("tag_name", "").lstrip("v")
        if latest and [int(x) for x in latest.split(".")] > [int(x) for x in VERSION.split(".")]:
            print(Fore.CYAN + f"A newer version is available: {latest} (current: {VERSION})" + Style.RESET_ALL)
    except (requests.RequestException, ValueError) as e:
        log.debug("Update check skipped/failed: %s", e)


def save_validation_code(transaction_number: str, validation_code: str, completed_count: int = None):
    with open(VALIDATION_CODES_PATH, "a", encoding="utf-8") as f:
        f.write(f"Order number {transaction_number} - {validation_code}\n")


def run_one_survey(config: dict, driver, log: logging.Logger) -> bool:
    """Run a single survey submission. Returns True on success, False on failure."""
    try:
        general, breakfast, lunch = load_reviews(CWD)
    except ReviewLoadError as e:
        log.error("Could not load reviews: %s", e)
        return False

    when, transaction = generate_survey_data(config)

    try:
        result = run_survey(driver, config, when, transaction, general, breakfast, lunch)
    except SurveyError as e:
        log.error("Survey failed: %s", e)
        return False

    print(Fore.GREEN + f"Validation code: {result.validation_code}" + Style.RESET_ALL)
    save_validation_code(result.transaction_number, result.validation_code)
    return True


def parse_args():
    parser = argparse.ArgumentParser(description="HappyMeal - McDonald's survey autofiller")
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable verbose debug logging (also written to happymeal.log)"
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="Run Chrome in headless mode"
    )
    parser.add_argument(
        "--count", type=int, default=None,
        help="Number of surveys to complete (auto mode only; overrides interactive prompt)"
    )
    return parser.parse_args()


def main():
    colorama_init(autoreset=True)
    args = parse_args()

    os.system("cls" if os.name == "nt" else "clear")

    try:
        if ensure_config_exists(CONFIG_PATH):
            print("A new config.txt was created. Please edit it before running again.")
            return
        config = read_config(CONFIG_PATH)
    except ConfigError as e:
        print(Fore.RED + f"Configuration error: {e}" + Style.RESET_ALL)
        sys.exit(1)

    # --debug flag overrides config.txt's debug setting
    debug = args.debug or config_bool(config, "debug")
    log = setup_logging(debug)

    print_logo()
    check_for_update(log)

    driver = build_driver(headless=args.headless)
    completed = 0

    try:
        if config.get("auto") == "True":
            target = args.count
            if target is None:
                target = int(input("How many surveys would you like completed? : "))
            while completed < target:
                print(f"Survey {completed + 1} of {target}")
                if run_one_survey(config, driver, log):
                    completed += 1
            print(Fore.GREEN + f"Completed {completed} surveys." + Style.RESET_ALL)
        else:
            while True:
                run_one_survey(config, driver, log)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Cleaning up...")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
