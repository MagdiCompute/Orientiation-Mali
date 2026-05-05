"""Point d'entrée de l'application Orientation Mali.

Ce module sert de point d'entrée pour uvicorn. Il importe l'application
FastAPI configurée et permet de lancer le serveur avec :

    uvicorn src.orientation_mali.main:app --reload

Ou directement :

    python -m src.orientation_mali.main
"""

import uvicorn

from src.orientation_mali.app import app

__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run(
        "src.orientation_mali.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
