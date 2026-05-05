# Project Structure

```
src/
└── orientation_mali/          # Main application package
    ├── __init__.py
    ├── main.py                # Uvicorn entry point
    ├── app.py                 # FastAPI app, routes
    ├── agents/                # AI agent implementations
    │   ├── __init__.py
    │   ├── profile_agent.py   # Profile Agent (analyzes questionnaire)
    │   ├── recommendation_agent.py  # Recommendation Agent (generates suggestions)
    │   └── orchestrator.py    # Chains agents, retry logic, error handling
    ├── models/                # Pydantic data models
    │   ├── __init__.py
    │   ├── schemas.py         # All data models (StudentProfile, RecommendationSet, etc.)
    │   └── questionnaire.py   # 10-question definition
    ├── validation/            # Input validation
    │   ├── __init__.py
    │   └── validator.py       # French-language validation with error messages
    ├── templates/             # Jinja2 HTML templates
    │   ├── base.html
    │   ├── questionnaire.html
    │   ├── results.html
    │   └── error.html
    └── static/                # CSS, JS, images

tests/
├── unit/                      # Specific example tests
│   ├── test_validation.py
│   ├── test_profile_parsing.py
│   ├── test_recommendation_parsing.py
│   └── test_rendering.py
├── property/                  # Hypothesis property-based tests
│   ├── test_validation_properties.py
│   ├── test_parsing_properties.py
│   └── test_rendering_properties.py
└── integration/               # Full pipeline tests (require Bedrock)
    ├── test_profile_agent.py
    ├── test_recommendation_agent.py
    └── test_pipeline.py
```

## Conventions

- Source code lives under `src/orientation_mali/`
- Tests mirror the source structure under `tests/`
- All user-facing strings (templates, error messages, agent prompts) are in French
- Data models use Pydantic with field descriptions in French
- Agents are isolated in their own modules with a single public function each
- Orchestration logic is separate from individual agent implementations
