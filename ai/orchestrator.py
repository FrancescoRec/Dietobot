"""Choose which AI workflow should handle a chat message."""

from typing import Any

from ai.profile.workflow import run_profile_onboarding
from nutrition.calculations import format_targets_message
from profiles.models import UserProfile


def run_chat_workflow(user, message: str) -> dict[str, Any]:
    """Process one message received from the central chat page.

    Args:
        user:    Django User instance for the current session.
        message: The raw text the user just sent.

    Returns:
        ``{"reply": str, "result": dict}``

    Routing logic
    -------------
    * If the profile is still being built (required fields OR optional phase not
      done yet) → profile-onboarding workflow.
    * If both phases are complete → return the deterministic nutrition targets.
    """
    # Check current profile state before deciding which workflow to run.
    try:
        profile_done = user.profile.optional_complete
    except UserProfile.DoesNotExist:
        profile_done = False

    if profile_done:
        reply = format_targets_message(user.profile)
        return {"reply": reply, "result": {"profile_complete": True, "optional_complete": True}}

    result = run_profile_onboarding(user, message)
    return {"reply": result["reply"], "result": result}
