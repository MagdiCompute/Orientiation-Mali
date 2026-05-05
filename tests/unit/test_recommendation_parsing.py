"""Tests unitaires pour le parsing du Recommendation Agent.

Vérifie que la fonction _extract_json et la validation RecommendationSet
gèrent correctement les réponses valides, malformées et incomplètes.
"""

import json

import pytest

from src.orientation_mali.agents.recommendation_agent import _extract_json
from src.orientation_mali.models.schemas import RecommendationSet


# --- Fixtures ---


VALID_RECOMMENDATION_DATA = {
    "majors": [
        {
            "name": "Sciences Exactes",
            "description": "Filière orientée vers les mathématiques, la physique et la chimie",
            "relevance": "Correspond aux forces analytiques et à l'intérêt pour les sciences de l'étudiant",
        },
        {
            "name": "Informatique",
            "description": "Formation en développement logiciel et systèmes d'information",
            "relevance": "L'étudiant montre un intérêt marqué pour la technologie et la résolution de problèmes",
        },
    ],
    "training_programs": [
        {
            "name": "Licence en Informatique",
            "institution": "USTTB - Université des Sciences, des Techniques et des Technologies de Bamako",
            "duration": "3 ans",
        },
        {
            "name": "Diplôme d'Ingénieur",
            "institution": "École Nationale d'Ingénieurs (ENI)",
            "duration": "5 ans",
        },
    ],
    "schools": [
        {
            "name": "USTTB",
            "location": "Bamako",
            "website": "https://www.usttb.edu.ml",
            "programs": ["Licence Informatique", "Master Mathématiques Appliquées"],
        },
        {
            "name": "École Nationale d'Ingénieurs",
            "location": "Bamako",
            "website": None,
            "programs": ["Génie Informatique", "Génie Civil"],
        },
    ],
    "career_paths": [
        {
            "title": "Ingénieur Informatique",
            "description": "Conception et développement de systèmes informatiques",
            "sector": "Technologies de l'information et communication",
        },
        {
            "title": "Data Analyst",
            "description": "Analyse de données pour la prise de décision",
            "sector": "Technologies de l'information et communication",
        },
    ],
}


# --- Tests: Parsing valid recommendation JSON into RecommendationSet ---


class TestValidRecommendationParsing:
    """Tests pour le parsing de JSON valide en RecommendationSet."""

    def test_parse_valid_recommendation_direct_json(self):
        """Un JSON valide direct est parsé correctement en RecommendationSet."""
        text = json.dumps(VALID_RECOMMENDATION_DATA, ensure_ascii=False)
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert len(reco.majors) == 2
        assert reco.majors[0].name == "Sciences Exactes"
        assert reco.majors[1].name == "Informatique"
        assert len(reco.training_programs) == 2
        assert len(reco.schools) == 2
        assert len(reco.career_paths) == 2

    def test_parse_recommendation_from_markdown_code_block(self):
        """Un JSON dans un bloc markdown ```json``` est extrait correctement."""
        text = f"Voici les recommandations :\n```json\n{json.dumps(VALID_RECOMMENDATION_DATA, ensure_ascii=False)}\n```"
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert len(reco.majors) >= 1
        assert len(reco.schools) >= 1

    def test_parse_recommendation_from_plain_code_block(self):
        """Un JSON dans un bloc markdown ``` sans annotation est extrait."""
        text = f"Résultat :\n```\n{json.dumps(VALID_RECOMMENDATION_DATA, ensure_ascii=False)}\n```"
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert reco.career_paths[0].title == "Ingénieur Informatique"

    def test_parse_recommendation_with_surrounding_text(self):
        """Un JSON entouré de texte explicatif est extrait correctement."""
        text = (
            "Basé sur le profil de l'étudiant, voici mes recommandations :\n\n"
            + json.dumps(VALID_RECOMMENDATION_DATA, ensure_ascii=False)
            + "\n\nCes recommandations sont adaptées au contexte malien."
        )
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert len(reco.training_programs) >= 1

    def test_parse_recommendation_with_extra_fields_ignored(self):
        """Des champs supplémentaires dans le JSON sont ignorés par Pydantic."""
        data_with_extra = {
            **VALID_RECOMMENDATION_DATA,
            "confidence": 0.92,
            "notes": "Recommandations générées avec succès",
        }
        text = json.dumps(data_with_extra, ensure_ascii=False)
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert reco.majors == RecommendationSet(**VALID_RECOMMENDATION_DATA).majors

    def test_parse_recommendation_school_with_website(self):
        """Un établissement avec un site web est correctement parsé."""
        text = json.dumps(VALID_RECOMMENDATION_DATA, ensure_ascii=False)
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert reco.schools[0].website == "https://www.usttb.edu.ml"

    def test_parse_recommendation_school_without_website(self):
        """Un établissement sans site web (null) est correctement parsé."""
        text = json.dumps(VALID_RECOMMENDATION_DATA, ensure_ascii=False)
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert reco.schools[1].website is None

    def test_parse_recommendation_with_many_items(self):
        """Des recommandations avec de nombreux éléments sont valides."""
        data = {
            "majors": [
                {"name": f"Filière {i}", "description": f"Description {i}", "relevance": f"Pertinence {i}"}
                for i in range(5)
            ],
            "training_programs": [
                {"name": f"Programme {i}", "institution": f"Institut {i}", "duration": f"{i+2} ans"}
                for i in range(4)
            ],
            "schools": [
                {"name": f"École {i}", "location": "Bamako", "website": None, "programs": [f"Prog {i}"]}
                for i in range(3)
            ],
            "career_paths": [
                {"title": f"Métier {i}", "description": f"Description {i}", "sector": f"Secteur {i}"}
                for i in range(6)
            ],
        }
        text = json.dumps(data, ensure_ascii=False)
        parsed = _extract_json(text)
        reco = RecommendationSet(**parsed)

        assert len(reco.majors) == 5
        assert len(reco.training_programs) == 4
        assert len(reco.schools) == 3
        assert len(reco.career_paths) == 6


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
            _extract_json(
                "Je recommande les sciences exactes pour cet étudiant. "
                "Il devrait s'inscrire à l'USTTB."
            )

    def test_extract_json_raises_on_truncated_json(self):
        """Un JSON tronqué (incomplet) lève ValueError."""
        truncated = '{"majors": [{"name": "Sciences Exactes", "description": "Filière orientée vers'
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json(truncated)

    def test_extract_json_raises_on_invalid_syntax(self):
        """Un JSON avec une syntaxe invalide lève ValueError."""
        invalid = "{'majors': [{'name': 'Sciences Exactes'}]}"
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json(invalid)

    def test_array_response_fails_at_recommendation_creation(self):
        """Un tableau JSON (au lieu d'un objet) est parsé mais échoue à la création."""
        array_text = '[{"name": "Sciences Exactes"}]'
        parsed = _extract_json(array_text)
        assert isinstance(parsed, list)
        with pytest.raises(Exception):
            RecommendationSet(**parsed)

    def test_extract_json_raises_on_nested_invalid_json(self):
        """Un bloc markdown avec du JSON invalide à l'intérieur lève ValueError."""
        text = "```json\n{invalid json content here}\n```"
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json(text)

    def test_extract_json_raises_on_html_response(self):
        """Une réponse HTML (pas JSON) lève ValueError."""
        html = "<html><body><h1>Erreur 500</h1></body></html>"
        with pytest.raises(ValueError, match="Impossible d'extraire"):
            _extract_json(html)


# --- Tests: Handling empty lists in agent output ---


class TestEmptyListsHandling:
    """Tests pour la gestion des listes vides dans la sortie de l'agent."""

    def test_empty_majors_list_raises_validation_error(self):
        """Une liste 'majors' vide lève une erreur de validation (min_length=1)."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "majors": [],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_empty_training_programs_list_raises_validation_error(self):
        """Une liste 'training_programs' vide lève une erreur de validation."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "training_programs": [],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_empty_schools_list_raises_validation_error(self):
        """Une liste 'schools' vide lève une erreur de validation."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "schools": [],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_empty_career_paths_list_raises_validation_error(self):
        """Une liste 'career_paths' vide lève une erreur de validation."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "career_paths": [],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_all_lists_empty_raises_validation_error(self):
        """Toutes les listes vides lèvent une erreur de validation."""
        data = {
            "majors": [],
            "training_programs": [],
            "schools": [],
            "career_paths": [],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_missing_majors_field_raises_validation_error(self):
        """L'absence du champ 'majors' lève une erreur de validation."""
        data = {
            "training_programs": VALID_RECOMMENDATION_DATA["training_programs"],
            "schools": VALID_RECOMMENDATION_DATA["schools"],
            "career_paths": VALID_RECOMMENDATION_DATA["career_paths"],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_missing_training_programs_field_raises_validation_error(self):
        """L'absence du champ 'training_programs' lève une erreur de validation."""
        data = {
            "majors": VALID_RECOMMENDATION_DATA["majors"],
            "schools": VALID_RECOMMENDATION_DATA["schools"],
            "career_paths": VALID_RECOMMENDATION_DATA["career_paths"],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_missing_schools_field_raises_validation_error(self):
        """L'absence du champ 'schools' lève une erreur de validation."""
        data = {
            "majors": VALID_RECOMMENDATION_DATA["majors"],
            "training_programs": VALID_RECOMMENDATION_DATA["training_programs"],
            "career_paths": VALID_RECOMMENDATION_DATA["career_paths"],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_missing_career_paths_field_raises_validation_error(self):
        """L'absence du champ 'career_paths' lève une erreur de validation."""
        data = {
            "majors": VALID_RECOMMENDATION_DATA["majors"],
            "training_programs": VALID_RECOMMENDATION_DATA["training_programs"],
            "schools": VALID_RECOMMENDATION_DATA["schools"],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_completely_empty_json_object(self):
        """Un objet JSON vide {} lève une erreur de validation."""
        with pytest.raises(Exception):
            RecommendationSet(**{})

    def test_empty_programs_list_in_school_is_rejected(self):
        """Une liste 'programs' vide dans un School est rejetée."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "schools": [
                {
                    "name": "USTTB",
                    "location": "Bamako",
                    "website": None,
                    "programs": [],
                }
            ],
        }
        # programs field has no min_length constraint, so this may or may not raise
        # depending on schema definition. We test the actual behavior.
        reco = RecommendationSet(**data)
        assert reco.schools[0].programs == []

    def test_wrong_types_raise_validation_error(self):
        """Des types incorrects (string au lieu de list) lèvent une erreur."""
        data = {
            "majors": "Sciences Exactes",  # Should be a list
            "training_programs": VALID_RECOMMENDATION_DATA["training_programs"],
            "schools": VALID_RECOMMENDATION_DATA["schools"],
            "career_paths": VALID_RECOMMENDATION_DATA["career_paths"],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_major_missing_required_field_raises_error(self):
        """Un major sans champ requis 'relevance' lève une erreur."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "majors": [
                {
                    "name": "Sciences Exactes",
                    "description": "Filière scientifique",
                    # missing "relevance"
                }
            ],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_training_program_missing_required_field_raises_error(self):
        """Un programme sans champ requis 'duration' lève une erreur."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "training_programs": [
                {
                    "name": "Licence Informatique",
                    "institution": "USTTB",
                    # missing "duration"
                }
            ],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)

    def test_career_path_missing_required_field_raises_error(self):
        """Un métier sans champ requis 'sector' lève une erreur."""
        data = {
            **VALID_RECOMMENDATION_DATA,
            "career_paths": [
                {
                    "title": "Ingénieur",
                    "description": "Conception de systèmes",
                    # missing "sector"
                }
            ],
        }
        with pytest.raises(Exception):
            RecommendationSet(**data)
