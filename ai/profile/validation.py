"""Validate extracted profile values and check profile completeness."""

from decimal import Decimal, InvalidOperation
from typing import Any

from profiles.models import UserProfile


REQUIRED_FIELDS = ("age", "sex", "height_cm", "weight_kg", "activity_level", "goal")


def validate_profile_extraction(extraction) -> dict[str, Any]:
    """Map raw extraction values to Django-ready field values.

    Only fields with a valid non-None value are included in the returned dict,
    so the caller can safely pass it to UserProfile.objects.update_or_create()
    as ``defaults`` without overwriting already-saved fields with None.
    """

    values: dict[str, Any] = {}

    # --- age ---
    age = getattr(extraction, "age", None)
    if age is not None and 13 <= int(age) <= 120:
        values["age"] = int(age)

    # --- sex ---
    sex = getattr(extraction, "sex", None)
    if sex == "male":
        values["sex"] = UserProfile.Sex.MALE
    elif sex == "female":
        values["sex"] = UserProfile.Sex.FEMALE

    # --- height_cm ---
    height_cm = getattr(extraction, "height_cm", None)
    if height_cm is not None and 80 <= int(height_cm) <= 250:
        values["height_cm"] = int(height_cm)

    # --- weight_kg ---
    weight_kg = getattr(extraction, "weight_kg", None)
    if weight_kg is not None:
        try:
            d = Decimal(str(weight_kg)).quantize(Decimal("0.01"))
            if 25 <= d <= 400:
                values["weight_kg"] = d
        except InvalidOperation:
            pass

    # --- activity_level ---
    activity_level = getattr(extraction, "activity_level", None)
    valid_levels = {c.value for c in UserProfile.ActivityLevel}
    if activity_level in valid_levels:
        values["activity_level"] = activity_level

    # --- goal ---
    goal = getattr(extraction, "goal", None)
    valid_goals = {c.value for c in UserProfile.Goal}
    if goal in valid_goals:
        values["goal"] = goal

    # --- optional list fields (stored as comma-joined strings) ---
    for field in ("foods_disliked", "dietary_preferences", "allergies"):
        raw = getattr(extraction, field, None)
        if raw:
            if isinstance(raw, list):
                joined = ",".join(str(item) for item in raw if item)
                if joined:
                    values[field] = joined
            elif isinstance(raw, str) and raw.strip():
                values[field] = raw.strip()

    # --- optional numeric fields ---
    meals_per_day = getattr(extraction, "meals_per_day", None)
    if meals_per_day is not None:
        values["meals_per_day"] = int(meals_per_day)

    max_cooking_minutes = getattr(extraction, "max_cooking_minutes", None)
    if max_cooking_minutes is not None:
        values["max_cooking_minutes"] = int(max_cooking_minutes)

    weekly_budget = getattr(extraction, "weekly_budget", None)
    if weekly_budget is not None:
        try:
            values["weekly_budget"] = Decimal(str(weekly_budget)).quantize(Decimal("0.01"))
        except InvalidOperation:
            pass

    return values


def missing_required_fields(profile: UserProfile) -> list[str]:
    """Return names of required fields not yet set on the persisted profile."""

    missing = []
    if not profile.age:
        missing.append("age")
    if not profile.sex:
        missing.append("sex")
    if not profile.height_cm:
        missing.append("height_cm")
    if not profile.weight_kg:
        missing.append("weight_kg")
    if not profile.activity_level:
        missing.append("activity_level")
    if not profile.goal:
        missing.append("goal")
    return missing
