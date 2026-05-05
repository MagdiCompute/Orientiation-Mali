"""Tests unitaires pour l'orchestrateur du pipeline d'orientation.

Vérifie la logique de retry, la génération de messages d'erreur en français
pour chaque scénario d'échec, et l'exécution réussie du pipeline avec des
agents mockés.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.orientation_mali.agents.orchestrator import (
    OrientationError,
    _ERROR_MESSAGES,
    _classify_error,
    _is_bedrock_service_error,
    _run_with_retry,
    process_orientation,
)
from src.orientation_mali.models.schemas import (
    CareerPath,
    ExamType,
    RecommendationSet,
    RecommendedMajor,
    School,
    StudentProfile,
    TrainingProgram,
)


# --- Fixtures ---


def _make_student_profile() -> StudentProfile:
    """Crée un StudentProfile valide pour les tests."""
    return StudentProfile(
        strengths=["Analyse logique", "Résolution de problèmes"],
        interests=["Mathématiques", "Informatique"],
        personality_traits=["Curieux", "Persévérant"],
        academic_inclinations=["Sciences exactes", "Technologie"],
        summary="Étudiant avec un profil scientifique marqué.",
    )


def _make_recommendation_set() -> RecommendationSet:
    """Crée un RecommendationSet valide pour les tests."""
    return RecommendationSet(
        majors=[
            RecommendedMajor(
                name="Sciences Exactes",
                description="Filière scientifique",
                relevance="Correspond aux points forts de l'étudiant",
            )
        ],
        training_programs=[
            TrainingProgram(
                name="Licence en Informatique",
                institution="USTTB",
                duration="3 ans",
            )
        ],
        schools=[
            School(
                name="USTTB",
                location="Bamako",
                website="https://www.usttb.edu.ml",
                programs=["Informatique", "Mathématiques"],
            )
        ],
        career_paths=[
            CareerPath(
                title="Ingénieur informatique",
                description="Conception et développement de systèmes",
                sector="Technologies de l'information",
            )
        ],
    )


SAMPLE_RESPONSES = {
    "q1": "Les mathématiques",
    "q2": "Résoudre des problèmes logiques",
    "q3": "Informatique et technologie",
    "q4": "Ingénieur",
    "q5": "Travailler seul avec concentration",
    "q6": "Sciences exactes",
    "q7": "Créer des applications",
    "q8": "Très motivé",
    "q9": "Analytique",
    "q10": "Contribuer à l'innovation technologique",
}


# --- Tests: _is_bedrock_service_error ---


class TestBedrockServiceErrorDetection:
    """Tests pour la détection des erreurs de service Bedrock."""

    def test_throttling_detected(self):
        """Une erreur de throttling est identifiée comme erreur de service."""
        exc = Exception("ThrottlingException: Rate exceeded")
        assert _is_bedrock_service_error(exc) is True

    def test_service_unavailable_detected(self):
        """Une erreur ServiceUnavailable est identifiée."""
        exc = Exception("ServiceUnavailableException")
        assert _is_bedrock_service_error(exc) is True

    def test_internal_server_error_detected(self):
        """Une erreur InternalServerError est identifiée."""
        exc = Exception("InternalServerError: something went wrong")
        assert _is_bedrock_service_error(exc) is True

    def test_timeout_detected(self):
        """Une erreur de timeout est identifiée comme erreur de service."""
        exc = Exception("Connection timeout after 30s")
        assert _is_bedrock_service_error(exc) is True

    def test_connection_error_detected(self):
        """Une erreur de connexion est identifiée comme erreur de service."""
        exc = Exception("Connection refused to endpoint")
        assert _is_bedrock_service_error(exc) is True

    def test_rate_exceeded_detected(self):
        """Une erreur 'too many requests' est identifiée."""
        exc = Exception("Too many requests")
        assert _is_bedrock_service_error(exc) is True

    def test_value_error_not_service_error(self):
        """Une ValueError standard n'est pas une erreur de service."""
        exc = ValueError("Invalid JSON format")
        assert _is_bedrock_service_error(exc) is False

    def test_generic_runtime_error_not_service_error(self):
        """Une RuntimeError générique n'est pas une erreur de service."""
        exc = RuntimeError("Agent failed to respond")
        assert _is_bedrock_service_error(exc) is False


# --- Tests: _classify_error ---


class TestErrorClassification:
    """Tests pour la classification des erreurs par étape du pipeline."""

    def test_runtime_error_classified_as_timeout_for_profile(self):
        """Une RuntimeError au stade 'profile' est classée comme profile_timeout."""
        exc = RuntimeError("Agent failed")
        assert _classify_error(exc, "profile") == "profile_timeout"

    def test_runtime_error_classified_as_timeout_for_recommendation(self):
        """Une RuntimeError au stade 'recommendation' est classée comme recommendation_timeout."""
        exc = RuntimeError("Agent failed")
        assert _classify_error(exc, "recommendation") == "recommendation_timeout"

    def test_value_error_classified_as_invalid_output_for_profile(self):
        """Une ValueError au stade 'profile' est classée comme profile_invalid_output."""
        exc = ValueError("Cannot parse JSON")
        assert _classify_error(exc, "profile") == "profile_invalid_output"

    def test_value_error_classified_as_invalid_output_for_recommendation(self):
        """Une ValueError au stade 'recommendation' est classée comme recommendation_invalid_output."""
        exc = ValueError("Cannot parse JSON")
        assert _classify_error(exc, "recommendation") == "recommendation_invalid_output"

    def test_bedrock_service_error_classified_as_service_unavailable(self):
        """Une erreur Bedrock est toujours classée comme service_unavailable."""
        exc = Exception("ServiceUnavailableException")
        assert _classify_error(exc, "profile") == "service_unavailable"
        assert _classify_error(exc, "recommendation") == "service_unavailable"

    def test_unknown_exception_defaults_to_timeout(self):
        """Une exception inconnue est classée par défaut comme timeout."""
        exc = TypeError("unexpected error")
        assert _classify_error(exc, "profile") == "profile_timeout"


# --- Tests: Retry logic (_run_with_retry) ---


class TestRetryLogic:
    """Tests pour la logique de retry avec backoff exponentiel."""

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    def test_success_on_first_attempt_no_retry(self, mock_sleep):
        """Si la première tentative réussit, pas de retry ni de sleep."""
        func = MagicMock(return_value="success")

        result = _run_with_retry(func, "profile")

        assert result == "success"
        func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    def test_success_on_second_attempt_after_retry(self, mock_sleep):
        """Si la première tentative échoue, retry après backoff et réussit."""
        func = MagicMock(side_effect=[RuntimeError("fail"), "success"])

        result = _run_with_retry(func, "profile")

        assert result == "success"
        assert func.call_count == 2
        mock_sleep.assert_called_once_with(2.0)

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    def test_raises_orientation_error_after_two_failures(self, mock_sleep):
        """Après deux échecs, lève OrientationError avec le bon message."""
        func = MagicMock(side_effect=[RuntimeError("fail1"), RuntimeError("fail2")])

        with pytest.raises(OrientationError) as exc_info:
            _run_with_retry(func, "profile")

        assert func.call_count == 2
        mock_sleep.assert_called_once_with(2.0)
        assert exc_info.value.stage == "profile"
        assert exc_info.value.message == _ERROR_MESSAGES["profile_timeout"]

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    def test_retry_with_value_error_classifies_as_invalid_output(self, mock_sleep):
        """Deux ValueError sont classées comme invalid_output."""
        func = MagicMock(side_effect=[ValueError("bad"), ValueError("bad")])

        with pytest.raises(OrientationError) as exc_info:
            _run_with_retry(func, "recommendation")

        assert exc_info.value.message == _ERROR_MESSAGES["recommendation_invalid_output"]

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    def test_retry_with_service_error_classifies_as_unavailable(self, mock_sleep):
        """Une erreur de service Bedrock est classée comme service_unavailable."""
        func = MagicMock(
            side_effect=[
                Exception("ServiceUnavailableException"),
                Exception("ServiceUnavailableException"),
            ]
        )

        with pytest.raises(OrientationError) as exc_info:
            _run_with_retry(func, "profile")

        assert exc_info.value.message == _ERROR_MESSAGES["service_unavailable"]

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    def test_retry_preserves_original_error(self, mock_sleep):
        """L'erreur originale est préservée dans OrientationError."""
        original = RuntimeError("original failure")
        func = MagicMock(side_effect=[original, original])

        with pytest.raises(OrientationError) as exc_info:
            _run_with_retry(func, "profile")

        assert exc_info.value.original_error is original


# --- Tests: OrientationError ---


class TestOrientationError:
    """Tests pour la classe OrientationError et sa conversion en ErrorResponse."""

    def test_to_error_response_structure(self):
        """to_error_response produit une ErrorResponse valide."""
        error = OrientationError(
            message="Message d'erreur test",
            stage="profile",
            original_error=RuntimeError("test"),
        )

        response = error.to_error_response()

        assert response.error is True
        assert response.message == "Message d'erreur test"
        assert response.retry_available is True
        assert response.missing_questions is None

    def test_error_message_is_str_representation(self):
        """Le message est aussi la représentation string de l'exception."""
        error = OrientationError(
            message="Une erreur est survenue",
            stage="recommendation",
        )
        assert str(error) == "Une erreur est survenue"


# --- Tests: Error message generation for each failure scenario ---


class TestErrorMessages:
    """Tests pour la génération de messages d'erreur en français."""

    def test_all_error_messages_are_in_french(self):
        """Tous les messages d'erreur sont en français (pas de texte anglais)."""
        english_indicators = ["error", "failed", "please", "try again", "unable"]
        for key, message in _ERROR_MESSAGES.items():
            for indicator in english_indicators:
                assert indicator not in message.lower(), (
                    f"Message '{key}' contient du texte anglais: '{indicator}'"
                )

    def test_profile_timeout_message(self):
        """Le message pour profile_timeout est correct."""
        expected = (
            "Une erreur est survenue lors de l'analyse de votre profil. "
            "Veuillez réessayer."
        )
        assert _ERROR_MESSAGES["profile_timeout"] == expected

    def test_profile_invalid_output_message(self):
        """Le message pour profile_invalid_output est correct."""
        expected = "Nous n'avons pas pu analyser vos réponses. Veuillez réessayer."
        assert _ERROR_MESSAGES["profile_invalid_output"] == expected

    def test_recommendation_timeout_message(self):
        """Le message pour recommendation_timeout est correct."""
        expected = (
            "Une erreur est survenue lors de la génération des recommandations. "
            "Veuillez réessayer."
        )
        assert _ERROR_MESSAGES["recommendation_timeout"] == expected

    def test_recommendation_invalid_output_message(self):
        """Le message pour recommendation_invalid_output est correct."""
        expected = "Nous n'avons pas pu générer vos recommandations. Veuillez réessayer."
        assert _ERROR_MESSAGES["recommendation_invalid_output"] == expected

    def test_service_unavailable_message(self):
        """Le message pour service_unavailable est correct."""
        expected = (
            "Le service est temporairement indisponible. "
            "Veuillez réessayer dans quelques minutes."
        )
        assert _ERROR_MESSAGES["service_unavailable"] == expected


# --- Tests: Successful pipeline execution with mocked agents ---


class TestSuccessfulPipeline:
    """Tests pour l'exécution réussie du pipeline avec agents mockés."""

    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_successful_pipeline_returns_orientation_result(
        self, mock_analyze, mock_recommend
    ):
        """Le pipeline complet retourne un OrientationResult valide."""
        profile = _make_student_profile()
        recommendations = _make_recommendation_set()
        mock_analyze.return_value = profile
        mock_recommend.return_value = recommendations

        result = process_orientation("BAC", SAMPLE_RESPONSES)

        assert result.profile == profile
        assert result.recommendations == recommendations
        assert result.exam_type == ExamType.BAC

    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_pipeline_passes_correct_args_to_profile_agent(
        self, mock_analyze, mock_recommend
    ):
        """Le pipeline passe exam_type et responses au Profile Agent."""
        mock_analyze.return_value = _make_student_profile()
        mock_recommend.return_value = _make_recommendation_set()

        process_orientation("DEF", SAMPLE_RESPONSES)

        mock_analyze.assert_called_once_with("DEF", SAMPLE_RESPONSES)

    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_pipeline_passes_profile_to_recommendation_agent(
        self, mock_analyze, mock_recommend
    ):
        """Le pipeline passe le profil généré au Recommendation Agent."""
        profile = _make_student_profile()
        mock_analyze.return_value = profile
        mock_recommend.return_value = _make_recommendation_set()

        process_orientation("BAC", SAMPLE_RESPONSES)

        mock_recommend.assert_called_once_with(profile, "BAC")

    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_pipeline_with_def_exam_type(self, mock_analyze, mock_recommend):
        """Le pipeline fonctionne avec le type d'examen DEF."""
        mock_analyze.return_value = _make_student_profile()
        mock_recommend.return_value = _make_recommendation_set()

        result = process_orientation("DEF", SAMPLE_RESPONSES)

        assert result.exam_type == ExamType.DEF


# --- Tests: Pipeline failure scenarios ---


class TestPipelineFailures:
    """Tests pour les scénarios d'échec du pipeline."""

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_profile_agent_failure_raises_orientation_error(
        self, mock_analyze, mock_sleep
    ):
        """Un échec du Profile Agent lève OrientationError après retry."""
        mock_analyze.side_effect = RuntimeError("Agent failed to produce output")

        with pytest.raises(OrientationError) as exc_info:
            process_orientation("BAC", SAMPLE_RESPONSES)

        assert exc_info.value.stage == "profile"
        assert "profil" in exc_info.value.message

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_recommendation_agent_failure_raises_orientation_error(
        self, mock_analyze, mock_recommend, mock_sleep
    ):
        """Un échec du Recommendation Agent lève OrientationError après retry."""
        mock_analyze.return_value = _make_student_profile()
        mock_recommend.side_effect = ValueError("Invalid output")

        with pytest.raises(OrientationError) as exc_info:
            process_orientation("BAC", SAMPLE_RESPONSES)

        assert exc_info.value.stage == "recommendation"
        assert "recommandations" in exc_info.value.message

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_bedrock_service_error_in_profile_stage(
        self, mock_analyze, mock_sleep
    ):
        """Une erreur de service Bedrock au stade profil donne le bon message."""
        mock_analyze.side_effect = Exception("ServiceUnavailableException")

        with pytest.raises(OrientationError) as exc_info:
            process_orientation("BAC", SAMPLE_RESPONSES)

        assert "temporairement indisponible" in exc_info.value.message

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_bedrock_service_error_in_recommendation_stage(
        self, mock_analyze, mock_recommend, mock_sleep
    ):
        """Une erreur de service Bedrock au stade recommandation donne le bon message."""
        mock_analyze.return_value = _make_student_profile()
        mock_recommend.side_effect = Exception("ThrottlingException: Rate exceeded")

        with pytest.raises(OrientationError) as exc_info:
            process_orientation("BAC", SAMPLE_RESPONSES)

        assert "temporairement indisponible" in exc_info.value.message

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_profile_agent_retried_once_before_failure(
        self, mock_analyze, mock_sleep
    ):
        """Le Profile Agent est appelé exactement 2 fois (1 tentative + 1 retry)."""
        mock_analyze.side_effect = RuntimeError("fail")

        with pytest.raises(OrientationError):
            process_orientation("BAC", SAMPLE_RESPONSES)

        assert mock_analyze.call_count == 2

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_recommendation_agent_not_called_if_profile_fails(
        self, mock_analyze, mock_recommend, mock_sleep
    ):
        """Le Recommendation Agent n'est pas appelé si le Profile Agent échoue."""
        mock_analyze.side_effect = RuntimeError("fail")

        with pytest.raises(OrientationError):
            process_orientation("BAC", SAMPLE_RESPONSES)

        mock_recommend.assert_not_called()

    @patch("src.orientation_mali.agents.orchestrator.time.sleep")
    @patch("src.orientation_mali.agents.orchestrator.generate_recommendations")
    @patch("src.orientation_mali.agents.orchestrator.analyze_profile")
    def test_profile_succeeds_on_retry_then_recommendation_called(
        self, mock_analyze, mock_recommend, mock_sleep
    ):
        """Si le Profile Agent réussit au retry, le Recommendation Agent est appelé."""
        profile = _make_student_profile()
        mock_analyze.side_effect = [RuntimeError("first fail"), profile]
        mock_recommend.return_value = _make_recommendation_set()

        result = process_orientation("BAC", SAMPLE_RESPONSES)

        assert result.profile == profile
        mock_recommend.assert_called_once()
