from pydantic import BaseModel, Field


class HotelSearchResult(BaseModel):
    name: str = Field(description="Hotel name")
    rating: float = Field(default=0.0, description="Rating out of 5")
    price: str = Field(default="N/A", description="Price string")
    location: str = Field(default="", description="Location/address")
    description: str = Field(default="", description="Brief description")


class AttractionResult(BaseModel):
    name: str = Field(description="Attraction name")
    category: str = Field(default="", description="Category like museum, park, etc.")
    rating: float = Field(default=0.0, description="Rating out of 5")
    description: str = Field(default="", description="Why worth visiting")
    suggested_duration: str = Field(default="", description="Suggested visit duration")


class AgentResearchOutput(BaseModel):
    """Schema for intermediate agent outputs shared across the crew."""
    raw_data: str = Field(default="", description="Raw research data from agent")
    source_agent: str = Field(default="", description="Name of the producing agent")
