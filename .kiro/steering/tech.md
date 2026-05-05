# Tech Stack

## Language & Runtime

- Python 3.12
- Virtual environment managed with `uv` (v0.11.7)

## Frameworks & Libraries

- **FastAPI** — Web framework (backend API and server-side rendering)
- **Jinja2** — HTML templating
- **Pydantic** — Data validation and models
- **Strands Agents SDK** (`strands-agents`, `strands-agents-bedrock`) — AI agent framework
- **Amazon Nova Pro** (`us.amazon.nova-pro-v1:0`) — Foundation model via Amazon Bedrock
- **Uvicorn** — ASGI server
- **Hypothesis** — Property-based testing
- **Pytest** — Test runner

## Build & Configuration

- `pyproject.toml` — Project metadata and dependencies
- No separate build step; Python source runs directly

## Common Commands

```bash
# Activate virtual environment
source .venv/Scripts/activate   # bash on Windows
.venv\Scripts\activate.bat      # cmd on Windows

# Install dependencies
uv pip install -e .

# Run the application
uvicorn src.orientation_mali.main:app --reload

# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run property-based tests
pytest tests/property/

# Run integration tests
pytest tests/integration/
```

## Infrastructure

- Amazon Bedrock (us-east-1 region) for model inference
- AWS credentials required for Bedrock access
