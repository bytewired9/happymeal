"""Data models for survey submissions: date/time and transaction info."""
import random
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

log = logging.getLogger("happymeal.models")


@dataclass
class DateTimeData:
    """Date/time values used to fill the survey's visit-date fields."""
    month: str
    day: str
    hour: str
    minute: str

    @staticmethod
    def generate() -> "DateTimeData":
        """Generate a plausible recent visit date/time (within the last 5 days, 5am-11am)."""
        current_date = datetime.today()
        selected_day = current_date.day - random.randint(0, 5)

        if selected_day <= 0:
            prev_month_last_date = current_date.replace(day=1) - timedelta(days=1)
            selected_day += prev_month_last_date.day

        data = DateTimeData(
            month=str(current_date.month).zfill(2),
            day=str(selected_day).zfill(2),
            hour=str(random.randint(5, 11)).zfill(2),
            minute=str(random.randint(0, 59)).zfill(2),
        )
        log.debug("Generated date/time data: %s", data)
        return data

    @staticmethod
    def from_manual_input(date_input: str, time_input: str) -> "DateTimeData":
        """Build DateTimeData from user-provided 'mm/dd' and 'HH:MM' strings."""
        month, day = date_input.split("/")
        hour, minute = time_input.split(":")
        data = DateTimeData(month=month, day=day, hour=hour, minute=minute)
        log.debug("Parsed manual date/time data: %s", data)
        return data


@dataclass
class TransactionData:
    """Transaction number and amount spent used to fill the survey's receipt fields."""
    number: str
    dollars: str
    cents: str

    @staticmethod
    def generate(ks_number: str) -> "TransactionData":
        """Generate a pseudo-random transaction number and amount."""
        data = TransactionData(
            number=f"{ks_number}{random.randint(0, 99):02}",
            dollars=str(random.randint(1, 30)),
            cents=str(random.randint(0, 99)).zfill(2),
        )
        log.debug("Generated transaction data: %s", data)
        return data

    @staticmethod
    def from_manual_input(transaction_number: str, amount_spent: str) -> "TransactionData":
        """Build TransactionData from a user-provided transaction number and 'dollars.cents'."""
        dollars, cents = amount_spent.split(".")
        data = TransactionData(number=transaction_number, dollars=dollars, cents=cents)
        log.debug("Parsed manual transaction data: %s", data)
        return data
