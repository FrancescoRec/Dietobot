from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.profile.validation import missing_optional_fields, missing_required_fields, validate_profile_extraction
from ai.profile.workflow import run_profile_onboarding
from .models import UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_extraction(**overrides):
    """Fake extractor returning all required fields plus any overrides."""
    base = dict(
        age=27, sex="female", height_cm=168, weight_kg=64,
        activity_level="light", goal="maintain",
        meals_per_day=None, foods_disliked=None,
        dietary_preferences=None, allergies=None,
        max_cooking_minutes=None, weekly_budget=None,
    )
    base.update(overrides)
    return lambda _msg: SimpleNamespace(**base)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class ProfileValidationTests(TestCase):
    def test_missing_required_empty_for_complete_profile(self):
        user = get_user_model().objects.create_user(username="sam")
        profile = UserProfile.objects.create(
            user=user, age=32, sex=UserProfile.Sex.MALE,
            height_cm=180, weight_kg=Decimal("82.00"),
            activity_level=UserProfile.ActivityLevel.MODERATE,
            goal=UserProfile.Goal.LOSE,
        )
        self.assertEqual(missing_required_fields(profile), [])

    def test_missing_optional_lists_blank_fields(self):
        user = get_user_model().objects.create_user(username="opt")
        profile = UserProfile.objects.create(
            user=user, age=25, sex=UserProfile.Sex.FEMALE,
            height_cm=165, weight_kg=Decimal("60.00"),
            activity_level=UserProfile.ActivityLevel.LIGHT,
            goal=UserProfile.Goal.MAINTAIN,
        )
        missing = missing_optional_fields(profile)
        self.assertIn("foods_disliked", missing)
        self.assertIn("dietary_preferences", missing)
        self.assertIn("allergies", missing)
        self.assertIn("weekly_budget", missing)

    def test_missing_optional_excludes_already_filled(self):
        user = get_user_model().objects.create_user(username="opt2")
        profile = UserProfile.objects.create(
            user=user, age=25, sex=UserProfile.Sex.FEMALE,
            height_cm=165, weight_kg=Decimal("60.00"),
            activity_level=UserProfile.ActivityLevel.LIGHT,
            goal=UserProfile.Goal.MAINTAIN,
            dietary_preferences="vegetarian",
            allergies="peanuts",
            weekly_budget=Decimal("100.00"),
        )
        missing = missing_optional_fields(profile)
        self.assertIn("foods_disliked", missing)
        self.assertNotIn("dietary_preferences", missing)
        self.assertNotIn("allergies", missing)
        self.assertNotIn("weekly_budget", missing)

    def test_validate_extraction_maps_values_correctly(self):
        extraction = SimpleNamespace(
            age=27, sex="male", height_cm=182, weight_kg=84,
            activity_level="moderate", goal="lose",
            meals_per_day=4, foods_disliked=["olives"],
            dietary_preferences=None, allergies=["peanuts"],
            max_cooking_minutes=45, weekly_budget=80,
        )
        values = validate_profile_extraction(extraction)
        self.assertEqual(values["age"], 27)
        self.assertEqual(values["sex"], UserProfile.Sex.MALE)
        self.assertEqual(values["foods_disliked"], "olives")
        self.assertEqual(values["allergies"], "peanuts")


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class OnboardingWorkflowTests(TestCase):
    def test_required_complete_triggers_optional_phase(self):
        """First time required fields are all set → optional prompt sent, flag stored."""
        user = get_user_model().objects.create_user(username="mira")

        result = run_profile_onboarding(
            user, "I'm 27, female, 168 cm, 64 kg, lightly active, maintaining.",
            extractor=_make_full_extraction(),
            optional_follow_up_generator=lambda _: "Any dietary needs?",
        )

        profile = UserProfile.objects.get(user=user)
        self.assertTrue(result["profile_complete"])
        self.assertFalse(result["optional_complete"])    # optional asked, not complete yet
        self.assertTrue(profile.optional_questions_asked)
        self.assertIn("Perfect", result["reply"])        # prefix present

    def test_second_turn_reaches_fully_complete(self):
        """After optional prompt is sent and user answers, next turn is fully_complete."""
        user = get_user_model().objects.create_user(username="mira2")

        # Turn 1: required complete → optional prompt sent
        run_profile_onboarding(
            user, "required info",
            extractor=_make_full_extraction(),
            optional_follow_up_generator=lambda _: "Any dietary needs?",
        )

        # Turn 2: user answers with optional data
        result = run_profile_onboarding(
            user, "I'm vegetarian, budget 80 euros.",
            extractor=_make_full_extraction(dietary_preferences="vegetarian", weekly_budget=80),
        )

        self.assertTrue(result["profile_complete"])
        self.assertTrue(result["optional_complete"])

    def test_missing_required_asks_follow_up(self):
        """If required fields are missing, bot asks for them (no optional phase yet)."""
        user = get_user_model().objects.create_user(username="leo")

        result = run_profile_onboarding(
            user, "I am 27, 182 cm, 84 kg, gym often.",
            extractor=_make_full_extraction(sex=None),  # sex missing
            follow_up_generator=lambda _: "Male or female?",
        )

        self.assertFalse(result["profile_complete"])
        self.assertEqual(result["missing_fields"], ["sex"])
