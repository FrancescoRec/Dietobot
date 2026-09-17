"""Extract profile information from one user message."""

from typing import Literal

from langchain_google_vertexai import ChatVertexAI
from pydantic import BaseModel, Field


# model name
MODEL_NAME = "gemini-2.5-flash"

# Profile extraction model
class ProfileExtraction(BaseModel):
    """The profile fields that Vertex should find in the message."""

    age: int | None = None
    sex: Literal["male", "female"] | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    activity_level: Literal["sedentary", "light", "moderate", "high"] | None = None
    goal: Literal["lose", "maintain", "gain"] | None = None
    meals_per_day: int | None = None
    max_cooking_minutes: int | None = None
    foods_disliked: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    weekly_budget: float | None = None


def extract_profile(message: str) -> ProfileExtraction:
    """Ask Vertex to turn a message into structured profile data."""

    # Create the model used only by this extraction step.
    model = ChatVertexAI(model=MODEL_NAME, temperature=0)

    # Make Vertex return a ProfileExtraction object instead of free text.
    structured_model = model.with_structured_output(ProfileExtraction)

    return structured_model.invoke(message)
