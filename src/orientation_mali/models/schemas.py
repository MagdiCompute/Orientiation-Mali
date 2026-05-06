"""Schémas Pydantic pour l'application Orientation Mali.

Ce module définit tous les modèles de données utilisés dans l'application :
questionnaire, profil étudiant, recommandations, et réponses d'erreur.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ExamType(str, Enum):
    """Type d'examen préparé par l'étudiant."""

    DEF = "DEF"
    BAC = "BAC"


class Question(BaseModel):
    """Définition d'une question du questionnaire de profilage."""

    id: str
    text: str = Field(..., description="Texte de la question en français")
    question_type: Literal["open", "multiple_choice", "checkbox", "scale"]
    options: list[str] | None = Field(
        None, description="Options pour les questions à choix multiples"
    )


class QuestionnaireSubmission(BaseModel):
    """Soumission du questionnaire par un étudiant."""

    exam_type: ExamType
    responses: dict[str, str] = Field(
        ...,
        description="Correspondance entre l'identifiant de la question et la réponse",
        min_length=9,
        max_length=9,
    )


class StudentProfile(BaseModel):
    """Profil de l'étudiant généré par le Profile Agent."""

    strengths: list[str] = Field(
        ..., min_length=1, description="Points forts identifiés"
    )
    interests: list[str] = Field(
        ..., min_length=1, description="Centres d'intérêt"
    )
    personality_traits: list[str] = Field(
        ..., min_length=1, description="Traits de personnalité"
    )
    academic_inclinations: list[str] = Field(
        ..., min_length=1, description="Inclinations académiques"
    )
    summary: str = Field(
        ..., min_length=1, description="Résumé du profil en français"
    )


class RecommendedMajor(BaseModel):
    """Filière recommandée pour l'étudiant."""

    name: str = Field(..., description="Nom de la filière")
    description: str = Field(..., description="Description de la filière")
    relevance: str = Field(
        ..., description="Pourquoi cette filière convient à l'étudiant"
    )


class TrainingProgram(BaseModel):
    """Programme de formation recommandé."""

    name: str = Field(..., description="Nom du programme")
    institution: str = Field(
        ..., description="Établissement proposant le programme"
    )
    duration: str = Field(..., description="Durée de la formation")


class School(BaseModel):
    """Établissement scolaire ou universitaire au Mali."""

    name: str = Field(..., description="Nom de l'établissement")
    location: str = Field(..., description="Localisation au Mali")
    website: str | None = Field(None, description="Lien vers le site web")
    programs: list[str] = Field(..., description="Programmes proposés")


class CareerPath(BaseModel):
    """Métier ou parcours professionnel recommandé."""

    title: str = Field(..., description="Intitulé du métier")
    description: str = Field(..., description="Description du métier")
    sector: str = Field(..., description="Secteur d'activité")


class RecommendationSet(BaseModel):
    """Ensemble de recommandations d'orientation."""

    majors: list[RecommendedMajor] = Field(
        ..., min_length=1, description="Filières recommandées"
    )
    training_programs: list[TrainingProgram] = Field(
        ..., min_length=1, description="Programmes de formation"
    )
    schools: list[School] = Field(
        ..., min_length=1, description="Établissements recommandés"
    )
    career_paths: list[CareerPath] = Field(
        ..., min_length=1, description="Métiers et parcours professionnels"
    )


class OrientationResult(BaseModel):
    """Résultat complet de l'orientation combinant profil et recommandations."""

    profile: StudentProfile
    recommendations: RecommendationSet
    exam_type: ExamType


class ErrorResponse(BaseModel):
    """Réponse d'erreur avec message en français."""

    error: bool = True
    message: str = Field(..., description="Message d'erreur en français")
    retry_available: bool = True
    missing_questions: list[str] | None = Field(
        None, description="Questions manquantes pour les erreurs de validation"
    )
