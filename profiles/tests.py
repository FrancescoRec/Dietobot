from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.profile.validation import missing_required_fields, validate_profile_extraction
from ai.profile.workflow import run_profile_onboarding

from .models import UserProfile


class ProfileValidationTests(TestCase):
    def test_missing_required_fields_returns_empty_for_complete_profile(self):
        user = get_user_model().objects.create_user(username="sam")
        profile = UserProfile.objects.create(
            user=user,
            age=32,
            sex=UserProfile.Sex.MALE,
            height_cm=180,
            weight_kg=Decimal("82.00"),
            activity_level=UserProfile.ActivityLevel.MODERATE,
            goal=UserProfile.Goal.LOSE,
        )

        self.assertEqual(missing_required_fields(profile), [])

    def test_validate_profile_extraction_keeps_only_valid_values(self):
        extraction = SimpleNamespace(
            age=27,
            sex="male",
            height_cm=182,
            weight_kg=84,
            activity_level="moderate",
            goal="lose",
            meals_per_day=4,
            foods_disliked=["olives"],
            dietary_preferences=None,
            allergies=["peanuts"],
            max_cooking_minutes=45,
            weekly_budget=80,
        )

        values = validate_profile_extraction(extraction)

        self.assertEqual(values["age"], 27)
        self.assertEqual(values["sex"], UserProfile.Sex.MALE)
        self.assertEqual(values["height_cm"], 182)
        self.assertEqual(values["weight_kg"], Decimal("84.00"))
        self.assertEqual(values["activity_level"], UserProfile.ActivityLevel.MODERATE)
        self.assertEqual(values["goal"], UserProfile.Goal.LOSE)
        self.assertEqual(values["foods_disliked"], "olives")
        self.assertEqual(values["allergies"], "peanuts")


class OnboardingWorkflowTests(TestCase):
    def test_workflow_saves_extracted_values_and_completes_profile(self):
        user = get_user_model().objects.create_user(username="mira")

        def fake_extractor(message):
            return SimpleNamespace(
                age=27,
                sex="female",
                height_cm=168,
                weight_kg=64,
                activity_level="light",
                goal="maintain",
                meals_per_day=None,
                foods_disliked=None,
                dietary_preferences=None,
                allergies=None,
                max_cooking_minutes=None,
                weekly_budget=None,
            )

        result = run_profile_onboarding(
            user,
            "I'm 27, female, 168 cm, 64 kg, lightly active, maintaining.",
            extractor=fake_extractor,
        )

        profile = UserProfile.objects.get(user=user)
        self.assertTrue(result["profile_complete"])
        self.assertTrue(profile.profile_complete)
        self.assertEqual(profile.goal, UserProfile.Goal.MAINTAIN)

    def test_workflow_asks_one_follow_up_for_missing_fields(self):
        user = get_user_model().objects.create_user(username="leo")

        def fake_extractor(message):
            return SimpleNamespace(
                age=27,
                sex=None,
                height_cm=182,
                weight_kg=84,
                activity_level="moderate",
                goal="lose",
                meals_per_day=None,
                foods_disliked=None,
                dietary_preferences=None,
                allergies=None,
                max_cooking_minutes=None,
                weekly_budget=None,
            )

        result = run_profile_onboarding(
            user,
            "I am 27, 182 cm, 84 kg, gym often.",
            extractor=fake_extractor,
        )

        self.assertFalse(result["profile_complete"])
        self.assertEqual(result["missing_fields"], ["sex"])
        self.assertIn("male or female", result["reply"])
