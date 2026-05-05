# Implementation Plan: Orientation Mali

## Overview

This plan implements the Orientation Mali school orientation application using FastAPI, Strands Agents SDK with Amazon Nova Pro, Pydantic data models, and Jinja2 templates. Tasks are ordered to build incrementally: data models first, then validation, agents, orchestration, web layer, and finally integration wiring.

## Tasks

- [x] 1. Set up project structure and dependencies
  - [x] 1.1 Create project directory structure and configuration files
    - Create the following directory structure: `src/orientation_mali/` (main package), `src/orientation_mali/agents/`, `src/orientation_mali/models/`, `src/orientation_mali/validation/`, `src/orientation_mali/templates/`, `src/orientation_mali/static/`, `tests/unit/`, `tests/property/`, `tests/integration/`
    - Create `pyproject.toml` with dependencies: fastapi, uvicorn, jinja2, pydantic, strands-agents, strands-agents-bedrock, hypothesis, pytest
    - Create `src/orientation_mali/__init__.py` and sub-package `__init__.py` files
    - _Requirements: 7.1, 7.2_

- [x] 2. Implement data models
  - [x] 2.1 Create Pydantic data models for questionnaire, profile, and recommendations
    - Create `src/orientation_mali/models/schemas.py`
    - Implement `ExamType` enum with DEF and BAC values
    - Implement `Question` model with id, text, question_type, and optional options fields
    - Implement `QuestionnaireSubmission` model with exam_type and responses (dict with exactly 10 entries)
    - Implement `StudentProfile` model with strengths, interests, personality_traits, academic_inclinations (all non-empty lists), and summary (non-empty string)
    - Implement `RecommendedMajor`, `TrainingProgram`, `School`, `CareerPath` models
    - Implement `RecommendationSet` model with min_length=1 constraints on all lists
    - Implement `OrientationResult` model combining profile, recommendations, and exam_type
    - Implement `ErrorResponse` model with error, message, retry_available, and optional missing_questions
    - _Requirements: 3.3, 4.3, 4.4, 4.5, 4.6_

  - [x] 2.2 Write property test for StudentProfile parsing completeness
    - **Property 2: Parsed StudentProfile contains all required fields**
    - Use Hypothesis to generate valid profile JSON structures and verify all fields are non-empty
    - **Validates: Requirements 3.3**

  - [x] 2.3 Write property test for RecommendationSet structural completeness
    - **Property 3: RecommendationSet structural completeness**
    - Use Hypothesis to generate RecommendationSet instances and verify all lists have at least one element
    - **Validates: Requirements 4.3, 4.4, 4.5, 4.6**

- [x] 3. Implement questionnaire definition and validation module
  - [x] 3.1 Define the 10-question profiling questionnaire
    - Create `src/orientation_mali/models/questionnaire.py`
    - Define `QUESTIONNAIRE` list with 10 `Question` instances in French covering: academic interests, strengths, preferred subjects, career aspirations, learning style, and goals
    - Questions must assess interests, strengths, preferred subjects, and career aspirations
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 3.2 Implement validation module with French error messages
    - Create `src/orientation_mali/validation/validator.py`
    - Implement `validate_submission(data: dict) -> tuple[QuestionnaireSubmission | None, list[str]]` function
    - Validate that all 10 questions are answered; return French error messages listing missing question IDs
    - Validate exam_type is "DEF" or "BAC"; return "Veuillez sélectionner votre type d'examen (DEF ou BAC)." if invalid
    - Validate no empty string responses; return "Veuillez répondre à toutes les questions avant de soumettre."
    - All error messages must be in French from a message catalog
    - _Requirements: 2.1, 2.2, 6.3_

  - [x] 3.3 Write property test for incomplete submission validation
    - **Property 1: Incomplete submission validation identifies all missing questions**
    - Use Hypothesis to generate subsets of 0-9 responses and verify error messages reference exactly the missing question IDs
    - **Validates: Requirements 2.2**

  - [x] 3.4 Write property test for French validation messages
    - **Property 6: All validation error messages are in French**
    - Use Hypothesis to generate various invalid submissions and verify all returned messages are from the French message catalog
    - **Validates: Requirements 6.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Profile Agent
  - [x] 5.1 Create the Profile Agent using Strands SDK and Amazon Nova Pro
    - Create `src/orientation_mali/agents/profile_agent.py`
    - Configure `BedrockModel` with model_id="us.amazon.nova-pro-v1:0", region_name="us-east-1", temperature=0.3, max_tokens=2048
    - Write a French-language system prompt instructing the agent to analyze student responses and output a JSON-structured StudentProfile with strengths, interests, personality_traits, academic_inclinations, and summary
    - Instantiate the `Agent` with the model and system prompt
    - Implement `analyze_profile(exam_type: str, responses: dict) -> StudentProfile` function that formats input as JSON, calls the agent, and parses the response into a StudentProfile
    - Implement JSON parsing with error handling for malformed agent output
    - _Requirements: 3.1, 3.2, 3.3, 6.4, 7.1, 7.3_

  - [x] 5.2 Write unit tests for Profile Agent parsing
    - Test parsing valid profile JSON into StudentProfile
    - Test handling of malformed JSON responses
    - Test handling of missing fields in agent output
    - _Requirements: 3.3_

- [x] 6. Implement Recommendation Agent
  - [x] 6.1 Create the Recommendation Agent using Strands SDK and Amazon Nova Pro
    - Create `src/orientation_mali/agents/recommendation_agent.py`
    - Configure `BedrockModel` with model_id="us.amazon.nova-pro-v1:0", region_name="us-east-1", temperature=0.5, max_tokens=4096
    - Write a French-language system prompt with Malian education context: DEF/BAC paths, available BAC series (Sciences Exactes, Sciences Biologiques, Lettres, Sciences Humaines, Sciences Économiques), Malian institutions, and career paths
    - Instantiate the `Agent` with the model and system prompt
    - Implement `generate_recommendations(profile: StudentProfile, exam_type: str) -> RecommendationSet` function that formats input as JSON, calls the agent, and parses the response into a RecommendationSet
    - Implement JSON parsing with error handling for malformed agent output
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 6.5, 7.2, 7.4, 8.1, 8.2, 8.3, 8.4_

  - [x] 6.2 Write unit tests for Recommendation Agent parsing
    - Test parsing valid recommendation JSON into RecommendationSet
    - Test handling of malformed JSON responses
    - Test handling of empty lists in agent output
    - _Requirements: 4.3, 4.4, 4.5, 4.6_

- [x] 7. Implement orchestration layer and error handling
  - [x] 7.1 Create the orchestration service that chains Profile Agent and Recommendation Agent
    - Create `src/orientation_mali/agents/orchestrator.py`
    - Implement `process_orientation(exam_type: str, responses: dict) -> OrientationResult` function
    - Chain Profile Agent output to Recommendation Agent input
    - Implement retry logic: single automatic retry with 2-second exponential backoff on agent failure
    - Implement error handling: catch agent timeouts, invalid output, and Bedrock service errors
    - Return appropriate French error messages for each failure scenario
    - _Requirements: 2.3, 3.4, 4.7, 7.5_

  - [x] 7.2 Write unit tests for orchestration error handling
    - Test retry logic on agent failure (mock agent calls)
    - Test error message generation for each failure scenario
    - Test successful pipeline execution with mocked agents
    - _Requirements: 3.4, 4.7_

- [x] 8. Implement web layer with FastAPI and Jinja2 templates
  - [x] 8.1 Create FastAPI application with routes
    - Create `src/orientation_mali/app.py`
    - Configure FastAPI app with Jinja2 templates directory and static files
    - Implement `GET /` route: render questionnaire.html with QUESTIONNAIRE data
    - Implement `POST /api/submit` route: validate submission, call orchestrator, handle errors, redirect to results
    - Implement `GET /results` route: render results.html with OrientationResult data
    - Store results in session or pass via query mechanism
    - _Requirements: 1.1, 1.4, 2.1, 2.3, 5.1_

  - [x] 8.2 Create Jinja2 templates for questionnaire, results, and error pages
    - Create `src/orientation_mali/templates/questionnaire.html`: form with 10 questions, exam type selector (DEF/BAC), submit button, all text in French
    - Create `src/orientation_mali/templates/results.html`: display StudentProfile summary, then RecommendationSet organized into sections (Filières recommandées, Programmes de formation, Établissements, Métiers), render school website links as `<a>` tags when available
    - Create `src/orientation_mali/templates/error.html`: French error message display with retry button
    - Create a base template `src/orientation_mali/templates/base.html` for shared layout
    - All UI text must be in French
    - _Requirements: 1.1, 1.2, 1.4, 5.1, 5.2, 5.3, 5.4, 6.1_

  - [x] 8.3 Write property test for rendered recommendations sections
    - **Property 4: Rendered recommendations contain all category sections**
    - Use Hypothesis to generate valid RecommendationSets, render the template, and verify all four sections are present in the HTML
    - **Validates: Requirements 5.2**

  - [x] 8.4 Write property test for school website link rendering
    - **Property 5: School website links rendered when available**
    - Use Hypothesis to generate Schools with and without website fields, render, and verify `<a>` tag presence/absence
    - **Validates: Requirements 5.3**

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Wire everything together and create application entry point
  - [x] 10.1 Create the application entry point and wire all components
    - Create `src/orientation_mali/main.py` as the uvicorn entry point
    - Wire the FastAPI app with the orchestrator, validation module, and questionnaire data
    - Ensure the full flow works: questionnaire display → submission → validation → profile agent → recommendation agent → results display
    - Add proper error handling at the route level to catch and display French error messages
    - _Requirements: 1.1, 2.3, 5.1_

  - [x] 10.2 Write integration tests for the full pipeline
    - Test POST /api/submit with valid submission returns results page
    - Test POST /api/submit with incomplete submission returns validation errors in French
    - Test that results page displays all recommendation sections
    - Test error page displays with retry button on agent failure (mocked)
    - _Requirements: 2.1, 2.2, 5.1, 5.2_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- The application uses Python throughout: FastAPI, Strands Agents SDK, Pydantic, Jinja2
- All user-facing content (templates, error messages, agent prompts) must be in French
- Amazon Nova Pro model ID: `us.amazon.nova-pro-v1:0`
