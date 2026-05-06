"""Tests d'intégration pour le pipeline complet Orientation Mali.

Ces tests vérifient le fonctionnement de bout en bout de l'application :
- Soumission valide → page de résultats
- Soumission incomplète → erreurs de validation en français
- Page de résultats → toutes les sections de recommandations
- Erreur agent → page d'erreur avec bouton de retry

Requirements: 2.1, 2.2, 5.1, 5.2
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.orientation_mali.agents.orchestrator import OrientationError
from src.orientation_mali.app import app
from src.orientation_mali.models.schemas import (
    CareerPath,
    ExamType,
    OrientationResult,
    RecommendationSet,
    RecommendedMajor,
    School,
    StudentProfile,
    TrainingProgram,
)


@pytest.fixture
def client():
    """Client de test FastAPI."""
    return TestClient(app)


@pytest.fixture
def valid_form_data():
    """Données de formulaire valides avec les 10 réponses."""
    return {
        "exam_type": "BAC",
        "q1": "📐 Maths et Sciences",
        "q2": "🔬 Sciences et mathématiques",
        "q3": "📱 Créer du contenu sur les réseaux sociaux",
        "q4": "🧪 En pratiquant et en expérimentant",
        "q5": "5",
        "q6": "🎓 Poursuivre des études universitaires",
        "q7": "🧠 Analyste",
        "q8": "🧍 Seul(e)",
        "q9": "📚 L'éducation",
    }


@pytest.fixture
def mock_orientation_result():
    """Résultat d'orientation complet pour les mocks."""
    return OrientationResult(
        profile=StudentProfile(
            strengths=["Mathématiques", "Logique analytique"],
            interests=["Sciences", "Technologie"],
            personality_traits=["Méthodique", "Persévérant"],
            academic_inclinations=["Sciences exactes", "Ingénierie"],
            summary="Étudiant avec un profil scientifique fort, orienté vers les sciences exactes et l'ingénierie.",
        ),
        recommendations=RecommendationSet(
            majors=[
                RecommendedMajor(
                    name="Sciences Exactes",
                    description="Filière axée sur les mathématiques, la physique et la chimie",
                    relevance="Correspond à vos points forts en mathématiques et logique",
                )
            ],
            training_programs=[
                TrainingProgram(
                    name="Licence en Mathématiques Appliquées",
                    institution="Université des Sciences de Bamako",
                    duration="3 ans",
                )
            ],
            schools=[
                School(
                    name="Université des Sciences, des Techniques et des Technologies de Bamako",
                    location="Bamako, Mali",
                    website="https://www.usttb.edu.ml",
                    programs=["Mathématiques", "Physique", "Informatique"],
                )
            ],
            career_paths=[
                CareerPath(
                    title="Ingénieur en informatique",
                    description="Conception et développement de systèmes informatiques",
                    sector="Technologie",
                )
            ],
        ),
        exam_type=ExamType.BAC,
    )


class TestValidSubmission:
    """Tests pour la soumission valide du questionnaire."""

    def test_valid_submission_redirects_to_results(
        self, client, valid_form_data, mock_orientation_result
    ):
        """POST /api/submit avec soumission valide redirige vers la page de résultats.

        Requirements: 2.1, 5.1
        """
        with patch(
            "src.orientation_mali.app.process_orientation",
            return_value=mock_orientation_result,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
                follow_redirects=False,
            )

        # Vérifie la redirection 303 vers /results
        assert response.status_code == 303
        assert "/results" in response.headers["location"]

    def test_valid_submission_results_page_accessible(
        self, client, valid_form_data, mock_orientation_result
    ):
        """POST /api/submit suivi de GET /results affiche les résultats.

        Requirements: 2.1, 5.1
        """
        with patch(
            "src.orientation_mali.app.process_orientation",
            return_value=mock_orientation_result,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
                follow_redirects=True,
            )

        assert response.status_code == 200
        # Vérifie que la page de résultats est affichée
        assert "Résultats" in response.text or "résultats" in response.text


class TestIncompleteSubmission:
    """Tests pour la soumission incomplète du questionnaire."""

    def test_missing_responses_returns_validation_errors(self, client):
        """POST /api/submit avec réponses manquantes retourne des erreurs en français.

        Requirements: 2.2
        """
        # Soumettre seulement 3 réponses sur 10
        incomplete_data = {
            "exam_type": "BAC",
            "q1": "Mathématiques",
            "q2": "Sciences et mathématiques",
            "q3": "Lecture",
        }

        response = client.post("/api/submit", data=incomplete_data)

        assert response.status_code == 422
        # Vérifie que les erreurs sont en français
        content = response.text
        # Le message doit mentionner les questions manquantes
        assert "q4" in content or "q5" in content or "question" in content.lower()

    def test_missing_exam_type_returns_french_error(self, client):
        """POST /api/submit sans type d'examen retourne une erreur en français.

        Requirements: 2.2
        """
        data = {
            "q1": "📐 Maths et Sciences",
            "q2": "🔬 Sciences et mathématiques",
            "q3": "🔧 Réparer ou construire des choses",
            "q4": "🧪 En pratiquant et en expérimentant",
            "q5": "4",
            "q6": "🎓 Poursuivre des études universitaires",
            "q7": "🧠 Analyste",
            "q8": "👫 En équipe",
            "q9": "📚 L'éducation",
        }

        response = client.post("/api/submit", data=data)

        assert response.status_code == 422
        content = response.text
        # Vérifie que le message d'erreur est en français
        assert "examen" in content.lower() or "sélectionner" in content.lower()

    def test_empty_responses_returns_french_error(self, client):
        """POST /api/submit avec réponses vides retourne une erreur en français.

        Requirements: 2.2
        """
        data = {
            "exam_type": "DEF",
            "q1": "",
            "q2": "🔬 Sciences et mathématiques",
            "q3": "🤝 Aider les gens autour de moi",
            "q4": "👥 En travaillant en groupe",
            "q5": "3",
            "q6": "🛠️ Suivre une formation professionnelle courte",
            "q7": "❤️ Aidant",
            "q8": "👫 En équipe",
            "q9": "🏥 La santé",
        }

        response = client.post("/api/submit", data=data)

        assert response.status_code == 422
        content = response.text
        # Vérifie que le message est en français
        assert "répondre" in content.lower() or "question" in content.lower()

    def test_invalid_exam_type_returns_french_error(self, client):
        """POST /api/submit avec type d'examen invalide retourne une erreur en français.

        Requirements: 2.2
        """
        data = {
            "exam_type": "INVALID",
            "q1": "📐 Maths et Sciences",
            "q2": "🔬 Sciences et mathématiques",
            "q3": "🔧 Réparer ou construire des choses",
            "q4": "🧪 En pratiquant et en expérimentant",
            "q5": "4",
            "q6": "🎓 Poursuivre des études universitaires",
            "q7": "🧠 Analyste",
            "q8": "👫 En équipe",
            "q9": "📚 L'éducation",
        }

        response = client.post("/api/submit", data=data)

        assert response.status_code == 422
        content = response.text
        assert "DEF" in content or "BAC" in content


class TestResultsPage:
    """Tests pour la page de résultats."""

    def test_results_page_displays_all_recommendation_sections(
        self, client, valid_form_data, mock_orientation_result
    ):
        """La page de résultats affiche toutes les sections de recommandations.

        Requirements: 5.1, 5.2
        """
        with patch(
            "src.orientation_mali.app.process_orientation",
            return_value=mock_orientation_result,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
                follow_redirects=True,
            )

        assert response.status_code == 200
        content = response.text

        # Vérifie la présence des 4 sections de recommandations
        assert "Filières recommandées" in content
        assert "Programmes de formation" in content
        assert "Établissements" in content
        assert "Métiers" in content

    def test_results_page_displays_profile_summary(
        self, client, valid_form_data, mock_orientation_result
    ):
        """La page de résultats affiche le résumé du profil étudiant.

        Requirements: 5.1
        """
        with patch(
            "src.orientation_mali.app.process_orientation",
            return_value=mock_orientation_result,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
                follow_redirects=True,
            )

        assert response.status_code == 200
        content = response.text

        # Vérifie que le résumé du profil est affiché
        assert "profil scientifique fort" in content

    def test_results_page_displays_school_website_link(
        self, client, valid_form_data, mock_orientation_result
    ):
        """La page de résultats affiche les liens vers les sites web des écoles.

        Requirements: 5.2
        """
        with patch(
            "src.orientation_mali.app.process_orientation",
            return_value=mock_orientation_result,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
                follow_redirects=True,
            )

        assert response.status_code == 200
        content = response.text

        # Vérifie que le lien vers le site web est présent
        assert "https://www.usttb.edu.ml" in content
        assert "Visiter le site web" in content

    def test_results_page_displays_recommendation_details(
        self, client, valid_form_data, mock_orientation_result
    ):
        """La page de résultats affiche les détails des recommandations.

        Requirements: 5.2
        """
        with patch(
            "src.orientation_mali.app.process_orientation",
            return_value=mock_orientation_result,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
                follow_redirects=True,
            )

        assert response.status_code == 200
        content = response.text

        # Vérifie les détails des recommandations
        assert "Sciences Exactes" in content
        assert "Licence en Mathématiques Appliquées" in content
        assert "Université des Sciences" in content
        assert "Ingénieur en informatique" in content


class TestErrorPage:
    """Tests pour la page d'erreur lors d'une défaillance agent."""

    def test_agent_failure_displays_error_page_with_retry(
        self, client, valid_form_data
    ):
        """Erreur agent affiche la page d'erreur avec bouton de retry.

        Requirements: 2.1
        """
        error = OrientationError(
            message="Une erreur est survenue lors de l'analyse de votre profil. Veuillez réessayer.",
            stage="profile",
            original_error=RuntimeError("Agent timeout"),
        )

        with patch(
            "src.orientation_mali.app.process_orientation",
            side_effect=error,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
            )

        assert response.status_code == 200
        content = response.text

        # Vérifie que le message d'erreur est affiché en français
        assert "erreur" in content.lower()
        assert "réessayer" in content.lower() or "Réessayer" in content

        # Vérifie que le bouton de retry est présent
        assert "Réessayer" in content

    def test_recommendation_agent_failure_displays_error(
        self, client, valid_form_data
    ):
        """Erreur du Recommendation Agent affiche un message d'erreur approprié.

        Requirements: 2.1
        """
        error = OrientationError(
            message="Nous n'avons pas pu générer vos recommandations. Veuillez réessayer.",
            stage="recommendation",
            original_error=ValueError("Invalid JSON output"),
        )

        with patch(
            "src.orientation_mali.app.process_orientation",
            side_effect=error,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
            )

        assert response.status_code == 200
        content = response.text

        # Vérifie le message d'erreur spécifique
        assert "recommandations" in content.lower()
        assert "Réessayer" in content

    def test_service_unavailable_displays_maintenance_message(
        self, client, valid_form_data
    ):
        """Service indisponible affiche un message de maintenance en français.

        Requirements: 2.1
        """
        error = OrientationError(
            message="Le service est temporairement indisponible. Veuillez réessayer dans quelques minutes.",
            stage="profile",
            original_error=Exception("Service unavailable"),
        )

        with patch(
            "src.orientation_mali.app.process_orientation",
            side_effect=error,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
            )

        assert response.status_code == 200
        content = response.text

        # Vérifie le message de maintenance
        assert "temporairement indisponible" in content
        assert "Réessayer" in content

    def test_error_page_has_retry_link_to_home(self, client, valid_form_data):
        """La page d'erreur contient un lien de retry vers l'accueil.

        Requirements: 2.1
        """
        error = OrientationError(
            message="Une erreur est survenue.",
            stage="profile",
            original_error=RuntimeError("timeout"),
        )

        with patch(
            "src.orientation_mali.app.process_orientation",
            side_effect=error,
        ):
            response = client.post(
                "/api/submit",
                data=valid_form_data,
            )

        content = response.text

        # Vérifie que le lien de retry pointe vers l'accueil
        assert 'href="/"' in content


class TestQuestionnairePage:
    """Tests pour la page du questionnaire."""

    def test_questionnaire_page_loads(self, client):
        """GET / affiche la page du questionnaire.

        Requirements: 2.1
        """
        response = client.get("/")

        assert response.status_code == 200
        content = response.text

        # Vérifie que le formulaire est présent
        assert "questionnaire" in content.lower() or "form" in content.lower()
        # Vérifie que les options d'examen sont présentes
        assert "DEF" in content
        assert "BAC" in content
