# Bot Health Check

## Endpoint
`GET http://moddy.railway.internal:3000/internal/health`

## Description
Health check endpoint pour vérifier que le bot Discord est accessible depuis le backend via Railway Private Network.

## Use Case
- Vérifier la disponibilité du bot avant d'envoyer des notifications
- Monitoring et alertes de santé du bot
- Validation de la configuration Railway Private Network
- Diagnostics de connexion

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request
Aucun paramètre requis.

### Example Request
```bash
curl -X GET "http://moddy.railway.internal:3000/internal/health" \
  -H "Authorization: Bearer your_secret_key_here"
```

### Python Example (Backend → Bot)
```python
import httpx

async def check_bot_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://moddy.railway.internal:3000/internal/health",
            headers={"Authorization": "Bearer your_secret_key_here"}
        )
        return response.json()
```

## Response

### Success Response (200 OK)
```json
{
  "status": "healthy",
  "service": "discord-bot",
  "version": "1.0.0"
}
```

### Response Schema
```python
class InternalHealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]  # État du service
    service: str                              # Nom du service (discord-bot)
    version: Optional[str]                    # Version du bot
```

## Error Responses

### 401 Unauthorized
Missing or invalid Authorization header.

```json
{
  "error": "Missing Authorization header"
}
```

### 403 Forbidden
Invalid secret key.

```json
{
  "error": "Invalid internal API secret"
}
```

### Connection Errors
Si le bot est down ou inaccessible:
- `httpx.ConnectError`: Bot non accessible
- `httpx.TimeoutError`: Bot ne répond pas

```python
try:
    response = await check_bot_health()
except httpx.ConnectError:
    # Bot is down or unreachable
    logger.error("Bot is unreachable")
except httpx.TimeoutError:
    # Bot is not responding
    logger.error("Bot timeout")
```

## Implementation Notes (Bot Side)

### FastAPI Implementation
```python
from fastapi import FastAPI, Header, HTTPException
from app.schemas.internal import InternalHealthResponse
from app.config import settings

app = FastAPI()

def verify_internal_auth(authorization: str = Header(None)):
    """Verify internal API secret"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization")

    token = authorization.replace("Bearer ", "")
    if token != settings.internal_api_secret:
        raise HTTPException(status_code=403, detail="Invalid secret")

@app.get("/internal/health", response_model=InternalHealthResponse)
async def health_check(auth: str = Depends(verify_internal_auth)):
    return InternalHealthResponse(
        status="healthy",
        service="discord-bot",
        version="1.0.0"
    )
```

### Discord.py Implementation (Alternative)
```python
import discord
from aiohttp import web
from discord.ext import commands

bot = commands.Bot(command_prefix="/")

# HTTP server pour les endpoints internes
async def internal_health(request):
    # Vérifier l'authentification
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return web.json_response(
            {"error": "Missing Authorization"},
            status=401
        )

    token = auth_header.replace("Bearer ", "")
    if token != settings.internal_api_secret:
        return web.json_response(
            {"error": "Invalid secret"},
            status=403
        )

    # Retourner le health check
    return web.json_response({
        "status": "healthy",
        "service": "discord-bot",
        "version": "1.0.0"
    })

# Démarrer le serveur HTTP interne
async def start_internal_server():
    app = web.Application()
    app.router.add_get('/internal/health', internal_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 3000)
    await site.start()
    print("Internal API running on port 3000")
```

## Backend Usage

### BotClient Implementation
```python
# app/services/bot_client.py

import httpx
import logging
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class BotClient:
    def __init__(self):
        self.bot_url = settings.bot_internal_url  # http://moddy.railway.internal:3000
        self.api_secret = settings.internal_api_secret
        self.client = httpx.AsyncClient(base_url=self.bot_url, timeout=10.0)

    def _get_auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_secret}"}

    async def check_health(self) -> bool:
        """Check if bot is healthy"""
        try:
            response = await self.client.get(
                "/internal/health",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()

            data = response.json()
            return data.get("status") == "healthy"

        except httpx.HTTPError as e:
            logger.error(f"Bot health check failed: {e}")
            return False

# Usage globale
async def get_bot_client():
    return BotClient()
```

### Usage in Payment Webhook
```python
# app/routes/payments.py

@payment_router.post("/webhook")
async def stripe_webhook(request: Request):
    # ... parse Stripe event ...

    # Vérifier que le bot est accessible avant de notifier
    bot_client = get_bot_client()

    try:
        is_healthy = await bot_client.check_health()
        if not is_healthy:
            logger.warning("⚠️ Bot is not healthy, notification may fail")
            # Continue quand même (le paiement a réussi)

        # Notifier le bot
        await bot_client.notify_user(
            discord_id=discord_id,
            action=UserAction.SUBSCRIPTION_CREATED,
            plan="moddy_max"
        )

    except Exception as e:
        # Ne pas faire échouer le webhook
        logger.error(f"Failed to notify bot: {e}")
```

## Railway Configuration

### Bot Service - Environment Variables
```bash
# Port pour l'API interne (séparé du port Discord)
INTERNAL_API_PORT=3000

# Secret partagé avec le backend
INTERNAL_API_SECRET=your_generated_secret_here

# URL publique du bot (Railway auto)
PORT=8080
```

### Bot Service - Expose Port
Railway expose automatiquement le port 8080 (Discord webhooks).
Le port 3000 est accessible **uniquement** via Railway Private Network.

### Private Network DNS
- Backend appelle: `http://moddy.railway.internal:3000`
- Résolution automatique par Railway
- Pas accessible depuis Internet ✓

## Monitoring & Alerting

### Health Check Scheduler
```python
import asyncio

async def monitor_bot_health():
    """Monitor bot health every 60 seconds"""
    bot_client = get_bot_client()

    while True:
        try:
            is_healthy = await bot_client.check_health()

            if is_healthy:
                logger.info("✅ Bot is healthy")
            else:
                logger.error("❌ Bot is unhealthy")
                # Send alert (email, Slack, etc.)

        except Exception as e:
            logger.error(f"Health check error: {e}")

        await asyncio.sleep(60)  # Check every minute

# Start monitoring
asyncio.create_task(monitor_bot_health())
```

## Important Notes

### Two Ports Architecture
Le bot Discord utilise **deux ports**:
- **Port 8080**: Public (Discord webhooks, interactions)
- **Port 3000**: Privé (Backend communication, Railway Private Network)

**Avantages**:
- Sécurité: Les endpoints internes ne sont pas exposés publiquement
- Séparation des concerns: Traffic Discord vs Backend séparés
- Rate limiting différent par port

### Timeout Configuration
```python
# Timeout recommandé: 10 secondes
client = httpx.AsyncClient(
    base_url="http://moddy.railway.internal:3000",
    timeout=10.0  # 10 seconds
)
```

## Logs

### Backend Logs
```
INFO: Checking bot health...
INFO: ✅ Bot is healthy
WARNING: ⚠️ Bot health check timeout
ERROR: ❌ Bot is unreachable: Connection refused
```

### Bot Logs
```
INFO: Health check received from backend
INFO: Internal API running on port 3000
WARNING: Invalid authentication attempt on /internal/health
```

## Related Endpoints
- Backend Health Check: `GET http://website-backend.railway.internal:8080/internal/health`
- Bot Notify User: `POST http://moddy.railway.internal:3000/internal/notify`
- Bot Update Roles: `POST http://moddy.railway.internal:3000/internal/roles/update`
