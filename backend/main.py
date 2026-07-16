import logging
import time
from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from models import TripRequest, ItineraryResponse, WeatherInfo, HotelRecommendation, BudgetBreakdown, DayPlan, HealthResponse
from crew import build_crew
from services import WeatherService, SerpService
from utils import setup_logging, extract_json_from_text, generate_trip_id

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
    version="1.0.0",
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
    return HealthResponse(status="ok", version="1.0.0")


@app.post("/plan-trip", response_model=ItineraryResponse)
async def plan_trip(request: TripRequest):
    start = time.time()
    logger.info(
        "Trip request: %s → %s (%d days, %d travellers, $%.0f)",
        request.source_city,
        request.destination,
        request.num_days,
        request.num_travellers,
        request.budget,
    )

    try:
        crew, context = build_crew(request)
        result = crew.kickoff()

        raw_output = str(result)
        logger.info("Crew execution completed in %.2fs", time.time() - start)

        itinerary = _parse_itinerary(raw_output, request)
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


def _parse_itinerary(raw_output: str, request: TripRequest) -> ItineraryResponse:
    """Parse the crew output into a structured ItineraryResponse.

    Attempts to extract structured JSON first, falls back to building
    a default response with the raw output as the trip summary.
    """
    extracted = extract_json_from_text(raw_output)

    if isinstance(extracted, dict):
        try:
            return ItineraryResponse(**extracted)
        except Exception:
            logger.warning("Failed to parse extracted JSON into ItineraryResponse")

    if isinstance(extracted, list) and len(extracted) > 0:
        try:
            return ItineraryResponse(**extracted[0])
        except Exception:
            pass

    daily_plans = []
    for day in range(1, request.num_days + 1):
        daily_plans.append(
            DayPlan(
                day_number=day,
                morning="To be planned based on agent recommendations",
                afternoon="To be planned based on agent recommendations",
                evening="To be planned based on agent recommendations",
                estimated_daily_cost=round(request.budget / request.num_days, 2),
            )
        )

    return ItineraryResponse(
        trip_summary=raw_output[:2000] if len(raw_output) > 2000 else raw_output,
        destination_overview=f"Trip from {request.source_city} to {request.destination} for {request.num_days} days.",
        weather_summary=WeatherInfo(
            temperature=25.0,
            humidity=60,
            condition="Pleasant",
            suggestions=["Carry a light jacket for evenings", "Stay hydrated during daytime"],
        ),
        recommended_hotels=[
            HotelRecommendation(
                name="Recommended Hotel",
                rating=4.0,
                price_per_night=round(request.budget / request.num_days / request.num_travellers * 0.4, 2),
                location=request.destination,
                reason="Good value option matching your budget",
            )
        ],
        budget=BudgetBreakdown(
            hotel=round(request.budget * 0.40, 2),
            food=round(request.budget * 0.25, 2),
            transport=round(request.budget * 0.15, 2),
            activities=round(request.budget * 0.15, 2),
            miscellaneous=round(request.budget * 0.05, 2),
            total=request.budget,
            within_budget=True,
            suggestions=["Book hotels in advance for better rates"],
        ),
        daily_plans=daily_plans,
        travel_tips=[
            "Carry a universal power adapter",
            "Keep digital copies of important documents",
            "Learn basic local phrases",
            "Check visa requirements before travel",
        ],
        things_to_carry=[
            "Passport and travel documents",
            "Medications and first-aid kit",
            "Comfortable walking shoes",
            "Weather-appropriate clothing",
            "Phone charger and power bank",
            "Local currency and cards",
        ],
        best_times=["Visit popular attractions early morning to avoid crowds"],
    )

from config import get_settings

#settings = get_settings()

#print("=" * 50)
#print("GOOGLE_API_KEY exists:", bool(settings.google_api_key))
#print("Key starts with:", settings.google_api_key[:6] if settings.google_api_key else "EMPTY")
#print("Model:", settings.gemini_model)
#print("=" * 50)


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
