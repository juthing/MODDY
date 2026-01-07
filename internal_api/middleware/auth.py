"""
Middleware d'authentification pour les endpoints internes.
Vérifie que toutes les requêtes vers /internal/* contiennent le bon secret.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import os
import logging

logger = logging.getLogger('moddy.internal_api.auth')

# Récupérer le secret depuis les variables d'environnement
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET")

if not INTERNAL_API_SECRET:
    logger.warning("⚠️ INTERNAL_API_SECRET environment variable is not set!")
    logger.warning("⚠️ Internal API authentication is DISABLED (not secure for production)")


async def verify_internal_auth(request: Request, call_next):
    """
    Middleware global pour vérifier l'authentification des requêtes internes.

    Vérifie que le header Authorization contient le bon secret pour toutes
    les requêtes vers /internal/*.

    Args:
        request: Requête FastAPI
        call_next: Fonction pour appeler le prochain middleware/handler

    Returns:
        Réponse HTTP ou erreur d'authentification
    """
    # Ne vérifier que les endpoints /internal/*
    if request.url.path.startswith("/internal"):

        # Si le secret n'est pas configuré, refuser toutes les requêtes internes
        if not INTERNAL_API_SECRET:
            logger.error(f"❌ Internal API call rejected: INTERNAL_API_SECRET not configured")
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"error": "Internal API authentication not configured"}
            )

        # Vérifier la présence du header Authorization
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(f"❌ Missing Authorization header on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Missing Authorization header"}
            )

        # Format attendu: "Bearer {SECRET}"
        if not auth_header.startswith("Bearer "):
            logger.warning(f"❌ Invalid Authorization format on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid Authorization format"}
            )

        # Extraire le token
        token = auth_header.replace("Bearer ", "")

        # Vérifier que le token correspond au secret
        if token != INTERNAL_API_SECRET:
            logger.warning(f"❌ Invalid secret on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Invalid secret"}
            )

        # Authentification réussie
        logger.info(f"✅ Internal auth verified for {request.url.path}")

    # Authentification réussie ou route publique, continuer
    response = await call_next(request)
    return response
