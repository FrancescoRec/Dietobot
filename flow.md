## Data flow

```mermaid
flowchart TD
    A["POST /dietobot/"] --> B["chat.views.chat"]
    B --> C["run_chat_workflow(user, message)"]

    C -->|"profile.optional_complete"| Z["orchestrator shortcut\n→ meal planning later"]
    C -->|"onboarding still\nin progress"| D["run_profile_onboarding(user, message)"]

    D --> LC["load_context\n(missing required · was_profile_complete)"]
    LC --> EX["extract\n(Gemini · all fields including optional)"]
    EX --> VS["validate_and_save\n(UserProfile.update_or_create)"]
    VS --> CP["check_profile\n(missing required · optional_questions_asked)"]

    CP -->|"required fields\nstill missing"| F1["ask_follow_up\nPhase 1"]
    CP -->|"required complete\noptional not asked yet"| F2["ask_optional\nPhase 2 — asked once\nsets optional_questions_asked = True"]
    CP -->|"both phases done"| FC["fully_complete"]

    F1 --> R["reply → ChatMessage → redirect"]
    F2 --> R
    FC --> R
    Z  --> R
```

### Model properties

| Property | Derived from |
|---|---|
| `profile_complete` | all 6 required fields non-null |
| `optional_complete` | `profile_complete and optional_questions_asked` |

`optional_questions_asked` is a `BooleanField` — it records the *event* of the prompt being sent, which cannot be derived from field values alone (a user might volunteer allergy info in Phase 1, which would flip a field-value property too early).
