# Backend Subscription Invoices

## Endpoint
`POST /internal/subscription/invoices`

## Description
Récupère la liste des factures Stripe d'un utilisateur avec liens PDF.

## Use Case
- Commande Discord `/invoices` pour afficher l'historique de facturation
- Téléchargement de factures pour la comptabilité
- Support client pour vérifier les paiements
- Affichage des factures dans un dashboard utilisateur
- Audit des transactions

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request

### Request Body Schema
```python
class BotInvoicesRequest(BaseModel):
    discord_id: str     # Discord ID de l'utilisateur
    limit: int = 10     # Nombre maximum de factures (défaut: 10)
```

### Example Request
```bash
curl -X POST "http://website-backend.railway.internal:8080/internal/subscription/invoices" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "limit": 5
  }'
```

### Python Example
```python
import httpx
from app.schemas.internal import BotInvoicesRequest

async def get_user_invoices(discord_id: str, limit: int = 10):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://website-backend.railway.internal:8080/internal/subscription/invoices",
            headers={"Authorization": "Bearer your_secret_key_here"},
            json={
                "discord_id": discord_id,
                "limit": limit
            }
        )
        return response.json()

# Usage
result = await get_user_invoices("123456789012345678", limit=5)

if result["invoices"]:
    for invoice in result["invoices"]:
        print(f"Invoice {invoice['invoice_id']}: {invoice['amount']/100}€")
        print(f"  Status: {invoice['status']}")
        print(f"  PDF: {invoice['invoice_pdf']}")
```

## Response

### Success Response - With Invoices (200 OK)
```json
{
  "success": true,
  "message": "Found 3 invoice(s)",
  "invoices": [
    {
      "invoice_id": "in_1ABC23DEF456GHI",
      "amount": 9900,
      "currency": "eur",
      "status": "paid",
      "created": "2024-01-01T00:00:00+00:00",
      "invoice_pdf": "https://pay.stripe.com/invoice/acct_xxx/invst_xxx/pdf"
    },
    {
      "invoice_id": "in_2ABC23DEF456GHI",
      "amount": 9900,
      "currency": "eur",
      "status": "paid",
      "created": "2023-12-01T00:00:00+00:00",
      "invoice_pdf": "https://pay.stripe.com/invoice/acct_xxx/invst_xxx/pdf"
    },
    {
      "invoice_id": "in_3ABC23DEF456GHI",
      "amount": 9900,
      "currency": "eur",
      "status": "paid",
      "created": "2023-11-01T00:00:00+00:00",
      "invoice_pdf": "https://pay.stripe.com/invoice/acct_xxx/invst_xxx/pdf"
    }
  ]
}
```

### Success Response - No Customer (200 OK)
```json
{
  "success": true,
  "message": "No customer found",
  "invoices": []
}
```

### Success Response - No Invoices (200 OK)
```json
{
  "success": true,
  "message": "Found 0 invoice(s)",
  "invoices": []
}
```

### Response Schema
```python
class InvoiceInfo(BaseModel):
    invoice_id: str              # ID Stripe de la facture
    amount: int                  # Montant payé en centimes
    currency: str                # Devise (eur, usd, etc.)
    status: str                  # Statut (paid, open, void, uncollectible)
    created: str                 # Date de création (ISO 8601)
    invoice_pdf: Optional[str]   # URL du PDF de la facture

class BotInvoicesResponse(BaseModel):
    success: bool                # Si la requête a réussi
    message: str                 # Message de confirmation
    invoices: list[InvoiceInfo]  # Liste des factures
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
  "detail": "Stripe error: Invalid customer ID"
}
```

## Invoice Status Values

### paid
Facture payée avec succès.

### open
Facture en attente de paiement (pas encore payée).

### void
Facture annulée (ne sera pas payée).

### uncollectible
Facture marquée comme impossible à collecter (après plusieurs tentatives échouées).

### draft
Facture en brouillon (pas encore finalisée).

## Implementation Details

### Stripe API Calls
1. **Recherche du customer**:
   ```python
   customers = stripe.Customer.list(
       limit=1,
       query=f'metadata["discord_id"]:"{discord_id}"'
   )
   ```

2. **Récupération des factures**:
   ```python
   invoices_data = stripe.Invoice.list(
       customer=customer.id,
       limit=limit
   )
   ```

3. **Formatage des données**:
   ```python
   for inv in invoices_data.data:
       invoices.append(InvoiceInfo(
           invoice_id=inv.id,
           amount=inv.amount_paid,  # Montant payé (pas amount_due)
           currency=inv.currency,
           status=inv.status,
           created=datetime.fromtimestamp(inv.created, tz=timezone.utc).isoformat(),
           invoice_pdf=inv.invoice_pdf
       ))
   ```

### Amount vs Amount Paid
- `inv.amount_paid`: Montant effectivement payé ✓ (utilisé)
- `inv.amount_due`: Montant restant à payer (si partiel)

### PDF Access
Les liens PDF Stripe:
- Sont **publics** mais **non listables** (sécurité par obscurité)
- Expirent après **30 jours** (puis nécessitent régénération)
- Format: `https://pay.stripe.com/invoice/acct_xxx/invst_xxx/pdf`

## Use Cases Examples

### Discord Command - List Invoices
```python
@bot.slash_command(name="invoices", description="View your payment invoices")
async def invoices_command(ctx, limit: int = 5):
    await ctx.defer()

    result = await get_user_invoices(str(ctx.author.id), limit=limit)

    if not result["invoices"]:
        await ctx.respond("📄 No invoices found.")
        return

    embed = discord.Embed(
        title="Your Invoices",
        description=f"Showing your last {len(result['invoices'])} invoice(s)",
        color=0x0099ff
    )

    for inv in result["invoices"]:
        amount = inv["amount"] / 100
        status_emoji = "✅" if inv["status"] == "paid" else "⏳"

        embed.add_field(
            name=f"{status_emoji} {amount}€ - {inv['status'].upper()}",
            value=(
                f"Date: {inv['created'][:10]}\n"
                f"ID: `{inv['invoice_id']}`\n"
                f"[Download PDF]({inv['invoice_pdf']})"
            ),
            inline=False
        )

    await ctx.respond(embed=embed)
```

### Discord Command - Download Latest Invoice
```python
@bot.slash_command(name="latest_invoice", description="Get your latest invoice PDF")
async def latest_invoice_command(ctx):
    result = await get_user_invoices(str(ctx.author.id), limit=1)

    if not result["invoices"]:
        await ctx.respond("❌ No invoices found.")
        return

    invoice = result["invoices"][0]
    amount = invoice["amount"] / 100

    embed = discord.Embed(
        title="Latest Invoice",
        color=0x00ff00
    )
    embed.add_field(name="Amount", value=f"{amount}€", inline=True)
    embed.add_field(name="Status", value=invoice["status"].upper(), inline=True)
    embed.add_field(name="Date", value=invoice["created"][:10], inline=True)
    embed.add_field(
        name="Download",
        value=f"[Click here to download PDF]({invoice['invoice_pdf']})",
        inline=False
    )

    await ctx.respond(embed=embed)
```

### Admin Command - View User Invoices
```python
@bot.slash_command(name="admin_invoices", description="View user's invoices")
@commands.has_permissions(administrator=True)
async def admin_invoices(ctx, user: discord.Member, limit: int = 10):
    await ctx.defer()

    result = await get_user_invoices(str(user.id), limit=limit)

    if not result["invoices"]:
        await ctx.respond(f"📄 No invoices found for {user.mention}")
        return

    total = sum(inv["amount"] for inv in result["invoices"]) / 100

    embed = discord.Embed(
        title=f"Invoices for {user.name}",
        description=f"Total: {total}€ across {len(result['invoices'])} invoice(s)",
        color=0x0099ff
    )

    for inv in result["invoices"][:5]:  # Show max 5 in embed
        amount = inv["amount"] / 100
        embed.add_field(
            name=f"{amount}€ - {inv['status']}",
            value=f"{inv['created'][:10]} - {inv['invoice_id']}",
            inline=False
        )

    await ctx.respond(embed=embed)
```

### Calculate Total Revenue
```python
async def calculate_user_lifetime_value(discord_id: str) -> float:
    """Calculate total amount paid by user"""
    result = await get_user_invoices(discord_id, limit=100)

    total_cents = sum(
        inv["amount"]
        for inv in result["invoices"]
        if inv["status"] == "paid"
    )

    return total_cents / 100  # Convert to euros

# Usage
ltv = await calculate_user_lifetime_value("123456789012345678")
print(f"User lifetime value: {ltv}€")
```

## Pagination

### Default Limit
- Par défaut: **10 factures**
- Maximum recommandé: **100 factures**
- Stripe supporte jusqu'à **100** par requête

### Handling Many Invoices
Si un utilisateur a plus de factures que la limite:

```python
async def get_all_user_invoices(discord_id: str):
    """Get all invoices with pagination"""
    all_invoices = []
    limit = 100

    result = await get_user_invoices(discord_id, limit=limit)
    all_invoices.extend(result["invoices"])

    # Note: Pour une vraie pagination, il faudrait utiliser
    # starting_after dans l'API Stripe (pas implémenté ici)

    return all_invoices
```

## Important Notes

### PDF Expiration
⚠️ Les liens PDF Stripe expirent après **30 jours**.

Pour régénérer un PDF:
```python
# Pas directement supporté par cet endpoint
# Il faudrait appeler directement l'API Stripe:
invoice = stripe.Invoice.retrieve(invoice_id)
pdf_url = invoice.invoice_pdf
```

### Invoice vs Payment
- **Invoice**: Demande de paiement (peut être non payée)
- **Payment**: Paiement effectué

Cet endpoint retourne les **invoices**, pas seulement les paiements réussis.

Filtrer uniquement les factures payées:
```python
paid_invoices = [
    inv for inv in result["invoices"]
    if inv["status"] == "paid"
]
```

## Logs
```
INFO: 📄 Récupération des factures pour discord_id=123456789012345678, limit=10
INFO: ✅ 5 facture(s) trouvée(s)
WARNING: ⚠️ Aucun customer trouvé pour discord_id=999999999999999999
ERROR: ❌ Erreur Stripe: Invalid customer ID
```

## Related Endpoints
- Subscription Info: `POST /internal/subscription/info`
- Refund Payment: `POST /internal/subscription/refund`
- Cancel Subscription: `POST /internal/subscription/cancel`
