"""Agent de recommandation pour la génération de suggestions d'orientation.

Ce module implémente le Recommendation Agent qui utilise le Strands Agents SDK
avec Amazon Nova Pro pour générer des recommandations personnalisées (filières,
programmes, établissements, métiers) basées sur le profil de l'étudiant et le
contexte éducatif malien.
"""

import json
import logging
import re

from strands import Agent
from strands.models.bedrock import BedrockModel

from src.orientation_mali.models.schemas import RecommendationSet, StudentProfile

logger = logging.getLogger(__name__)

RECOMMENDATION_SYSTEM_PROMPT = """\
Tu es un conseiller d'orientation scolaire expert du système éducatif malien. \
Ton rôle est de générer des recommandations d'orientation personnalisées pour un étudiant \
en te basant sur son profil et son type d'examen.

Contexte du système éducatif malien :

PARCOURS APRÈS LE DEF (Diplôme d'Études Fondamentales) :
- Entrée au lycée avec choix de série au Baccalauréat
- Séries disponibles : Sciences Exactes (SE), Sciences Biologiques (SB), \
Lettres (L), Sciences Humaines (SH), Sciences Économiques (SEC)
- Formation professionnelle et technique (CAP, BT)
- Instituts de Formation Professionnelle (IFP)

PARCOURS APRÈS LE BAC (Baccalauréat) :
- Universités publiques : Université des Sciences, des Techniques et des Technologies \
de Bamako (USTTB), Université des Sciences Sociales et de Gestion de Bamako (USSGB), \
Université des Lettres et des Sciences Humaines de Bamako (ULSHB)
- Grandes écoles : École Nationale d'Ingénieurs (ENI), Institut Polytechnique Rural (IPR/IFRA), \
École Normale Supérieure (ENSup), Institut Universitaire de Gestion (IUG)
- Écoles privées : Université Privée de Bamako, SUP'Management, ISTA
- Formations professionnelles supérieures

SÉRIES DU BAC ET DÉBOUCHÉS :
- Sciences Exactes (SE) : ingénierie, informatique, mathématiques, physique
- Sciences Biologiques (SB) : médecine, pharmacie, agronomie, biologie
- Lettres (L) : droit, journalisme, enseignement, traduction
- Sciences Humaines (SH) : sociologie, histoire, géographie, administration
- Sciences Économiques (SEC) : gestion, comptabilité, économie, commerce

SECTEURS D'ACTIVITÉ AU MALI :
- Agriculture et agro-industrie
- Mines et énergie
- Technologies de l'information et communication
- Santé et services sociaux
- Éducation et formation
- Commerce et entrepreneuriat
- Administration publique
- BTP et génie civil

Tu recevras le profil de l'étudiant et son type d'examen au format JSON.

Tu dois produire des recommandations JSON avec exactement cette structure :

{
  "majors": [
    {
      "name": "Nom de la filière",
      "description": "Description de la filière",
      "relevance": "Pourquoi cette filière convient à l'étudiant"
    }
  ],
  "training_programs": [
    {
      "name": "Nom du programme",
      "institution": "Établissement proposant le programme",
      "duration": "Durée de la formation"
    }
  ],
  "schools": [
    {
      "name": "Nom de l'établissement",
      "location": "Localisation au Mali",
      "website": "URL du site web ou null si non disponible",
      "programs": ["Liste des programmes proposés"]
    }
  ],
  "career_paths": [
    {
      "title": "Intitulé du métier",
      "description": "Description du métier",
      "sector": "Secteur d'activité"
    }
  ]
}

Règles importantes :
- Toutes les valeurs doivent être en français.
- Chaque liste doit contenir au minimum 2 éléments.
- Les recommandations doivent être adaptées au type d'examen (DEF ou BAC).
- Pour un étudiant DEF, recommande des séries de BAC et des formations techniques.
- Pour un étudiant BAC, recommande des programmes universitaires et des grandes écoles.
- Les établissements doivent être des institutions réelles au Mali.
- Les métiers doivent être réalistes et accessibles au Mali.
- Le champ "website" peut être null si le site web n'est pas connu.
- Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire avant ou après.
"""


def _create_recommendation_model() -> BedrockModel:
    """Crée et configure le modèle Bedrock pour le Recommendation Agent."""
    return BedrockModel(
        model_id="us.amazon.nova-pro-v1:0",
        region_name="us-east-1",
        temperature=0.5,
        max_tokens=4096,
    )


def _create_recommendation_agent() -> Agent:
    """Crée et configure l'instance du Recommendation Agent."""
    model = _create_recommendation_model()
    return Agent(
        model=model,
        system_prompt=RECOMMENDATION_SYSTEM_PROMPT,
    )


# Instance globale de l'agent (créée au premier appel)
_recommendation_agent: Agent | None = None


def _get_agent() -> Agent:
    """Retourne l'instance du Recommendation Agent, en la créant si nécessaire."""
    global _recommendation_agent
    if _recommendation_agent is None:
        _recommendation_agent = _create_recommendation_agent()
    return _recommendation_agent


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


def generate_recommendations(
    profile: StudentProfile, exam_type: str
) -> RecommendationSet:
    """Génère des recommandations d'orientation basées sur le profil étudiant.

    Args:
        profile: Profil structuré de l'étudiant généré par le Profile Agent.
        exam_type: Type d'examen préparé ("DEF" ou "BAC").

    Returns:
        RecommendationSet validé avec filières, programmes, établissements et métiers.

    Raises:
        ValueError: Si la réponse de l'agent ne peut pas être parsée en
            un RecommendationSet valide.
        RuntimeError: Si l'agent échoue à produire une réponse.
    """
    agent = _get_agent()

    # Formater l'entrée pour l'agent
    input_data = json.dumps(
        {"profile": profile.model_dump(), "exam_type": exam_type},
        ensure_ascii=False,
        indent=2,
    )

    logger.info(
        "Appel du Recommendation Agent pour un étudiant %s", exam_type
    )

    try:
        result = agent(input_data)
        response_text = str(result)
    except Exception as e:
        logger.error(
            "Erreur lors de l'appel au Recommendation Agent: %s", e
        )
        raise RuntimeError(
            "Nous n'avons pas pu générer vos recommandations. Veuillez réessayer."
        ) from e

    # Parser la réponse JSON
    try:
        recommendation_data = _extract_json(response_text)
    except ValueError as e:
        logger.error(
            "Réponse du Recommendation Agent non parseable: %s",
            response_text[:500],
        )
        raise ValueError(
            "Nous n'avons pas pu générer vos recommandations. Veuillez réessayer."
        ) from e

    # Valider avec Pydantic
    try:
        recommendations = RecommendationSet(**recommendation_data)
    except Exception as e:
        logger.error(
            "Données de recommandation invalides: %s — Erreur: %s",
            recommendation_data,
            e,
        )
        raise ValueError(
            "Nous n'avons pas pu générer vos recommandations. Veuillez réessayer."
        ) from e

    logger.info("Recommandations générées avec succès")
    return recommendations
