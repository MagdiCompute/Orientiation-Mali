"""Modèles de données Pydantic pour l'application."""

from src.orientation_mali.models.questionnaire import QUESTION_IDS, QUESTIONNAIRE
from src.orientation_mali.models.schemas import (
    CareerPath,
    ErrorResponse,
    ExamType,
    OrientationResult,
    Question,
    QuestionnaireSubmission,
    RecommendationSet,
    RecommendedMajor,
    School,
    StudentProfile,
    TrainingProgram,
)

__all__ = [
    "CareerPath",
    "ErrorResponse",
    "ExamType",
    "OrientationResult",
    "Question",
    "QUESTION_IDS",
    "QUESTIONNAIRE",
    "QuestionnaireSubmission",
    "RecommendationSet",
    "RecommendedMajor",
    "School",
    "StudentProfile",
    "TrainingProgram",
]
