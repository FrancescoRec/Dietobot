# Project Engineering Rules

## 1. Keep it simple and maintainable

Write clear, human-readable code.

Prefer simple Python and Django over unnecessary abstractions.

Use SOLID principles when they improve the design, but do not create interfaces, factories, services, or patterns just to look sophisticated.

Less code is usually better.

## 2. Earn complexity incrementally

Start with the smallest clean solution.

Only introduce things like:

* interfaces
* repositories
* subgraphs
* model routers
* adapters
* additional services

when they solve a real problem that already exists.

Do not design a large theoretical architecture before understanding the actual domain.

## 3. Django first

Keep Django as the main application framework.

Use Django for models, forms, validation, views, templates, authentication, persistence, and business logic.

Avoid JavaScript frameworks and unnecessary frontend complexity.

Use simple semantic HTML and Bootstrap where useful.

## 4. Use the right tool for the right job

Use normal Python for deterministic logic such as:

* calculations
* constraints
* validation
* budgets
* nutrition totals
* filtering

Use LangChain for model interaction, structured output, embeddings, retrieval, and tools.

Use LangGraph only when there is a real workflow involving state, branching, retries, loops, or human decisions.

Do not use an LLM where ordinary code is more reliable.

## 5. Keep AI isolated

Do not scatter model calls across views, models, forms, and templates.

AI logic should have clear boundaries and responsibilities.

Vertex AI is an infrastructure provider and should not leak throughout the whole codebase.

## 6. Keep state explicit

Do not use chat history as the source of truth.

Important information should be stored as structured application or graph state.

Persist real business data in Django/PostgreSQL.

## 7. Prefer structured outputs

When another component depends on an LLM response, use structured schemas instead of parsing arbitrary text.

## 8. Build meaningful modules

Modules and classes should represent real concepts.

Prefer:

```text
nutrition/calculations.py
meal_planning/validators.py
ai/workflows/meal_plan.py
```

over vague modules such as:

```text
utils.py
helpers.py
misc.py
```

Do not split code into dozens of tiny files without a reason.

## 9. No AI slop

Do not add features, abstractions, HTML, comments, or code just because they can be generated.

Avoid huge templates, excessive `<div>` / `<span>` nesting, fake production infrastructure, unnecessary dependencies, and generic generated-looking code.

Everything added to the project should have a clear purpose.

## 10. Test what matters

Deterministic logic should have deterministic tests.

Separate:

* unit tests
* workflow tests
* integration tests
* AI evaluations

Normal Django tests should not require live Vertex AI calls.

## 11. Measure AI behavior

Do not judge the system only because a generated answer looks good.

Measure things such as:

* constraint satisfaction
* failures
* repair iterations
* latency
* token usage
* cost
* retrieval quality

Never invent benchmark results.

## 12. Ask when the requirement matters

If something is genuinely unclear and the decision would materially affect the architecture or behavior, ask before implementing it.

Do not invent requirements.

For small implementation details, choose the simplest reasonable solution.

## 13. Do not run project code

Do not run project code, Python scripts, Django management commands, tests, migrations, servers, package installers, or other executable project workflows from the assistant side.

When testing, validation, migrations, or Django commands are needed, provide the exact Docker command for the user to run instead.

The expected command shape is:

```text
docker-compose run --rm django python manage.py <command>
```

The user runs these commands.

## Final principle

The project should feel like:

> a small system designed carefully

not:

> a large amount of generated code assembled quickly.

Django should solve Django problems.

LangChain should solve model and retrieval problems.

LangGraph should solve workflow problems.

Python should solve deterministic problems.
