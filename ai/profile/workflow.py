"""LangGraph profile-onboarding workflow with conditional branching."""

from typing import Any, Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from ai.profile.extraction import ProfileExtraction, extract_profile
from ai.profile.validation import missing_required_fields, validate_profile_extraction
from profiles.models import UserProfile


FOLLOW_UP_QUESTIONS: dict[str, str] = {
    "age":            "How old are you?",
    "sex":            "For the energy estimate, should I use male or female?",
    "height_cm":      "What's your height?",
    "weight_kg":      "What's your current weight?",
    "activity_level": "What does a normal week of physical activity look like for you?",
    "goal":           "What are you mainly trying to achieve: lose, maintain, or gain weight?",
}

ONBOARDING_COMPLETE_MESSAGE = (
    "Great, I have enough information to build your profile. "
    "I'll work out your energy requirements next."
)


class ProfileState(TypedDict, total=False):
    """Data passed from one workflow node to the next."""

    user_id: int
    message: str
    extraction: ProfileExtraction
    valid_values: dict[str, Any]
    missing_fields: list[str]
    reply: str
    profile_complete: bool


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def extract_node(state: ProfileState) -> dict:
    """Extract profile fields from the user's message using Gemini."""
    extractor = state.get("_extractor") or extract_profile
    return {"extraction": extractor(state["message"])}


def validate_and_save_node(state: ProfileState) -> dict:
    """Validate extracted values and persist them to UserProfile."""
    valid_values = validate_profile_extraction(state["extraction"])
    if valid_values:
        UserProfile.objects.update_or_create(
            user_id=state["user_id"],
            defaults=valid_values,
        )
    return {"valid_values": valid_values}


def check_profile_node(state: ProfileState) -> dict:
    """Load the persisted profile and compute which required fields are still missing."""
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    missing = missing_required_fields(profile)
    return {"missing_fields": missing}


def ask_follow_up_node(state: ProfileState) -> dict:
    """Pick the next follow-up question for the first missing required field."""
    first_missing = state["missing_fields"][0]
    reply = FOLLOW_UP_QUESTIONS.get(first_missing, "Could you tell me a bit more about yourself?")
    return {"reply": reply, "profile_complete": False}


def onboarding_complete_node(state: ProfileState) -> dict:
    """Return the completion message when all required fields are filled."""
    return {"reply": ONBOARDING_COMPLETE_MESSAGE, "profile_complete": True}


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

def route_after_check(state: ProfileState) -> str:
    """Route to ask_follow_up if fields are missing, otherwise to onboarding_complete."""
    return "ask_follow_up" if state.get("missing_fields") else "onboarding_complete"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

graph = StateGraph(ProfileState)
graph.add_node("extract", extract_node)
graph.add_node("validate_and_save", validate_and_save_node)
graph.add_node("check_profile", check_profile_node)
graph.add_node("ask_follow_up", ask_follow_up_node)
graph.add_node("onboarding_complete", onboarding_complete_node)

graph.add_edge(START, "extract")
graph.add_edge("extract", "validate_and_save")
graph.add_edge("validate_and_save", "check_profile")
graph.add_conditional_edges("check_profile", route_after_check)
graph.add_edge("ask_follow_up", END)
graph.add_edge("onboarding_complete", END)

profile_onboarding_graph = graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_profile_onboarding(
    user,
    message: str,
    extractor: Callable | None = None,
) -> dict[str, Any]:
    """Run the profile-onboarding workflow for one user message.

    Args:
        user:      Django User instance.
        message:   The raw text the user just sent.
        extractor: Optional callable replacing the live Gemini call.
                   Signature: ``(message: str) -> ProfileExtraction``.
                   Useful in tests to avoid network calls.

    Returns:
        ``{"reply": str, "missing_fields": list[str], "profile_complete": bool}``
    """
    initial_state: ProfileState = {
        "user_id": user.pk,
        "message": message,
    }
    if extractor is not None:
        # Pass the injected extractor through LangGraph state.
        initial_state["_extractor"] = extractor  # type: ignore[typeddict-unknown-key]

    final_state = profile_onboarding_graph.invoke(initial_state)

    return {
        "reply":            final_state["reply"],
        "missing_fields":   final_state.get("missing_fields", []),
        "profile_complete": final_state.get("profile_complete", False),
    }
