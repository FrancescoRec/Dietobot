"""LangGraph workflow for the first profile step."""

import json
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, START, StateGraph

from ai.extraction.step_01_profile import ProfileExtraction, extract_profile
from ai.validation.step_01_profile import validate_profile


REPLY_MODEL_NAME = "gemini-2.5-flash-lite"

REPLY_SYSTEM_PROMPT = """
You are DietoBot, a warm nutrition assistant.

Write the next chat reply for a user who is building their basic nutrition
profile. Keep it short, human, and conversational. If profile fields are
missing, ask naturally for only what is needed next. Never show internal field
names like height_cm, weight_kg, or activity_level. Do not use bullet lists.
Do not say "to get started" if the conversation has already started. Do not ask
again for details already present in the workflow result. Do not give nutrition
advice yet unless the profile is complete.
""".strip()


class ProfileState(TypedDict, total=False):
    """Data passed from one workflow node to the next."""

    message: str
    conversation: list[dict[str, str]]
    profile: ProfileExtraction
    result: dict[str, Any]


def extract_node(state: ProfileState) -> dict[str, ProfileExtraction]:
    """Extract profile fields from the user's message."""

    return {"profile": extract_profile(state["message"], state.get("conversation"))}


def validate_node(state: ProfileState) -> dict[str, dict[str, Any]]:
    """Validate the fields extracted by Vertex."""

    return {"result": validate_profile(state["profile"])}


def reply_node(state: ProfileState) -> dict[str, dict[str, Any]]:
    """Generate the visible chat reply for the profile step."""

    model = ChatVertexAI(model=REPLY_MODEL_NAME, temperature=0.4)
    payload = {
        "user_message": state["message"],
        "conversation": state.get("conversation", []),
        "workflow_result": state["result"],
    }
    response = model.invoke(
        [
            SystemMessage(content=REPLY_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(payload, default=str)),
        ]
    )

    result = {**state["result"], "reply": response.content.strip()}
    return {"result": result}


# Build the workflow in the same order in which the work happens.
graph = StateGraph(ProfileState)
graph.add_node("extract", extract_node)
graph.add_node("validate", validate_node)
graph.add_node("reply", reply_node)
graph.add_edge(START, "extract")
graph.add_edge("extract", "validate")
graph.add_edge("validate", "reply")
graph.add_edge("reply", END)

profile_workflow = graph.compile()


def run_profile_workflow(
    message: str,
    conversation: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Run the first profile step for one user message."""

    final_state = profile_workflow.invoke(
        {
            "message": message,
            "conversation": conversation or [{"role": "user", "content": message}],
        }
    )
    return final_state["result"]
