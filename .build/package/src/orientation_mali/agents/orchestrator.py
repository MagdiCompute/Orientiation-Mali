"""Orchestrateur pour le pipeline d'orientation.

Ce module chaîne le Profile Agent et le Recommendation Agent,
avec gestion des erreurs et logique de retry automatique.
"""

import logging
import time

from src.orientation_mali.agents.profile_agent import analyze_profile
from src.orientation_mali.agents.recommendation_agent import generate_recommendations
from src.orientation_mali.models.schemas import (
    ErrorResponse,
    ExamType,
    OrientationResult,
)

logger = logging.getLogger(__name__)

# Messages d'erreur en français pour chaque scénario
_ERROR_MESSAGES = {
    "profile_timeout": (
        "Une erreur est survenue lors de l'analyse de votre profil. "
        "Veuillez réessayer."
    ),
    "profile_invalid_output": (
        "Nous n'avons pas pu analyser vos réponses. Veuillez réessayer."
    ),
    "recommendation_timeout": (
        "Une erreur est survenue lors de la génération des recommandations. "
        "Veuillez réessayer."
    ),
    "recommendation_invalid_output": (
        "Nous n'avons pas pu générer vos recommandations. Veuillez réessayer."
    ),
    "service_unavailable": (
        "Le service est temporairement indisponible. "
        "Veuillez réessayer dans quelques minutes."
    ),
}

# Délai de base pour le backoff exponentiel (en secondes)
_RETRY_DELAY_SECONDS = 2.0


def _is_bedrock_service_error(exc: BaseException) -> bool:
    """Détermine si l'exception est une erreur de service Bedrock."""
    error_msg = str(exc).lower()
    service_indicators = [
        "throttling",
        "serviceunavailable",
        "service unavailable",
        "internalservererror",
        "internal server error",
        "too many requests",
        "rate exceeded",
        "endpoint",
        "connection",
        "timeout",
    ]
    return any(indicator in error_msg for indicator in service_indicators)


def _classify_error(exc: BaseException, stage: str) -> str:
    """Classifie une exception et retourne la clé du message d'erreur approprié.

    Args:
        exc: L'exception levée.
        stage: Étape du pipeline ("profile" ou "recommendation").

    Returns:
        Clé du message d'erreur dans _ERROR_MESSAGES.
    """
    if _is_bedrock_service_error(exc):
        return "service_unavailable"

    if isinstance(exc, RuntimeError):
        return f"{stage}_timeout"

    if isinstance(exc, ValueError):
        return f"{stage}_invalid_output"

    # Par défaut, traiter comme un timeout/erreur réseau
    return f"{stage}_timeout"


def _run_with_retry(func, stage: str):
    """Exécute une fonction avec une seule tentative de retry.

    Implémente un backoff exponentiel de 2 secondes entre les tentatives.

    Args:
        func: Callable sans argument à exécuter.
        stage: Étape du pipeline ("profile" ou "recommendation") pour
            la classification des erreurs.

    Returns:
        Le résultat de func() en cas de succès.

    Raises:
        OrientationError: Si les deux tentatives échouent.
    """
    last_exception: BaseException | None = None

    for attempt in range(2):  # Tentative initiale + 1 retry
        try:
            return func()
        except Exception as exc:
            last_exception = exc
            logger.warning(
                "Tentative %d/%d échouée pour %s: %s",
                attempt + 1,
                2,
                stage,
                exc,
            )
            if attempt == 0:
                # Backoff exponentiel avant le retry
                time.sleep(_RETRY_DELAY_SECONDS)

    # Les deux tentatives ont échoué
    error_key = _classify_error(last_exception, stage)
    raise OrientationError(
        message=_ERROR_MESSAGES[error_key],
        stage=stage,
        original_error=last_exception,
    )


class OrientationError(Exception):
    """Erreur survenue pendant le pipeline d'orientation.

    Attributes:
        message: Message d'erreur en français destiné à l'utilisateur.
        stage: Étape du pipeline où l'erreur s'est produite.
        original_error: Exception d'origine.
    """

    def __init__(
        self,
        message: str,
        stage: str,
        original_error: BaseException | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.original_error = original_error

    def to_error_response(self) -> ErrorResponse:
        """Convertit l'erreur en réponse structurée."""
        return ErrorResponse(
            error=True,
            message=self.message,
            retry_available=True,
        )


def process_orientation(exam_type: str, responses: dict) -> OrientationResult:
    """Exécute le pipeline complet d'orientation.

    Chaîne le Profile Agent et le Recommendation Agent avec retry
    automatique et gestion des erreurs.

    Args:
        exam_type: Type d'examen préparé ("DEF" ou "BAC").
        responses: Dictionnaire des réponses (question_id -> réponse).

    Returns:
        OrientationResult contenant le profil et les recommandations.

    Raises:
        OrientationError: Si le pipeline échoue après les tentatives de retry.
            Contient un message en français et peut être converti en ErrorResponse.
    """
    logger.info(
        "Démarrage du pipeline d'orientation pour un étudiant %s", exam_type
    )

    # Étape 1 : Analyse du profil avec retry
    student_profile = _run_with_retry(
        func=lambda: analyze_profile(exam_type, responses),
        stage="profile",
    )

    logger.info("Profil généré, passage au Recommendation Agent")

    # Étape 2 : Génération des recommandations avec retry
    recommendations = _run_with_retry(
        func=lambda: generate_recommendations(student_profile, exam_type),
        stage="recommendation",
    )

    logger.info("Pipeline d'orientation terminé avec succès")

    return OrientationResult(
        profile=student_profile,
        recommendations=recommendations,
        exam_type=ExamType(exam_type),
    )
