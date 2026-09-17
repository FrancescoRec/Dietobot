"""LangGraph profile-onboarding workflow with two-phase conditional branching.

Phase 1 — Required fields:
    age, sex, height_cm, weight_kg, activity_level, goal

Phase 2 — Optional fields (asked once, after phase 1 is complete):
    meals_per_day, max_cooking_minutes, foods_disliked,
    dietary_preferences, allergies, weekly_budget

Extraction and saving of ALL fields (including optional ones) happens on every
turn regardless of which phase the user is in, so any info mentioned early is
never lost.
"""

from typing import Any, Callable, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, START, StateGraph

from ai.profile.extraction import ProfileExtraction, extract_profile
from ai.profile.validation import (
    missing_optional_fields,
    missing_required_fields,
    validate_profile_extraction,
)
from profiles.models import UserProfile


FOLLOW_UP_MODEL = "gemini-2.5-flash-lite"

# ---------------------------------------------------------------------------
# Phase-1 follow-up (required fields)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Phase-2 (optional fields)
# ---------------------------------------------------------------------------

REQUIRED_COMPLETE_MESSAGE = "Perfect, I now have all the essentials!"

ASK_OPTIONAL_SYSTEM_PROMPT = """
You are DietoBot, a friendly nutrition assistant.

The user has just completed the core part of their profile.
Now ask about a few extra details that will help personalise their meal plan.

Always ask about ALL of the following, unless the user has already mentioned them:
- Any dietary preferences or restrictions (e.g., vegetarian, vegan, gluten-free, halal, kosher)
- Any food allergies
- Foods they dislike or want to avoid
- How many meals a day they prefer (mention the default is 3 if helpful)
- How much time they usually have to cook per meal
- Their weekly food budget (make clear this is optional)

Rules:
- Never reveal internal field names (e.g., dietary_preferences, max_cooking_minutes).
- Briefly acknowledge any details already provided.
- Keep it warm and conversational — two to four sentences, no bullet points.
- Mention the budget question last and flag it as optional.
""".strip()

OPTIONAL_FIELD_LABELS: dict[str, str] = {
    "foods_disliked":      "foods they dislike",
    "dietary_preferences": "dietary preferences (e.g., vegetarian, vegan, gluten-free)",
    "allergies":           "food allergies",
    "weekly_budget":       "weekly food budget (optional)",
}

FULLY_COMPLETE_MESSAGE = (
    "You're all set — I have everything I need to build your personalised meal plan! 🎉"
)

ALL_REQUIRED = ("age", "sex", "height_cm", "weight_kg", "activity_level", "goal")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class ProfileState(TypedDict, total=False):
    """Data passed from one workflow node to the next."""

    user_id: int
    message: str
    # True if the required profile was already complete BEFORE this message.
    was_profile_complete: bool
    # True if the optional-questions prompt was already sent in a previous turn.
    optional_questions_asked: bool
    # The field we were waiting for before this message arrived.
    context_field: str | None
    extraction: ProfileExtraction
    valid_values: dict[str, Any]
    missing_fields: list[str]
    reply: str
    profile_complete: bool
    optional_complete: bool


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def load_context_node(state: ProfileState) -> dict:
    """Load the current profile BEFORE extraction.

    Knowing which required field is still missing tells extract_node what the
    user was replying to — critical for interpreting bare answers like "180".
    Also records whether the required profile was already complete so later
    nodes can decide whether to prepend the "essentials done!" message.
    """
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    missing = missing_required_fields(profile)
    context_field = missing[0] if missing else None
    return {
        "missing_fields": missing,
        "context_field": context_field,
        "was_profile_complete": len(missing) == 0,
    }


def extract_node(state: ProfileState) -> dict:
    """Extract profile fields from the user's message."""
    test_extractor = state.get("_extractor")
    if test_extractor:
        extraction = test_extractor(state["message"])
    else:
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
    """Re-load the profile after saving and recompute missing required fields."""
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    missing = missing_required_fields(profile)
    return {"missing_fields": missing}


def ask_follow_up_node(state: ProfileState) -> dict:
    """Ask for all remaining *required* missing fields using a small LLM."""

    missing = state["missing_fields"]

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


# ---------------------------------------------------------------------------
# Phase-2 nodes
# ---------------------------------------------------------------------------

def check_optional_node(state: ProfileState) -> dict:
    """Check whether the optional-fields phase has already been triggered."""
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    return {"optional_questions_asked": profile.optional_questions_asked}


def ask_optional_node(state: ProfileState) -> dict:
    """Ask the user for optional profile details (Phase 2).

    Marks ``optional_questions_asked = True`` on the profile so this prompt
    is only shown once.  If the required profile was *just* completed in this
    same turn, the completion acknowledgement is prepended to the reply.
    """
    # Build context: tell the LLM what optional info the user has already shared.
    profile = UserProfile.objects.get(user_id=state["user_id"])
    opt_missing = missing_optional_fields(profile)
    already_known_optional = [
        label
        for field, label in OPTIONAL_FIELD_LABELS.items()
        if field not in opt_missing
    ]

    context_parts = []
    if already_known_optional:
        context_parts.append(f"Already known: {'; '.join(already_known_optional)}.")
    user_content = " ".join(context_parts) if context_parts else "No optional info collected yet."

    # Test path: reuse the injected follow-up generator with a sentinel list.
    optional_follow_up_generator = state.get("_optional_follow_up_generator")
    if optional_follow_up_generator:
        reply = optional_follow_up_generator(opt_missing)
    else:
        model = ChatVertexAI(model=FOLLOW_UP_MODEL, temperature=0.7)
        response = model.invoke([
            SystemMessage(content=ASK_OPTIONAL_SYSTEM_PROMPT),
            HumanMessage(content=user_content),
        ])
        reply = response.content.strip()

    # If the required profile was completed *this very turn*, acknowledge it first.
    if not state.get("was_profile_complete"):
        reply = REQUIRED_COMPLETE_MESSAGE + "\n\n" + reply

    return {"reply": reply, "profile_complete": True, "optional_complete": False}


def fully_complete_node(state: ProfileState) -> dict:
    """Return the final message when both phases are done."""
    return {
        "reply": FULLY_COMPLETE_MESSAGE,
        "profile_complete": True,
        "optional_complete": True,
    }


# ---------------------------------------------------------------------------
# Conditional edges
# ---------------------------------------------------------------------------

def route_after_check(state: ProfileState) -> str:
    """Route to Phase-1 follow-up if required fields are missing, else Phase 2."""
    return "ask_follow_up" if state.get("missing_fields") else "check_optional"


def route_after_optional(state: ProfileState) -> str:
    """Route to the optional-ask node or the fully-complete node."""
    return "fully_complete" if state.get("optional_questions_asked") else "ask_optional"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

graph = StateGraph(ProfileState)

# Nodes
graph.add_node("load_context",      load_context_node)
graph.add_node("extract",           extract_node)
graph.add_node("validate_and_save", validate_and_save_node)
graph.add_node("check_profile",     check_profile_node)
graph.add_node("ask_follow_up",     ask_follow_up_node)
graph.add_node("check_optional",    check_optional_node)
graph.add_node("ask_optional",      ask_optional_node)
graph.add_node("fully_complete",    fully_complete_node)

# Edges — Phase 1
graph.add_edge(START, "load_context")
graph.add_edge("load_context", "extract")
graph.add_edge("extract", "validate_and_save")
graph.add_edge("validate_and_save", "check_profile")
graph.add_conditional_edges("check_profile", route_after_check)
graph.add_edge("ask_follow_up", END)

# Edges — Phase 2
graph.add_conditional_edges("check_optional", route_after_optional)
graph.add_edge("ask_optional", END)
graph.add_edge("fully_complete", END)

profile_onboarding_graph = graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_profile_onboarding(
    user,
    message: str,
    extractor: Callable | None = None,
    follow_up_generator: Callable | None = None,
    optional_follow_up_generator: Callable | None = None,
) -> dict[str, Any]:
    """Run the profile-onboarding workflow for one user message.

    Args:
        user:                         Django User instance.
        message:                      The raw text the user just sent.
        extractor:                    Optional callable replacing the live Gemini extraction call.
                                      Signature: ``(message: str) -> ProfileExtraction``.
        follow_up_generator:          Optional callable replacing the Phase-1 LLM follow-up call.
                                      Signature: ``(missing_fields: list[str]) -> str``.
        optional_follow_up_generator: Optional callable replacing the Phase-2 LLM call.
                                      Signature: ``(missing_optional: list[str]) -> str``.

    All injectable kwargs are for tests only.

    Returns:
        ``{
            "reply":             str,
            "missing_fields":    list[str],
            "profile_complete":  bool,
            "optional_complete": bool,
        }``
    """
    initial_state: ProfileState = {
        "user_id": user.pk,
        "message": message,
    }
    if extractor is not None:
        initial_state["_extractor"] = extractor  # type: ignore[typeddict-unknown-key]
    if follow_up_generator is not None:
        initial_state["_follow_up_generator"] = follow_up_generator  # type: ignore[typeddict-unknown-key]
    if optional_follow_up_generator is not None:
        initial_state["_optional_follow_up_generator"] = optional_follow_up_generator  # type: ignore[typeddict-unknown-key]

    final_state = profile_onboarding_graph.invoke(initial_state)

    return {
        "reply":             final_state["reply"],
        "missing_fields":    final_state.get("missing_fields", []),
        "profile_complete":  final_state.get("profile_complete", False),
        "optional_complete": final_state.get("optional_complete", False),
    }
