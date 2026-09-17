"""Step 01: extract profile fields from raw user or AI input."""

from collections.abc import Mapping
from typing import Any


PROFILE_FIELDS = (
    "date_of_birth",
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "activity_level",
    "goal",
    "meals_per_day",
    "max_cooking_minutes",
    "foods_disliked",
    "dietary_preferences",
    "allergies",
    "weekly_budget",
)

NUMERIC_FIELDS = {
    "age",
    "height_cm",
    "weight_kg",
    "meals_per_day",
    "max_cooking_minutes",
    "weekly_budget",
}

TEXT_LIST_FIELDS = {
    "foods_disliked",
    "dietary_preferences",
    "allergies",
}


def extract_profile_fields(raw_input: Mapping[str, Any]) -> dict[str, Any]:
    """
    Keep only fields that belong to UserProfile and normalize empty values.

    The input can be a flat dict or a dict with a nested ``profile`` object.
    This keeps the extraction layer focused on shape cleanup; business rules live
    in ``ai.validation.step_01_profile``.
    """
    source = raw_input.get("profile", raw_input)
    if not isinstance(source, Mapping):
        return {}

    extracted: dict[str, Any] = {}
    for field in PROFILE_FIELDS:
        if field not in source:
            continue

        value = source[field]
        if isinstance(value, str):
            value = value.strip()

        if value == "" and field in NUMERIC_FIELDS:
            value = None
        elif isinstance(value, list) and field in TEXT_LIST_FIELDS:
            value = ", ".join(str(item).strip() for item in value if str(item).strip())

        extracted[field] = value

    return extracted
