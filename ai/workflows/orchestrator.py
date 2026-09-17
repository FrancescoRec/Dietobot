"""Choose which AI workflow should handle a chat message."""

from typing import Any

from ai.workflows.step_01_profile import run_profile_workflow


def run_chat_workflow(
    message: str,
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Process one message received from the central chat page."""

    # For now, every message goes to the profile workflow.
    # Later, add routing here for meals, recipes, and other workflows.
    result = run_profile_workflow(message, conversation)

    # Return both the visible reply and the complete workflow result.
    return {"reply": result["reply"], "result": result}
