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

    date_of_birth = models.DateField()
    sex = models.CharField(max_length=10, choices=Sex.choices)

    height_cm = models.PositiveSmallIntegerField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)

    activity_level = models.CharField(
        max_length=20,
        choices=ActivityLevel.choices,
    )

    goal = models.CharField(
        max_length=10,
        choices=Goal.choices,
    )

    meals_per_day = models.PositiveSmallIntegerField(default=3)
    max_cooking_minutes = models.PositiveSmallIntegerField(default=30)

    weekly_budget = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"Profile of {self.user}"