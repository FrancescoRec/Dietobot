"""Extract profile information from a single user message."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from pydantic import BaseModel, Field


MODEL_NAME = "gemini-2.5-flash"

BASE_SYSTEM_PROMPT = """
Extract the user's nutrition profile from their message.

If the user says they want to become skinnier, lose fat, cut, slim down, or
similar, set goal to "lose". If they want to bulk or gain muscle/weight, set
goal to "gain". If they want to stay the same, set goal to "maintain".

Only extract values the user explicitly states. Leave all other fields as null.
""".strip()

# Plain-language hints per field, appended to the prompt when we know
# which field was just asked for. This lets Gemini interpret bare replies
# like "180" or "80kg" correctly when the user is answering a specific question.
CONTEXT_HINTS: dict[str, str] = {
    "age":            "The user was just asked their age. A bare number is their age in years.",
    "sex":            "The user was just asked their biological sex. A word like 'male', 'female', 'man', or 'woman' is their sex.",
    "height_cm":      "The user was just asked their height. A bare number (e.g. 180) is their height in centimetres.",
    "weight_kg":      "The user was just asked their weight. A bare number (e.g. 80) is their weight in kilograms.",
    "activity_level": "The user was just asked their activity level. Map their description to: sedentary, light, moderate, or high.",
    "goal":           "The user was just asked their weight goal. Map their answer to: lose, maintain, or gain.",
}


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


def extract_profile(
    message: str,
    context_field: str | None = None,
) -> ProfileExtraction:
    """Ask Gemini to turn a single message into structured profile data.

    Args:
        message:       The raw user message.
        context_field: The field name we last asked for (e.g. "height_cm").
                       When provided, appended to the prompt so Gemini can
                       correctly interpret bare replies like "180".
    """
    prompt = BASE_SYSTEM_PROMPT
    if context_field and context_field in CONTEXT_HINTS:
        prompt += "\n\n" + CONTEXT_HINTS[context_field]

    model = ChatVertexAI(model=MODEL_NAME, temperature=0)
    structured_model = model.with_structured_output(ProfileExtraction)

    return structured_model.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=message),
        ]
    )
