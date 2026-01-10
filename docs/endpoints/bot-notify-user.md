# Bot Notify User

## Endpoint
`POST http://moddy.railway.internal:3000/internal/notify`

## Description
Notifie le bot Discord d'un événement utilisateur (paiement, abonnement, upgrade, etc.) pour que le bot puisse envoyer un message à l'utilisateur et/ou exécuter des actions.

## Use Case
- Notification de paiement réussi (abonnement créé)
- Notification de renouvellement d'abonnement
- Alerte d'abonnement annulé
- Notification de plan upgradé/downgradé
- Message de bienvenue automatique après paiement

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request

### Request Body Schema
```python
class UserAction(str, Enum):
    """Actions possibles pour un utilisateur"""
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PLAN_UPGRADED = "plan_upgraded"
    PLAN_DOWNGRADED = "plan_downgraded"

class InternalNotifyUserRequest(BaseModel):
    discord_id: str              # Discord ID de l'utilisateur (Snowflake)
    action: UserAction           # Action effectuée
    plan: Optional[str]          # Nom du plan (ex: "moddy_max", "free")
    metadata: Optional[dict]     # Métadonnées additionnelles
```

### Example Request - Subscription Created
```bash
curl -X POST "http://moddy.railway.internal:3000/internal/notify" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "action": "subscription_created",
    "plan": "moddy_max",
    "metadata": {
      "subscription_id": "sub_1ABC23DEF456GHI",
      "subscription_type": "yearly",
      "amount": 9900,
      "currency": "eur",
      "customer_id": "cus_ABC123DEF456"
    }
  }'
```

### Example Request - Subscription Cancelled
```bash
curl -X POST "http://moddy.railway.internal:3000/internal/notify" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "action": "subscription_cancelled",
    "plan": "free",
    "metadata": {
      "subscription_id": "sub_1ABC23DEF456GHI",
      "canceled_at": "2024-01-20T16:30:00Z",
      "message": "Subscription canceled"
    }
  }'
```

### Python Example (Backend → Bot)
```python
# app/services/bot_client.py

import httpx
from app.schemas.internal import InternalNotifyUserRequest, UserAction

class BotClient:
    def __init__(self):
        self.bot_url = "http://moddy.railway.internal:3000"
        self.api_secret = settings.internal_api_secret
        self.client = httpx.AsyncClient(base_url=self.bot_url, timeout=10.0)

    def _get_auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_secret}"}

    async def notify_user(
        self,
        discord_id: str,
        action: UserAction,
        plan: str = None,
        metadata: dict = None
    ):
        """Notify bot of user event"""
        try:
            response = await self.client.post(
                "/internal/notify",
                headers=self._get_auth_headers(),
                json={
                    "discord_id": discord_id,
                    "action": action.value,
                    "plan": plan,
                    "metadata": metadata or {}
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to notify bot: {e}")
            raise BotClientError(f"Notification failed: {str(e)}")

# Usage
bot_client = BotClient()

await bot_client.notify_user(
    discord_id="123456789012345678",
    action=UserAction.SUBSCRIPTION_CREATED,
    plan="moddy_max",
    metadata={
        "subscription_type": "yearly",
        "amount": 9900
    }
)
```

## Response

### Success Response (200 OK)
```json
{
  "success": true,
  "message": "User notified successfully",
  "notification_sent": true
}
```

### Response Schema
```python
class InternalNotifyUserResponse(BaseModel):
    success: bool              # Si la notification a été traitée
    message: str               # Message de confirmation
    notification_sent: bool    # Si une notification Discord a été envoyée
```

## Error Responses

### 401 Unauthorized
```json
{
  "error": "Missing Authorization header"
}
```

### 403 Forbidden
```json
{
  "error": "Invalid internal API secret"
}
```

### 404 Not Found - User Not in Server
```json
{
  "success": false,
  "message": "User not found in Discord server",
  "notification_sent": false
}
```

### 500 Internal Server Error
```json
{
  "success": false,
  "message": "Failed to send Discord message",
  "notification_sent": false
}
```

## Implementation (Bot Side)

### FastAPI Implementation
```python
# bot/routes/internal.py

from fastapi import APIRouter, Depends, HTTPException
from app.schemas.internal import InternalNotifyUserRequest, InternalNotifyUserResponse, UserAction
import discord

router = APIRouter(prefix="/internal")

# Référence au bot Discord
bot: discord.Bot = None

def set_bot_instance(bot_instance):
    global bot
    bot = bot_instance

@router.post("/notify", response_model=InternalNotifyUserResponse)
async def notify_user(payload: InternalNotifyUserRequest):
    """Receive notification from backend and send Discord message"""

    try:
        # Récupérer l'utilisateur Discord
        user = await bot.fetch_user(int(payload.discord_id))

        if not user:
            return InternalNotifyUserResponse(
                success=False,
                message="User not found",
                notification_sent=False
            )

        # Créer le message en fonction de l'action
        if payload.action == UserAction.SUBSCRIPTION_CREATED:
            embed = discord.Embed(
                title="🎉 Welcome to Moddy Max!",
                description="Your subscription has been activated.",
                color=0x00ff00
            )

            amount = payload.metadata.get("amount", 0) / 100
            sub_type = payload.metadata.get("subscription_type", "monthly")

            embed.add_field(name="Plan", value="Moddy Max", inline=True)
            embed.add_field(name="Type", value=sub_type.capitalize(), inline=True)
            embed.add_field(name="Price", value=f"{amount}€", inline=True)
            embed.add_field(
                name="What's next?",
                value="You now have access to all premium features!",
                inline=False
            )

            await user.send(embed=embed)

        elif payload.action == UserAction.SUBSCRIPTION_CANCELLED:
            embed = discord.Embed(
                title="😢 Subscription Cancelled",
                description="Your Moddy Max subscription has been cancelled.",
                color=0xff0000
            )

            message = payload.metadata.get("message", "")
            embed.add_field(name="Status", value=message, inline=False)

            await user.send(embed=embed)

        elif payload.action == UserAction.SUBSCRIPTION_UPDATED:
            embed = discord.Embed(
                title="🔄 Subscription Updated",
                description="Your subscription has been updated.",
                color=0x0099ff
            )

            message = payload.metadata.get("message", "")
            if message:
                embed.add_field(name="Details", value=message, inline=False)

            await user.send(embed=embed)

        return InternalNotifyUserResponse(
            success=True,
            message="User notified successfully",
            notification_sent=True
        )

    except discord.NotFound:
        return InternalNotifyUserResponse(
            success=False,
            message="User not found in Discord",
            notification_sent=False
        )

    except discord.Forbidden:
        return InternalNotifyUserResponse(
            success=False,
            message="Cannot send DM to user (DMs disabled)",
            notification_sent=False
        )

    except Exception as e:
        logger.error(f"Error sending notification: {e}", exc_info=True)
        return InternalNotifyUserResponse(
            success=False,
            message=f"Failed to send notification: {str(e)}",
            notification_sent=False
        )
```

### Discord.py Bot Startup
```python
# bot/main.py

import discord
from discord.ext import commands
from fastapi import FastAPI
import uvicorn
import asyncio

# Discord bot
bot = commands.Bot(command_prefix="/", intents=discord.Intents.all())

# FastAPI pour les endpoints internes
app = FastAPI()

# Importer les routes internes
from bot.routes import internal
internal.set_bot_instance(bot)
app.include_router(internal.router)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")

async def start_bot():
    """Start Discord bot"""
    await bot.start(settings.discord_token)

async def start_api():
    """Start internal API server"""
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=3000,  # Internal API port
        log_level="info"
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Run both bot and API server"""
    await asyncio.gather(
        start_bot(),
        start_api()
    )

if __name__ == "__main__":
    asyncio.run(main())
```

## Metadata Examples

### SUBSCRIPTION_CREATED
```json
{
  "subscription_id": "sub_1ABC23DEF456GHI",
  "customer_id": "cus_ABC123DEF456",
  "subscription_type": "yearly",
  "amount": 9900,
  "currency": "eur",
  "email": "user@example.com",
  "phone": "+33612345678"
}
```

### SUBSCRIPTION_CANCELLED
```json
{
  "subscription_id": "sub_1ABC23DEF456GHI",
  "canceled_at": "2024-01-20T16:30:00Z",
  "message": "Subscription canceled at user request",
  "cancel_at_period_end": true,
  "current_period_end": "2025-01-01T00:00:00Z"
}
```

### SUBSCRIPTION_UPDATED
```json
{
  "subscription_id": "sub_1ABC23DEF456GHI",
  "message": "Payment method updated successfully",
  "changes": ["payment_method"]
}
```

### PLAN_UPGRADED
```json
{
  "old_plan": "moddy_basic",
  "new_plan": "moddy_max",
  "upgrade_date": "2024-01-20T16:30:00Z",
  "prorated_amount": 5000
}
```

## Backend Usage Examples

### Stripe Webhook - Subscription Created
```python
# app/routes/payments.py

@payment_router.post("/webhook")
async def stripe_webhook(request: Request):
    event = stripe.Event.construct_from(...)

    if event.type == "customer.subscription.created":
        subscription = event.data.object
        discord_id = subscription.metadata.get("discord_id")

        if discord_id:
            bot_client = get_bot_client()

            interval = subscription.items.data[0].price.recurring.interval
            subscription_type = "yearly" if interval == "year" else "monthly"

            await bot_client.notify_user(
                discord_id=discord_id,
                action=UserAction.SUBSCRIPTION_CREATED,
                plan="moddy_max",
                metadata={
                    "subscription_id": subscription.id,
                    "subscription_type": subscription_type,
                    "amount": subscription.items.data[0].price.unit_amount,
                    "currency": subscription.items.data[0].price.currency
                }
            )
```

### Stripe Webhook - Subscription Deleted
```python
elif event.type == "customer.subscription.deleted":
    subscription = event.data.object
    discord_id = subscription.metadata.get("discord_id")

    if discord_id:
        bot_client = get_bot_client()

        await bot_client.notify_user(
            discord_id=discord_id,
            action=UserAction.SUBSCRIPTION_CANCELLED,
            plan="free",
            metadata={
                "subscription_id": subscription.id,
                "canceled_at": subscription.canceled_at,
                "message": "Subscription canceled"
            }
        )
```

## Important Notes

### Don't Fail the Webhook
⚠️ **Critical**: Si la notification au bot échoue, **ne pas faire échouer le webhook Stripe**.

Le paiement a réussi, donc on doit confirmer à Stripe même si la notification Discord échoue.

```python
try:
    await bot_client.notify_user(...)
    logger.info("✅ Bot notified successfully")
except BotClientError as e:
    # Log l'erreur mais continue
    logger.error(f"❌ Failed to notify bot: {e}")
    # Ne pas raise l'exception ici!

return JSONResponse(content={"status": "success"})  # Toujours confirmer à Stripe
```

### DM Privacy Settings
Certains utilisateurs ont les DMs désactivés. Le bot doit gérer cette erreur:

```python
try:
    await user.send(embed=embed)
except discord.Forbidden:
    # User has DMs disabled
    # Try sending in a server channel instead, or log for later
    logger.warning(f"Cannot DM user {user.id}: DMs disabled")
```

### Async/Await
Toutes les opérations Discord sont **async**. Utiliser `await` partout.

## Logs

### Backend Logs
```
INFO: 📤 Notifying bot of subscription_created for discord_id=123456789012345678
INFO: ✅ Bot notified successfully
WARNING: ⚠️ Bot notification failed: Connection timeout
ERROR: ❌ Failed to notify bot: User not found
```

### Bot Logs
```
INFO: 📩 Received notification: action=subscription_created, discord_id=123456789012345678
INFO: ✅ DM sent to user 123456789012345678
WARNING: ⚠️ Cannot DM user 123456789012345678: DMs disabled
ERROR: ❌ User 123456789012345678 not found
```

## Related Endpoints
- Bot Health: `GET http://moddy.railway.internal:3000/internal/health`
- Bot Update Roles: `POST http://moddy.railway.internal:3000/internal/roles/update`
- Backend Webhook: `POST /pay/webhook` (calls this endpoint)
