"""Tests de propriétés pour le parsing des modèles de données.

Property 2: Parsed StudentProfile contains all required fields.
Validates: Requirements 3.3

Property 3: RecommendationSet structural completeness.
Validates: Requirements 4.3, 4.4, 4.5, 4.6
"""

import json

from hypothesis import given, settings
from hypothesis import strategies as st

from orientation_mali.models.schemas import (
    CareerPath,
    RecommendationSet,
    RecommendedMajor,
    School,
    StudentProfile,
    TrainingProgram,
)


# --- Strategies ---

non_empty_french_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        whitelist_characters="àâäéèêëïîôùûüÿçœæ '-",
    ),
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != "")

non_empty_list_of_strings = st.lists(non_empty_french_text, min_size=1, max_size=5)

student_profile_json_strategy = st.fixed_dictionaries(
    {
        "strengths": non_empty_list_of_strings,
        "interests": non_empty_list_of_strings,
        "personality_traits": non_empty_list_of_strings,
        "academic_inclinations": non_empty_list_of_strings,
        "summary": non_empty_french_text,
    }
)


# --- Property Tests ---


@given(profile_data=student_profile_json_strategy)
@settings(max_examples=100)
def test_property_2_student_profile_contains_all_required_fields(
    profile_data: dict,
) -> None:
    """Property 2: Parsed StudentProfile contains all required fields.

    For any valid JSON string representing a student profile, parsing it into a
    StudentProfile SHALL produce an object where strengths, interests,
    personality_traits, and academic_inclinations are all non-empty lists, and
    summary is a non-empty string.

    Feature: orientation-mali, Property 2: Parsed StudentProfile contains all required fields
    """
    # Parse from JSON string (simulates agent output parsing)
    json_str = json.dumps(profile_data, ensure_ascii=False)
    parsed = StudentProfile.model_validate_json(json_str)

    # Verify all list fields are non-empty
    assert len(parsed.strengths) >= 1, "strengths must be non-empty"
    assert len(parsed.interests) >= 1, "interests must be non-empty"
    assert len(parsed.personality_traits) >= 1, "personality_traits must be non-empty"
    assert len(parsed.academic_inclinations) >= 1, "academic_inclinations must be non-empty"

    # Verify summary is a non-empty string
    assert isinstance(parsed.summary, str), "summary must be a string"
    assert len(parsed.summary) >= 1, "summary must be non-empty"

    # Verify each item in lists is a non-empty string
    for field_name in ("strengths", "interests", "personality_traits", "academic_inclinations"):
        field_value = getattr(parsed, field_name)
        for item in field_value:
            assert isinstance(item, str), f"each item in {field_name} must be a string"
            assert len(item.strip()) > 0, f"each item in {field_name} must be non-empty"


@given(profile_data=student_profile_json_strategy)
@settings(max_examples=100)
def test_property_2_student_profile_roundtrip_preserves_data(
    profile_data: dict,
) -> None:
    """Property 2 (supplementary): StudentProfile roundtrip preserves all data.

    Parsing a valid profile JSON into StudentProfile and serializing it back
    SHALL preserve all original field values.

    Feature: orientation-mali, Property 2: Parsed StudentProfile contains all required fields
    """
    json_str = json.dumps(profile_data, ensure_ascii=False)
    parsed = StudentProfile.model_validate_json(json_str)

    # Roundtrip: model -> dict -> model
    roundtrip = StudentProfile.model_validate(parsed.model_dump())

    assert roundtrip.strengths == parsed.strengths
    assert roundtrip.interests == parsed.interests
    assert roundtrip.personality_traits == parsed.personality_traits
    assert roundtrip.academic_inclinations == parsed.academic_inclinations
    assert roundtrip.summary == parsed.summary


# --- Strategies for RecommendationSet ---

recommended_major_strategy = st.builds(
    RecommendedMajor,
    name=non_empty_french_text,
    description=non_empty_french_text,
    relevance=non_empty_french_text,
)

training_program_strategy = st.builds(
    TrainingProgram,
    name=non_empty_french_text,
    institution=non_empty_french_text,
    duration=non_empty_french_text,
)

school_strategy = st.builds(
    School,
    name=non_empty_french_text,
    location=non_empty_french_text,
    website=st.one_of(st.none(), non_empty_french_text),
    programs=st.lists(non_empty_french_text, min_size=1, max_size=5),
)

career_path_strategy = st.builds(
    CareerPath,
    title=non_empty_french_text,
    description=non_empty_french_text,
    sector=non_empty_french_text,
)

recommendation_set_strategy = st.builds(
    RecommendationSet,
    majors=st.lists(recommended_major_strategy, min_size=1, max_size=5),
    training_programs=st.lists(training_program_strategy, min_size=1, max_size=5),
    schools=st.lists(school_strategy, min_size=1, max_size=5),
    career_paths=st.lists(career_path_strategy, min_size=1, max_size=5),
)


# --- Property 3 Tests ---


@given(recommendation_set=recommendation_set_strategy)
@settings(max_examples=100)
def test_property_3_recommendation_set_structural_completeness(
    recommendation_set: RecommendationSet,
) -> None:
    """Property 3: RecommendationSet structural completeness.

    For any valid RecommendationSet, the majors, training_programs, schools,
    and career_paths lists SHALL each contain at least one element.

    Feature: orientation-mali, Property 3: RecommendationSet structural completeness
    """
    assert len(recommendation_set.majors) >= 1, "majors must contain at least one element"
    assert len(recommendation_set.training_programs) >= 1, (
        "training_programs must contain at least one element"
    )
    assert len(recommendation_set.schools) >= 1, "schools must contain at least one element"
    assert len(recommendation_set.career_paths) >= 1, (
        "career_paths must contain at least one element"
    )


@given(recommendation_set=recommendation_set_strategy)
@settings(max_examples=100)
def test_property_3_recommendation_set_json_roundtrip(
    recommendation_set: RecommendationSet,
) -> None:
    """Property 3 (supplementary): RecommendationSet JSON roundtrip preserves structure.

    Serializing a valid RecommendationSet to JSON and parsing it back SHALL
    produce an equivalent object with all lists still containing at least one element.

    Feature: orientation-mali, Property 3: RecommendationSet structural completeness
    """
    json_str = recommendation_set.model_dump_json()
    parsed = RecommendationSet.model_validate_json(json_str)

    # Structural completeness is preserved after roundtrip
    assert len(parsed.majors) >= 1, "majors must survive roundtrip"
    assert len(parsed.training_programs) >= 1, "training_programs must survive roundtrip"
    assert len(parsed.schools) >= 1, "schools must survive roundtrip"
    assert len(parsed.career_paths) >= 1, "career_paths must survive roundtrip"

    # Content equality
    assert parsed.majors == recommendation_set.majors
    assert parsed.training_programs == recommendation_set.training_programs
    assert parsed.schools == recommendation_set.schools
    assert parsed.career_paths == recommendation_set.career_paths
