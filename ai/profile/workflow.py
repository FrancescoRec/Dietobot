"""LangGraph profile-onboarding workflow — two phases, one routing function.

Phase 1  required  age, sex, height_cm, weight_kg, activity_level, goal
Phase 2  optional  meals_per_day, max_cooking_minutes, foods_disliked,
                   dietary_preferences, allergies, weekly_budget

Extraction runs on every turn, so info the user volunteers early is always saved
regardless of which phase the conversation is in.
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


MODEL = "gemini-2.5-flash-lite"

FIELD_LABELS: dict[str, str] = {
    "age":            "age",
    "sex":            "biological sex (male or female)",
    "height_cm":      "height",
    "weight_kg":      "current weight",
    "activity_level": "activity level (sedentary / lightly active / moderately active / very active)",
    "goal":           "weight goal (lose, maintain, or gain)",
}

OPTIONAL_FIELD_LABELS: dict[str, str] = {
    "foods_disliked":      "foods they dislike",
    "dietary_preferences": "dietary preferences (e.g. vegetarian, vegan, gluten-free)",
    "allergies":           "food allergies",
    "weekly_budget":       "weekly food budget",
}

REQUIRED_DONE_PREFIX = "Perfect, I now have all the essentials!\n\n"
FULLY_COMPLETE_MESSAGE = (
    "You're all set — I have everything I need to build your personalised meal plan! 🎉"
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class ProfileState(TypedDict, total=False):
    user_id:                  int
    message:                  str
    context_field:            str | None   # field the bot last asked for (extraction hint)
    was_profile_complete:     bool         # required fields complete before this message?
    optional_questions_asked: bool         # optional prompt already sent?
    extraction:               ProfileExtraction
    valid_values:             dict[str, Any]
    missing_fields:           list[str]
    reply:                    str
    profile_complete:         bool
    optional_complete:        bool


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def load_context_node(state: ProfileState) -> dict:
    """Read the profile before extraction so we know what field the user is answering."""
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    missing = missing_required_fields(profile)
    return {
        "context_field":        missing[0] if missing else None,
        "missing_fields":       missing,
        "was_profile_complete": not missing,
    }


def extract_node(state: ProfileState) -> dict:
    """Extract all profile fields from the user's message."""
    extractor = state.get("_extractor")
    if extractor:
        return {"extraction": extractor(state["message"])}
    return {"extraction": extract_profile(state["message"], context_field=state.get("context_field"))}


def validate_and_save_node(state: ProfileState) -> dict:
    """Validate extracted values and persist them."""
    values = validate_profile_extraction(state["extraction"])
    if values:
        UserProfile.objects.update_or_create(user_id=state["user_id"], defaults=values)
    return {"valid_values": values}


def check_profile_node(state: ProfileState) -> dict:
    """Re-read the profile after saving. One DB call covers both phase checks."""
    profile, _ = UserProfile.objects.get_or_create(user_id=state["user_id"])
    return {
        "missing_fields":           missing_required_fields(profile),
        "optional_questions_asked": profile.optional_questions_asked,
    }


def ask_follow_up_node(state: ProfileState) -> dict:
    """Ask for the remaining required fields (Phase 1)."""
    missing = state["missing_fields"]
    generator = state.get("_follow_up_generator")
    if generator:
        return {"reply": generator(missing), "profile_complete": False}

    already = [f for f in FIELD_LABELS if f not in missing]
    prompt = (
        (f"Already collected: {', '.join(already)}. " if already else "")
        + f"Ask the user for: {', '.join(FIELD_LABELS[f] for f in missing)}."
    )
    system = (
        "You are DietoBot, a friendly nutrition assistant. "
        "Ask for the missing info in one or two natural sentences. "
        "Never mention internal field names. No bullet points."
    )
    reply = ChatVertexAI(model=MODEL, temperature=0.7).invoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)]
    ).content.strip()
    return {"reply": reply, "profile_complete": False}


def ask_optional_node(state: ProfileState) -> dict:
    """Ask for missing optional details — once, right after Phase 1 completes (Phase 2)."""
    UserProfile.objects.filter(user_id=state["user_id"]).update(optional_questions_asked=True)

    profile = UserProfile.objects.get(user_id=state["user_id"])
    opt_missing = missing_optional_fields(profile)

    generator = state.get("_optional_follow_up_generator")
    if generator:
        reply = generator(opt_missing)
    else:
        already = [lbl for fld, lbl in OPTIONAL_FIELD_LABELS.items() if fld not in opt_missing]
        to_ask  = (
            [OPTIONAL_FIELD_LABELS[f] for f in opt_missing]
            + ["number of meals per day", "maximum cooking time per meal"]
        )
        prompt = (
            (f"Already known: {', '.join(already)}. " if already else "")
            + f"Ask the user for: {', '.join(to_ask)}. "
            + "Mention that the budget question is optional."
        )
        system = (
            "You are DietoBot, a friendly nutrition assistant. "
            "The user has just finished the core profile. "
            "Ask about the remaining optional details in two to three warm, natural sentences. "
            "Never mention internal field names. No bullet points."
        )
        reply = ChatVertexAI(model=MODEL, temperature=0.7).invoke(
            [SystemMessage(content=system), HumanMessage(content=prompt)]
        ).content.strip()

    if not state.get("was_profile_complete"):
        reply = REQUIRED_DONE_PREFIX + reply

    return {"reply": reply, "profile_complete": True, "optional_complete": False}


def fully_complete_node(state: ProfileState) -> dict:
    """Both phases done."""
    return {"reply": FULLY_COMPLETE_MESSAGE, "profile_complete": True, "optional_complete": True}


# ---------------------------------------------------------------------------
# Routing  (single function, three outcomes)
# ---------------------------------------------------------------------------

def route_after_check(state: ProfileState) -> str:
    if state.get("missing_fields"):
        return "ask_follow_up"
    if not state.get("optional_questions_asked"):
        return "ask_optional"
    return "fully_complete"


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

graph = StateGraph(ProfileState)

graph.add_node("load_context",      load_context_node)
graph.add_node("extract",           extract_node)
graph.add_node("validate_and_save", validate_and_save_node)
graph.add_node("check_profile",     check_profile_node)
graph.add_node("ask_follow_up",     ask_follow_up_node)
graph.add_node("ask_optional",      ask_optional_node)
graph.add_node("fully_complete",    fully_complete_node)

graph.add_edge(START,              "load_context")
graph.add_edge("load_context",     "extract")
graph.add_edge("extract",          "validate_and_save")
graph.add_edge("validate_and_save","check_profile")
graph.add_conditional_edges("check_profile", route_after_check)
graph.add_edge("ask_follow_up",    END)
graph.add_edge("ask_optional",     END)
graph.add_edge("fully_complete",   END)

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
    """Run one turn of the profile-onboarding workflow.

    Injectable callables (extractor, follow_up_generator,
    optional_follow_up_generator) replace the live Gemini calls in tests.
    """
    state: ProfileState = {"user_id": user.pk, "message": message}
    if extractor:
        state["_extractor"] = extractor                                       # type: ignore[typeddict-unknown-key]
    if follow_up_generator:
        state["_follow_up_generator"] = follow_up_generator                   # type: ignore[typeddict-unknown-key]
    if optional_follow_up_generator:
        state["_optional_follow_up_generator"] = optional_follow_up_generator # type: ignore[typeddict-unknown-key]

    final = profile_onboarding_graph.invoke(state)
    return {
        "reply":            final["reply"],
        "missing_fields":   final.get("missing_fields", []),
        "profile_complete": final.get("profile_complete", False),
        "optional_complete":final.get("optional_complete", False),
    }
