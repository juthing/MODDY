# Bot Update User Roles

## Endpoint
`POST http://moddy.railway.internal:3000/internal/roles/update`

## Description
Demande au bot Discord de mettre à jour les rôles d'un utilisateur (ajouter/retirer des rôles) suite à un changement d'abonnement ou de plan.

## Use Case
- Ajouter le rôle "Moddy Max" après un paiement réussi
- Retirer le rôle premium après annulation d'abonnement
- Mettre à jour les rôles lors d'un upgrade/downgrade
- Synchroniser les rôles Discord avec le statut d'abonnement

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request

### Request Body Schema
```python
class InternalUpdateRoleRequest(BaseModel):
    discord_id: str                   # Discord ID de l'utilisateur
    plan: str                         # Nouveau plan ("moddy_max", "free")
    add_roles: Optional[list[str]]    # IDs de rôles à ajouter
    remove_roles: Optional[list[str]] # IDs de rôles à retirer
```

### Example Request - Add Premium Role
```bash
curl -X POST "http://moddy.railway.internal:3000/internal/roles/update" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "plan": "moddy_max",
    "add_roles": ["1234567890123456789"],
    "remove_roles": null
  }'
```

### Example Request - Remove Premium Role
```bash
curl -X POST "http://moddy.railway.internal:3000/internal/roles/update" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "plan": "free",
    "add_roles": null,
    "remove_roles": ["1234567890123456789"]
  }'
```

### Python Example (Backend → Bot)
```python
# app/services/bot_client.py

class BotClient:
    async def update_user_role(
        self,
        discord_id: str,
        plan: str,
        add_roles: list[str] = None,
        remove_roles: list[str] = None
    ):
        """Update user's Discord roles"""
        try:
            response = await self.client.post(
                "/internal/roles/update",
                headers=self._get_auth_headers(),
                json={
                    "discord_id": discord_id,
                    "plan": plan,
                    "add_roles": add_roles,
                    "remove_roles": remove_roles
                }
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to update roles: {e}")
            raise BotClientError(f"Role update failed: {str(e)}")

# Usage - Add premium role
bot_client = BotClient()

await bot_client.update_user_role(
    discord_id="123456789012345678",
    plan="moddy_max",
    add_roles=["1234567890123456789"]  # Moddy Max role ID
)

# Usage - Remove premium role
await bot_client.update_user_role(
    discord_id="123456789012345678",
    plan="free",
    remove_roles=["1234567890123456789"]
)
```

## Response

### Success Response (200 OK)
```json
{
  "success": true,
  "message": "Roles updated successfully",
  "roles_updated": true,
  "guild_id": "987654321098765432"
}
```

### Error Response - User Not in Server (200 OK)
```json
{
  "success": false,
  "message": "User not found in Discord server",
  "roles_updated": false
}
```

### Error Response - Role Not Found (200 OK)
```json
{
  "success": false,
  "message": "Role not found in server",
  "roles_updated": false
}
```

### Response Schema
```python
class InternalUpdateRoleResponse(BaseModel):
    success: bool              # Si la mise à jour a réussi
    message: str               # Message de confirmation
    roles_updated: bool        # Si les rôles ont été modifiés
    guild_id: Optional[str]    # ID du serveur Discord
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

### 500 Internal Server Error
```json
{
  "success": false,
  "message": "Failed to update roles: Missing permissions",
  "roles_updated": false
}
```

## Implementation (Bot Side)

### FastAPI Implementation
```python
# bot/routes/internal.py

from fastapi import APIRouter, HTTPException
from app.schemas.internal import InternalUpdateRoleRequest, InternalUpdateRoleResponse
import discord

router = APIRouter(prefix="/internal")

# Configuration des rôles par plan
PLAN_ROLES = {
    "moddy_max": "1234567890123456789",  # ID du rôle Moddy Max
    "free": None  # Pas de rôle pour free
}

# ID du serveur Discord principal
MAIN_GUILD_ID = 987654321098765432

@router.post("/roles/update", response_model=InternalUpdateRoleResponse)
async def update_user_roles(payload: InternalUpdateRoleRequest):
    """Update user's Discord roles based on plan"""

    try:
        # Récupérer le serveur Discord
        guild = bot.get_guild(MAIN_GUILD_ID)
        if not guild:
            return InternalUpdateRoleResponse(
                success=False,
                message="Guild not found",
                roles_updated=False
            )

        # Récupérer le membre
        member = guild.get_member(int(payload.discord_id))
        if not member:
            return InternalUpdateRoleResponse(
                success=False,
                message="User not found in Discord server",
                roles_updated=False
            )

        # Ajouter les rôles
        if payload.add_roles:
            for role_id in payload.add_roles:
                role = guild.get_role(int(role_id))
                if role:
                    await member.add_roles(role, reason=f"Plan updated to {payload.plan}")
                    logger.info(f"✅ Added role {role.name} to {member.name}")
                else:
                    logger.warning(f"⚠️ Role {role_id} not found")

        # Retirer les rôles
        if payload.remove_roles:
            for role_id in payload.remove_roles:
                role = guild.get_role(int(role_id))
                if role:
                    await member.remove_roles(role, reason=f"Plan updated to {payload.plan}")
                    logger.info(f"✅ Removed role {role.name} from {member.name}")
                else:
                    logger.warning(f"⚠️ Role {role_id} not found")

        return InternalUpdateRoleResponse(
            success=True,
            message="Roles updated successfully",
            roles_updated=True,
            guild_id=str(MAIN_GUILD_ID)
        )

    except discord.Forbidden:
        return InternalUpdateRoleResponse(
            success=False,
            message="Bot lacks permissions to manage roles",
            roles_updated=False
        )

    except Exception as e:
        logger.error(f"Error updating roles: {e}", exc_info=True)
        return InternalUpdateRoleResponse(
            success=False,
            message=f"Failed to update roles: {str(e)}",
            roles_updated=False
        )
```

### Automatic Role Assignment by Plan
```python
# Simplification: Le bot détermine automatiquement les rôles selon le plan

@router.post("/roles/update", response_model=InternalUpdateRoleResponse)
async def update_user_roles(payload: InternalUpdateRoleRequest):
    """Update user's Discord roles based on plan"""

    guild = bot.get_guild(MAIN_GUILD_ID)
    member = guild.get_member(int(payload.discord_id))

    # Configuration des rôles par plan
    PLAN_ROLE_IDS = {
        "moddy_max": "1234567890123456789",
        "moddy_premium": "2345678901234567890",
        "free": None
    }

    # Rôles premium à retirer si l'utilisateur downgrade
    PREMIUM_ROLES = ["1234567890123456789", "2345678901234567890"]

    try:
        # Retirer tous les rôles premium
        for role_id in PREMIUM_ROLES:
            role = guild.get_role(int(role_id))
            if role and role in member.roles:
                await member.remove_roles(role)

        # Ajouter le nouveau rôle si le plan en a un
        new_role_id = PLAN_ROLE_IDS.get(payload.plan)
        if new_role_id:
            role = guild.get_role(int(new_role_id))
            if role:
                await member.add_roles(role, reason=f"Subscription: {payload.plan}")

        return InternalUpdateRoleResponse(
            success=True,
            message=f"Roles updated for plan: {payload.plan}",
            roles_updated=True,
            guild_id=str(MAIN_GUILD_ID)
        )

    except Exception as e:
        logger.error(f"Role update failed: {e}")
        return InternalUpdateRoleResponse(
            success=False,
            message=str(e),
            roles_updated=False
        )
```

## Backend Usage Examples

### Stripe Webhook - Subscription Created
```python
# app/routes/payments.py

@payment_router.post("/webhook")
async def stripe_webhook(request: Request):
    event = stripe.Event.construct_from(...)

    if event.type == "checkout.session.completed":
        session = event.data.object
        discord_id = session.get("metadata", {}).get("discord_id")

        if discord_id and session.get("payment_status") == "paid":
            bot_client = get_bot_client()

            # Notifier l'utilisateur
            await bot_client.notify_user(
                discord_id=discord_id,
                action=UserAction.SUBSCRIPTION_CREATED,
                plan="moddy_max"
            )

            # Mettre à jour les rôles Discord
            await bot_client.update_user_role(
                discord_id=discord_id,
                plan="moddy_max"
            )

            logger.info(f"✅ Roles Discord mis à jour pour discord_id={discord_id}")
```

### Stripe Webhook - Subscription Deleted
```python
elif event.type == "customer.subscription.deleted":
    subscription = event.data.object
    discord_id = subscription.metadata.get("discord_id")

    if discord_id:
        bot_client = get_bot_client()

        # Notifier l'utilisateur
        await bot_client.notify_user(
            discord_id=discord_id,
            action=UserAction.SUBSCRIPTION_CANCELLED,
            plan="free"
        )

        # Retirer les rôles premium
        await bot_client.update_user_role(
            discord_id=discord_id,
            plan="free"
        )

        logger.info(f"✅ Rôles premium retirés pour discord_id={discord_id}")
```

## Discord Role Configuration

### Finding Role IDs
Pour trouver l'ID d'un rôle Discord:

1. Activer le mode développeur Discord (Settings → Advanced → Developer Mode)
2. Clic droit sur le rôle → Copy ID
3. Utiliser l'ID dans la configuration

Ou via le bot:
```python
@bot.slash_command(name="role_id", description="Get role ID")
async def get_role_id(ctx, role: discord.Role):
    await ctx.respond(f"Role ID: {role.id}")
```

### Creating Roles Programmatically
```python
# Créer le rôle Moddy Max si il n'existe pas
guild = bot.get_guild(MAIN_GUILD_ID)

moddy_max_role = discord.utils.get(guild.roles, name="Moddy Max")

if not moddy_max_role:
    moddy_max_role = await guild.create_role(
        name="Moddy Max",
        color=discord.Color.gold(),
        hoist=True,  # Afficher séparément dans la liste
        mentionable=True
    )
    print(f"Created role: {moddy_max_role.id}")
```

### Role Hierarchy
⚠️ **Important**: Le bot doit avoir un rôle **supérieur** aux rôles qu'il veut gérer.

```
Hiérarchie des rôles (haut = plus de pouvoir):
1. Owner (propriétaire du serveur)
2. Admin
3. Bot Moddy (← Le bot doit être ICI)
4. Moddy Max (← Pour gérer ce rôle)
5. Member
6. @everyone
```

Sinon, erreur: `discord.Forbidden: 403 Forbidden (error code: 50013): Missing Permissions`

## Bot Permissions Required

Le bot doit avoir la permission **"Manage Roles"** (`MANAGE_ROLES`):

```python
# Bot invite URL avec permissions
permissions = discord.Permissions()
permissions.manage_roles = True
permissions.send_messages = True
permissions.read_messages = True

invite_url = discord.utils.oauth_url(
    client_id=bot.user.id,
    permissions=permissions
)
print(f"Invite bot: {invite_url}")
```

## Important Notes

### Don't Fail the Webhook
⚠️ Si la mise à jour des rôles échoue, **ne pas faire échouer le webhook Stripe**.

```python
try:
    await bot_client.update_user_role(discord_id, plan="moddy_max")
    logger.info("✅ Roles updated")
except BotClientError as e:
    # Log mais continue
    logger.error(f"❌ Failed to update roles: {e}")
    # Le paiement a réussi, on confirme quand même à Stripe

return JSONResponse(content={"status": "success"})
```

### User Not in Server
Si l'utilisateur n'est pas dans le serveur Discord, l'update échouera.

**Solutions**:
1. Encourager les utilisateurs à rejoindre avant de payer
2. Stocker les rôles en DB et les appliquer quand l'utilisateur rejoint
3. Demander le servername Discord lors du paiement

### Multiple Guilds
Si le bot est dans plusieurs serveurs:

```python
# Option 1: Spécifier le guild_id dans la requête
await bot_client.update_user_role(
    discord_id=discord_id,
    plan="moddy_max",
    guild_id="987654321098765432"
)

# Option 2: Mettre à jour dans tous les guilds où l'utilisateur est présent
for guild in bot.guilds:
    member = guild.get_member(int(discord_id))
    if member:
        # Update roles in this guild
        pass
```

## Logs

### Backend Logs
```
INFO: 🎭 Updating Discord roles for discord_id=123456789012345678, plan=moddy_max
INFO: ✅ Rôles Discord mis à jour
WARNING: ⚠️ Failed to update roles: User not in server
ERROR: ❌ Role update failed: Connection timeout
```

### Bot Logs
```
INFO: 🎭 Role update request: discord_id=123456789012345678, plan=moddy_max
INFO: ✅ Added role "Moddy Max" to user User#1234
INFO: ✅ Removed role "Free Member" from user User#1234
WARNING: ⚠️ User 123456789012345678 not found in server
ERROR: ❌ Missing permissions to manage roles
```

## Related Endpoints
- Bot Health: `GET http://moddy.railway.internal:3000/internal/health`
- Bot Notify User: `POST http://moddy.railway.internal:3000/internal/notify`
- Backend Webhook: `POST /pay/webhook` (calls this endpoint)
