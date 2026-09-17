"""Validate the profile fields returned by Vertex."""

from typing import Any

from ai.extraction.step_01_profile import ProfileExtraction


REQUIRED_FIELDS = (
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "activity_level",
    "goal",
)


def validate_profile(profile: ProfileExtraction) -> dict[str, Any]:
    """Return the extracted data together with simple validation errors."""

    # Convert the Pydantic object into a normal dictionary.
    data = profile.model_dump()
    errors: dict[str, str] = {}

    # Check the fields needed to complete the basic profile.
    for field in REQUIRED_FIELDS:
        if data[field] is None:
            errors[field] = "This field is required."

    # Check a few realistic numeric limits.
    if data["age"] is not None and not 13 <= data["age"] <= 120:
        errors["age"] = "Age must be between 13 and 120."

    if data["height_cm"] is not None and not 80 <= data["height_cm"] <= 250:
        errors["height_cm"] = "Height must be between 80 and 250 cm."

    if data["weight_kg"] is not None and not 25 <= data["weight_kg"] <= 400:
        errors["weight_kg"] = "Weight must be between 25 and 400 kg."

    missing_fields = [field for field in REQUIRED_FIELDS if data[field] is None]

    return {
        "is_valid": not errors,
        "data": data,
        "errors": errors,
        "missing_fields": missing_fields,
    }
