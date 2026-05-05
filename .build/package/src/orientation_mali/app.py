"""Application FastAPI pour Orientation Mali.

Ce module configure l'application web avec les routes, les templates Jinja2,
et les fichiers statiques.
"""

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.orientation_mali.agents.orchestrator import OrientationError, process_orientation
from src.orientation_mali.models.questionnaire import QUESTIONNAIRE
from src.orientation_mali.store import results_store
from src.orientation_mali.validation.validator import validate_submission

logger = logging.getLogger(__name__)

# Chemins vers les répertoires de templates et fichiers statiques
_BASE_DIR = Path(__file__).resolve().parent
_TEMPLATES_DIR = _BASE_DIR / "templates"
_STATIC_DIR = _BASE_DIR / "static"

app = FastAPI(
    title="Orientation Mali",
    description="Application d'orientation scolaire pour les étudiants maliens",
)

# Configuration des templates Jinja2
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# Montage des fichiers statiques
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Message d'erreur générique en français pour les erreurs inattendues
_GENERIC_ERROR_MESSAGE = (
    "Une erreur inattendue est survenue. Veuillez réessayer."
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Gestionnaire global pour les exceptions non gérées.

    Capture toute exception inattendue et affiche un message d'erreur
    en français à l'utilisateur.
    """
    logger.error("Erreur inattendue: %s", exc, exc_info=True)
    return templates.TemplateResponse(
        request,
        "error.html",
        context={
            "message": _GENERIC_ERROR_MESSAGE,
            "retry_available": True,
        },
        status_code=500,
    )


@app.get("/", response_class=HTMLResponse)
async def questionnaire_page(request: Request):
    """Affiche la page du questionnaire de profilage."""
    return templates.TemplateResponse(
        request,
        "questionnaire.html",
        context={"questions": QUESTIONNAIRE},
    )


@app.post("/api/submit")
async def submit_questionnaire(request: Request):
    """Traite la soumission du questionnaire.

    Valide les réponses, appelle le pipeline d'orientation,
    et redirige vers la page de résultats ou affiche les erreurs.
    """
    form_data = await request.form()

    # Extraire le type d'examen et les réponses du formulaire
    exam_type = form_data.get("exam_type", "")
    responses: dict[str, str] = {}
    for key, value in form_data.items():
        if key.startswith("q"):
            responses[key] = str(value)

    # Construire les données pour la validation
    submission_data = {
        "exam_type": exam_type,
        "responses": responses,
    }

    # Valider la soumission
    submission, errors = validate_submission(submission_data)

    if errors:
        return templates.TemplateResponse(
            request,
            "questionnaire.html",
            context={
                "questions": QUESTIONNAIRE,
                "errors": errors,
                "form_data": {"exam_type": exam_type, "responses": responses},
            },
            status_code=422,
        )

    # Appeler le pipeline d'orientation
    try:
        result = process_orientation(
            exam_type=submission.exam_type.value,
            responses=submission.responses,
        )
    except OrientationError as exc:
        error_response = exc.to_error_response()
        return templates.TemplateResponse(
            request,
            "error.html",
            context={
                "message": error_response.message,
                "retry_available": error_response.retry_available,
            },
        )

    # Stocker le résultat et rediriger vers la page de résultats
    result_id = str(uuid.uuid4())
    results_store.save(result_id, result)

    return RedirectResponse(
        url=f"/results?id={result_id}",
        status_code=303,
    )


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request, id: str = ""):
    """Affiche la page de résultats d'orientation."""
    result = results_store.get(id)

    if result is None:
        return templates.TemplateResponse(
            request,
            "error.html",
            context={
                "message": "Résultats introuvables. Veuillez remplir le questionnaire.",
                "retry_available": True,
            },
            status_code=404,
        )

    return templates.TemplateResponse(
        request,
        "results.html",
        context={"result": result},
    )
