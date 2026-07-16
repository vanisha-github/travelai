import json
import time
import logging
import httpx
from config import get_settings

logger = logging.getLogger(__name__)


class WeatherService:
    """Service for fetching weather data."""

    def __init__(self):
        self.settings = get_settings()

    async def get_weather(self, city: str) -> dict:
        """Fetch current weather for a city."""
        if self.settings.openweather_api_key:
            return await self._fetch_openweather(city)

        return {
            "city": city,
            "temperature": None,
            "condition": "Data unavailable",
            "humidity": None,
            "description": "Weather data could not be fetched. Please check API configuration.",
            "error": True,
        }

    async def _fetch_openweather(self, city: str) -> dict:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": self.settings.openweather_api_key, "units": "metric"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            result = {
                "city": data.get("name", city),
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"],
                "pressure": data["main"].get("pressure"),
                "visibility": data.get("visibility"),
                "clouds": data.get("clouds", {}).get("all"),
                "error": False,
            }

            rain_data = data.get("rain", {})
            result["rain_chance"] = rain_data.get("1h", rain_data.get("3h", None))

            await self._enrich_with_forecast(city, result)

            return result
        except httpx.HTTPStatusError as e:
            logger.error("OpenWeather API error: %s", e.response.status_code)
            return {"city": city, "error": True, "description": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error("Weather fetch failed: %s", e)
            return {"city": city, "error": True, "description": str(e)}

    async def _enrich_with_forecast(self, city: str, result: dict) -> None:
        """Enrich current weather with forecast data (rain chance, sunrise/sunset)."""
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {"q": city, "appid": self.settings.openweather_api_key, "units": "metric", "cnt": 8}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            if result.get("rain_chance") is None:
                pop_values = [item.get("pop", 0) for item in data.get("list", []) if item.get("pop")]
                if pop_values:
                    result["rain_chance"] = round(max(pop_values) * 100)

            city_data = data.get("city", {})
            sunrise_ts = city_data.get("sunrise", 0)
            sunset_ts = city_data.get("sunset", 0)
            if sunrise_ts:
                from datetime import datetime
                result["sunrise"] = datetime.fromtimestamp(sunrise_ts).strftime("%I:%M %p")
            if sunset_ts:
                from datetime import datetime
                result["sunset"] = datetime.fromtimestamp(sunset_ts).strftime("%I:%M %p")

        except Exception as e:
            logger.warning("Forecast enrichment failed: %s", e)


class SerpService:
    """Service for SerpAPI searches."""

    def __init__(self):
        self.settings = get_settings()
        self._cache: dict[str, tuple[float, str]] = {}
        self._cache_ttl = 300

    def _get_cached(self, key: str) -> str | None:
        if key in self._cache:
            ts, val = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                logger.info("Cache hit for: %s", key)
                return val
            del self._cache[key]
        return None

    def _set_cache(self, key: str, value: str) -> None:
        self._cache[key] = (time.time(), value)

    async def search(self, query: str) -> list[dict]:
        cached = self._get_cached(query)
        if cached:
            return json.loads(cached)

        if not self.settings.serp_api_key:
            return [{"error": "SERP_API_KEY is not configured."}]

        url = "https://serpapi.com/search"
        params = {"q": query, "api_key": self.settings.serp_api_key, "num": 5}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", [])[:5]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })

            self._set_cache(query, json.dumps(results))
            return results
        except Exception as e:
            logger.error("SerpAPI search failed: %s", e)
            return [{"error": str(e)}]

    async def search_hotels(self, destination: str, budget_level: str = "standard") -> list[dict]:
        price_map = {"budget": "cheap", "standard": "mid-range", "luxury": "luxury"}
        price_tag = price_map.get(budget_level, "mid-range")
        query = f"best {price_tag} hotels in {destination} with ratings and prices"
        return await self.search(query)

    async def search_attractions(self, destination: str, interests: str = "sightseeing") -> list[dict]:
        query = f"top things to do in {destination} for {interests} tourists"
        return await self.search(query)

    async def search_travel_info(self, destination: str, info_type: str = "tips") -> list[dict]:
        query = f"{info_type} for traveling to {destination}"
        return await self.search(query)
