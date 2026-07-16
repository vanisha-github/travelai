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
    temperature: float = Field(description="Temperature in Celsius")
    humidity: int = Field(description="Humidity percentage")
    condition: str = Field(description="Weather condition description")
    suggestions: list[str] = Field(default_factory=list, description="AI weather suggestions")


class HotelRecommendation(BaseModel):
    name: str = Field(description="Hotel name")
    rating: float = Field(description="Hotel rating out of 5")
    price_per_night: float = Field(description="Approximate price per night in USD")
    location: str = Field(description="Hotel location")
    reason: str = Field(description="Why this hotel is recommended")


class BudgetBreakdown(BaseModel):
    hotel: float = Field(description="Hotel cost")
    food: float = Field(description="Food cost")
    transport: float = Field(description="Transport cost")
    activities: float = Field(description="Activities cost")
    miscellaneous: float = Field(description="Miscellaneous cost")
    total: float = Field(description="Total estimated cost")
    within_budget: bool = Field(description="Whether estimate is within budget")
    suggestions: list[str] = Field(default_factory=list, description="Cost-saving suggestions")


class DayPlan(BaseModel):
    day_number: int = Field(description="Day number")
    morning: str = Field(description="Morning activities")
    afternoon: str = Field(description="Afternoon activities")
    evening: str = Field(description="Evening activities")
    estimated_daily_cost: float = Field(description="Estimated cost for this day")


class ItineraryResponse(BaseModel):
    trip_summary: str = Field(description="Overall trip summary")
    destination_overview: str = Field(description="Destination overview")
    weather_summary: WeatherInfo = Field(description="Weather information")
    recommended_hotels: list[HotelRecommendation] = Field(description="Hotel recommendations")
    budget: BudgetBreakdown = Field(description="Budget breakdown")
    daily_plans: list[DayPlan] = Field(description="Day-by-day itinerary")
    travel_tips: list[str] = Field(default_factory=list, description="Travel tips")
    things_to_carry: list[str] = Field(default_factory=list, description="Packing suggestions")
    best_times: list[str] = Field(default_factory=list, description="Best times to visit attractions")


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
