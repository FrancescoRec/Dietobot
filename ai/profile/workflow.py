"""LangGraph profile-onboarding workflow with conditional branching."""

from typing import Any, Callable, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, START, StateGraph

from ai.profile.extraction import ProfileExtraction, extract_profile
from ai.profile.validation import missing_required_fields, validate_profile_extraction
from profiles.models import UserProfile


FOLLOW_UP_MODEL = "gemini-2.5-flash-lite"

FOLLOW_UP_SYSTEM_PROMPT = """
You are DietoBot, a friendly nutrition assistant helping a user build their profile.

Your job is to ask for one or more missing pieces of information in a short, natural message.

Rules:
- Ask for all the fields listed in the user message — you can group related ones
  naturally (e.g. "height and weight" in one sentence) if it flows well.
- Never reveal internal field names like height_cm, weight_kg, or activity_level.
- Use plain, conversational language.
- If some fields are already known, briefly acknowledge that first (a few words max).
- No bullet points. Keep it concise — two sentences at most.
""".strip()

# Human-readable labels for each required field.
FIELD_LABELS: dict[str, str] = {
    "age":            "age",
    "sex":            "biological sex (male or female)",
    "height_cm":      "height",
    "weight_kg":      "current weight",
    "activity_level": "activity level (e.g. sedentary, lightly active, moderately active, very active)",
    "goal":           "weight goal (lose, maintain, or gain weight)",
}

ONBOARDING_COMPLETE_MESSAGE = (
    "Perfect, that's everything I need. "
    "I'll work out your energy requirements next."
)

ALL_REQUIRED = ("age", "sex", "height_cm", "weight_kg", "activity_level", "goal")


class ProfileState(TypedDict, total=False):
    """Data passed from one workflow node to the next."""

    user_id: int
    message: str
    # The field we were waiting for before this message arrived.
    # Set by load_context_node and used by extract_node as a hint.
    context_field: str | None
    extraction: ProfileExtraction
    valid_values: dict[str, Any]
    missing_fields: list[str]
    reply: str
    profile_complete: bool


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def load_context_node(state: ProfileState) -> dict:
    """Load the current profile BEFORE extraction.

    Knowing which field is still missing tells extract_node what the user
    was replying to — critical for interpreting bare answers like "180".
    """
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    missing = missing_required_fields(profile)
    # The first missing field is what the previous bot turn was asking for.
    context_field = missing[0] if missing else None
    return {"missing_fields": missing, "context_field": context_field}


def extract_node(state: ProfileState) -> dict:
    """Extract profile fields from the user's message."""
    test_extractor = state.get("_extractor")
    if test_extractor:
        # Test path: use the injected fake, no Vertex call.
        extraction = test_extractor(state["message"])
    else:
        # Production path: pass the context hint so Gemini interprets
        # bare replies correctly (e.g. "180" → height_cm).
        extraction = extract_profile(
            state["message"],
            context_field=state.get("context_field"),
        )
    return {"extraction": extraction}


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
    """Re-load the profile after saving and recompute missing fields."""
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    missing = missing_required_fields(profile)
    return {"missing_fields": missing}


def ask_follow_up_node(state: ProfileState) -> dict:
    """Ask for all remaining missing fields using a small LLM."""

    missing = state["missing_fields"]

    # Test path: use the injected fake generator.
    follow_up_generator = state.get("_follow_up_generator")
    if follow_up_generator:
        return {"reply": follow_up_generator(missing), "profile_complete": False}

    already_known = [f for f in ALL_REQUIRED if f not in missing]
    missing_labels = [FIELD_LABELS[f] for f in missing if f in FIELD_LABELS]

    context_parts = []
    if already_known:
        context_parts.append(f"Already collected: {', '.join(already_known)}.")
    context_parts.append(f"Ask the user for: {', '.join(missing_labels)}.")
    user_content = " ".join(context_parts)

    model = ChatVertexAI(model=FOLLOW_UP_MODEL, temperature=0.7)
    response = model.invoke([
        SystemMessage(content=FOLLOW_UP_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ])
    return {"reply": response.content.strip(), "profile_complete": False}


def onboarding_complete_node(state: ProfileState) -> dict:
    """Return the completion message when all required fields are filled."""
    return {"reply": ONBOARDING_COMPLETE_MESSAGE, "profile_complete": True}


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

def route_after_check(state: ProfileState) -> str:
    return "ask_follow_up" if state.get("missing_fields") else "onboarding_complete"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

graph = StateGraph(ProfileState)
graph.add_node("load_context", load_context_node)
graph.add_node("extract", extract_node)
graph.add_node("validate_and_save", validate_and_save_node)
graph.add_node("check_profile", check_profile_node)
graph.add_node("ask_follow_up", ask_follow_up_node)
graph.add_node("onboarding_complete", onboarding_complete_node)

graph.add_edge(START, "load_context")
graph.add_edge("load_context", "extract")
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
    follow_up_generator: Callable | None = None,
) -> dict[str, Any]:
    """Run the profile-onboarding workflow for one user message.

    Args:
        user:                Django User instance.
        message:             The raw text the user just sent.
        extractor:           Optional callable replacing the live Gemini extraction call.
                             Signature: ``(message: str) -> ProfileExtraction``.
        follow_up_generator: Optional callable replacing the live Gemini follow-up call.
                             Signature: ``(missing_fields: list[str]) -> str``.

    Both injectable kwargs are for tests only.

    Returns:
        ``{"reply": str, "missing_fields": list[str], "profile_complete": bool}``
    """
    initial_state: ProfileState = {
        "user_id": user.pk,
        "message": message,
    }
    if extractor is not None:
        initial_state["_extractor"] = extractor  # type: ignore[typeddict-unknown-key]
    if follow_up_generator is not None:
        initial_state["_follow_up_generator"] = follow_up_generator  # type: ignore[typeddict-unknown-key]

    final_state = profile_onboarding_graph.invoke(initial_state)

    return {
        "reply":            final_state["reply"],
        "missing_fields":   final_state.get("missing_fields", []),
        "profile_complete": final_state.get("profile_complete", False),
    }
