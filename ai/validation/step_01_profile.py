"""Step 01: validate extracted profile data before saving it."""

from decimal import Decimal, InvalidOperation
from typing import Any


VALID_SEX = {"male", "female"}
VALID_ACTIVITY_LEVELS = {"sedentary", "light", "moderate", "high"}
VALID_GOALS = {"lose", "maintain", "gain"}

REQUIRED_PROFILE_FIELDS = (
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "activity_level",
    "goal",
)


def validate_profile_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate and coerce extracted profile fields.

    Returns a workflow-friendly result with cleaned values plus errors. Views can
    decide whether to ask follow-up questions, save a partial profile, or persist
    a complete one.
    """
    cleaned = dict(data)
    errors: dict[str, str] = {}

    for field in REQUIRED_PROFILE_FIELDS:
        if cleaned.get(field) in (None, ""):
            errors[field] = "This field is required."

    _clean_int(cleaned, errors, "age", minimum=13, maximum=120)
    _clean_int(cleaned, errors, "height_cm", minimum=80, maximum=250)
    _clean_decimal(cleaned, errors, "weight_kg", minimum=Decimal("25"), maximum=Decimal("400"))
    _clean_int(cleaned, errors, "meals_per_day", minimum=1, maximum=8)
    _clean_int(cleaned, errors, "max_cooking_minutes", minimum=0, maximum=300)
    _clean_decimal(cleaned, errors, "weekly_budget", minimum=Decimal("0"), maximum=Decimal("9999"))

    _clean_choice(cleaned, errors, "sex", VALID_SEX)
    _clean_choice(cleaned, errors, "activity_level", VALID_ACTIVITY_LEVELS)
    _clean_choice(cleaned, errors, "goal", VALID_GOALS)

    return {
        "is_valid": not errors,
        "cleaned_data": cleaned,
        "errors": errors,
        "missing_fields": [field for field in REQUIRED_PROFILE_FIELDS if field in errors],
    }


def _clean_choice(
    cleaned: dict[str, Any],
    errors: dict[str, str],
    field: str,
    valid_values: set[str],
) -> None:
    value = cleaned.get(field)
    if value in (None, ""):
        return

    normalized = str(value).strip().lower()
    if normalized not in valid_values:
        errors[field] = f"Use one of: {', '.join(sorted(valid_values))}."
        return

    cleaned[field] = normalized


def _clean_int(
    cleaned: dict[str, Any],
    errors: dict[str, str],
    field: str,
    *,
    minimum: int,
    maximum: int,
) -> None:
    value = cleaned.get(field)
    if value in (None, ""):
        return

    try:
        parsed = int(value)
    except (TypeError, ValueError):
        errors[field] = "Use a whole number."
        return

    if parsed < minimum or parsed > maximum:
        errors[field] = f"Use a value between {minimum} and {maximum}."
        return

    cleaned[field] = parsed


def _clean_decimal(
    cleaned: dict[str, Any],
    errors: dict[str, str],
    field: str,
    *,
    minimum: Decimal,
    maximum: Decimal,
) -> None:
    value = cleaned.get(field)
    if value in (None, ""):
        return

    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        errors[field] = "Use a numeric value."
        return

    if parsed < minimum or parsed > maximum:
        errors[field] = f"Use a value between {minimum} and {maximum}."
        return

    cleaned[field] = parsed
