"""Extract profile information from a single user message."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from pydantic import BaseModel, Field


MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """
Extract the user's nutrition profile from their message.

If the user says they want to become skinnier, lose fat, cut, slim down, or
similar, set goal to "lose". If they want to bulk or gain muscle/weight, set
goal to "gain". If they want to stay the same, set goal to "maintain".

Only extract values the user explicitly states. Leave all other fields as null.
""".strip()


class ProfileExtraction(BaseModel):
    """Profile fields that Gemini should find in the message."""

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
    """Ask Gemini to turn a single message into structured profile data."""

    model = ChatVertexAI(model=MODEL_NAME, temperature=0)
    structured_model = model.with_structured_output(ProfileExtraction)

    return structured_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=message),
        ]
    )
