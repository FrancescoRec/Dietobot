"""Deterministic nutrition target calculations."""

from dataclasses import dataclass
from decimal import Decimal


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "high": 1.725,
}

PROTEIN_GRAMS_PER_KG = {
    "lose": (1.6, 2.2),
    "maintain": (1.4, 1.8),
    "gain": (1.6, 2.0),
}


@dataclass(frozen=True)
class NutritionTargets:
    bmr: int
    maintenance_calories: int
    calorie_min: int
    calorie_max: int
    protein_min: int
    protein_max: int
    fat_min: int
    fat_max: int
    carbs_min: int
    carbs_max: int


def calculate_targets(profile) -> NutritionTargets:
    """Calculate calorie and macro targets from a completed user profile."""
    weight_kg = _to_float(profile.weight_kg)
    bmr = _calculate_bmr(
        sex=profile.sex,
        weight_kg=weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
    )
    maintenance = bmr * ACTIVITY_MULTIPLIERS[profile.activity_level]
    calorie_min, calorie_max = _goal_calorie_range(
        maintenance=maintenance,
        goal=profile.goal,
        sex=profile.sex,
    )
    protein_min, protein_max = _protein_range(weight_kg, profile.goal)
    fat_min, fat_max = _fat_range((calorie_min + calorie_max) / 2)
    carbs_min, carbs_max = _carb_range(
        calorie_min=calorie_min,
        calorie_max=calorie_max,
        protein_min=protein_min,
        protein_max=protein_max,
        fat_min=fat_min,
        fat_max=fat_max,
    )

    return NutritionTargets(
        bmr=_round_to_step(bmr, 10),
        maintenance_calories=_round_to_step(maintenance, 10),
        calorie_min=calorie_min,
        calorie_max=calorie_max,
        protein_min=protein_min,
        protein_max=protein_max,
        fat_min=fat_min,
        fat_max=fat_max,
        carbs_min=carbs_min,
        carbs_max=carbs_max,
    )


def format_targets_message(profile) -> str:
    """Build the final onboarding message from deterministic targets."""
    targets = calculate_targets(profile)
    goal_label = {
        "lose": "fat loss",
        "maintain": "maintenance",
        "gain": "weight gain",
    }[profile.goal]

    return (
        "Perfect, your profile is complete.\n\n"
        "Here are your starting targets:\n\n"
        f"Maintenance: {targets.maintenance_calories} kcal/day\n"
        f"{goal_label.title()} target: {targets.calorie_min}-{targets.calorie_max} kcal/day\n\n"
        f"Protein: {targets.protein_min}-{targets.protein_max}g/day\n"
        f"Fat: {targets.fat_min}-{targets.fat_max}g/day\n"
        f"Carbs: {targets.carbs_min}-{targets.carbs_max}g/day\n\n"
        "These are starting estimates. We can adjust them later based on progress."
    )


def _calculate_bmr(*, sex: str, weight_kg: float, height_cm: int, age: int) -> float:
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if sex == "male":
        return base + 5
    if sex == "female":
        return base - 161
    raise ValueError("sex must be male or female")


def _goal_calorie_range(*, maintenance: float, goal: str, sex: str) -> tuple[int, int]:
    if goal == "lose":
        floor = 1500 if sex == "male" else 1200
        minimum = max(floor, maintenance - 500)
        maximum = max(minimum, maintenance - 300)
    elif goal == "gain":
        minimum = maintenance + 200
        maximum = maintenance + 300
    elif goal == "maintain":
        minimum = maintenance - 100
        maximum = maintenance + 100
    else:
        raise ValueError("goal must be lose, maintain, or gain")

    return _round_to_step(minimum, 10), _round_to_step(maximum, 10)


def _protein_range(weight_kg: float, goal: str) -> tuple[int, int]:
    min_per_kg, max_per_kg = PROTEIN_GRAMS_PER_KG[goal]
    return _round_to_step(weight_kg * min_per_kg, 5), _round_to_step(weight_kg * max_per_kg, 5)


def _fat_range(calories: float) -> tuple[int, int]:
    return _round_to_step((calories * 0.20) / 9, 5), _round_to_step((calories * 0.30) / 9, 5)


def _carb_range(
    *,
    calorie_min: int,
    calorie_max: int,
    protein_min: int,
    protein_max: int,
    fat_min: int,
    fat_max: int,
) -> tuple[int, int]:
    minimum = (calorie_min - (protein_max * 4) - (fat_max * 9)) / 4
    maximum = (calorie_max - (protein_min * 4) - (fat_min * 9)) / 4
    return max(0, _round_to_step(minimum, 5)), max(0, _round_to_step(maximum, 5))


def _round_to_step(value: float, step: int) -> int:
    return int(round(value / step) * step)


def _to_float(value: Decimal | float | int) -> float:
    return float(value)
