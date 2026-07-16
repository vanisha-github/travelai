from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class HotelPreference(str, Enum):
    BUDGET = "budget"
    STANDARD = "standard"
    LUXURY = "luxury"


class InterestType(str, Enum):
    NATURE = "nature"
    ADVENTURE = "adventure"
    FOOD = "food"
    HISTORY = "history"
    SHOPPING = "shopping"
    BEACH = "beach"
    NIGHTLIFE = "nightlife"


class TripRequest(BaseModel):
    source_city: str = Field(..., min_length=2, max_length=100, description="Departure city")
    destination: str = Field(..., min_length=2, max_length=100, description="Destination city")
    num_days: int = Field(..., ge=1, le=30, description="Number of travel days")
    budget: float = Field(..., gt=0, description="Total budget in USD")
    num_travellers: int = Field(..., ge=1, le=20, description="Number of travellers")
    interests: list[InterestType] = Field(..., min_length=1, description="Travel interests")
    hotel_preference: HotelPreference = Field(
        default=HotelPreference.STANDARD, description="Hotel preference"
    )


class WeatherInfo(BaseModel):
    temperature: float = Field(default=0, description="Temperature in Celsius")
    feels_like: float = Field(default=0, description="Feels like temperature")
    humidity: int = Field(default=0, description="Humidity percentage")
    condition: str = Field(default="N/A", description="Weather condition")
    description: str = Field(default="", description="Weather description")
    wind_speed: float = Field(default=0, description="Wind speed in m/s")
    rain_chance: Optional[int] = Field(default=None, description="Rain chance percentage (None if unavailable)")
    sunrise: str = Field(default="", description="Sunrise time")
    sunset: str = Field(default="", description="Sunset time")
    icon: str = Field(default="☀️", description="Weather emoji icon")
    pressure: Optional[int] = Field(default=None, description="Atmospheric pressure in hPa")
    visibility: Optional[int] = Field(default=None, description="Visibility in meters")
    cloud_pct: Optional[int] = Field(default=None, description="Cloud cover percentage")
    uv_index: Optional[float] = Field(default=None, description="UV index")
    suggestions: list[str] = Field(default_factory=list, description="AI weather suggestions")


class HotelRecommendation(BaseModel):
    name: str = Field(description="Hotel name")
    rating: float = Field(default=0, description="Hotel rating out of 5")
    price_per_night: float = Field(default=0, description="Price per night in USD")
    location: str = Field(default="", description="Hotel location/address")
    reason: str = Field(default="", description="Why recommended")
    amenities: list[str] = Field(default_factory=list, description="Hotel amenities")
    description: str = Field(default="", description="Brief description")
    pros: list[str] = Field(default_factory=list, description="Pros of this hotel")
    cons: list[str] = Field(default_factory=list, description="Cons of this hotel")
    image_url: str = Field(default="", description="Hotel image URL")
    maps_url: str = Field(default="", description="Google Maps link")
    website_url: str = Field(default="", description="Official website")
    distance_from_center: str = Field(default="", description="Distance from city center")


class AttractionRecommendation(BaseModel):
    name: str = Field(description="Attraction name")
    description: str = Field(default="", description="What it is")
    category: str = Field(default="", description="Category (museum, park, etc)")
    rating: float = Field(default=0, description="Rating out of 5")
    entry_fee: str = Field(default="", description="Entry fee")
    opening_hours: str = Field(default="", description="Opening hours")
    time_required: str = Field(default="", description="Time needed to visit")
    best_time: str = Field(default="", description="Best time to visit")
    image_url: str = Field(default="", description="Attraction image URL")
    maps_url: str = Field(default="", description="Google Maps link")
    website_url: str = Field(default="", description="Official website")


class RestaurantRecommendation(BaseModel):
    name: str = Field(description="Restaurant name")
    cuisine: str = Field(default="", description="Type of cuisine")
    rating: float = Field(default=0, description="Rating out of 5")
    price_range: str = Field(default="", description="Price range ($, $$, $$$)")
    description: str = Field(default="", description="Why AI recommends it")
    opening_hours: str = Field(default="", description="Opening hours")
    image_url: str = Field(default="", description="Restaurant image URL")
    maps_url: str = Field(default="", description="Google Maps link")
    website_url: str = Field(default="", description="Official website")


class TransportOption(BaseModel):
    mode: str = Field(description="Transport mode (metro, bus, taxi, walking, etc)")
    description: str = Field(default="", description="Details and tips")
    estimated_time: str = Field(default="", description="Estimated travel time")
    estimated_cost: str = Field(default="", description="Estimated cost")
    tips: str = Field(default="", description="Local tips")


class AIInsights(BaseModel):
    hidden_gems: list[str] = Field(default_factory=list, description="Hidden gems")
    tourist_traps: list[str] = Field(default_factory=list, description="Tourist traps to avoid")
    local_food: list[str] = Field(default_factory=list, description="Must-try local food")
    safety_tips: list[str] = Field(default_factory=list, description="Safety advice")
    money_tips: list[str] = Field(default_factory=list, description="Money-saving tips")
    scam_alerts: list[str] = Field(default_factory=list, description="Common scams to avoid")
    photography_spots: list[str] = Field(default_factory=list, description="Best photography spots")
    sunrise_spots: list[str] = Field(default_factory=list, description="Best sunrise/sunset spots")


class BudgetBreakdown(BaseModel):
    hotel: float = Field(default=0, description="Hotel cost")
    food: float = Field(default=0, description="Food cost")
    transport: float = Field(default=0, description="Transport cost")
    activities: float = Field(default=0, description="Activities cost")
    miscellaneous: float = Field(default=0, description="Miscellaneous cost")
    total: float = Field(default=0, description="Total estimated cost")
    per_person: float = Field(default=0, description="Per person cost")
    within_budget: bool = Field(default=True, description="Within budget")
    remaining: float = Field(default=0, description="Remaining budget")
    suggestions: list[str] = Field(default_factory=list, description="Cost-saving suggestions")


class DayPlan(BaseModel):
    day_number: int = Field(description="Day number")
    title: str = Field(default="", description="Day theme/title")
    morning: str = Field(default="", description="Morning activities")
    afternoon: str = Field(default="", description="Afternoon activities")
    evening: str = Field(default="", description="Evening activities")
    night: str = Field(default="", description="Night activities")
    lunch: str = Field(default="", description="Lunch recommendation")
    dinner: str = Field(default="", description="Dinner recommendation")
    estimated_daily_cost: float = Field(default=0, description="Estimated cost")
    highlights: list[str] = Field(default_factory=list, description="Day highlights")


class ItineraryResponse(BaseModel):
    trip_summary: str = Field(default="", description="Overall trip summary")
    destination_overview: str = Field(default="", description="Destination overview")
    destination_image: str = Field(default="", description="Main destination image URL")
    destination_gallery: list[str] = Field(default_factory=list, description="Gallery image URLs")
    weather_summary: WeatherInfo = Field(default_factory=WeatherInfo)
    recommended_hotels: list[HotelRecommendation] = Field(default_factory=list)
    attractions: list[AttractionRecommendation] = Field(default_factory=list)
    restaurants: list[RestaurantRecommendation] = Field(default_factory=list)
    transport_options: list[TransportOption] = Field(default_factory=list)
    budget: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    daily_plans: list[DayPlan] = Field(default_factory=list)
    ai_insights: AIInsights = Field(default_factory=AIInsights)
    travel_tips: list[str] = Field(default_factory=list)
    things_to_carry: list[str] = Field(default_factory=list)
    packing_checklist: dict[str, list[str]] = Field(default_factory=dict, description="Grouped packing list")
    best_times: list[str] = Field(default_factory=list)
    trip_score: int = Field(default=85, description="AI trip score out of 100")
    score_reasons: list[dict[str, str]] = Field(default_factory=list, description="Score breakdown reasons")


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
