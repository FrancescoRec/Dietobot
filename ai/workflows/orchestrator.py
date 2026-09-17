"""Choose which AI workflow should handle a chat message."""

from typing import Any

from ai.workflows.step_01_profile import run_profile_workflow


def run_chat_workflow(message: str) -> dict[str, Any]:
    """Process one message received from the central chat page."""

    # For now, every message goes to the profile workflow.
    # Later, add routing here for meals, recipes, and other workflows.
    result = run_profile_workflow(message)

    # Turn the workflow result into a simple message for the user.
    if result["missing_fields"]:
        fields = ", ".join(result["missing_fields"])
        reply = f"I still need these profile details: {fields}."
    else:
        reply = "Thanks. Your basic profile information is complete."

    # Return both the visible reply and the complete workflow result.
    return {"reply": reply, "result": result}
