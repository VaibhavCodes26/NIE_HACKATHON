from datetime import date 
from enum import Enum
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator

class TravelStyle(str,Enum):
    BUDGET ="budget"
    COMFORTABLE="comfortable"
    PREMIUM="premium"
    ULTRA_PREMIUM="ultra-premium"
    

class Interest(str, Enum):
    HERITAGE_CULTURE = "Heritage & culture"
    TOURIST_ATTRACTIONS = "Tourist attractions"
    LOCAL_FOOD = "Local food"
    NATURE = "Nature & hills"
    BEACHES = "Beaches"
    ADVENTURE = "Adventure"
    HIDDEN_GEMS = "Hidden gems"
    FESTIVALS = "Festivals & traditions"



class ItineraryRequest(BaseModel):
    """Data received from the PlanJourney.jsx form."""

    destinations: list[str] = Field(min_length=1, max_length=8)

    selected_attraction_ids: list[int] = Field(default_factory=list, max_length=100)

    start_date: date
    end_date: date

    traveller_count: int = Field(ge=1, le=30)
    travel_style: TravelStyle
    total_budget: int = Field(ge=1000, le=100000)
    interests: list[Interest] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def validate_trip(self):
        if self.end_date < self.start_date:
            raise ValueError("End date must be on or after start date.")

        if len(set(self.destinations)) != len(self.destinations):
            raise ValueError("Duplicate destinations are not allowed.")

        if any(not destination.strip() for destination in self.destinations):
            raise ValueError("Destination IDs cannot be empty.")

        if len(set(self.interests)) != len(self.interests):
            raise ValueError("Duplicate interests are not allowed.")

        if len(set(self.selected_attraction_ids)) != len(
            self.selected_attraction_ids
        ):
            raise ValueError("Duplicate attraction IDs are not allowed.")

        return self


class DestinationResponse(BaseModel):
    """A destination returned to the frontend."""

    id: str
    name: str
    region: str

    model_config = ConfigDict(from_attributes=True)


class ItineraryWarning(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning"] = "info"


class ItineraryStop(BaseModel):
    """One attraction or activity in a day's itinerary."""

    name: str
    category: str
    description: str
    suggested_time: str
    source_status: Literal[
        "curated_reference", "needs_verification"
    ] = "needs_verification"
    attraction_id: int | None = None


class ItineraryDay(BaseModel):
    day_number: int
    date: date
    destination_id: str
    destination_name: str
    stops: list[ItineraryStop]
    attraction_id: int | None = None
    intercity_transfer_from_previous: dict | None = None
    weather_status: str = "not_requested"


class ItineraryPreviewResponse(BaseModel):
    """Response shape consumed by PlanJourney.jsx."""

    status: Literal["preview"] = "preview"
    title: str
    start_date: date
    end_date: date
    duration_days: int
    destinations: list[DestinationResponse]
    traveller_count: int
    travel_style: TravelStyle
    total_budget: int
    budget_per_traveller: float
    interests: list[str]
    days: list[ItineraryDay]
    warnings: list[ItineraryWarning]
    data_policy: str

    
    