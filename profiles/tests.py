from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase

from ai.profile.validation import missing_optional_fields, missing_required_fields, validate_profile_extraction
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

    def test_missing_optional_fields_returns_all_when_blank(self):
        user = get_user_model().objects.create_user(username="opttest")
        profile = UserProfile.objects.create(
            user=user,
            age=25,
            sex=UserProfile.Sex.FEMALE,
            height_cm=165,
            weight_kg=Decimal("60.00"),
            activity_level=UserProfile.ActivityLevel.LIGHT,
            goal=UserProfile.Goal.MAINTAIN,
        )

        missing = missing_optional_fields(profile)
        self.assertIn("foods_disliked", missing)
        self.assertIn("dietary_preferences", missing)
        self.assertIn("allergies", missing)
        self.assertIn("weekly_budget", missing)

    def test_missing_optional_fields_excludes_filled_ones(self):
        user = get_user_model().objects.create_user(username="opttest2")
        profile = UserProfile.objects.create(
            user=user,
            age=25,
            sex=UserProfile.Sex.FEMALE,
            height_cm=165,
            weight_kg=Decimal("60.00"),
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
    def _full_extractor(self, message):
        """Fake extractor that returns a fully complete required profile."""
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

    def test_workflow_saves_extracted_values_and_moves_to_optional_phase(self):
        """When required fields become complete, the workflow asks optional questions."""
        user = get_user_model().objects.create_user(username="mira")

        def fake_optional_follow_up(missing_optional):
            return "Do you have any food preferences or allergies?"

        result = run_profile_onboarding(
            user,
            "I'm 27, female, 168 cm, 64 kg, lightly active, maintaining.",
            extractor=self._full_extractor,
            optional_follow_up_generator=fake_optional_follow_up,
        )

        profile = UserProfile.objects.get(user=user)
        # Required phase done.
        self.assertTrue(result["profile_complete"])
        self.assertTrue(profile.profile_complete)
        self.assertEqual(profile.goal, UserProfile.Goal.MAINTAIN)
        # Optional phase just started — not complete yet (no optional fields saved).
        self.assertFalse(result["optional_complete"])
        # optional_questions_asked is a property: False because no optional fields set yet.
        self.assertFalse(profile.optional_questions_asked)
        # Reply should contain both the completion acknowledgement and the optional prompt.
        self.assertIn("Perfect", result["reply"])

    def test_workflow_reaches_fully_complete_on_second_turn(self):
        """After optional questions are asked and the user provides some data,
        the next turn routes to fully_complete."""
        user = get_user_model().objects.create_user(username="mira2")

        # Turn 1: complete required fields → optional phase starts.
        run_profile_onboarding(
            user,
            "I'm 27, female, 168 cm, 64 kg, lightly active, maintaining.",
            extractor=self._full_extractor,
            optional_follow_up_generator=lambda _: "Optional question?",
        )

        def extractor_with_optional(message):
            """Extractor that returns optional data — simulates the user answering."""
            return SimpleNamespace(
                age=27, sex="female", height_cm=168, weight_kg=64,
                activity_level="light", goal="maintain",
                meals_per_day=3,
                foods_disliked=None,
                dietary_preferences="vegetarian",   # ← optional field set
                allergies=None,
                max_cooking_minutes=None,
                weekly_budget=80,                   # ← optional field set
            )

        # Turn 2: user provides optional info → property flips → fully_complete.
        result = run_profile_onboarding(
            user,
            "I'm vegetarian, no allergies, budget is 80 euros a week.",
            extractor=extractor_with_optional,
        )

        self.assertTrue(result["profile_complete"])
        self.assertTrue(result["optional_complete"])

    def test_workflow_asks_one_follow_up_for_missing_required_fields(self):
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

        def fake_follow_up(missing_fields):
            return "Should I use male or female for the energy calculation?"

        result = run_profile_onboarding(
            user,
            "I am 27, 182 cm, 84 kg, gym often.",
            extractor=fake_extractor,
            follow_up_generator=fake_follow_up,
        )

        self.assertFalse(result["profile_complete"])
        self.assertEqual(result["missing_fields"], ["sex"])
        self.assertIsInstance(result["reply"], str)
        self.assertTrue(len(result["reply"]) > 0)
