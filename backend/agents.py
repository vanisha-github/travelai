import os
import logging
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

from config import get_settings
settings = get_settings()
_api_key = settings.gemini_api_key or settings.google_api_key
os.environ["GEMINI_API_KEY"] = _api_key
os.environ["GOOGLE_API_KEY"] = _api_key

import litellm

_original_completion = litellm.completion

def _patched_completion(*args, **kwargs):
    kwargs["api_key"] = _api_key
    kwargs["model"] = _llm_model
    logger.info("LiteLLM patched call: model=%s key_present=%s", kwargs.get("model"), bool(kwargs.get("api_key")))
    return _original_completion(*args, **kwargs)

litellm.completion = _patched_completion

from crewai import Agent, LLM
from tools import (
    SerpSearchTool,
    HotelSearchTool,
    AttractionSearchTool,
    WeatherSearchTool,
    TravelInfoSearchTool,
)

logger = logging.getLogger(__name__)

_llm_model = f"gemini/{settings.gemini_model or 'gemini-3.1-flash-lite'}"
logger.info("LLM model: %s, key present: %s", _llm_model, bool(_api_key))


def _build_llm() -> LLM:
    return LLM(model=_llm_model, api_key=_api_key)


def create_travel_planner_agent() -> Agent:
    return Agent(
        role="Senior Travel Planner",
        goal=(
            "Coordinate all research from specialized agents and produce a comprehensive "
            "personalized travel itinerary."
        ),
        backstory=(
            "You are an expert travel consultant with years of experience creating "
            "personalized travel plans."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        max_iter=15,
    )


def create_hotel_agent() -> Agent:
    return Agent(
        role="Hotel Recommendation Specialist",
        goal="Find the best hotels according to budget, comfort and location.",
        backstory="You are a hotel expert who compares ratings, prices and amenities.",
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[HotelSearchTool(), SerpSearchTool()],
        max_iter=10,
    )


def create_attraction_agent() -> Agent:
    return Agent(
        role="Tourist Attraction Guide",
        goal="Find the best attractions and create an efficient sightseeing plan.",
        backstory="You are a local travel expert who knows famous attractions and hidden gems.",
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[AttractionSearchTool(), SerpSearchTool()],
        max_iter=10,
    )


def create_weather_agent() -> Agent:
    return Agent(
        role="Weather Advisor",
        goal="Provide weather forecast and travel advice based on current conditions.",
        backstory="You are an experienced weather analyst for travellers.",
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[WeatherSearchTool()],
        max_iter=8,
    )


def create_budget_agent() -> Agent:
    return Agent(
        role="Budget Advisor",
        goal="Estimate total trip expenses and suggest cheaper alternatives if required.",
        backstory="You specialize in travel budgeting and cost optimization.",
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[SerpSearchTool()],
        max_iter=8,
    )
