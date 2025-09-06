"""
Webhook JSK pour Moddy
Service FastAPI qui expose un endpoint sécurisé pour exécuter du code JSK
envoyé par Noddy uniquement.
"""

import os
import time
import hmac
import hashlib
import subprocess
import asyncio
import resource
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, Header, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import redis.asyncio as redis
import uvicorn

# Configuration
TUNNEL_SECRET = os.environ.get("TUNNEL_SECRET", "your-secret-key-here")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
MAX_TIME_DRIFT = 30  # secondes max d'écart entre timestamps
NONCE_TTL = 60  # TTL du nonce en Redis (secondes)
JSK_TIMEOUT = 3  # Timeout d'exécution JSK (secondes)
JSK_MEMORY_LIMIT = 64 * 1024 * 1024  # 64 MB en bytes
JSK_CPU_LIMIT = 1  # 1 seconde de CPU max

# Initialisation FastAPI
app = FastAPI(title="Moddy JSK Webhook", version="1.0.0")

# Pool Redis (sera initialisé au démarrage)
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


# Modèles Pydantic
class JSKPayload(BaseModel):
    """Payload JSK envoyé par Noddy"""
    type: str
    code: str
    ctx: Dict[str, Any] = {}


class JSKResponse(BaseModel):
    """Réponse du webhook JSK"""
    ok: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


# Helpers de sécurité
def compute_signature(body: bytes, timestamp: str, nonce: str) -> str:
    """
    Calcule la signature HMAC SHA-256 pour vérifier l'authenticité.

    Format: HMAC_SHA256(secret, "{timestamp}.{nonce}.{body_hash}")
    """
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{timestamp}.{nonce}.{body_hash}"

    signature = hmac.new(
        TUNNEL_SECRET.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return signature


def constant_time_compare(val1: str, val2: str) -> bool:
    """Compare deux chaînes de manière sécurisée (constant time)."""
    return hmac.compare_digest(val1, val2)


async def check_nonce(nonce: str) -> bool:
    """
    Vérifie que le nonce n'a pas déjà été utilisé.
    Retourne True si le nonce est nouveau, False sinon.
    """
    if not redis_client:
        raise RuntimeError("Redis client not initialized")

    # Clé Redis pour le nonce
    nonce_key = f"jsk:nonce:{nonce}"

    # Essaie de créer la clé avec SET NX (Not eXists)
    # Si elle existe déjà, retourne False
    result = await redis_client.set(
        nonce_key,
        "1",
        nx=True,  # Ne crée que si n'existe pas
        ex=NONCE_TTL  # Expire après NONCE_TTL secondes
    )

    return result is not None


def validate_timestamp(timestamp_str: str) -> bool:
    """
    Vérifie que le timestamp n'a pas plus de MAX_TIME_DRIFT secondes d'écart.
    """
    try:
        timestamp = int(timestamp_str)
        current_time = int(time.time())
        time_diff = abs(current_time - timestamp)

        return time_diff <= MAX_TIME_DRIFT
    except (ValueError, TypeError):
        return False


async def execute_jsk_code(code: str, ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Exécute le code JSK dans un sous-processus Python sécurisé.

    Options de sécurité:
    - python3 -I : Mode isolé (pas d'import de site packages)
    - python3 -S : Pas d'import automatique du module site
    - Timeout : 3 secondes max
    - Limite mémoire : 64 MB
    - Limite CPU : 1 seconde
    """
    # Prépare le contexte (peut être utilisé pour injecter des variables)
    context_code = ""
    if ctx:
        # Injection sécurisée du contexte
        for key, value in ctx.items():
            if isinstance(value, str):
                context_code += f"{key} = {repr(value)}\n"
            elif isinstance(value, (int, float, bool)):
                context_code += f"{key} = {value}\n"

    # Code final à exécuter
    final_code = context_code + code

    # Commande Python avec options de sécurité
    cmd = ["python3", "-I", "-S", "-c", final_code]

    try:
        # Exécution avec timeout et limites
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Limite les ressources du processus
            preexec_fn=lambda: (
                # Limite mémoire
                resource.setrlimit(resource.RLIMIT_AS, (JSK_MEMORY_LIMIT, JSK_MEMORY_LIMIT)),
                # Limite CPU
                resource.setrlimit(resource.RLIMIT_CPU, (JSK_CPU_LIMIT, JSK_CPU_LIMIT))
            ) if hasattr(resource, 'setrlimit') else None
        )

        # Attente avec timeout
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=JSK_TIMEOUT
        )

        return {
            "stdout": stdout.decode('utf-8', errors='replace'),
            "stderr": stderr.decode('utf-8', errors='replace'),
            "exit_code": process.returncode
        }

    except asyncio.TimeoutError:
        # Timeout atteint
        if process:
            process.kill()
            await process.wait()

        return {
            "stdout": "",
            "stderr": "Execution timeout (3 seconds)",
            "exit_code": -1
        }

    except Exception as e:
        return {
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
            "exit_code": -2
        }


# Endpoints
@app.on_event("startup")
async def startup_event():
    """Initialise Redis au démarrage."""
    global redis_pool, redis_client

    redis_pool = redis.ConnectionPool.from_url(
        REDIS_URL,
        decode_responses=True
    )
    redis_client = redis.Redis(connection_pool=redis_pool)

    # Test de connexion
    try:
        await redis_client.ping()
        print("✅ Redis connecté")
    except Exception as e:
        print(f"❌ Erreur Redis: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Ferme les connexions Redis."""
    global redis_client, redis_pool

    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()


@app.get("/health")
async def health_check():
    """Endpoint de santé pour vérifier que le service fonctionne."""
    return {"status": "healthy", "service": "moddy-jsk-webhook"}


@app.post("/webhook/jsk")
async def jsk_webhook(
        request: Request,
        x_ts: str = Header(..., description="Timestamp Unix"),
        x_nonce: str = Header(..., description="Nonce unique"),
        x_sig: str = Header(..., description="Signature HMAC SHA-256")
):
    """
    Webhook JSK sécurisé pour exécuter du code envoyé par Noddy.

    Sécurité:
    1. Vérifie le timestamp (max 30 secondes d'écart)
    2. Vérifie le nonce (anti-replay)
    3. Vérifie la signature HMAC
    4. Exécute le code avec limites strictes
    """

    # 1. Vérification du timestamp
    if not validate_timestamp(x_ts):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired timestamp"
        )

    # 2. Vérification du nonce (anti-replay)
    nonce_valid = await check_nonce(x_nonce)
    if not nonce_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Replay attack detected (nonce already used)"
        )

    # 3. Récupération et vérification du body
    try:
        body = await request.body()
        payload = JSKPayload.parse_raw(body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )

    # 4. Vérification de la signature
    expected_signature = compute_signature(body, x_ts, x_nonce)
    if not constant_time_compare(x_sig, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    # 5. Validation du type
    if payload.type != "jsk":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid type: {payload.type}"
        )

    # 6. Log de l'exécution (pour audit)
    print(f"[JSK] Execution from Noddy - Context: {payload.ctx}")

    # 7. Exécution du code JSK
    try:
        result = await execute_jsk_code(payload.code, payload.ctx)

        # Succès
        return JSONResponse(
            content={
                "ok": True,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"]
            }
        )

    except Exception as e:
        # Erreur d'exécution
        print(f"[JSK] Execution error: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "ok": False,
                "error": f"Execution failed: {str(e)}"
            }
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Gestionnaire d'exceptions HTTP personnalisé."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": exc.detail
        }
    )


# Point d'entrée principal
if __name__ == "__main__":
    # Configuration uvicorn
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",  # Écoute en local uniquement
        port=8100,  # Port du webhook JSK
        log_level="info",
        access_log=True,
        reload=False  # Pas de reload en production
    )

    # Lancement du serveur
    server = uvicorn.Server(config)
    asyncio.run(server.serve())