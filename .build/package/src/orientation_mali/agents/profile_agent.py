"""Agent de profilage pour l'analyse des réponses au questionnaire.

Ce module implémente le Profile Agent qui utilise le Strands Agents SDK
avec Amazon Nova Pro pour analyser les réponses d'un étudiant et générer
un profil structuré (StudentProfile).
"""

import json
import logging
import re

from strands import Agent
from strands.models.bedrock import BedrockModel

from src.orientation_mali.models.schemas import StudentProfile

logger = logging.getLogger(__name__)

PROFILE_SYSTEM_PROMPT = """\
Tu es un conseiller d'orientation scolaire expert du système éducatif malien. \
Ton rôle est d'analyser les réponses d'un étudiant à un questionnaire de profilage \
et de produire un profil structuré en JSON.

Tu recevras les réponses de l'étudiant au format JSON avec son type d'examen (DEF ou BAC) \
et ses réponses aux 10 questions du questionnaire.

Tu dois analyser ces réponses et produire un profil JSON avec exactement cette structure :

{
  "strengths": ["liste de points forts identifiés, minimum 2 éléments"],
  "interests": ["liste de centres d'intérêt, minimum 2 éléments"],
  "personality_traits": ["liste de traits de personnalité, minimum 2 éléments"],
  "academic_inclinations": ["liste d'inclinations académiques, minimum 2 éléments"],
  "summary": "Un résumé en français du profil de l'étudiant en 2-3 phrases."
}

Règles importantes :
- Toutes les valeurs doivent être en français.
- Chaque liste doit contenir au minimum 2 éléments.
- Le résumé doit être une phrase complète et informative.
- Base ton analyse uniquement sur les réponses fournies.
- Adapte ton analyse au niveau de l'étudiant (DEF = collège, BAC = lycée).
- Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire avant ou après.
"""


def _create_profile_model() -> BedrockModel:
    """Crée et configure le modèle Bedrock pour le Profile Agent."""
    return BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.3,
        max_tokens=2048,
    )


def _create_profile_agent() -> Agent:
    """Crée et configure l'instance du Profile Agent."""
    model = _create_profile_model()
    return Agent(
        model=model,
        system_prompt=PROFILE_SYSTEM_PROMPT,
    )


# Instance globale de l'agent (créée au premier appel)
_profile_agent: Agent | None = None


def _get_agent() -> Agent:
    """Retourne l'instance du Profile Agent, en la créant si nécessaire."""
    global _profile_agent
    if _profile_agent is None:
        _profile_agent = _create_profile_agent()
    return _profile_agent


def _extract_json(text: str) -> dict:
    """Extrait un objet JSON depuis la réponse textuelle de l'agent.

    Tente d'abord un parsing direct, puis cherche un bloc JSON dans le texte.

    Args:
        text: Texte brut de la réponse de l'agent.

    Returns:
        Dictionnaire Python extrait du JSON.

    Raises:
        ValueError: Si aucun JSON valide n'est trouvé dans la réponse.
    """
    # Tentative de parsing direct
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Chercher un bloc JSON entre accolades
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Chercher un bloc de code markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Impossible d'extraire un JSON valide de la réponse de l'agent."
    )


def analyze_profile(exam_type: str, responses: dict) -> StudentProfile:
    """Analyse les réponses au questionnaire et génère un profil étudiant.

    Args:
        exam_type: Type d'examen préparé ("DEF" ou "BAC").
        responses: Dictionnaire des réponses (question_id -> réponse).

    Returns:
        StudentProfile validé avec les champs structurés.

    Raises:
        ValueError: Si la réponse de l'agent ne peut pas être parsée en
            un StudentProfile valide.
        RuntimeError: Si l'agent échoue à produire une réponse.
    """
    agent = _get_agent()

    # Formater l'entrée pour l'agent
    input_data = json.dumps(
        {"exam_type": exam_type, "responses": responses},
        ensure_ascii=False,
        indent=2,
    )

    logger.info("Appel du Profile Agent pour un étudiant %s", exam_type)

    try:
        result = agent(input_data)
        response_text = str(result)
    except Exception as e:
        logger.error("Erreur lors de l'appel au Profile Agent: %s", e)
        raise RuntimeError(
            "Nous n'avons pas pu analyser vos réponses. Veuillez réessayer."
        ) from e

    # Parser la réponse JSON
    try:
        profile_data = _extract_json(response_text)
    except ValueError as e:
        logger.error(
            "Réponse du Profile Agent non parseable: %s", response_text[:500]
        )
        raise ValueError(
            "Nous n'avons pas pu analyser vos réponses. Veuillez réessayer."
        ) from e

    # Valider avec Pydantic
    try:
        profile = StudentProfile(**profile_data)
    except Exception as e:
        logger.error(
            "Données du profil invalides: %s — Erreur: %s", profile_data, e
        )
        raise ValueError(
            "Nous n'avons pas pu analyser vos réponses. Veuillez réessayer."
        ) from e

    logger.info("Profil étudiant généré avec succès")
    return profile
