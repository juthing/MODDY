# Backend Subscription Refund

## Endpoint
`POST /internal/subscription/refund`

## Description
Rembourse un paiement Stripe d'un utilisateur, soit totalement, soit partiellement.

## Use Case
- Remboursement suite à une annulation immédiate
- Support client pour problèmes de service
- Remboursement partiel pour résolution de litiges
- Gestion des erreurs de facturation
- Remboursement pour violations de service (par l'équipe)

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request

### Request Body Schema
```python
class BotRefundPaymentRequest(BaseModel):
    discord_id: str           # Discord ID de l'utilisateur
    amount: Optional[int]     # Montant en centimes (None = remboursement total)
    reason: Optional[str]     # Raison du remboursement
```

### Example Request - Full Refund
```bash
curl -X POST "http://website-backend.railway.internal:8080/internal/subscription/refund" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "amount": null,
    "reason": "Service issue - full refund requested"
  }'
```

### Example Request - Partial Refund
```bash
curl -X POST "http://website-backend.railway.internal:8080/internal/subscription/refund" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "amount": 5000,
    "reason": "Partial refund for service downtime"
  }'
```

### Python Example
```python
import httpx
from app.schemas.internal import BotRefundPaymentRequest

async def refund_user_payment(
    discord_id: str,
    amount: int = None,
    reason: str = None
):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://website-backend.railway.internal:8080/internal/subscription/refund",
            headers={"Authorization": "Bearer your_secret_key_here"},
            json={
                "discord_id": discord_id,
                "amount": amount,
                "reason": reason
            }
        )
        return response.json()

# Usage - Full refund
result = await refund_user_payment(
    discord_id="123456789012345678",
    amount=None,  # None = remboursement total
    reason="User not satisfied with service"
)

# Usage - Partial refund (50.00€)
result = await refund_user_payment(
    discord_id="123456789012345678",
    amount=5000,  # 5000 centimes = 50.00€
    reason="Partial refund for technical issue"
)

if result["refunded"]:
    amount_euros = result["amount_refunded"] / 100
    print(f"Refunded: {amount_euros}€")
```

## Response

### Success Response - Refund Processed (200 OK)
```json
{
  "success": true,
  "message": "Refund processed successfully",
  "refunded": true,
  "refund_id": "re_1ABC23DEF456GHI",
  "amount_refunded": 9900
}
```

### Error Response - No Customer Found (200 OK)
```json
{
  "success": false,
  "message": "No customer found for this Discord ID",
  "refunded": false
}
```

### Error Response - No Paid Invoice (200 OK)
```json
{
  "success": false,
  "message": "No paid invoice found to refund",
  "refunded": false
}
```

### Error Response - No Payment Intent (200 OK)
```json
{
  "success": false,
  "message": "No payment intent found for this invoice",
  "refunded": false
}
```

### Response Schema
```python
class BotRefundPaymentResponse(BaseModel):
    success: bool                   # Si le remboursement a réussi
    message: str                    # Message de confirmation
    refunded: bool                  # Si le remboursement a été effectué
    refund_id: Optional[str]        # ID Stripe du remboursement
    amount_refunded: Optional[int]  # Montant remboursé en centimes
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
  "detail": "Stripe error: Charge already refunded"
}
```

## Implementation Details

### Refund Process Flow

1. **Recherche du customer Stripe**:
   ```python
   customers = stripe.Customer.list(
       limit=1,
       query=f'metadata["discord_id"]:"{discord_id}"'
   )
   ```

2. **Récupération de la dernière facture payée**:
   ```python
   invoices = stripe.Invoice.list(
       customer=customer.id,
       status="paid",
       limit=1
   )
   ```

3. **Création du remboursement**:
   ```python
   refund_params = {"payment_intent": invoice.payment_intent}

   if amount:  # Remboursement partiel
       refund_params["amount"] = amount

   if reason:
       refund_params["reason"] = "requested_by_customer"
       refund_params["metadata"] = {"reason": reason}

   refund = stripe.Refund.create(**refund_params)
   ```

### Amount Format
- Les montants sont en **centimes**
- Exemples:
  - `9900` = 99.00€
  - `5000` = 50.00€
  - `1250` = 12.50€
  - `None` = remboursement total

### Stripe Refund Reasons
Stripe supporte ces raisons prédéfinies:
- `duplicate`: Paiement en double
- `fraudulent`: Fraude détectée
- `requested_by_customer`: Demandé par le client (utilisé par défaut)

## Refund Timing
- **Remboursements carte de crédit**: 5-10 jours ouvrables
- **Remboursements SEPA**: 5-10 jours ouvrables
- **Stripe crédite le compte immédiatement**
- Le délai dépend de la banque du client

## Use Cases Examples

### Admin Command - Full Refund
```python
@bot.slash_command(name="admin_refund", description="Refund user payment")
@commands.has_permissions(administrator=True)
async def admin_refund(
    ctx,
    user: discord.Member,
    amount: int = None,
    reason: str = "Admin refund"
):
    await ctx.defer()

    result = await refund_user_payment(
        discord_id=str(user.id),
        amount=amount,
        reason=reason
    )

    if result["refunded"]:
        amount_euros = result["amount_refunded"] / 100
        await ctx.respond(
            f"✅ Refunded {amount_euros}€ to {user.mention}\n"
            f"Refund ID: {result['refund_id']}\n"
            f"⏱️ Will appear in bank account in 5-10 business days"
        )
    else:
        await ctx.respond(f"❌ {result['message']}")
```

### Support Ticket System
```python
async def handle_refund_request(ticket_id: str, discord_id: str, amount: int):
    """Handle refund from support ticket system"""

    # Log to support system
    logger.info(f"Processing refund for ticket {ticket_id}")

    # Process refund
    result = await refund_user_payment(
        discord_id=discord_id,
        amount=amount,
        reason=f"Support ticket {ticket_id}"
    )

    if result["refunded"]:
        # Notify user via DM
        user = await bot.fetch_user(int(discord_id))
        await user.send(
            f"✅ Your refund of {amount/100}€ has been processed.\n"
            f"Refund ID: {result['refund_id']}\n"
            f"You will see it in your account within 5-10 business days."
        )

        # Update support ticket
        await update_ticket_status(ticket_id, "refunded")

    return result
```

### Automatic Refund on Immediate Cancel
```python
async def cancel_and_refund(discord_id: str, reason: str):
    """Cancel subscription and issue full refund"""

    # 1. Get subscription info to calculate prorated refund
    sub_info = await get_user_subscription(discord_id)

    if not sub_info["has_subscription"]:
        return {"success": False, "message": "No subscription to cancel"}

    # 2. Cancel immediately
    cancel_result = await cancel_user_subscription(
        discord_id=discord_id,
        immediate=True,
        reason=reason
    )

    if not cancel_result["canceled"]:
        return cancel_result

    # 3. Process full refund
    refund_result = await refund_user_payment(
        discord_id=discord_id,
        amount=None,  # Full refund
        reason=reason
    )

    return {
        "canceled": cancel_result["canceled"],
        "refunded": refund_result["refunded"],
        "amount": refund_result.get("amount_refunded")
    }
```

## Important Notes

### Partial Refunds
- Vous pouvez faire plusieurs remboursements partiels
- Le total des remboursements ne peut pas dépasser le montant payé
- Exemple: Paiement 99€ → Refund 50€ → Refund 49€ ✓

### Refund Limits
- **Délai maximum**: 180 jours après le paiement
- Après 180 jours, contacter le support Stripe
- Les remboursements après 180 jours nécessitent un transfert manuel

### Impact on Subscription
⚠️ **Important**: Rembourser un paiement **n'annule PAS** l'abonnement automatiquement.

**Best practice**:
1. D'abord annuler l'abonnement: `/internal/subscription/cancel`
2. Puis rembourser: `/internal/subscription/refund`

```python
# Correct flow
await cancel_user_subscription(discord_id, immediate=True)
await refund_user_payment(discord_id)
```

### Stripe Fees
- Les frais Stripe (2.9% + 0.25€) ne sont **pas remboursés**
- Exemple: Paiement 100€ → Vous recevez 97.15€ → Refund 100€ → Vous payez 2.85€

## Logs
```
INFO: 💰 Remboursement pour discord_id=123456789012345678, montant=None
INFO: ✅ Remboursement créé: re_1ABC23DEF456GHI, montant=9900
WARNING: ⚠️ Aucun customer trouvé pour discord_id=999999999999999999
WARNING: ⚠️ Aucune facture payée trouvée à rembourser
ERROR: ❌ Erreur Stripe: Charge already fully refunded
```

## Related Endpoints
- Cancel Subscription: `POST /internal/subscription/cancel`
- Subscription Info: `POST /internal/subscription/info`
- Get Invoices: `POST /internal/subscription/invoices`
