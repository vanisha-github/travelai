import json
import httpx
from crewai.tools import BaseTool
from pydantic import Field

from config import get_settings


class SerpSearchTool(BaseTool):
    """Search Google via SerpAPI and return structured results."""

    name: str = "serp_search"
    description: str = (
        "Search the web using SerpAPI. Input should be a search query string. "
        "Returns top search results with titles, links, and snippets."
    )

    def _run(self, query: str) -> str:
        settings = get_settings()
        if not settings.serp_api_key:
            return json.dumps({"error": "SERP_API_KEY is not configured."})

        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": settings.serp_api_key,
            "num": 10,
        }

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", [])[:8]:
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "rating": item.get("rating"),
                    "price": item.get("price"),
                    "address": item.get("address"),
                })

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class HotelSearchTool(BaseTool):
    """Search for hotels in a specific destination using SerpAPI."""

    name: str = "hotel_search"
    description: str = (
        "Search for hotels in a given destination. "
        "Input format: 'destination | budget_level (budget/standard/luxury)'"
    )

    def _run(self, query: str) -> str:
        settings = get_settings()
        if not settings.serp_api_key:
            return json.dumps({"error": "SERP_API_KEY is not configured."})

        parts = [p.strip() for p in query.split("|")]
        destination = parts[0] if parts else query
        budget_level = parts[1] if len(parts) > 1 else "standard"

        price_map = {"budget": "cheap", "standard": "mid-range", "luxury": "luxury"}
        price_tag = price_map.get(budget_level, "mid-range")

        search_query = f"best {price_tag} hotels in {destination} with ratings reviews prices amenities"

        url = "https://serpapi.com/search"
        params = {
            "q": search_query,
            "api_key": settings.serp_api_key,
            "num": 10,
        }

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", [])[:8]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "rating": item.get("rating"),
                    "price": item.get("price"),
                    "address": item.get("address"),
                })

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class AttractionSearchTool(BaseTool):
    """Search for tourist attractions in a destination using SerpAPI."""

    name: str = "attraction_search"
    description: str = (
        "Search for tourist attractions and activities in a destination. "
        "Input format: 'destination | interests (comma-separated)'"
    )

    def _run(self, query: str) -> str:
        settings = get_settings()
        if not settings.serp_api_key:
            return json.dumps({"error": "SERP_API_KEY is not configured."})

        parts = [p.strip() for p in query.split("|")]
        destination = parts[0] if parts else query
        interests = parts[1] if len(parts) > 1 else "sightseeing"

        search_query = f"best things to do in {destination} for {interests} tourists top attractions reviews"

        url = "https://serpapi.com/search"
        params = {
            "q": search_query,
            "api_key": settings.serp_api_key,
            "num": 10,
        }

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", [])[:8]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "rating": item.get("rating"),
                    "price": item.get("price"),
                    "address": item.get("address"),
                })

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class WeatherSearchTool(BaseTool):
    """Fetch comprehensive weather data for a destination."""

    name: str = "weather_search"
    description: str = (
        "Search for current weather information for a destination. "
        "Input should be the destination city name."
    )

    def _run(self, destination: str) -> str:
        settings = get_settings()

        if settings.openweather_api_key:
            return self._fetch_openweather(destination, settings.openweather_api_key)

        if settings.serp_api_key:
            return self._search_weather_serp(destination, settings.serp_api_key)

        return json.dumps({"error": "No weather API key configured."})

    def _fetch_openweather(self, city: str, api_key: str) -> str:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": api_key, "units": "metric"}

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            from datetime import datetime

            sunrise_ts = data.get("sys", {}).get("sunrise", 0)
            sunset_ts = data.get("sys", {}).get("sunset", 0)
            sunrise = datetime.fromtimestamp(sunrise_ts).strftime("%I:%M %p") if sunrise_ts else ""
            sunset = datetime.fromtimestamp(sunset_ts).strftime("%I:%M %p") if sunset_ts else ""

            weather = {
                "city": data.get("name", city),
                "country": data.get("sys", {}).get("country", ""),
                "temperature": round(data["main"]["temp"], 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "humidity": data["main"]["humidity"],
                "pressure": data["main"].get("pressure", 0),
                "condition": data["weather"][0]["main"],
                "description": data["weather"][0]["description"],
                "wind_speed": round(data["wind"]["speed"], 1),
                "wind_deg": data["wind"].get("deg", 0),
                "clouds": data.get("clouds", {}).get("all", 0),
                "visibility": data.get("visibility", 0),
                "sunrise": sunrise,
                "sunset": sunset,
            }
            return json.dumps(weather, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _search_weather_serp(self, city: str, api_key: str) -> str:
        url = "https://serpapi.com/search"
        params = {"q": f"current weather in {city}", "api_key": api_key, "num": 3}

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", [])[:3]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                })

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class TravelInfoSearchTool(BaseTool):
    """Search for general travel information about a destination."""

    name: str = "travel_info_search"
    description: str = (
        "Search for travel tips, visa info, local customs, and transport info. "
        "Input format: 'destination | info_type (tips/visa/transport/customs/food)'"
    )

    def _run(self, query: str) -> str:
        settings = get_settings()
        if not settings.serp_api_key:
            return json.dumps({"error": "SERP_API_KEY is not configured."})

        parts = [p.strip() for p in query.split("|")]
        destination = parts[0] if parts else query
        info_type = parts[1] if len(parts) > 1 else "tips"

        search_query = f"{info_type} for traveling to {destination}"

        url = "https://serpapi.com/search"
        params = {"q": search_query, "api_key": settings.serp_api_key, "num": 8}

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", [])[:8]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                })

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


class RestaurantSearchTool(BaseTool):
    """Search for restaurants and local food in a destination."""

    name: str = "restaurant_search"
    description: str = (
        "Search for restaurants and local food recommendations. "
        "Input format: 'destination | cuisine_type (optional)'"
    )

    def _run(self, query: str) -> str:
        settings = get_settings()
        if not settings.serp_api_key:
            return json.dumps({"error": "SERP_API_KEY is not configured."})

        parts = [p.strip() for p in query.split("|")]
        destination = parts[0] if parts else query
        cuisine = parts[1] if len(parts) > 1 else ""

        search_query = f"best restaurants in {destination}"
        if cuisine:
            search_query += f" {cuisine} cuisine"
        search_query += " ratings prices reviews"

        url = "https://serpapi.com/search"
        params = {"q": search_query, "api_key": settings.serp_api_key, "num": 8}

        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("organic_results", [])[:6]:
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "rating": item.get("rating"),
                    "price": item.get("price"),
                    "address": item.get("address"),
                })

            return json.dumps(results, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


def get_all_tools() -> list:
    """Return list of all available tools for the crew."""
    return [
        SerpSearchTool(),
        HotelSearchTool(),
        AttractionSearchTool(),
        WeatherSearchTool(),
        TravelInfoSearchTool(),
        RestaurantSearchTool(),
    ]
