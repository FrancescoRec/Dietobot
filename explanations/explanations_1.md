## 🧠 1. Context-Aware Prompt Injection (The Big Escamotage)

This is the cleverest trick in the whole codebase. The problem: if the bot just asked "what's your height?" and the user replies "180", Gemini has no idea if that's height, weight, age, or something else. The solution is dynamic prompt injection based on conversation state:

```python
CONTEXT_HINTS: dict[str, str] = {
    "age": "The user was just asked their age. A bare number is their age in years.",
    "sex": "The user was just asked their biological sex. A word like 'male', 'female', 'man', or 'woman' is their sex.",
    "height_cm": "The user was just asked their height. A bare number (e.g. 180) is their height in centimetres.",
    "weight_kg": "The user was just asked their weight. A bare number (e.g. 80) is their weight in kilograms.",
    "activity_level": "The user was just asked their activity level. Map their description to: sedentary, light, moderate, or high.",
    "goal": "The user was just asked their weight goal. Map their answer to their answer to: lose, maintain, or gain.",
}

prompt = BASE_SYSTEM_PROMPT

if context_field and context_field in CONTEXT_HINTS:
    prompt += "\n\n" + CONTEXT_HINTS[context_field]
```

## 🔁 2. LangGraph State Machine with Conditional Routing

The workflow is a compiled DAG using LangGraph — each node does one thing, data flows through a TypedDict state, and routing decisions are centralized in one edge function:

```python
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

graph.add_conditional_edges(
    "check_profile",
    route_after_check
)

graph.add_edge("ask_follow_up", END)
graph.add_edge("onboarding_complete", END)


def route_after_check(state: ProfileState) -> str:
    return "ask_follow_up" if state.get("missing_fields") else "onboarding_complete"
```

## 🏗️ 3. Structured Output via Pydantic + with_structured_output

Gemini is forced to return a type-safe object, not a raw string to parse:

```python
class ProfileExtraction(BaseModel):
    """Profile fields that Gemini should find in the message."""

    age: int | None = None
    sex: Literal["male", "female"] | None = None
    height_cm: int | None = None
    weight_kg: float | None = None
    activity_level: Literal["sedentary", "light", "moderate", "high"] | None = None
    goal: Literal["lose", "maintain", "gain"] | None = None
    meals_per_day: int | None = None
    max_cooking_minutes: int | None = None
    foods_disliked: list[str] = Field(default_factory=list)
    dietary_preferences: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    weekly_budget: float | None = None


model = ChatVertexAI(
    model=MODEL_NAME,
    temperature=0
)

structured_model = model.with_structured_output(ProfileExtraction)
```

## 🔒 5. Defensive Validation Layer Between LLM and Database

The LLM output is never trusted directly. A dedicated validation function sanity-checks every value before it touches the DB:

```python
# --- age ---

age = getattr(extraction, "age", None)

if age is not None and 13 <= int(age) <= 120:
    values["age"] = int(age)

...

# --- weight_kg ---

weight_kg = getattr(extraction, "weight_kg", None)

if weight_kg is not None:
    try:
        d = Decimal(str(weight_kg)).quantize(Decimal("0.01"))

        if 25 <= d <= 400:
            values["weight_kg"] = d

    except InvalidOperation:
        pass
```

## ⚡ 6. profile_complete as a Computed @property (Not a DB Field)

The original design stored profile_complete as a boolean column. It was removed from the DB (see migration `0002_remove_date_of_birth_profile_complete.py`) and replaced with a Python property:

```python
@property
def profile_complete(self) -> bool:
    """True when all six required fields are filled in."""

    return bool(
        self.age
        and self.sex
        and self.height_cm
        and self.weight_kg
        and self.activity_level
        and self.goal
    )
```

By making it a `@property`, it's always derived from the ground truth. Zero risk of stale state, zero extra write, and the API surface is identical.
