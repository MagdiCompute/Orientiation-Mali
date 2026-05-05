"""Agents IA pour l'analyse de profil et la génération de recommandations."""

from src.orientation_mali.agents.orchestrator import (
    OrientationError,
    process_orientation,
)
from src.orientation_mali.agents.profile_agent import analyze_profile
from src.orientation_mali.agents.recommendation_agent import generate_recommendations

__all__ = [
    "analyze_profile",
    "generate_recommendations",
    "OrientationError",
    "process_orientation",
]
