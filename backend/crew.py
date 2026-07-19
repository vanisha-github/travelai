import json
import logging
import httpx
from crewai import Crew, Process

from agents import (
    create_travel_planner_agent,
    create_hotel_agent,
    create_attraction_agent,
    create_weather_agent,
    create_budget_agent,
)
from tasks import (
    create_hotel_task,
    create_attraction_task,
    create_weather_task,
    create_budget_task,
    create_planning_task,
)
from utils import build_trip_context
from config import get_settings

logger = logging.getLogger(__name__)


def _fetch_real_weather(city: str) -> dict:
    """Fetch real weather data from OpenWeather API. Returns dict or empty dict."""
    settings = get_settings()
    if not settings.openweather_api_key:
        return {}

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": settings.openweather_api_key, "units": "metric"}
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        from datetime import datetime
        sunrise_ts = data.get("sys", {}).get("sunrise", 0)
        sunset_ts = data.get("sys", {}).get("sunset", 0)

        result = {
            "city": data.get("name", city),
            "country": data.get("sys", {}).get("country", ""),
            "temperature": round(data["main"]["temp"], 1),
            "feels_like": round(data["main"]["feels_like"], 1),
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "wind_speed": round(data["wind"]["speed"], 1),
            "clouds": data.get("clouds", {}).get("all", 0),
            "pressure": data["main"].get("pressure"),
            "visibility": data.get("visibility"),
            "sunrise": datetime.fromtimestamp(sunrise_ts).strftime("%I:%M %p") if sunrise_ts else "",
            "sunset": datetime.fromtimestamp(sunset_ts).strftime("%I:%M %p") if sunset_ts else "",
        }

        result["rain_chance"] = None

        try:
            forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
            forecast_params = {"q": city, "appid": settings.openweather_api_key, "units": "metric", "cnt": 8}
            with httpx.Client(timeout=10) as client:
                fresp = client.get(forecast_url, params=forecast_params)
                fresp.raise_for_status()
                fdata = fresp.json()

            if result.get("rain_chance") is None:
                pop_values = [item.get("pop", 0) for item in fdata.get("list", []) if item.get("pop")]
                if pop_values:
                    result["rain_chance"] = round(max(pop_values) * 100)

            city_data = fdata.get("city", {})
            if not sunrise_ts:
                fsunrise = city_data.get("sunrise", 0)
                if fsunrise:
                    result["sunrise"] = datetime.fromtimestamp(fsunrise).strftime("%I:%M %p")
            if not sunset_ts:
                fsunset = city_data.get("sunset", 0)
                if fsunset:
                    result["sunset"] = datetime.fromtimestamp(fsunset).strftime("%I:%M %p")

        except Exception as e:
            logger.warning("Forecast enrichment failed: %s", e)

        return result
    except Exception as e:
        logger.warning("Weather fetch failed: %s", e)
        return {}


def _fetch_serp_data(query: str) -> list[dict]:
    """Fetch data from SerpAPI. Returns list of result dicts."""
    settings = get_settings()
    if not settings.serp_api_key:
        return []

    try:
        url = "https://serpapi.com/search"
        params = {"q": query, "api_key": settings.serp_api_key, "num": 8}
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        junk_patterns = ["wikipedia.org/wiki/Top", "disambiguation", "may refer to",
                         "Wiktionary", "Wikimedia", "Wikidata"]
        for item in data.get("organic_results", [])[:8]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            link = item.get("link", "")
            if any(p.lower() in (title + snippet + link).lower() for p in junk_patterns):
                continue
            if len(snippet) < 15:
                continue
            results.append({
                "title": title,
                "snippet": snippet,
                "link": link,
                "rating": item.get("rating"),
                "address": item.get("address"),
                "thumbnail": item.get("thumbnail", ""),
            })
        return results[:6]
    except Exception as e:
        logger.warning("SerpAPI fetch failed: %s", e)
        return []


def build_crew(trip_request):
    """Build and configure the CrewAI crew for trip planning.

    Pre-fetches real data and stores it on the request for later use.
    """
    context = build_trip_context(trip_request)
    destination = trip_request.destination

    logger.info("Fetching real data for %s...", destination)

    real_weather = _fetch_real_weather(destination)
    hotel_serp = _fetch_serp_data(f"best hotels in {destination} ratings prices reviews amenities")
    attraction_serp = _fetch_serp_data(f"top things to do in {destination} attractions sights activities")
    restaurant_serp = _fetch_serp_data(f"best restaurants in {destination} local food cuisine")

    logger.info("Weather: %s | Hotels: %d results | Attractions: %d results | Restaurants: %d results",
                "fetched" if real_weather else "none",
                len(hotel_serp), len(attraction_serp), len(restaurant_serp))

    # Store pre-fetched data for use in response building
    trip_request._pre_fetched = {
        "weather": real_weather,
        "hotels": hotel_serp,
        "attractions": attraction_serp,
        "restaurants": restaurant_serp,
    }

    hotel_agent = create_hotel_agent()
    attraction_agent = create_attraction_agent()
    weather_agent = create_weather_agent()
    budget_agent = create_budget_agent()
    planner_agent = create_travel_planner_agent()

    weather_json = json.dumps(real_weather, indent=2) if real_weather else ""
    hotel_json = json.dumps(hotel_serp, indent=2) if hotel_serp else ""
    attraction_json = json.dumps(attraction_serp, indent=2) if attraction_serp else ""
    restaurant_json = json.dumps(restaurant_serp, indent=2) if restaurant_serp else ""

    hotel_task = create_hotel_task(hotel_agent, context, weather_json, hotel_json)
    attraction_task = create_attraction_task(attraction_agent, context, attraction_json)
    weather_task = create_weather_task(weather_agent, context, weather_json)
    budget_task = create_budget_task(budget_agent, context, hotel_json)
    planning_task = create_planning_task(planner_agent, context, num_days=trip_request.num_days)

    hotel_task.context = []
    attraction_task.context = [hotel_task]
    weather_task.context = [hotel_task, attraction_task]
    budget_task.context = [hotel_task, attraction_task, weather_task]
    planning_task.context = [hotel_task, attraction_task, weather_task, budget_task]

    crew = Crew(
        agents=[hotel_agent, attraction_agent, weather_agent, budget_agent, planner_agent],
        tasks=[hotel_task, attraction_task, weather_task, budget_task, planning_task],
        process=Process.sequential,
        verbose=True,
    )

    logger.info("Crew built with %d agents and %d tasks", len(crew.agents), len(crew.tasks))
    return crew, context
