"""Tests de propriétés pour la validation des soumissions.

Property 1: Incomplete submission validation identifies all missing questions.
Validates: Requirements 2.2

Property 6: All validation error messages are in French.
Validates: Requirements 6.3
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from orientation_mali.models.questionnaire import QUESTION_IDS
from orientation_mali.validation.validator import MESSAGES, validate_submission


# --- Strategies ---

# Strategy to generate a non-empty response string
non_empty_response = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        whitelist_characters="àâäéèêëïîôùûüÿçœæ '-",
    ),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != "")

# Strategy to generate a strict subset of question IDs (0 to 9 questions answered)
incomplete_response_subset = st.lists(
    st.sampled_from(QUESTION_IDS),
    min_size=0,
    max_size=9,
    unique=True,
)


# --- Property Tests ---


@given(answered_ids=incomplete_response_subset, response_text=non_empty_response)
@settings(max_examples=100)
def test_property_1_incomplete_submission_identifies_all_missing_questions(
    answered_ids: list[str],
    response_text: str,
) -> None:
    """Property 1: Incomplete submission validation identifies all missing questions.

    For any subset of questionnaire responses containing fewer than 10 answers,
    the validation function SHALL return error messages that reference exactly
    the missing question IDs, and the submission SHALL be rejected.

    Feature: orientation-mali, Property 1: Incomplete submission validation identifies all missing questions
    """
    # Build a submission with only the answered subset
    responses = {qid: response_text for qid in answered_ids}
    data = {"exam_type": "DEF", "responses": responses}

    submission, errors = validate_submission(data)

    # Submission must be rejected (None) since fewer than 10 questions answered
    assert submission is None, (
        f"Submission with {len(answered_ids)} responses should be rejected"
    )

    # Determine which questions are missing
    expected_missing = set(QUESTION_IDS) - set(answered_ids)
    assert len(expected_missing) > 0, "Test precondition: at least one question must be missing"

    # The errors must contain a message referencing the missing questions
    # The message format is: "Veuillez répondre aux questions suivantes : q2, q3, q5."
    missing_message_found = False
    for error in errors:
        if " : " in error:
            ids_portion = error.split(" : ", 1)[1].rstrip(".")
            referenced_ids = {qid.strip() for qid in ids_portion.split(",")}
            # Verify the referenced IDs match exactly the expected missing set
            if referenced_ids == expected_missing:
                missing_message_found = True
                break

    assert missing_message_found, (
        f"Error messages should reference exactly the missing question IDs: {expected_missing}. "
        f"Got errors: {errors}"
    )


@given(answered_ids=incomplete_response_subset, response_text=non_empty_response)
@settings(max_examples=100)
def test_property_1_missing_count_matches_unanswered(
    answered_ids: list[str],
    response_text: str,
) -> None:
    """Property 1 (supplementary): Number of missing IDs in error equals unanswered count.

    For any incomplete submission, the number of question IDs referenced in the
    validation error SHALL equal exactly (10 - number of answered questions).

    Feature: orientation-mali, Property 1: Incomplete submission validation identifies all missing questions
    """
    responses = {qid: response_text for qid in answered_ids}
    data = {"exam_type": "DEF", "responses": responses}

    submission, errors = validate_submission(data)

    # Submission must be rejected
    assert submission is None

    expected_missing = set(QUESTION_IDS) - set(answered_ids)
    expected_missing_count = len(expected_missing)

    # Find the missing questions error message and count referenced IDs
    for error in errors:
        if " : " in error:
            ids_portion = error.split(" : ", 1)[1].rstrip(".")
            referenced_ids = [qid.strip() for qid in ids_portion.split(",")]
            assert len(referenced_ids) == expected_missing_count, (
                f"Expected {expected_missing_count} missing IDs, "
                f"but error references {len(referenced_ids)}: {referenced_ids}"
            )
            # Verify the referenced IDs match exactly the expected missing set
            assert set(referenced_ids) == expected_missing, (
                f"Referenced IDs {set(referenced_ids)} != expected {expected_missing}"
            )
            break
    else:
        # If no message with " : " found, that means the format is unexpected
        raise AssertionError(
            f"No missing questions message found with expected format. Errors: {errors}"
        )


# --- French Message Catalog Reference ---

# All valid French messages that the validator can produce (exact or as templates)
_FRENCH_MESSAGE_TEMPLATES = set(MESSAGES.values())

# The set of known French message prefixes (before the dynamic portion)
_MISSING_QUESTIONS_PREFIX = MESSAGES["missing_questions"].split("{ids}")[0]


def _is_from_french_catalog(message: str) -> bool:
    """Check if a message is from the French message catalog.

    A message is considered valid if it either:
    - Matches an exact catalog entry, or
    - Is a formatted version of the 'missing_questions' template
      (starts with the known prefix and ends with a period).
    """
    # Exact match with a static message
    if message in _FRENCH_MESSAGE_TEMPLATES:
        return True

    # Formatted version of the missing_questions template
    if message.startswith(_MISSING_QUESTIONS_PREFIX) and message.endswith("."):
        return True

    return False


# --- Strategies for Property 6 ---

# Strategy for invalid exam types (not DEF or BAC)
invalid_exam_type = st.text(min_size=0, max_size=20).filter(
    lambda s: s not in ("DEF", "BAC")
)

# Strategy for a subset of question IDs (0 to 9 answered)
partial_question_ids = st.lists(
    st.sampled_from(QUESTION_IDS),
    min_size=0,
    max_size=9,
    unique=True,
)

# Strategy for response values that may include empty strings
response_value = st.one_of(
    st.just(""),  # empty response
    st.just("   "),  # whitespace-only response
    non_empty_response,  # valid response
)


# --- Property 6 Tests ---


@given(
    exam_type=invalid_exam_type,
    answered_ids=st.lists(
        st.sampled_from(QUESTION_IDS), min_size=0, max_size=10, unique=True
    ),
    response_text=non_empty_response,
)
@settings(max_examples=100)
def test_property_6_invalid_exam_type_messages_are_french(
    exam_type: str,
    answered_ids: list[str],
    response_text: str,
) -> None:
    """Property 6: Invalid exam type produces only French error messages.

    For any submission with an invalid exam type, all returned error messages
    SHALL be strings from the French message catalog.

    Feature: orientation-mali, Property 6: All validation error messages are in French
    """
    responses = {qid: response_text for qid in answered_ids}
    data = {"exam_type": exam_type, "responses": responses}

    submission, errors = validate_submission(data)

    # Must have at least one error (invalid exam type)
    assert len(errors) > 0, "Invalid exam type should produce errors"

    for error in errors:
        assert _is_from_french_catalog(error), (
            f"Error message is not from the French catalog: '{error}'"
        )


@given(
    answered_ids=partial_question_ids,
    response_text=non_empty_response,
)
@settings(max_examples=100)
def test_property_6_missing_questions_messages_are_french(
    answered_ids: list[str],
    response_text: str,
) -> None:
    """Property 6: Missing questions produces only French error messages.

    For any submission with fewer than 10 responses, all returned error messages
    SHALL be strings from the French message catalog.

    Feature: orientation-mali, Property 6: All validation error messages are in French
    """
    responses = {qid: response_text for qid in answered_ids}
    data = {"exam_type": "DEF", "responses": responses}

    submission, errors = validate_submission(data)

    assert len(errors) > 0, "Incomplete submission should produce errors"

    for error in errors:
        assert _is_from_french_catalog(error), (
            f"Error message is not from the French catalog: '{error}'"
        )


@given(
    empty_ids=st.lists(
        st.sampled_from(QUESTION_IDS), min_size=1, max_size=10, unique=True
    ),
)
@settings(max_examples=100)
def test_property_6_empty_responses_messages_are_french(
    empty_ids: list[str],
) -> None:
    """Property 6: Empty string responses produce only French error messages.

    For any submission where some responses are empty strings, all returned
    error messages SHALL be strings from the French message catalog.

    Feature: orientation-mali, Property 6: All validation error messages are in French
    """
    # Build responses where selected IDs have empty strings, rest have valid text
    responses = {}
    for qid in QUESTION_IDS:
        if qid in empty_ids:
            responses[qid] = ""
        else:
            responses[qid] = "Réponse valide"

    data = {"exam_type": "BAC", "responses": responses}

    submission, errors = validate_submission(data)

    assert len(errors) > 0, "Submission with empty responses should produce errors"

    for error in errors:
        assert _is_from_french_catalog(error), (
            f"Error message is not from the French catalog: '{error}'"
        )


@given(
    exam_type=invalid_exam_type,
    empty_ids=st.lists(
        st.sampled_from(QUESTION_IDS), min_size=1, max_size=5, unique=True
    ),
    missing_ids=st.lists(
        st.sampled_from(QUESTION_IDS), min_size=1, max_size=5, unique=True
    ),
)
@settings(max_examples=100)
def test_property_6_combined_errors_all_french(
    exam_type: str,
    empty_ids: list[str],
    missing_ids: list[str],
) -> None:
    """Property 6: Combined validation errors are all in French.

    For any submission with multiple types of errors (invalid exam type,
    missing questions, and empty responses), ALL returned error messages
    SHALL be strings from the French message catalog.

    Feature: orientation-mali, Property 6: All validation error messages are in French
    """
    # Build responses: exclude missing_ids entirely, make empty_ids empty strings
    responses = {}
    for qid in QUESTION_IDS:
        if qid in missing_ids:
            continue  # missing question
        elif qid in empty_ids:
            responses[qid] = "  "  # whitespace-only (treated as empty)
        else:
            responses[qid] = "Une réponse"

    data = {"exam_type": exam_type, "responses": responses}

    submission, errors = validate_submission(data)

    # Should have errors (at minimum invalid exam type)
    assert len(errors) > 0, "Combined invalid submission should produce errors"

    for error in errors:
        assert _is_from_french_catalog(error), (
            f"Error message is not from the French catalog: '{error}'"
        )
