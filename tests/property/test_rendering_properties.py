"""Tests de propriétés pour le rendu des recommandations.

Property 4: Rendered recommendations contain all category sections.
Validates: Requirements 5.2
"""

from hypothesis import given, settings
from hypothesis import strategies as st
from jinja2 import Environment, FileSystemLoader
from markupsafe import escape

from orientation_mali.models.schemas import (
    CareerPath,
    ExamType,
    OrientationResult,
    RecommendationSet,
    RecommendedMajor,
    School,
    StudentProfile,
    TrainingProgram,
)


# --- Template Environment ---

_env = Environment(
    loader=FileSystemLoader("src/orientation_mali/templates"),
    autoescape=True,
)
_results_template = _env.get_template("results.html")


# --- Strategies ---

non_empty_french_text = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        whitelist_characters="àâäéèêëïîôùûüÿçœæ '-",
    ),
    min_size=1,
    max_size=80,
).filter(lambda s: s.strip() != "")

student_profile_strategy = st.builds(
    StudentProfile,
    strengths=st.lists(non_empty_french_text, min_size=1, max_size=4),
    interests=st.lists(non_empty_french_text, min_size=1, max_size=4),
    personality_traits=st.lists(non_empty_french_text, min_size=1, max_size=4),
    academic_inclinations=st.lists(non_empty_french_text, min_size=1, max_size=4),
    summary=non_empty_french_text,
)

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
    website=st.one_of(st.none(), st.just("https://example.ml")),
    programs=st.lists(non_empty_french_text, min_size=1, max_size=3),
)

career_path_strategy = st.builds(
    CareerPath,
    title=non_empty_french_text,
    description=non_empty_french_text,
    sector=non_empty_french_text,
)

recommendation_set_strategy = st.builds(
    RecommendationSet,
    majors=st.lists(recommended_major_strategy, min_size=1, max_size=4),
    training_programs=st.lists(training_program_strategy, min_size=1, max_size=4),
    schools=st.lists(school_strategy, min_size=1, max_size=4),
    career_paths=st.lists(career_path_strategy, min_size=1, max_size=4),
)

orientation_result_strategy = st.builds(
    OrientationResult,
    profile=student_profile_strategy,
    recommendations=recommendation_set_strategy,
    exam_type=st.sampled_from(ExamType),
)


# --- Property Tests ---


@given(result=orientation_result_strategy)
@settings(max_examples=100)
def test_property_4_rendered_recommendations_contain_all_category_sections(
    result: OrientationResult,
) -> None:
    """Property 4: Rendered recommendations contain all category sections.

    For any valid RecommendationSet, the rendered HTML output SHALL contain
    distinct sections for majors, training programs, schools/universities,
    and career paths.

    Feature: orientation-mali, Property 4: Rendered recommendations contain all category sections
    """
    html = _results_template.render(result=result)

    # Verify all four recommendation section headings are present
    assert "Filières recommandées" in html, (
        "Rendered HTML must contain the 'Filières recommandées' section"
    )
    assert "Programmes de formation" in html, (
        "Rendered HTML must contain the 'Programmes de formation' section"
    )
    assert "Établissements" in html, (
        "Rendered HTML must contain the 'Établissements' section"
    )
    assert "Métiers" in html, (
        "Rendered HTML must contain the 'Métiers' section"
    )


@given(result=orientation_result_strategy)
@settings(max_examples=100)
def test_property_4_rendered_recommendations_contain_item_content(
    result: OrientationResult,
) -> None:
    """Property 4 (supplementary): Rendered HTML contains actual recommendation items.

    For any valid OrientationResult, the rendered HTML SHALL contain the name/title
    of each recommendation item from all four categories (HTML-escaped as appropriate).

    Feature: orientation-mali, Property 4: Rendered recommendations contain all category sections
    """
    html = _results_template.render(result=result)

    # Each major name must appear in the rendered output (accounting for HTML escaping)
    for major in result.recommendations.majors:
        escaped_name = str(escape(major.name))
        assert escaped_name in html, (
            f"Major name '{major.name}' (escaped: '{escaped_name}') must appear in rendered HTML"
        )

    # Each training program name must appear
    for program in result.recommendations.training_programs:
        escaped_name = str(escape(program.name))
        assert escaped_name in html, (
            f"Training program name '{program.name}' (escaped: '{escaped_name}') must appear in rendered HTML"
        )

    # Each school name must appear
    for school in result.recommendations.schools:
        escaped_name = str(escape(school.name))
        assert escaped_name in html, (
            f"School name '{school.name}' (escaped: '{escaped_name}') must appear in rendered HTML"
        )

    # Each career path title must appear
    for career in result.recommendations.career_paths:
        escaped_title = str(escape(career.title))
        assert escaped_title in html, (
            f"Career path title '{career.title}' (escaped: '{escaped_title}') must appear in rendered HTML"
        )


# --- Strategies for Property 5 ---

_url_strategy = st.from_regex(
    r"https://[a-z]{3,12}\.(ml|edu\.ml|org)", fullmatch=True
)

school_with_website_strategy = st.builds(
    School,
    name=non_empty_french_text,
    location=non_empty_french_text,
    website=_url_strategy,
    programs=st.lists(non_empty_french_text, min_size=1, max_size=3),
)

school_without_website_strategy = st.builds(
    School,
    name=non_empty_french_text,
    location=non_empty_french_text,
    website=st.none(),
    programs=st.lists(non_empty_french_text, min_size=1, max_size=3),
)


def _build_orientation_result_with_schools(schools: list) -> OrientationResult:
    """Helper to build a minimal OrientationResult with specific schools."""
    profile = StudentProfile(
        strengths=["Mathématiques"],
        interests=["Sciences"],
        personality_traits=["Curieux"],
        academic_inclinations=["Recherche"],
        summary="Profil test",
    )
    recommendations = RecommendationSet(
        majors=[RecommendedMajor(name="Informatique", description="Desc", relevance="Rel")],
        training_programs=[TrainingProgram(name="Prog", institution="Inst", duration="2 ans")],
        schools=schools,
        career_paths=[CareerPath(title="Ingénieur", description="Desc", sector="Tech")],
    )
    return OrientationResult(
        profile=profile,
        recommendations=recommendations,
        exam_type=ExamType.BAC,
    )


# --- Property 5 Tests ---


@given(school=school_with_website_strategy)
@settings(max_examples=100)
def test_property_5_school_website_link_rendered_when_available(
    school: School,
) -> None:
    """Property 5: School website links rendered when available.

    For any School with a non-null website field, the rendered HTML SHALL
    contain a navigable link (<a> tag) with that URL.

    Feature: orientation-mali, Property 5: School website links rendered when available
    """
    result = _build_orientation_result_with_schools([school])
    html = _results_template.render(result=result)

    assert f'href="{school.website}"' in html, (
        f"School with website '{school.website}' must have an <a> tag with that URL in rendered HTML"
    )
    assert f'<a href="{school.website}" class="school-link"' in html, (
        "The link must be an <a> tag with the 'school-link' CSS class"
    )
    assert "Visiter le site web" in html, (
        "The link must contain 'Visiter le site web' text"
    )


@given(school=school_without_website_strategy)
@settings(max_examples=100)
def test_property_5_no_link_rendered_when_website_absent(
    school: School,
) -> None:
    """Property 5: No link rendered when school website is absent.

    For any School with a null website field, no link SHALL be rendered
    for that school.

    Feature: orientation-mali, Property 5: School website links rendered when available
    """
    result = _build_orientation_result_with_schools([school])
    html = _results_template.render(result=result)

    assert "Visiter le site web" not in html, (
        "School without a website must NOT have 'Visiter le site web' link text"
    )
    assert 'class="school-link"' not in html, (
        "School without a website must NOT have an <a> element with 'school-link' class in the body"
    )


@given(
    schools_with=st.lists(school_with_website_strategy, min_size=1, max_size=3),
    schools_without=st.lists(school_without_website_strategy, min_size=1, max_size=3),
)
@settings(max_examples=100)
def test_property_5_mixed_schools_link_presence(
    schools_with: list,
    schools_without: list,
) -> None:
    """Property 5 (supplementary): Mixed schools render links only for those with websites.

    For a mix of Schools with and without website fields, the rendered HTML SHALL
    contain exactly as many link occurrences as there are schools with websites.

    Feature: orientation-mali, Property 5: School website links rendered when available
    """
    all_schools = schools_with + schools_without
    result = _build_orientation_result_with_schools(all_schools)
    html = _results_template.render(result=result)

    # Count occurrences of the link text — should match number of schools with websites
    link_count = html.count("Visiter le site web")
    assert link_count == len(schools_with), (
        f"Expected {len(schools_with)} 'Visiter le site web' links, found {link_count}"
    )

    # Each school with a website should have its URL in the HTML
    for school in schools_with:
        assert school.website in html, (
            f"School website URL '{school.website}' must appear in rendered HTML"
        )
