"""Choose which AI workflow should handle a chat message."""

from typing import Any

from ai.profile.workflow import run_profile_onboarding


def run_chat_workflow(user, message: str) -> dict[str, Any]:
    """Process one message received from the central chat page.

    Args:
        user:    Django User instance for the current session.
        message: The raw text the user just sent.

    Returns:
        ``{"reply": str, "result": dict}``
    """
    # For now, every message goes to the profile-onboarding workflow.
    # Later, add routing here for meals, recipes, and other workflows.
    result = run_profile_onboarding(user, message)
    return {"reply": result["reply"], "result": result}
