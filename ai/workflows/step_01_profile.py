"""Step 01 workflow for conversational profile onboarding."""

from collections.abc import Mapping
from typing import Any

from ai.extraction.step_01_profile import extract_profile_fields
from ai.validation.step_01_profile import validate_profile_data


def run_profile_workflow(raw_input: Mapping[str, Any]) -> dict[str, Any]:
    """
    Run extraction and validation for the profile onboarding step.

    This intentionally does not save to the database. Callers can inspect the
    result, ask for missing fields, and save only when ``is_valid`` is true.
    """
    extracted_data = extract_profile_fields(raw_input)
    validation = validate_profile_data(extracted_data)

    return {
        "step": "step_01_profile",
        "extracted_data": extracted_data,
        **validation,
    }
