"""Module de validation des soumissions du questionnaire.

Ce module valide les réponses soumises par les étudiants et retourne
des messages d'erreur en français lorsque la soumission est invalide.
"""

from src.orientation_mali.models.questionnaire import QUESTION_IDS
from src.orientation_mali.models.schemas import ExamType, QuestionnaireSubmission

# Catalogue de messages d'erreur en français
MESSAGES = {
    "exam_type_invalid": "Veuillez sélectionner votre type d'examen (DEF ou BAC).",
    "empty_responses": "Veuillez répondre à toutes les questions avant de soumettre.",
    "missing_questions": "Veuillez répondre aux questions suivantes : {ids}.",
}


def validate_submission(
    data: dict,
) -> tuple[QuestionnaireSubmission | None, list[str]]:
    """Valide une soumission de questionnaire.

    Args:
        data: Dictionnaire contenant 'exam_type' et 'responses'.

    Returns:
        Un tuple (submission, errors) où submission est un objet
        QuestionnaireSubmission valide ou None, et errors est une liste
        de messages d'erreur en français (vide si la soumission est valide).
    """
    errors: list[str] = []

    # Valider le type d'examen
    exam_type_raw = data.get("exam_type", "")
    valid_exam_types = {e.value for e in ExamType}
    if exam_type_raw not in valid_exam_types:
        errors.append(MESSAGES["exam_type_invalid"])

    # Valider les réponses
    responses = data.get("responses", {})

    if not isinstance(responses, dict):
        errors.append(MESSAGES["empty_responses"])
        return None, errors

    # Vérifier les questions manquantes
    missing_ids = [qid for qid in QUESTION_IDS if qid not in responses]
    if missing_ids:
        ids_str = ", ".join(missing_ids)
        errors.append(MESSAGES["missing_questions"].format(ids=ids_str))

    # Vérifier les réponses vides
    empty_ids = [
        qid
        for qid in QUESTION_IDS
        if qid in responses and responses[qid].strip() == ""
    ]
    if empty_ids:
        errors.append(MESSAGES["empty_responses"])

    if errors:
        return None, errors

    # Construire l'objet validé
    submission = QuestionnaireSubmission(
        exam_type=ExamType(exam_type_raw),
        responses={qid: responses[qid] for qid in QUESTION_IDS},
    )
    return submission, []
