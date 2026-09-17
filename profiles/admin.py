from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "age",
        "sex",
        "height_cm",
        "weight_kg",
        "activity_level",
        "goal",
        "profile_complete",
    )
    list_filter = ("profile_complete", "sex", "activity_level", "goal")
    search_fields = ("user__username", "user__email")
