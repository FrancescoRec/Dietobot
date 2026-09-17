"""LangGraph workflow for the first profile step."""

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from ai.extraction.step_01_profile import ProfileExtraction, extract_profile
from ai.validation.step_01_profile import validate_profile


class ProfileState(TypedDict, total=False):
    """Data passed from one workflow node to the next."""

    message: str
    profile: ProfileExtraction
    result: dict[str, Any]


def extract_node(state: ProfileState) -> dict[str, ProfileExtraction]:
    """Extract profile fields from the user's message."""

    return {"profile": extract_profile(state["message"])}


def validate_node(state: ProfileState) -> dict[str, dict[str, Any]]:
    """Validate the fields extracted by Vertex."""

    return {"result": validate_profile(state["profile"])}


# Build the workflow in the same order in which the work happens.
graph = StateGraph(ProfileState)
graph.add_node("extract", extract_node)
graph.add_node("validate", validate_node)
graph.add_edge(START, "extract")
graph.add_edge("extract", "validate")
graph.add_edge("validate", END)

profile_workflow = graph.compile()


def run_profile_workflow(message: str) -> dict[str, Any]:
    """Run extraction and validation for one user message."""

    final_state = profile_workflow.invoke({"message": message})
    return final_state["result"]
