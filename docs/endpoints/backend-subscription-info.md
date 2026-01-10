# Backend Subscription Info

## Endpoint
`POST /internal/subscription/info`

## Description
Récupère les informations détaillées de l'abonnement Stripe d'un utilisateur à partir de son Discord ID.

## Use Case
- Afficher le statut d'abonnement dans une commande Discord (`/subscription`)
- Vérifier si un utilisateur a un abonnement actif
- Afficher la date de renouvellement
- Montrer le type d'abonnement (mensuel/annuel)
- Vérifier si l'abonnement est marqué pour annulation

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request

### Request Body Schema
```python
class BotSubscriptionInfoRequest(BaseModel):
    discord_id: str  # Discord ID de l'utilisateur
```

### Example Request
```bash
curl -X POST "http://website-backend.railway.internal:8080/internal/subscription/info" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678"
  }'
```

### Python Example
```python
import httpx
from app.schemas.internal import BotSubscriptionInfoRequest

async def get_user_subscription(discord_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://website-backend.railway.internal:8080/internal/subscription/info",
            headers={"Authorization": "Bearer your_secret_key_here"},
            json={"discord_id": discord_id}
        )
        return response.json()

# Usage
result = await get_user_subscription("123456789012345678")
if result["has_subscription"]:
    sub = result["subscription"]
    print(f"Status: {sub['status']}")
    print(f"Type: {sub['subscription_type']}")
    print(f"Renews: {sub['current_period_end']}")
```

## Response

### Success Response - Has Active Subscription (200 OK)
```json
{
  "success": true,
  "message": "Subscription found",
  "has_subscription": true,
  "subscription": {
    "subscription_id": "sub_1ABC23DEF456GHI",
    "customer_id": "cus_ABC123DEF456",
    "status": "active",
    "subscription_type": "yearly",
    "current_period_start": "2024-01-01T00:00:00+00:00",
    "current_period_end": "2025-01-01T00:00:00+00:00",
    "cancel_at_period_end": false,
    "amount": 9900,
    "currency": "eur"
  }
}
```

### Success Response - No Subscription (200 OK)
```json
{
  "success": true,
  "message": "No active subscription",
  "has_subscription": false,
  "subscription": null
}
```

### Response Schema
```python
class SubscriptionType(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    UNPAID = "unpaid"

class SubscriptionInfo(BaseModel):
    subscription_id: str              # ID Stripe de l'abonnement
    customer_id: str                  # ID Stripe du customer
    status: SubscriptionStatus        # Statut de l'abonnement
    subscription_type: SubscriptionType  # monthly ou yearly
    current_period_start: str         # Début période (ISO 8601)
    current_period_end: str           # Fin période (ISO 8601)
    cancel_at_period_end: bool        # Si annulé à la fin
    amount: int                       # Montant en centimes (9900 = 99.00€)
    currency: str                     # Devise (eur, usd, etc.)

class BotSubscriptionInfoResponse(BaseModel):
    success: bool                     # Si la requête a réussi
    message: str                      # Message de confirmation
    has_subscription: bool            # Si l'utilisateur a un abonnement
    subscription: Optional[SubscriptionInfo]  # Détails de l'abonnement
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

### 500 Internal Server Error - Stripe Error
```json
{
  "detail": "Stripe error: API key invalid"
}
```

## Implementation Details

### Stripe API Calls
1. **Recherche du customer par Discord ID**:
   ```python
   customers = stripe.Customer.list(
       limit=1,
       query=f'metadata["discord_id"]:"{discord_id}"'
   )
   ```

2. **Récupération de l'abonnement actif**:
   ```python
   subscriptions = stripe.Subscription.list(
       customer=customer.id,
       status="active",
       limit=1
   )
   ```

3. **Détermination du type d'abonnement**:
   - Vérifie `price.id` pour `year` keyword
   - Vérifie `price.recurring.interval == "year"`

### Amount Format
- Stripe retourne les montants en **centimes**
- Exemples:
  - `9900` = 99.00€ (abonnement annuel)
  - `1200` = 12.00€ (abonnement mensuel)

Pour convertir en euros:
```python
amount_euros = subscription["amount"] / 100
```

## Use Cases Examples

### Discord Command - Check Subscription
```python
@bot.slash_command(name="subscription", description="Check your subscription")
async def subscription_command(ctx):
    result = await get_user_subscription(str(ctx.author.id))

    if not result["has_subscription"]:
        await ctx.respond("❌ You don't have an active subscription.")
        return

    sub = result["subscription"]
    amount = sub["amount"] / 100

    embed = discord.Embed(title="Your Subscription", color=0x00ff00)
    embed.add_field(name="Status", value=sub["status"].upper(), inline=True)
    embed.add_field(name="Type", value=sub["subscription_type"].upper(), inline=True)
    embed.add_field(name="Price", value=f"{amount}€", inline=True)
    embed.add_field(name="Renews", value=sub["current_period_end"], inline=False)

    if sub["cancel_at_period_end"]:
        embed.add_field(
            name="⚠️ Cancellation Scheduled",
            value=f"Your subscription will end on {sub['current_period_end']}",
            inline=False
        )

    await ctx.respond(embed=embed)
```

### Check if User is Premium
```python
async def is_user_premium(discord_id: str) -> bool:
    """Check if user has active premium subscription"""
    result = await get_user_subscription(discord_id)

    if not result["has_subscription"]:
        return False

    sub = result["subscription"]
    return sub["status"] == "active" and not sub["cancel_at_period_end"]
```

## Logs
```
INFO: 📊 Récupération des infos d'abonnement pour discord_id=123456789012345678
INFO: ✅ Abonnement trouvé: sub_1ABC23DEF456GHI, status=active
WARNING: ⚠️ Aucun customer Stripe trouvé pour discord_id=999999999999999999
WARNING: ⚠️ Aucun abonnement actif pour customer cus_ABC123DEF456
ERROR: ❌ Erreur Stripe: Invalid API key
```

## Related Endpoints
- Cancel Subscription: `POST /internal/subscription/cancel`
- Get Invoices: `POST /internal/subscription/invoices`
- Refund Payment: `POST /internal/subscription/refund`
