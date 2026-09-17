# Generated manually for Phase 1 conversational onboarding.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("age", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "sex",
                    models.CharField(
                        blank=True,
                        choices=[("male", "Male"), ("female", "Female")],
                        max_length=10,
                    ),
                ),
                ("height_cm", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "weight_kg",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "activity_level",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("sedentary", "Sedentary"),
                            ("light", "Lightly active"),
                            ("moderate", "Moderately active"),
                            ("high", "Very active"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "goal",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("lose", "Lose weight"),
                            ("maintain", "Maintain weight"),
                            ("gain", "Gain weight"),
                        ],
                        max_length=10,
                    ),
                ),
                ("meals_per_day", models.PositiveSmallIntegerField(default=3)),
                ("max_cooking_minutes", models.PositiveSmallIntegerField(default=30)),
                ("foods_disliked", models.TextField(blank=True)),
                ("dietary_preferences", models.TextField(blank=True)),
                ("allergies", models.TextField(blank=True)),
                (
                    "weekly_budget",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=6,
                        null=True,
                    ),
                ),
                ("profile_complete", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
