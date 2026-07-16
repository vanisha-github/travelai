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
    """Try to extract JSON from agent text output.

    Uses multiple strategies to find valid JSON even in messy output.
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Strategy 1: Try parsing the entire text as JSON
    try:
        parsed = json.loads(text)
        return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Find JSON in code fences
    patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
        r"```json(.*?)```",
        r"```(.*?)```",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                parsed = json.loads(match.strip())
                return parsed
            except (json.JSONDecodeError, ValueError):
                continue

    # Strategy 3: Find the outermost { } or [ ]
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start = text.find(start_char)
        if start == -1:
            continue
        # Find matching end bracket by counting nesting
        depth = 0
        for i in range(start, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        parsed = json.loads(candidate)
                        return parsed
                    except (json.JSONDecodeError, ValueError):
                        break
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


def validate_url(url) -> str:
    """Validate a URL field. Returns empty string for invalid URLs."""
    if not url:
        return ""
    url = str(url).strip()
    if not url:
        return ""
    if '<' in url or '>' in url or '"' in url:
        logger.warning("Invalid URL discarded (HTML): %s", url[:120])
        return ""
    if 'javascript:' in url.lower():
        logger.warning("Invalid URL discarded (javascript): %s", url[:120])
        return ""
    if not url.lower().startswith(('http://', 'https://')):
        logger.warning("Invalid URL discarded (not http): %s", url[:120])
        return ""
    return url


def validate_trip_urls(data: dict) -> dict:
    """Recursively validate all URL fields in a trip data dict."""
    url_keys = {'website_url', 'maps_url', 'booking_url', 'url', 'link'}
    if isinstance(data, dict):
        for key in data:
            if key in url_keys and isinstance(data[key], str):
                data[key] = validate_url(data[key])
            elif isinstance(data[key], (dict, list)):
                validate_trip_urls(data[key])
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                validate_trip_urls(item)
    return data


def generate_trip_id() -> str:
    """Generate a unique trip identifier."""
    return datetime.now().strftime("trip_%Y%m%d_%H%M%S")
