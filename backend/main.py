import json
import logging
import re
import time
from contextlib import asynccontextmanager
import traceback
import urllib.parse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from models import (
    TripRequest, ItineraryResponse, WeatherInfo, HotelRecommendation,
    BudgetBreakdown, DayPlan, AttractionRecommendation, RestaurantRecommendation,
    TransportOption, AIInsights, HealthResponse,
)
from crew import build_crew
from services import WeatherService, SerpService
from utils import setup_logging, extract_json_from_text, generate_trip_id, validate_url

setup_logging()
logger = logging.getLogger(__name__)

weather_service = WeatherService()
serp_service = SerpService()

trip_history: list[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Starting AI Travel Planner on %s:%s", settings.host, settings.port)
    yield
    logger.info("Shutting down AI Travel Planner")


app = FastAPI(
    title="AI Travel Planner API",
    description="Multi-agent travel planning system powered by CrewAI and Google Gemini",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", version="3.0.0")


@app.post("/plan-trip", response_model=ItineraryResponse)
async def plan_trip(request: TripRequest):
    start = time.time()
    logger.info(
        "Trip request: %s -> %s (%d days, %d travellers, $%.0f)",
        request.source_city, request.destination,
        request.num_days, request.num_travellers, request.budget,
    )

    try:
        crew, context = build_crew(request)
        result = crew.kickoff()

        raw_output = str(result)
        logger.info("Crew execution completed in %.2fs", time.time() - start)

        pre_fetched = getattr(request, "_pre_fetched", {})
        itinerary = _parse_itinerary(raw_output, request, pre_fetched)

        trip_id = generate_trip_id()
        trip_history.append({
            "id": trip_id,
            "destination": request.destination,
            "itinerary": itinerary.model_dump(),
        })

        logger.info("Trip planned successfully: %s", trip_id)
        return itinerary

    except Exception as e:
        traceback.print_exc()
        raise


@app.get("/weather/{city}")
async def get_weather(city: str):
    logger.info("Weather request for: %s", city)
    data = await weather_service.get_weather(city)
    if data.get("error"):
        raise HTTPException(status_code=502, detail=data.get("description", "Weather service error"))
    return data


@app.get("/hotels/{destination}")
async def get_hotels(destination: str, budget: str = "standard"):
    logger.info("Hotel search: %s (%s)", destination, budget)
    results = await serp_service.search_hotels(destination, budget)
    return {"destination": destination, "budget": budget, "results": results}


@app.get("/trips")
async def list_trips():
    return {"trips": trip_history, "count": len(trip_history)}


@app.delete("/trips/{trip_id}")
async def delete_trip(trip_id: str):
    global trip_history
    trip_history = [t for t in trip_history if t["id"] != trip_id]
    return {"status": "deleted"}


def _maps_url(name: str, city: str = "") -> str:
    query = f"{name} {city}".strip() if city else name
    encoded = urllib.parse.quote_plus(query)
    return f"https://www.google.com/maps/search/?api=1&query={encoded}"


def _weather_icon(condition: str) -> str:
    mapping = {
        "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️", "Drizzle": "🌦️",
        "Thunderstorm": "⛈️", "Snow": "❄️", "Mist": "🌫️", "Fog": "🌫️",
        "Haze": "🌫️", "Smoke": "🌫️", "Dust": "💨", "Wind": "💨",
        "overcast clouds": "☁️", "scattered clouds": "⛅", "broken clouds": "🌥️",
        "few clouds": "🌤️", "light rain": "🌦️", "moderate rain": "🌧️",
        "heavy rain": "⛈️", "clear sky": "☀️",
    }
    for key, icon in mapping.items():
        if key.lower() in condition.lower():
            return icon
    return "🌤️"


def _clean_text(text: str) -> str:
    """Remove any JSON fragments, code fences, or raw data from display text."""
    if not text:
        return text
    text = re.sub(r"```json.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"```\s*.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r'\{[^{}]*"[^"]*"[^{}]*\}', "", text)
    text = re.sub(r"\[[\s\S]{0,200}\]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_itinerary(raw_output: str, request: TripRequest, pre_fetched: dict = None) -> ItineraryResponse:
    """Parse crew output with retry and fallback to pre-fetched data."""
    if pre_fetched is None:
        pre_fetched = {}

    # Attempt 1: Extract JSON from crew output
    extracted = extract_json_from_text(raw_output)
    if isinstance(extracted, dict) and _has_required_fields(extracted):
        try:
            response = _build_response_from_dict(extracted, raw_output, request, pre_fetched)
            response.trip_summary = _clean_text(response.trip_summary)
            return response
        except Exception as e:
            logger.warning("JSON parse attempt 1 failed: %s", e)

    # Attempt 2: Try again with different extraction
    if isinstance(extracted, dict):
        try:
            response = _build_response_from_dict(extracted, raw_output, request, pre_fetched)
            response.trip_summary = _clean_text(response.trip_summary)
            if response.recommended_hotels and response.attractions:
                return response
        except Exception:
            pass

    # Attempt 3: Build from pre-fetched data + raw output
    logger.info("Building response from pre-fetched data")
    response = _build_from_pre_fetched(raw_output, request, pre_fetched)
    response.trip_summary = _clean_text(response.trip_summary)
    return response


def _has_required_fields(data: dict) -> bool:
    """Check if JSON has the minimum required fields."""
    return any(k in data for k in ["recommended_hotels", "hotels", "attractions", "daily_plans", "budget"])


def _calculate_trip_score(request, weather_info, hotels, attractions, restaurants, transport, budget_info, daily_plans, ai_insights, packing, tips):
    """Dynamically calculate trip score out of 100 based on data quality and completeness."""
    score = 0
    reasons = []

    # ── Hotel Quality (20 pts) ──
    hotel_score = 0
    n_hotels = len(hotels)
    avg_rating = sum(h.rating for h in hotels if h.rating) / max(n_hotels, 1)
    if n_hotels >= 3 and avg_rating >= 4.0:
        hotel_score = 20
        reasons.append(("Excellent hotels with high ratings", "good"))
    elif n_hotels >= 3:
        hotel_score = 16
        reasons.append(("Good hotel variety", "good"))
    elif n_hotels >= 2:
        hotel_score = 12
        reasons.append(("Some hotel options found", "ok"))
    elif n_hotels >= 1:
        hotel_score = 8
        reasons.append(("Limited hotel options", "ok"))
    else:
        reasons.append(("No hotels found", "warn"))

    tier = request.hotel_preference.value if hasattr(request.hotel_preference, "value") else request.hotel_preference
    tier_match = any(
        (tier == "budget" and h.price_per_night < 150) or
        (tier == "standard" and 80 <= h.price_per_night <= 350) or
        (tier == "luxury" and h.price_per_night > 250)
        for h in hotels if h.price_per_night > 0
    )
    if tier_match:
        hotel_score = min(hotel_score + 2, 20)
        reasons.append(("Matches your hotel preference", "good"))
    score += hotel_score

    # ── Attractions (20 pts) ──
    attr_score = 0
    n_attr = len(attractions)
    avg_attr_rating = sum(a.rating for a in attractions if a.rating) / max(n_attr, 1)
    if n_attr >= 7:
        attr_score = 14
        reasons.append(("Great attraction coverage", "good"))
    elif n_attr >= 4:
        attr_score = 10
        reasons.append(("Good selection of attractions", "ok"))
    elif n_attr >= 2:
        attr_score = 6
        reasons.append(("Some attractions found", "ok"))
    elif n_attr >= 1:
        attr_score = 3
        reasons.append(("Limited attractions", "warn"))
    else:
        reasons.append(("No attractions found", "warn"))

    if avg_attr_rating >= 4.3:
        attr_score = min(attr_score + 3, 17)
        reasons.append(("High-rated attractions", "good"))
    elif avg_attr_rating >= 3.8:
        attr_score = min(attr_score + 2, 17)

    interests = request.interests if hasattr(request, "interests") else []
    interest_cats = set(str(i).lower() for i in interests)
    matched = sum(1 for a in attractions if a.category and a.category.lower() in interest_cats)
    if matched >= 3:
        attr_score = min(attr_score + 3, 20)
        reasons.append(("Matches your interests", "good"))
    elif matched >= 1:
        attr_score = min(attr_score + 1, 20)
    score += attr_score

    # ── Budget Fit (20 pts) ──
    budget_score = 0
    if budget_info and budget_info.total > 0:
        budget_ratio = budget_info.total / max(request.budget, 1)
        if budget_ratio <= 0.85:
            budget_score = 20
            reasons.append(("Great value under budget", "good"))
        elif budget_ratio <= 1.0:
            budget_score = 18
            reasons.append(("Within budget", "good"))
        elif budget_ratio <= 1.10:
            budget_score = 13
            reasons.append(("Slightly over budget", "ok"))
        elif budget_ratio <= 1.25:
            budget_score = 8
            reasons.append(("Over budget", "warn"))
        else:
            budget_score = 3
            reasons.append(("Significantly over budget", "warn"))
    else:
        reasons.append(("No budget data available", "warn"))
    score += budget_score

    # ── Weather (15 pts) ──
    weather_score = 0
    temp = weather_info.temperature if hasattr(weather_info, "temperature") else 0
    rain = weather_info.rain_chance if hasattr(weather_info, "rain_chance") else None
    wind = weather_info.wind_speed if hasattr(weather_info, "wind_speed") else 0
    cond = (weather_info.condition if hasattr(weather_info, "condition") else "").lower()

    has_real = temp != 0 and weather_info and hasattr(weather_info, "condition") and weather_info.condition != "N/A"
    if has_real:
        if 18 <= temp <= 28:
            weather_score += 6
            reasons.append(("Comfortable temperature", "good"))
        elif 10 <= temp <= 35:
            weather_score += 4
            reasons.append(("Moderate temperature", "ok"))
        else:
            weather_score += 1
            reasons.append(("Extreme temperature", "warn"))

        if rain is not None:
            if rain <= 10:
                weather_score += 4
                reasons.append(("Low rain probability", "good"))
            elif rain <= 30:
                weather_score += 2
                reasons.append(("Some rain possible", "ok"))
            else:
                weather_score += 0
                reasons.append(("High rain probability", "warn"))
        else:
            weather_score += 2
            reasons.append(("Rain data unavailable", "ok"))

        if wind < 10:
            weather_score += 3
            reasons.append(("Calm winds", "good"))
        elif wind < 20:
            weather_score += 2
        else:
            weather_score += 0
            reasons.append(("Strong winds", "warn"))

        severe = any(s in cond for s in ["thunderstorm", "snow", "tornado", "hurricane"])
        if not severe:
            weather_score += 2
        else:
            reasons.append(("Severe weather warning", "warn"))

        weather_score = min(weather_score, 15)
        reasons.append((f"Real weather data for {weather_info.condition}", "good"))
    elif weather_info:
        weather_score = 5
        reasons.append(("Weather forecast available", "ok"))
    else:
        reasons.append(("No weather data", "warn"))
    score += weather_score

    # ── Itinerary Quality (15 pts) ──
    plan_score = 0
    n_days = len(daily_plans)
    target = request.num_days
    if n_days >= target:
        plan_score += 8
        reasons.append(("Full itinerary planned", "good"))
    elif n_days >= target * 0.7:
        plan_score += 5
        reasons.append(("Mostly complete itinerary", "ok"))
    else:
        plan_score += 2
        reasons.append(("Incomplete itinerary", "warn"))

    days_with_all = sum(1 for d in daily_plans if d.morning and d.afternoon and d.evening)
    if days_with_all >= target * 0.8:
        plan_score += 4
        reasons.append(("Well-structured daily plans", "good"))
    elif days_with_all >= target * 0.5:
        plan_score += 2
        reasons.append(("Some days well planned", "ok"))

    has_highlights = sum(1 for d in daily_plans if d.highlights)
    if has_highlights >= target * 0.6:
        plan_score += 3
        reasons.append(("Detailed highlights per day", "good"))
    elif has_highlights >= 1:
        plan_score += 1

    plan_score = min(plan_score, 15)
    score += plan_score

    # ── Food & Transport (10 pts) ──
    ft_score = 0
    n_rest = len(restaurants)
    n_trans = len(transport)
    if n_rest >= 4:
        ft_score += 5
        reasons.append(("Great restaurant variety", "good"))
    elif n_rest >= 2:
        ft_score += 3
        reasons.append(("Good food recommendations", "ok"))
    elif n_rest >= 1:
        ft_score += 1
    else:
        reasons.append(("No restaurant picks", "warn"))

    if n_trans >= 3:
        ft_score += 5
        reasons.append(("Comprehensive transport options", "good"))
    elif n_trans >= 2:
        ft_score += 3
        reasons.append(("Multiple transport modes", "ok"))
    elif n_trans >= 1:
        ft_score += 1
    else:
        reasons.append(("Limited transport info", "warn"))
    score += ft_score

    score = min(score, 98)
    score = max(score, 45)

    return score, reasons


def _build_response_from_dict(data: dict, raw_output: str, request: TripRequest, pre_fetched: dict = None) -> ItineraryResponse:
    """Build ItineraryResponse from a parsed JSON dict."""
    if pre_fetched is None:
        pre_fetched = {}

    # Weather: prefer pre-fetched real data
    real_weather = pre_fetched.get("weather", {}) or {}
    if not isinstance(real_weather, dict):
        real_weather = {}
    weather_data = data.get("weather_summary") or data.get("weather") or {}
    if isinstance(weather_data, dict) and weather_data.get("temperature", 0) != 0:
        w = weather_data
    elif real_weather:
        w = real_weather
    else:
        w = weather_data if isinstance(weather_data, dict) else {}

    weather_info = WeatherInfo(
        temperature=w.get("temperature", 0),
        feels_like=w.get("feels_like", 0),
        humidity=w.get("humidity", 0),
        condition=w.get("condition", "N/A"),
        description=w.get("description", ""),
        wind_speed=w.get("wind_speed", 0),
        rain_chance=w.get("rain_chance"),
        sunrise=w.get("sunrise", ""),
        sunset=w.get("sunset", ""),
        icon=_weather_icon(w.get("condition", "")),
        pressure=w.get("pressure"),
        visibility=w.get("visibility"),
        cloud_pct=w.get("clouds"),
        uv_index=w.get("uv_index"),
        suggestions=w.get("suggestions", ["Check weather forecast before departure", "Pack layers for changing conditions"]),
    )

    # Hotels: prefer JSON data, supplement with pre-fetched
    hotels = _parse_hotels(data, request, pre_fetched)
    attractions = _parse_attractions(data, request, pre_fetched)
    restaurants = _parse_restaurants(data, request, pre_fetched)

    transport = []
    for t in data.get("transport_options", []):
        if isinstance(t, dict):
            transport.append(TransportOption(
                mode=t.get("mode", ""),
                description=t.get("description", ""),
                estimated_time=t.get("estimated_time", ""),
                estimated_cost=t.get("estimated_cost", ""),
                tips=t.get("tips", ""),
            ))

    budget_data = data.get("budget") or {}
    budget_info = BudgetBreakdown(
        hotel=float(budget_data.get("hotel", 0)),
        food=float(budget_data.get("food", 0)),
        transport=float(budget_data.get("transport", 0)),
        activities=float(budget_data.get("activities", 0)),
        miscellaneous=float(budget_data.get("miscellaneous", 0)),
        total=float(budget_data.get("total", 0)),
        per_person=float(budget_data.get("per_person", 0)),
        within_budget=budget_data.get("within_budget", True),
        remaining=float(budget_data.get("remaining", 0)),
        suggestions=budget_data.get("suggestions", []),
    )
    if budget_info.total == 0:
        budget_info = _calculate_budget(request)

    daily_plans = []
    for d in data.get("daily_plans", []):
        if isinstance(d, dict):
            daily_plans.append(DayPlan(
                day_number=d.get("day_number", len(daily_plans) + 1),
                title=d.get("title", ""),
                morning=d.get("morning", ""),
                afternoon=d.get("afternoon", ""),
                evening=d.get("evening", ""),
                night=d.get("night", ""),
                lunch=d.get("lunch", ""),
                dinner=d.get("dinner", ""),
                estimated_daily_cost=float(d.get("estimated_daily_cost", 0)),
                highlights=d.get("highlights", []),
            ))

    # Validate daily_plans count matches request.num_days; pad if needed
    target_days = request.num_days
    if len(daily_plans) < target_days:
        logger.info("Padding daily_plans from %d to %d days", len(daily_plans), target_days)
        avg_cost = round(request.budget / target_days, 2) if target_days else 0
        existing_days = {d.day_number for d in daily_plans}
        for day_num in range(1, target_days + 1):
            if day_num not in existing_days:
                daily_plans.append(DayPlan(
                    day_number=day_num,
                    title=f"Day {day_num} in {request.destination}",
                    morning=f"Explore {request.destination} city center and local neighborhoods",
                    afternoon=f"Visit top attractions and museums",
                    evening=f"Enjoy dinner at a local restaurant and evening stroll",
                    night=f"Relax and prepare for the next day",
                    estimated_daily_cost=avg_cost,
                    highlights=["Explore local area", "Try local cuisine"],
                ))
        daily_plans.sort(key=lambda d: d.day_number)
    elif len(daily_plans) > target_days:
        logger.info("Trimming daily_plans from %d to %d days", len(daily_plans), target_days)
        daily_plans = daily_plans[:target_days]

    ai_insights_data = data.get("ai_insights") or {}
    ai_insights = AIInsights(
        hidden_gems=ai_insights_data.get("hidden_gems", []),
        tourist_traps=ai_insights_data.get("tourist_traps", []),
        local_food=ai_insights_data.get("local_food", []),
        safety_tips=ai_insights_data.get("safety_tips", []),
        money_tips=ai_insights_data.get("money_tips", []),
        scam_alerts=ai_insights_data.get("scam_alerts", []),
        photography_spots=ai_insights_data.get("photography_spots", []),
        sunrise_spots=ai_insights_data.get("sunrise_spots", []),
    )

    packing = data.get("packing_checklist") or {}
    if not packing:
        packing = {
            "documents": ["Passport", "Travel insurance", "Boarding passes", "Hotel confirmations"],
            "electronics": ["Phone charger", "Power bank", "Travel adapter", "Camera"],
            "medicines": ["Pain relievers", "Band-aids", "Personal medications"],
            "clothes": ["Comfortable shoes", "Weather-appropriate clothing", "Swimwear"],
            "essentials": ["Sunscreen", "Water bottle", "Day bag", "Umbrella"],
        }

    score_val, score_reasons = _calculate_trip_score(request, weather_info, hotels, attractions, restaurants, transport, budget_info, daily_plans, ai_insights, packing, data.get("travel_tips", []))

    return ItineraryResponse(
        trip_summary=data.get("trip_summary", "")[:3000],
        destination_overview=data.get("destination_overview", f"Trip from {request.source_city} to {request.destination} for {request.num_days} days."),
        weather_summary=weather_info,
        recommended_hotels=hotels,
        attractions=attractions,
        restaurants=restaurants,
        transport_options=transport,
        budget=budget_info,
        daily_plans=daily_plans,
        ai_insights=ai_insights,
        travel_tips=data.get("travel_tips", []),
        things_to_carry=data.get("things_to_carry", []),
        packing_checklist=packing,
        best_times=data.get("best_times", []),
        trip_score=score_val,
        score_reasons=[{"text": r[0], "type": r[1]} for r in score_reasons],
    )


def _parse_hotels(data: dict, request: TripRequest, pre_fetched: dict) -> list[HotelRecommendation]:
    """Parse hotels from JSON data, supplement with pre-fetched if needed."""
    hotels = []
    for h in data.get("recommended_hotels") or data.get("hotels") or []:
        if isinstance(h, dict) and h.get("name"):
            hotels.append(HotelRecommendation(
                name=h.get("name", "Hotel"),
                rating=float(h.get("rating", 0)),
                price_per_night=float(h.get("price_per_night", 0)),
                location=h.get("location", ""),
                reason=h.get("reason", ""),
                amenities=h.get("amenities", []),
                description=h.get("description", ""),
                pros=h.get("pros", []),
                cons=h.get("cons", []),
                maps_url=validate_url(h.get("maps_url")) or _maps_url(h.get("name", "hotel"), request.destination),
                website_url=validate_url(h.get("website_url")),
                distance_from_center=h.get("distance_from_center", ""),
            ))

    # Supplement with pre-fetched SerpAPI data if we have fewer than 3
    if len(hotels) < 3 and pre_fetched.get("hotels"):
        for item in pre_fetched["hotels"]:
            if len(hotels) >= 3:
                break
            name = item.get("title") or ""
            if not name or any(name.lower() in h.name.lower() for h in hotels):
                continue
            hotels.append(HotelRecommendation(
                name=name[:80],
                rating=float(item.get("rating") or 4.0),
                price_per_night=0,
                location=item.get("address") or request.destination,
                reason=item.get("snippet") or "Recommended based on search results.",
                description=item.get("snippet") or "",
                maps_url=validate_url(item.get("link")) or _maps_url(name, request.destination),
                website_url=validate_url(item.get("link")) or "",
            ))

    return hotels[:5]


def _parse_attractions(data: dict, request: TripRequest, pre_fetched: dict) -> list[AttractionRecommendation]:
    """Parse attractions from JSON data, supplement with pre-fetched if needed."""
    attractions = []
    for a in data.get("attractions") or []:
        if isinstance(a, dict) and a.get("name"):
            attractions.append(AttractionRecommendation(
                name=a.get("name", ""),
                description=a.get("description", ""),
                category=a.get("category", ""),
                rating=float(a.get("rating", 0)),
                entry_fee=a.get("entry_fee", ""),
                opening_hours=a.get("opening_hours", ""),
                time_required=a.get("time_required", ""),
                best_time=a.get("best_time", ""),
                maps_url=validate_url(a.get("maps_url")) or _maps_url(a.get("name", ""), request.destination),
                website_url=validate_url(a.get("website_url")),
            ))

    if len(attractions) < 5 and pre_fetched.get("attractions"):
        for item in pre_fetched["attractions"]:
            if len(attractions) >= 8:
                break
            name = item.get("title") or ""
            if not name or any(name.lower() in a.name.lower() for a in attractions):
                continue
            attractions.append(AttractionRecommendation(
                name=name[:80],
                description=item.get("snippet") or "",
                category="attraction",
                rating=float(item.get("rating") or 4.0),
                maps_url=validate_url(item.get("link")) or _maps_url(name, request.destination),
                website_url=validate_url(item.get("link")) or "",
            ))

    return attractions[:10]


def _parse_restaurants(data: dict, request: TripRequest, pre_fetched: dict) -> list[RestaurantRecommendation]:
    """Parse restaurants from JSON data, supplement with pre-fetched if needed."""
    restaurants = []
    for r in data.get("restaurants") or []:
        if isinstance(r, dict) and r.get("name"):
            restaurants.append(RestaurantRecommendation(
                name=r.get("name", ""),
                cuisine=r.get("cuisine", ""),
                rating=float(r.get("rating", 0)),
                price_range=r.get("price_range", ""),
                description=r.get("description", ""),
                opening_hours=r.get("opening_hours", ""),
                maps_url=validate_url(r.get("maps_url")) or _maps_url(r.get("name", ""), request.destination),
                website_url=validate_url(r.get("website_url")),
            ))

    if len(restaurants) < 3 and pre_fetched.get("restaurants"):
        for item in pre_fetched["restaurants"]:
            if len(restaurants) >= 5:
                break
            name = item.get("title") or ""
            if not name or any(name.lower() in r.name.lower() for r in restaurants):
                continue
            restaurants.append(RestaurantRecommendation(
                name=name[:80],
                cuisine="Local cuisine",
                rating=float(item.get("rating") or 4.0),
                description=item.get("snippet") or "",
                maps_url=validate_url(item.get("link")) or _maps_url(name, request.destination),
                website_url=validate_url(item.get("link")) or "",
            ))

    return restaurants[:6]


def _calculate_budget(request: TripRequest) -> BudgetBreakdown:
    """Calculate budget breakdown based on trip parameters."""
    budget = request.budget
    hotel = round(budget * 0.40, 2)
    food = round(budget * 0.25, 2)
    transport = round(budget * 0.15, 2)
    activities = round(budget * 0.15, 2)
    misc = round(budget * 0.05, 2)
    total = hotel + food + transport + activities + misc
    per_person = round(total / max(request.num_travellers, 1), 2)
    return BudgetBreakdown(
        hotel=hotel, food=food, transport=transport,
        activities=activities, miscellaneous=misc,
        total=total, per_person=per_person,
        within_budget=total <= budget,
        remaining=round(budget - total, 2),
        suggestions=["Book hotels in advance", "Use public transport", "Eat at local restaurants"],
    )


def _build_from_pre_fetched(raw_output: str, request: TripRequest, pre_fetched: dict) -> ItineraryResponse:
    """Build response from pre-fetched data when JSON parsing fails."""
    real_weather = pre_fetched.get("weather", {}) or {}
    if not isinstance(real_weather, dict):
        real_weather = {}

    weather_info = WeatherInfo(
        temperature=real_weather.get("temperature", 0),
        feels_like=real_weather.get("feels_like", 0),
        humidity=real_weather.get("humidity", 0),
        condition=real_weather.get("condition", "N/A"),
        description=real_weather.get("description", ""),
        wind_speed=real_weather.get("wind_speed", 0),
        rain_chance=real_weather.get("rain_chance"),
        sunrise=real_weather.get("sunrise", ""),
        sunset=real_weather.get("sunset", ""),
        icon=_weather_icon(real_weather.get("condition", "")),
        pressure=real_weather.get("pressure"),
        visibility=real_weather.get("visibility"),
        cloud_pct=real_weather.get("clouds"),
        suggestions=["Check weather forecast before departure", "Pack layers for changing conditions"],
    )

    hotels = []
    for item in pre_fetched.get("hotels", [])[:3]:
        name = item.get("title") or "Hotel"
        hotels.append(HotelRecommendation(
            name=name[:80],
            rating=float(item.get("rating") or 4.0),
            price_per_night=0,
            location=item.get("address") or request.destination,
            reason=item.get("snippet") or "Highly rated hotel based on search results.",
            description=item.get("snippet") or "",
            maps_url=validate_url(item.get("link")) or _maps_url(name, request.destination),
            website_url=validate_url(item.get("link")) or "",
        ))

    attractions = []
    for item in pre_fetched.get("attractions", [])[:6]:
        name = item.get("title") or "Attraction"
        attractions.append(AttractionRecommendation(
            name=name[:80],
            description=item.get("snippet") or "",
            category="attraction",
            rating=float(item.get("rating") or 4.0),
            maps_url=validate_url(item.get("link")) or _maps_url(name, request.destination),
            website_url=validate_url(item.get("link")) or "",
        ))

    restaurants = []
    for item in pre_fetched.get("restaurants", [])[:4]:
        name = item.get("title") or "Restaurant"
        restaurants.append(RestaurantRecommendation(
            name=name[:80],
            cuisine="Local cuisine",
            rating=float(item.get("rating") or 4.0),
            description=item.get("snippet") or "",
            maps_url=validate_url(item.get("link")) or _maps_url(name, request.destination),
            website_url=validate_url(item.get("link")) or "",
        ))

    budget_info = _calculate_budget(request)

    daily_plans = []
    for day in range(1, request.num_days + 1):
        daily_plans.append(DayPlan(
            day_number=day,
            title=f"Day {day} in {request.destination}",
            morning=f"Explore {request.destination} city center",
            afternoon="Visit top-rated attractions",
            evening="Enjoy local dining experience",
            estimated_daily_cost=round(request.budget / request.num_days, 2),
        ))

    # Try to extract some useful text from raw output
    summary = raw_output[:2000] if len(raw_output) > 2000 else raw_output
    summary = _clean_text(summary)

    transport = ["Public metro/bus", "Airport transfer", "Walking tours"]

    packing = {"documents": ["Passport"], "clothing": ["Comfortable shoes"], "essentials": ["Sunscreen"]}

    ai_insights = AIInsights(
        hidden_gems=["Ask locals for their favorite spots", "Explore neighborhoods off the beaten path"],
        local_food=["Try the local street food", "Visit the nearest food market"],
        safety_tips=["Keep valuables secure", "Stay aware of your surroundings"],
        money_tips=["Use public transport", "Eat where locals eat"],
    )

    result = ItineraryResponse(
        trip_summary=summary,
        destination_overview=f"Trip from {request.source_city} to {request.destination} for {request.num_days} days. Explore the best attractions, restaurants, and experiences this destination has to offer.",
        weather_summary=weather_info,
        recommended_hotels=hotels,
        attractions=attractions,
        restaurants=restaurants,
        budget=budget_info,
        daily_plans=daily_plans,
        ai_insights=ai_insights,
        travel_tips=["Carry a universal power adapter", "Keep digital copies of documents", "Learn basic local phrases"],
        things_to_carry=["Passport", "Medications", "Comfortable shoes", "Weather-appropriate clothing"],
        packing_checklist={
            "documents": ["Passport", "Travel insurance", "Boarding passes"],
            "electronics": ["Phone charger", "Power bank", "Camera"],
            "medicines": ["Pain relievers", "Personal medications"],
            "clothes": ["Comfortable shoes", "Weather-appropriate clothing"],
            "essentials": ["Sunscreen", "Water bottle", "Day bag"],
        },
        best_times=["Visit popular attractions early morning to avoid crowds"],
    )

    score_val, score_reasons = _calculate_trip_score(
        request, weather_info, hotels, attractions, restaurants, transport, budget_info, daily_plans, ai_insights, packing, []
    )
    result.trip_score = score_val
    result.score_reasons = [{"text": r[0], "type": r[1]} for r in score_reasons]
    return result


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
