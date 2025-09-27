"""
JSK Webhook for Moddy
FastAPI service that exposes a secure endpoint to execute JSK code
sent by Noddy only.
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
MAX_TIME_DRIFT = 30  # max seconds difference between timestamps
NONCE_TTL = 60  # Nonce TTL in Redis (seconds)
JSK_TIMEOUT = 3  # JSK execution timeout (seconds)
JSK_MEMORY_LIMIT = 64 * 1024 * 1024  # 64 MB in bytes
JSK_CPU_LIMIT = 1  # 1 second of max CPU

# FastAPI Initialization
app = FastAPI(title="Moddy JSK Webhook", version="1.0.0")

# Redis Pool (will be initialized at startup)
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


# Pydantic Models
class JSKPayload(BaseModel):
    """JSK Payload sent by Noddy"""
    type: str
    code: str
    ctx: Dict[str, Any] = {}


class JSKResponse(BaseModel):
    """JSK Webhook Response"""
    ok: bool
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    exit_code: Optional[int] = None
    error: Optional[str] = None


# Security Helpers
def compute_signature(body: bytes, timestamp: str, nonce: str) -> str:
    """
    Computes the HMAC SHA-256 signature to verify authenticity.

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
    """Compares two strings securely (constant time)."""
    return hmac.compare_digest(val1, val2)


async def check_nonce(nonce: str) -> bool:
    """
    Checks that the nonce has not been used before.
    Returns True if the nonce is new, False otherwise.
    """
    if not redis_client:
        raise RuntimeError("Redis client not initialized")

    # Redis key for the nonce
    nonce_key = f"jsk:nonce:{nonce}"

    # Try to create the key with SET NX (Not eXists)
    # If it already exists, returns False
    result = await redis_client.set(
        nonce_key,
        "1",
        nx=True,  # Create only if it does not exist
        ex=NONCE_TTL  # Expires after NONCE_TTL seconds
    )

    return result is not None


def validate_timestamp(timestamp_str: str) -> bool:
    """
    Checks that the timestamp does not have more than MAX_TIME_DRIFT seconds difference.
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
    Executes JSK code in a secure Python subprocess.

    Security options:
    - python3 -I : Isolated mode (no import of site packages)
    - python3 -S : No automatic import of the site module
    - Timeout : 3 seconds max
    - Memory limit : 64 MB
    - CPU limit : 1 second
    """
    # Prepare the context (can be used to inject variables)
    context_code = ""
    if ctx:
        # Secure context injection
        for key, value in ctx.items():
            if isinstance(value, str):
                context_code += f"{key} = {repr(value)}\n"
            elif isinstance(value, (int, float, bool)):
                context_code += f"{key} = {value}\n"

    # Final code to execute
    final_code = context_code + code

    # Python command with security options
    cmd = ["python3", "-I", "-S", "-c", final_code]

    try:
        # Execution with timeout and limits
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            # Limit process resources
            preexec_fn=lambda: (
                # Memory limit
                resource.setrlimit(resource.RLIMIT_AS, (JSK_MEMORY_LIMIT, JSK_MEMORY_LIMIT)),
                # CPU limit
                resource.setrlimit(resource.RLIMIT_CPU, (JSK_CPU_LIMIT, JSK_CPU_LIMIT))
            ) if hasattr(resource, 'setrlimit') else None
        )

        # Wait with timeout
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
        # Timeout reached
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
    """Initializes Redis at startup."""
    global redis_pool, redis_client

    redis_pool = redis.ConnectionPool.from_url(
        REDIS_URL,
        decode_responses=True
    )
    redis_client = redis.Redis(connection_pool=redis_pool)

    # Connection test
    try:
        await redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print(f"❌ Redis Error: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Closes Redis connections."""
    global redis_client, redis_pool

    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()


@app.get("/health")
async def health_check():
    """Health endpoint to check that the service is working."""
    return {"status": "healthy", "service": "moddy-jsk-webhook"}


@app.post("/webhook/jsk")
async def jsk_webhook(
        request: Request,
        x_ts: str = Header(..., description="Unix Timestamp"),
        x_nonce: str = Header(..., description="Unique Nonce"),
        x_sig: str = Header(..., description="HMAC SHA-256 Signature")
):
    """
    Secure JSK webhook to execute code sent by Noddy.

    Security:
    1. Check timestamp (max 30 seconds difference)
    2. Check nonce (anti-replay)
    3. Check HMAC signature
    4. Execute code with strict limits
    """

    # 1. Check timestamp
    if not validate_timestamp(x_ts):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired timestamp"
        )

    # 2. Check nonce (anti-replay)
    nonce_valid = await check_nonce(x_nonce)
    if not nonce_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Replay attack detected (nonce already used)"
        )

    # 3. Retrieve and verify body
    try:
        body = await request.body()
        payload = JSKPayload.parse_raw(body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payload: {str(e)}"
        )

    # 4. Check signature
    expected_signature = compute_signature(body, x_ts, x_nonce)
    if not constant_time_compare(x_sig, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    # 5. Validate type
    if payload.type != "jsk":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid type: {payload.type}"
        )

    # 6. Log execution (for audit)
    print(f"[JSK] Execution from Noddy - Context: {payload.ctx}")

    # 7. Execute JSK code
    try:
        result = await execute_jsk_code(payload.code, payload.ctx)

        # Success
        return JSONResponse(
            content={
                "ok": True,
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"]
            }
        )

    except Exception as e:
        # Execution error
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
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "ok": False,
            "error": exc.detail
        }
    )


# Main entry point
if __name__ == "__main__":
    # Uvicorn configuration
    config = uvicorn.Config(
        app=app,
        host="127.0.0.1",  # Listen locally only
        port=8100,  # JSK webhook port
        log_level="info",
        access_log=True,
        reload=False  # No reload in production
    )

    # Launch the server
    server = uvicorn.Server(config)
    asyncio.run(server.serve())