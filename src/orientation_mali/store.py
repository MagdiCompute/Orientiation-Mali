"""Module de stockage des résultats d'orientation.

Utilise DynamoDB en production (Lambda) et un dictionnaire en mémoire
pour le développement local.

La variable d'environnement RESULTS_TABLE_NAME détermine le comportement :
- Si définie : utilise DynamoDB avec le nom de table spécifié
- Si absente : utilise le stockage en mémoire (développement local)
"""

import json
import logging
import os
import time
from typing import Protocol

from src.orientation_mali.models.schemas import OrientationResult

logger = logging.getLogger(__name__)

# TTL pour les résultats : 1 heure (suffisant pour que l'étudiant consulte)
_RESULT_TTL_SECONDS = 3600


class ResultStore(Protocol):
    """Interface pour le stockage des résultats."""

    def save(self, result_id: str, result: OrientationResult) -> None:
        """Sauvegarde un résultat d'orientation."""
        ...

    def get(self, result_id: str) -> OrientationResult | None:
        """Récupère un résultat par son ID. Retourne None si introuvable."""
        ...


class InMemoryStore:
    """Stockage en mémoire pour le développement local."""

    def __init__(self) -> None:
        self._store: dict[str, OrientationResult] = {}

    def save(self, result_id: str, result: OrientationResult) -> None:
        self._store[result_id] = result

    def get(self, result_id: str) -> OrientationResult | None:
        return self._store.get(result_id)


class DynamoDBStore:
    """Stockage DynamoDB pour la production (Lambda).

    Les résultats sont sérialisés en JSON et stockés avec un TTL
    pour nettoyage automatique.
    """

    def __init__(self, table_name: str) -> None:
        import boto3

        self._table_name = table_name
        self._dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self._table = self._dynamodb.Table(table_name)

    def save(self, result_id: str, result: OrientationResult) -> None:
        ttl = int(time.time()) + _RESULT_TTL_SECONDS
        self._table.put_item(
            Item={
                "id": result_id,
                "result": result.model_dump_json(),
                "ttl": ttl,
            }
        )
        logger.info("Résultat %s sauvegardé dans DynamoDB", result_id)

    def get(self, result_id: str) -> OrientationResult | None:
        response = self._table.get_item(Key={"id": result_id})
        item = response.get("Item")
        if item is None:
            return None
        try:
            return OrientationResult.model_validate_json(item["result"])
        except Exception:
            logger.error("Erreur de désérialisation pour %s", result_id)
            return None


def create_store() -> ResultStore:
    """Crée le store approprié selon l'environnement.

    Utilise DynamoDB si RESULTS_TABLE_NAME est défini,
    sinon utilise le stockage en mémoire.
    """
    table_name = os.environ.get("RESULTS_TABLE_NAME")
    if table_name:
        logger.info("Utilisation de DynamoDB (table: %s)", table_name)
        return DynamoDBStore(table_name)
    else:
        logger.info("Utilisation du stockage en mémoire (développement local)")
        return InMemoryStore()


# Instance globale du store
results_store: ResultStore = create_store()
