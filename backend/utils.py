import json
import re
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_trip_context(request) -> str:
    """Build a context string from trip request for agent consumption."""
    interests_str = ", ".join([i.value for i in request.interests])
    return (
        f"Trip from {request.source_city} to {request.destination}\n"
        f"Duration: {request.num_days} days\n"
        f"Travellers: {request.num_travellers}\n"
        f"Budget: ${request.budget:,.2f} total\n"
        f"Interests: {interests_str}\n"
        f"Hotel preference: {request.hotel_preference.value}\n"
    )


def extract_json_from_text(text: str) -> dict | list | None:
    """Try to extract JSON from agent text output."""
    patterns = [
        r"```json\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
        r"(\{.*\})",
        r"(\[.*\])",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


def calculate_budget_per_person(total_budget: float, num_travellers: int) -> dict:
    """Calculate budget breakdown per person."""
    per_person = total_budget / num_travellers
    return {
        "total_budget": total_budget,
        "per_person": round(per_person, 2),
        "num_travellers": num_travellers,
    }


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format a number as currency."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}
    symbol = symbols.get(currency, "$")
    return f"{symbol}{amount:,.2f}"


def timing_decorator(func):
    """Decorator to log execution time of functions."""
    async def wrapper(*args, **kwargs):
        start = time.time()
        logger.info("Starting %s", func.__name__)
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start
            logger.info("Completed %s in %.2fs", func.__name__, elapsed)
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error("Failed %s after %.2fs: %s", func.__name__, elapsed, e)
            raise
    return wrapper


def sanitize_output(text: str) -> str:
    """Clean up agent output text."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


def generate_trip_id() -> str:
    """Generate a unique trip identifier."""
    return datetime.now().strftime("trip_%Y%m%d_%H%M%S")
