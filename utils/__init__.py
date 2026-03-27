"""
Pacote de utilitários
"""

from .logger import setup_logger
from .report_writer import (
    build_daily_learning_digest,
    build_market_report,
    build_telegram_market_brief,
    save_report,
)
from .telegram_notifier import TelegramNotifier
from .theory_library import (
    get_macro_learning_cards,
    load_macro_library,
    select_relevant_theory_sections,
)
from .helpers import (
    serialize_to_json,
    format_number,
    percent_change,
    moving_average,
    find_outliers,
    merge_dataframes,
    DataCache,
)

__all__ = [
    "setup_logger",
    "build_daily_learning_digest",
    "build_market_report",
    "build_telegram_market_brief",
    "save_report",
    "TelegramNotifier",
    "get_macro_learning_cards",
    "load_macro_library",
    "select_relevant_theory_sections",
    "serialize_to_json",
    "format_number",
    "percent_change",
    "moving_average",
    "find_outliers",
    "merge_dataframes",
    "DataCache",
]
