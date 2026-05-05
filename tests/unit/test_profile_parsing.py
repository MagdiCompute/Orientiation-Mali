"""Tests unitaires pour le parsing du Profile Agent.

Vérifie que la fonction _extract_json et la validation StudentProfile
gèrent correctement les réponses valides, malformées et incomplètes.
"""

import json

import pytest

from src.orientation_mali.agents.profile_agent import _extract_json
from src.orientation_mali.models.schemas import StudentProfile


# --- Fixtures ---


VALID_PROFILE_DATA = {
    "strengths": ["Analyse logique", "Résolution de problèmes"],
    "interests": ["Mathématiques", "Informatique"],
    "personality_traits": ["Curieux", "Persévérant"],
    "academic_inclinations": ["Sciences exactes", "Technologie"],
    "summary": "Étudiant avec un profil scientifique marqué, orienté vers les sciences exactes et la technologie.",
}


# --- Tests: Parsing valid profile JSON into StudentProfile ---


class TestValidProfileParsing:
    """Tests pour le parsing de JSON valide en StudentProfile."""

    def test_parse_valid_profile_direct_json(self):
        """Un JSON valide direct est parsé correctement en StudentProfile."""
        text = json.dumps(VALID_PROFILE_DATA, ensure_ascii=False)
        parsed = _extract_json(text)
        profile = StudentProfile(**parsed)

        assert profile.strengths == ["Analyse logique", "Résolution de problèmes"]
        assert profile.interests == ["Mathématiques", "Informatique"]
        assert profile.personality_traits == ["Curieux", "Persévérant"]
        assert profile.academic_inclinations == ["Sciences exactes", "Technologie"]
        assert "scientifique" in profile.summary

    def test_parse_profile_from_markdown_code_block(self):
        """Un JSON dans un bloc markdown ```json``` est extrait correctement."""
        text = f"Voici le profil :\n```json\n{json.dumps(VALID_PROFILE_DATA, ensure_ascii=False)}\n```"
        parsed = _extract_json(text)
        profile = StudentProfile(**parsed)

        assert len(profile.strengths) == 2
        assert len(profile.interests) == 2

    def test_parse_profile_from_plain_code_block(self):
        """Un JSON dans un bloc markdown ``` sans annotation est extrait."""
        text = f"Résultat :\n```\n{json.dumps(VALID_PROFILE_DATA, ensure_ascii=False)}\n```"
        parsed = _extract_json(text)
        profile = StudentProfile(**parsed)

        assert profile.summary != ""

    def test_parse_profile_with_surrounding_text(self):
        """Un JSON entouré de texte explicatif est extrait correctement."""
        text = (
            "D'après l'analyse des réponses, voici le profil de l'étudiant :\n\n"
            + json.dumps(VALID_PROFILE_DATA, ensure_ascii=False)
            + "\n\nCe profil montre un intérêt marqué pour les sciences."
        )
        parsed = _extract_json(text)
        profile = StudentProfile(**parsed)

        assert len(profile.academic_inclinations) >= 1

    def test_parse_profile_with_extra_fields_ignored(self):
        """Des champs supplémentaires dans le JSON sont ignorés par Pydantic."""
        data_with_extra = {
            **VALID_PROFILE_DATA,
            "extra_field": "valeur inattendue",
            "confidence_score": 0.95,
        }
        text = json.dumps(data_with_extra, ensure_ascii=False)
        parsed = _extract_json(text)
        profile = StudentProfile(**parsed)

        assert profile.strengths == VALID_PROFILE_DATA["strengths"]

    def test_parse_profile_with_many_items(self):
        """Un profil avec de nombreux éléments dans les listes est valide."""
        data = {
            "strengths": ["Force 1", "Force 2", "Force 3", "Force 4", "Force 5"],
            "interests": ["Intérêt 1", "Intérêt 2", "Intérêt 3"],
            "personality_traits": ["Trait 1", "Trait 2", "Trait 3", "Trait 4"],
            "academic_inclinations": ["Incl 1", "Incl 2"],
            "summary": "Un étudiant polyvalent avec de nombreuses compétences.",
        }
        text = json.dumps(data, ensure_ascii=False)
        parsed = _extract_json(text)
        profile = StudentProfile(**parsed)

        assert len(profile.strengths) == 5
        assert len(profile.personality_traits) == 4


# --- Tests: Handling malformed JSON responses ---


class TestMalformedJsonHandling:
    """Tests pour la gestion des réponses JSON malformées."""

    def test_extract_json_raises_on_empty_string(self):
        """Une chaîne vide lève ValueError."""
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json("")

    def test_extract_json_raises_on_plain_text(self):
        """Du texte sans JSON lève ValueError."""
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json("Je suis un conseiller d'orientation et voici mon analyse.")

    def test_extract_json_raises_on_truncated_json(self):
        """Un JSON tronqué (incomplet) lève ValueError."""
        truncated = '{"strengths": ["Analyse logique", "Résolution de'
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json(truncated)

    def test_extract_json_raises_on_invalid_syntax(self):
        """Un JSON avec une syntaxe invalide lève ValueError."""
        invalid = "{'strengths': ['single quotes are invalid']}"
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json(invalid)

    def test_array_response_fails_at_profile_creation(self):
        """Un tableau JSON (au lieu d'un objet) est parsé mais échoue à la création du profil."""
        array_text = '["item1", "item2", "item3"]'
        # _extract_json parses it successfully (valid JSON), but it's a list not a dict
        parsed = _extract_json(array_text)
        assert isinstance(parsed, list)
        with pytest.raises(Exception):
            StudentProfile(**parsed)

    def test_extract_json_raises_on_nested_invalid_json(self):
        """Un bloc markdown avec du JSON invalide à l'intérieur lève ValueError."""
        text = "```json\n{invalid json content here}\n```"
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json(text)


# --- Tests: Handling missing fields in agent output ---


class TestMissingFieldsHandling:
    """Tests pour la gestion des champs manquants dans la sortie de l'agent."""

    def test_missing_strengths_raises_validation_error(self):
        """L'absence du champ 'strengths' lève une erreur de validation."""
        data = {
            "interests": ["Mathématiques"],
            "personality_traits": ["Curieux"],
            "academic_inclinations": ["Sciences"],
            "summary": "Résumé du profil.",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_missing_interests_raises_validation_error(self):
        """L'absence du champ 'interests' lève une erreur de validation."""
        data = {
            "strengths": ["Analyse"],
            "personality_traits": ["Curieux"],
            "academic_inclinations": ["Sciences"],
            "summary": "Résumé du profil.",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_missing_personality_traits_raises_validation_error(self):
        """L'absence du champ 'personality_traits' lève une erreur de validation."""
        data = {
            "strengths": ["Analyse"],
            "interests": ["Mathématiques"],
            "academic_inclinations": ["Sciences"],
            "summary": "Résumé du profil.",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_missing_academic_inclinations_raises_validation_error(self):
        """L'absence du champ 'academic_inclinations' lève une erreur de validation."""
        data = {
            "strengths": ["Analyse"],
            "interests": ["Mathématiques"],
            "personality_traits": ["Curieux"],
            "summary": "Résumé du profil.",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_missing_summary_raises_validation_error(self):
        """L'absence du champ 'summary' lève une erreur de validation."""
        data = {
            "strengths": ["Analyse"],
            "interests": ["Mathématiques"],
            "personality_traits": ["Curieux"],
            "academic_inclinations": ["Sciences"],
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_empty_strengths_list_raises_validation_error(self):
        """Une liste 'strengths' vide lève une erreur de validation (min_length=1)."""
        data = {
            "strengths": [],
            "interests": ["Mathématiques"],
            "personality_traits": ["Curieux"],
            "academic_inclinations": ["Sciences"],
            "summary": "Résumé du profil.",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_empty_summary_raises_validation_error(self):
        """Un résumé vide lève une erreur de validation (min_length=1)."""
        data = {
            "strengths": ["Analyse"],
            "interests": ["Mathématiques"],
            "personality_traits": ["Curieux"],
            "academic_inclinations": ["Sciences"],
            "summary": "",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_null_values_in_lists_are_rejected(self):
        """Des valeurs None dans les listes sont rejetées."""
        data = {
            "strengths": [None, "Analyse"],
            "interests": ["Mathématiques"],
            "personality_traits": ["Curieux"],
            "academic_inclinations": ["Sciences"],
            "summary": "Résumé du profil.",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)

    def test_completely_empty_json_object(self):
        """Un objet JSON vide {} lève une erreur de validation."""
        with pytest.raises(Exception):
            StudentProfile(**{})

    def test_wrong_types_raise_validation_error(self):
        """Des types incorrects (string au lieu de list) lèvent une erreur."""
        data = {
            "strengths": "Analyse logique",  # Should be a list
            "interests": ["Mathématiques"],
            "personality_traits": ["Curieux"],
            "academic_inclinations": ["Sciences"],
            "summary": "Résumé du profil.",
        }
        with pytest.raises(Exception):
            StudentProfile(**data)
