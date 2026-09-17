from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Sex(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class ActivityLevel(models.TextChoices):
        SEDENTARY = "sedentary", "Sedentary"
        LIGHT = "light", "Lightly active"
        MODERATE = "moderate", "Moderately active"
        HIGH = "high", "Very active"

    class Goal(models.TextChoices):
        LOSE = "lose", "Lose weight"
        MAINTAIN = "maintain", "Maintain weight"
        GAIN = "gain", "Gain weight"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # --- Phase 1: required ---
    age            = models.PositiveSmallIntegerField(null=True, blank=True)
    sex            = models.CharField(max_length=10, choices=Sex.choices, blank=True)
    height_cm      = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg      = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    activity_level = models.CharField(max_length=20, choices=ActivityLevel.choices, blank=True)
    goal           = models.CharField(max_length=10, choices=Goal.choices, blank=True)

    # --- Phase 2: optional ---
    meals_per_day       = models.PositiveSmallIntegerField(default=3)
    max_cooking_minutes = models.PositiveSmallIntegerField(default=30)
    foods_disliked      = models.TextField(blank=True)
    dietary_preferences = models.TextField(blank=True)
    allergies           = models.TextField(blank=True)
    weekly_budget       = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Records the event "optional-fields prompt was sent".
    # A @property can't do this: a user can volunteer allergies during Phase 1,
    # which would make a field-value-based property flip too early.
    optional_questions_asked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def profile_complete(self) -> bool:
        """True when all six required fields are filled in."""
        return bool(
            self.age
            and self.sex
            and self.height_cm
            and self.weight_kg
            and self.activity_level
            and self.goal
        )

    @property
    def optional_complete(self) -> bool:
        """True once both onboarding phases are done."""
        return self.profile_complete and self.optional_questions_asked

    def __str__(self):
        return f"Profile of {self.user}"
