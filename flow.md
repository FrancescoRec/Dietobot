## Data flow after the change

```mermaid
flowchart TD
    A["POST /dietobot/"] --> B["chat.views.chat"]
    B --> C["run_chat_workflow(user, message)"]
    C -->|"profile_complete\n& optional_questions_asked"| Z["orchestrator shortcut\n(→ meal planning later)"]
    C -->|"onboarding still\nin progress"| D["run_profile_onboarding(user, message)"]

    D --> E["load_context node\n(missing_required_fields · was_profile_complete)"]
    E --> F["extract node\n(Gemini Flash, single message)\nSaves ALL fields incl. optional"]
    F --> G["validate_and_save node\n(validate + UserProfile.update_or_create)"]
    G --> H["check_profile node\n(missing_required_fields after save)"]

    H -->|"required fields\nstill missing"| I["ask_follow_up node\n(Phase 1 · FOLLOW_UP_QUESTIONS dict)"]
    H -->|"required fields\ncomplete"| J["check_optional node\n(optional_questions_asked flag)"]

    J -->|"not yet asked"| K["ask_optional node\n(Phase 2 · optional fields LLM)\nSets optional_questions_asked = True"]
    J -->|"already asked"| L["fully_complete node"]

    I --> M["reply → ChatMessage → redirect"]
    K --> M
    L --> M
    Z --> M
```

### Phase summary

| Phase | Trigger | Fields covered | Node |
|-------|---------|---------------|------|
| **1 – Required** | Every turn until complete | age, sex, height_cm, weight_kg, activity_level, goal | `ask_follow_up` |
| **2 – Optional** | Once, right after Phase 1 finishes | meals_per_day, max_cooking_minutes, foods_disliked, dietary_preferences, allergies, weekly_budget | `ask_optional` |
| **Done** | After Phase 2 prompt was sent | — | `fully_complete` / orchestrator shortcut |

> **Key property**: extraction runs and saves *all* fields (including optional) on *every* turn,
> so any info the user volunteers early is never lost — only the *questioning* of optional fields
> is deferred to Phase 2.
```
