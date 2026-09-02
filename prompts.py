"""Interactive prompts for manual (non-auto) survey data entry."""
import re
import logging

from models import DateTimeData, TransactionData

log = logging.getLogger("happymeal.prompts")


def validate_input(prompt: str, pattern: str, error_message: str) -> str:
    """Repeatedly prompt until the user enters a string matching `pattern`."""
    while True:
        user_input = input(prompt)
        if re.match(pattern, user_input):
            return user_input
        print(error_message)


def collect_manual_data(config: dict):
    """Prompt the user for time/transaction details and combine with config date."""
    time_input = validate_input(
        "Enter the time in HH:MM format: ",
        r"^([0-9]|1[0-9]|2[0-3]):[0-5][0-9]$",
        "Incorrect time format. Please provide HH:MM.",
    )
    transaction_number = validate_input(
        "Enter the 4-digit transaction number: ",
        r"^\d{4}$",
        "Invalid transaction number. Please provide a 4-digit number.",
    )
    amount_spent = validate_input(
        "Enter the amount spent in dollars.cents format: ",
        r"^\d+\.\d{2}$",
        "Invalid amount format. Please provide dollars.cents format.",
    )

    when = DateTimeData.from_manual_input(config["date"], time_input)
    transaction = TransactionData.from_manual_input(transaction_number, amount_spent)
    return when, transaction


def generate_survey_data(config: dict):
    """Return (DateTimeData, TransactionData) either generated or manually entered."""
    if config.get("auto") == "True":
        when = DateTimeData.generate()
        transaction = TransactionData.generate(config["ks_number"])
        return when, transaction
    return collect_manual_data(config)
