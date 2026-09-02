"""Selenium automation for filling out the mcdvoice.com survey.

Design: rather than walking a fixed sequence of hardcoded question IDs
(fragile whenever McDonald's renumbers or reorders questions), every page
is scanned for radiogroups. Each group is answered in two passes:

  1. KNOWN ANSWERS  - if the group's ID matches an entry in
     KNOWN_ANSWER_OVERRIDES, click that specific option. Fast and precise
     for the questions we've deliberately chosen an answer for.

  2. SEMI-SMART FALLBACK - for any group not in the override table (new
     questions, renumbered questions, anything unrecognized), read the
     question's label text and choose a reasonable option:
       - meal-time style questions -> match the actual visit hour
       - negatively-framed questions ("was anything wrong?") -> first option
       - everything else -> last option (typically "Yes" / highest rating)
       - no readable label at all -> random option, so the survey never
         gets stuck waiting on a question we can't interpret

This means the whole survey flow is just: scan page, answer everything,
advance, repeat until the validation code appears.
"""
import time
import random
import logging
from dataclasses import dataclass

from selenium import webdriver
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    TimeoutException,
)

from models import DateTimeData, TransactionData

log = logging.getLogger("happymeal.survey")

SURVEY_URL = "https://www.mcdvoice.com/Index.aspx?POSType=PieceMeal"
MAX_PAGES = 40  # safety cap so a stuck/unexpected page can't loop forever

# ---------------------------------------------------------------------------
# Known answers: group ID -> specific option ID we always want clicked.
# These are deliberate choices (not just "pick something positive"), e.g.
# specific rating questions we want answered a particular way regardless of
# how the semi-smart heuristic would read the label text.
#
# Group IDs are the radiogroup <tr> id (e.g. "FNSR000474"), NOT the option
# id. Keying by group ID means a page reflow or option reordering doesn't
# break the match, as long as McDonald's keeps the same group id for the
# same question.
# ---------------------------------------------------------------------------
KNOWN_ANSWER_OVERRIDES = {
    "FNSR000060": "R000060.1",
    "FNSR000455": "R000455.1",
    "FNSR004000": "R004000.2",
    "FNSR001000": "R001000.5",
    "FNSR000444": "R000444.1",
    "FNSR000473": "R000473.1",
    "FNSR000474": "R000474.1",
    "FNSR016000": "R016000.2",
    "FNSR000026": "R000026.2",
    "FNSR020000": "R020000.2",
    "FNSR000387": "R000387.4",
    "FNSR000482": "R000482.5",
}

# Phrases that flip a question's polarity: when these appear in the question
# label, the FIRST/lowest option is the favorable one (e.g. "No" to "was
# anything wrong") rather than the last/highest option.
NEGATIVE_PHRASE_MARKERS = (
    "wrong",
    "problem",
    "issue",
    "complain",
    "error",
    "mistake",
    "miss",
    "incorrect",
    "inaccurate",
    "unhappy",
    "dissatisf",
    "difficult",
    "trouble",
    "cold",
    "rude",
    "wait too long",
    "long wait",
    "dirty",
)

# Phrases that identify a breakfast/lunch (meal-time) style question, so we
# can answer it based on the actual visit hour instead of guessing sentiment.
MEAL_TIME_PHRASE_MARKERS = ("breakfast", "lunch", "dinner", "time of your visit", "time of day")

# Top-level rating pattern used for the "rate these aspects" style pages
# (5-point scales where every option ID ends in .1 through .5).
TOP_RATING_CSS_PATTERN = '[id^="R"][id$=".5"]'


class SurveyError(Exception):
    """Raised when the survey flow cannot proceed."""


@dataclass
class SurveyResult:
    transaction_number: str
    validation_code: str


def build_driver(headless: bool = False) -> webdriver.Chrome:
    """Create a configured Chrome webdriver instance."""
    options = webdriver.ChromeOptions()
    options.add_argument("--log-level=3")
    if headless:
        options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)
    log.debug("Webdriver started (headless=%s)", headless)
    return driver


def safe_click(driver, elem_id: str = None, element=None, retries: int = 3, delay: float = 2.0, wait: float = 10.0) -> bool:
    """
    Click an element by ID (or an already-located WebElement), retrying and
    falling back to a native click if JS-click is intercepted. Returns True
    on success, False if the element could never be located/clicked.

    Pass `element` when you've already located the element (e.g. via a fast
    find_elements probe) to skip the extra lookup entirely. `wait` only
    applies when locating by `elem_id` and controls how long to wait for
    the element to appear.
    """
    found = element
    for attempt in range(1, retries + 1):
        try:
            if found is None:
                if attempt == 1:
                    # Fast path: try a no-wait lookup first: most elements
                    # we're clicking are already on the page (we usually only
                    # get here after confirming presence via find_elements).
                    candidates = driver.find_elements(By.ID, elem_id)
                    found = candidates[0] if candidates else None
                if found is None:
                    WebDriverWait(driver, wait).until(EC.presence_of_element_located((By.ID, elem_id)))
                    found = driver.find_element(By.ID, elem_id)

            driver.execute_script("arguments[0].click();", found)
            log.debug("Clicked #%s (attempt %d)", elem_id or found.get_attribute("id"), attempt)
            return True

        except (ElementClickInterceptedException, ElementNotInteractableException):
            if found is None:
                return False
            try:
                found.click()
                log.debug("Fallback native click succeeded on #%s", elem_id)
                return True
            except Exception as e:
                log.debug("Fallback click on #%s failed: %s", elem_id, e)
                return False

        except (NoSuchElementException, TimeoutException):
            found = None
            if attempt < retries:
                log.debug("Element #%s not found yet (attempt %d/%d), retrying", elem_id, attempt, retries)
                continue
            log.debug("Element with ID %s does not exist on the page.", elem_id)
            return False

        except Exception as e:
            log.warning("Error clicking #%s (attempt %d/%d): %s", elem_id, attempt, retries, e)
            found = None
            if attempt < retries:
                time.sleep(delay)
            else:
                return False
    return False


def click_matching_pattern(driver, css_pattern: str = TOP_RATING_CSS_PATTERN) -> int:
    """Click every element matching the given CSS pattern (default: the top rating option)."""
    elements = driver.find_elements(By.CSS_SELECTOR, css_pattern)
    clicked = 0
    for elem in elements:
        if safe_click(driver, elem.get_attribute("id"), element=elem):
            clicked += 1
    if elements:
        log.debug("Clicked %d/%d elements matching %s", clicked, len(elements), css_pattern)
    return clicked


def _question_label_text(driver, group_id: str) -> str:
    """Best-effort fetch of the human-readable question text for a radiogroup row. No-wait probes."""
    groups = driver.find_elements(By.ID, group_id)
    if not groups:
        return ""
    label_id = groups[0].get_attribute("aria-labelledby")
    if not label_id:
        return ""
    labels = driver.find_elements(By.ID, label_id)
    return labels[0].text.strip().lower() if labels else ""


def _is_negatively_framed(question_text: str) -> bool:
    """True if the question is phrased such that the LOWEST option is favorable."""
    return any(marker in question_text for marker in NEGATIVE_PHRASE_MARKERS)


def _is_meal_time_question(question_text: str) -> bool:
    return any(marker in question_text for marker in MEAL_TIME_PHRASE_MARKERS)


def _sort_option_ids(option_ids: list) -> list:
    """
    Sort option IDs like 'R006000.1' .. 'R006000.5' by their numeric suffix,
    ascending. DOM order is not reliable here — some pages list options in
    a different order than their numeric suffix (e.g. for layout/a11y
    reasons), so picking option_ids[0]/[-1] without sorting can silently
    grab the wrong end of the scale.
    """
    def suffix_key(opt_id: str):
        try:
            return int(opt_id.rsplit(".", 1)[-1])
        except (ValueError, IndexError):
            return 0
    return sorted(option_ids, key=suffix_key)


def _choose_option(option_ids: list, question_text: str, hour) -> tuple:
    """
    Decide which option to click for an unhandled radiogroup.
    Returns (chosen_option_id, reason_string_for_logging).
    """
    ordered = _sort_option_ids(option_ids)

    if question_text and hour is not None and _is_meal_time_question(question_text) and len(ordered) == 2:
        chosen = ordered[1] if int(hour) > 11 else ordered[0]
        return chosen, f"meal-time match for hour={hour}"

    if question_text:
        if _is_negatively_framed(question_text):
            return ordered[0], "lowest-numbered/negative-framed"
        return ordered[-1], "highest-numbered/positive-framed"

    return random.choice(ordered), "random fallback (no readable label)"


def answer_page_radiogroups(driver, hour=None) -> int:
    """
    Scan the current page for every radiogroup and answer each one:

      1. KNOWN ANSWERS - if the group ID is in KNOWN_ANSWER_OVERRIDES,
         click that specific option.
      2. SEMI-SMART FALLBACK - otherwise, infer a reasonable answer from
         the question's label text (see _choose_option).

    Returns the number of groups successfully answered.
    """
    groups = driver.find_elements(By.CSS_SELECTOR, 'tr[role="radiogroup"]')
    answered = 0

    for group in groups:
        group_id = group.get_attribute("id")
        if not group_id:
            continue

        options = group.find_elements(By.CSS_SELECTOR, 'input[type="radio"]')
        option_by_id = {o.get_attribute("id"): o for o in options if o.get_attribute("id")}
        option_ids = list(option_by_id.keys())
        if not option_ids:
            log.debug("Radiogroup %s has no options; skipping", group_id)
            continue

        # Pass 1: known answers.
        override = KNOWN_ANSWER_OVERRIDES.get(group_id)
        if override:
            target = option_by_id.get(override)
            if target is not None and safe_click(driver, override, element=target):
                log.debug("Known-answer: %s -> %s", group_id, override)
                answered += 1
            else:
                log.warning("Known-answer option %s for group %s not found/clickable", override, group_id)
            continue

        # Pass 2: semi-smart fallback.
        question_text = _question_label_text(driver, group_id)
        chosen, reason = _choose_option(option_ids, question_text, hour)

        log.info(
            "Semi-smart answer: %s (%r) -> %s (%s)",
            group_id, question_text or "<no label>", chosen, reason,
        )
        if safe_click(driver, chosen, element=option_by_id.get(chosen)):
            answered += 1
        else:
            log.warning("Failed to click chosen option %s for group %s", chosen, group_id)

    if answered:
        log.debug("Answered %d radiogroup(s) on this page", answered)
    return answered


def fill_initial_data(driver, config: dict, transaction: TransactionData, when: DateTimeData) -> None:
    """Fill in store number, till number, date/time, and transaction fields."""
    driver.get(SURVEY_URL)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "InputStoreID")))

    driver.find_element(By.ID, "InputStoreID").send_keys(config["store_number"])
    driver.find_element(By.ID, "InputRegisterNum").send_keys(config["ks_number"])

    Select(driver.find_element(By.ID, "InputMonth")).select_by_value(when.month)
    Select(driver.find_element(By.ID, "InputDay")).select_by_value(when.day)
    Select(driver.find_element(By.ID, "InputHour")).select_by_value(when.hour)
    Select(driver.find_element(By.ID, "InputMinute")).select_by_value(when.minute)

    driver.find_element(By.ID, "InputTransactionNum").send_keys(transaction.number)
    driver.find_element(By.ID, "AmountSpent1").send_keys(transaction.dollars)
    driver.find_element(By.ID, "AmountSpent2").send_keys(transaction.cents)

    log.info("Initial data filled (store=%s, till=%s, txn=%s)",
              config["store_number"], config["ks_number"], transaction.number)
    safe_click(driver, "NextButton")


def fill_review_text_if_present(driver, hour: str, breakfast: list, lunch: list, general: list) -> str:
    """
    If the free-text review field (#S081000) is present on the current
    page, fill it with a randomly selected review snippet. Returns the
    text used, or "" if the field wasn't on this page. Uses a fast no-wait
    probe since most pages won't have this field.
    """
    fields = driver.find_elements(By.ID, "S081000")
    if not fields:
        return ""

    pool = random.choice([breakfast, general]) if int(hour) < 11 else random.choice([lunch, general])
    review_text = random.choice(pool)

    safe_click(driver, element=fields[0])
    fields[0].send_keys(review_text)
    log.info("Submitted review text: %s", review_text)
    return review_text


def get_validation_code_if_present(driver) -> str:
    """Return the validation code if the confirmation page is currently showing, else "". Fast, no-wait probe."""
    codes = driver.find_elements(By.CLASS_NAME, "ValCode")
    return codes[0].text if codes else ""


def run_survey(driver, config: dict, when: DateTimeData, transaction: TransactionData,
                general: list, breakfast: list, lunch: list) -> SurveyResult:
    """
    Run through the full survey flow for a single submission.
    Raises SurveyError on unrecoverable failure.

    Instead of a fixed page-by-page script, this loops: scan the current
    page, answer every radiogroup (known answers first, semi-smart
    fallback second), fill the review text box if present, then advance.
    This keeps working even if McDonald's reorders, renumbers, or adds
    survey questions.
    """
    try:
        fill_initial_data(driver, config, transaction, when)

        for page_num in range(1, MAX_PAGES + 1):
            code = get_validation_code_if_present(driver)
            if code:
                log.info("Validation code retrieved: %s", code)
                return SurveyResult(transaction_number=transaction.number, validation_code=code)

            answer_page_radiogroups(driver, hour=when.hour)
            fill_review_text_if_present(driver, when.hour, breakfast, lunch, general)
            click_matching_pattern(driver)  # catch any bare 5-point-scale rows not in a tracked radiogroup

            advanced = safe_click(driver, "NextButton", wait=6.0)
            if not advanced:
                # Nothing left to click and no NextButton found; check once
                # more for the validation code before giving up.
                code = get_validation_code_if_present(driver)
                if code:
                    log.info("Validation code retrieved: %s", code)
                    return SurveyResult(transaction_number=transaction.number, validation_code=code)
                raise SurveyError(f"Stuck on page {page_num}: no NextButton and no validation code found")

        raise SurveyError(f"Exceeded MAX_PAGES ({MAX_PAGES}) without reaching a validation code")

    except SurveyError:
        raise
    except Exception as e:
        log.exception("Survey run failed")
        raise SurveyError(str(e)) from e
