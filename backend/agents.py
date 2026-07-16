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
    RestaurantSearchTool,
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
            "Compile research from all specialized agents into a SINGLE, COMPLETE JSON object "
            "with ALL required fields. You MUST output ONLY valid JSON - no markdown, no code fences, "
            "no text before or after the JSON object."
        ),
        backstory=(
            "You are a world-class travel consultant with 15 years of experience creating "
            "unforgettable trip itineraries. You are ALSO a JSON formatting expert - you NEVER "
            "include any text outside the JSON object. Your output is always parseable by json.loads(). "
            "You always include ALL required fields: trip_summary, destination_overview, recommended_hotels, "
            "attractions, daily_plans, budget, ai_insights, transport_options, restaurants, "
            "packing_checklist, travel_tips, best_times, trip_score. "
            "CRITICAL RULE: ALL text fields must be PLAIN TEXT ONLY. NEVER include HTML tags like "
            "<div>, </div>, <span>, <p>, <br>, <a>, <b>, <i>, or ANY other HTML/XML markup in ANY field. "
            "URL fields (maps_url, website_url) must contain ONLY valid http:// or https:// URLs, "
            "or be an empty string. NEVER put HTML fragments in URL fields."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        max_iter=15,
    )


def create_hotel_agent() -> Agent:
    return Agent(
        role="Hotel Recommendation Specialist",
        goal=(
            "Find the best hotels matching the traveler's budget, comfort, and location needs. "
            "Output ONLY a JSON array of 3 hotel objects - no markdown, no extra text."
        ),
        backstory=(
            "You are a luxury hotel consultant who personally vetted thousands of hotels worldwide. "
            "You know which hotels offer the best value, which have hidden fees, and which provide "
            "authentic local experiences. You always explain WHY a hotel is perfect for each traveler. "
            "Your output is ALWAYS a valid JSON array - never markdown, never explanations outside JSON. "
            "CRITICAL RULE: ALL text fields must be PLAIN TEXT ONLY. NEVER include HTML tags like "
            "<div>, </div>, <span>, <p>, <br>, <a>, or ANY HTML/XML markup in ANY field. "
            "If you don't know a URL, use an empty string. NEVER put HTML fragments in URL fields."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[HotelSearchTool(), SerpSearchTool()],
        max_iter=10,
    )


def create_attraction_agent() -> Agent:
    return Agent(
        role="Tourist Attraction Guide",
        goal=(
            "Find the best attractions and create an efficient sightseeing plan. "
            "Output ONLY a JSON array of 6-10 attraction objects - no markdown, no extra text."
        ),
        backstory=(
            "You are a passionate local travel expert who has visited every major attraction "
            "and discovered countless hidden gems. You know the best times to visit, "
            "how to skip crowds, and which experiences are truly worth the time and money. "
            "Your output is ALWAYS a valid JSON array - never markdown, never explanations outside JSON. "
            "CRITICAL RULE: ALL text fields must be PLAIN TEXT ONLY. NEVER include HTML tags like "
            "<div>, </div>, <span>, <p>, <br>, <a>, or ANY HTML/XML markup in ANY field. "
            "URL fields must contain ONLY valid http:// or https:// URLs, or be empty."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[AttractionSearchTool(), SerpSearchTool()],
        max_iter=10,
    )


def create_weather_agent() -> Agent:
    return Agent(
        role="Weather Advisor",
        goal=(
            "Provide detailed weather forecasts and weather-smart travel advice. "
            "Output ONLY a JSON object with weather data - no markdown, no extra text."
        ),
        backstory=(
            "You are a meteorologist specializing in travel weather. You help travelers "
            "plan around weather conditions, choose the right clothing, and make the most "
            "of good weather windows while having backup plans for rain. "
            "Your output is ALWAYS a valid JSON object - never markdown, never explanations outside JSON. "
            "CRITICAL RULE: ALL text fields must be PLAIN TEXT ONLY. NEVER include HTML tags in ANY field."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[WeatherSearchTool()],
        max_iter=8,
    )


def create_budget_agent() -> Agent:
    return Agent(
        role="Budget Advisor",
        goal=(
            "Estimate total trip expenses and provide smart money-saving strategies. "
            "Output ONLY a JSON object with budget data - no markdown, no extra text."
        ),
        backstory=(
            "You are a travel finance expert who knows real prices in every major destination. "
            "You provide accurate cost breakdowns and always include specific money-saving "
            "alternatives. You help travelers get the most value from their budget. "
            "Your output is ALWAYS a valid JSON object - never markdown, never explanations outside JSON. "
            "CRITICAL RULE: ALL text fields must be PLAIN TEXT ONLY. NEVER include HTML tags in ANY field."
        ),
        verbose=True,
        allow_delegation=False,
        llm=_build_llm(),
        tools=[SerpSearchTool(), RestaurantSearchTool()],
        max_iter=8,
    )
