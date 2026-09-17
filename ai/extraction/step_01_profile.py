"""Extract profile information from the profile chat step."""

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from pydantic import BaseModel, Field


# model name
MODEL_NAME = "gemini-2.5-flash"

SYSTEM_PROMPT = """
Extract the user's nutrition profile from the conversation.

Use the whole conversation, not only the latest message. If the user says they
want to become skinnier, lose fat, cut, slim down, or similar, set goal to
"lose". If they want to bulk or gain muscle/weight, set goal to "gain". If they
want to stay the same, set goal to "maintain".
""".strip()

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


def extract_profile(
    message: str,
    conversation: list[dict[str, str]] | None = None,
) -> ProfileExtraction:
    """Ask Vertex to turn a message into structured profile data."""

    # Create the model used only by this extraction step.
    model = ChatVertexAI(model=MODEL_NAME, temperature=0)

    # Make Vertex return a ProfileExtraction object instead of free text.
    structured_model = model.with_structured_output(ProfileExtraction)

    turns = conversation or [{"role": "user", "content": message}]
    transcript = "\n".join(
        f"{turn['role']}: {turn['content']}"
        for turn in turns
        if turn.get("content")
    )

    return structured_model.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=transcript),
        ]
    )
