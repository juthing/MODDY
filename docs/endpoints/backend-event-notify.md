# Backend Event Notify

## Endpoint
`POST /internal/event/notify`

## Description
Permet au bot Discord de notifier le backend d'événements Discord pour tracking, analytics et webhooks.

## Use Case
- Logger les événements Discord pour analytics
- Déclencher des webhooks externes
- Mettre à jour des statistiques en base de données
- Tracker l'activité des utilisateurs
- Audit trail des actions importantes

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request

### Request Body Schema
```python
class BotEventType(str, Enum):
    """Types d'événements Discord disponibles"""
    MEMBER_JOINED = "member_joined"      # Membre rejoint le serveur
    MEMBER_LEFT = "member_left"          # Membre quitte le serveur
    ROLE_UPDATED = "role_updated"        # Rôles modifiés
    COMMAND_USED = "command_used"        # Commande utilisée
    MESSAGE_SENT = "message_sent"        # Message envoyé

class BotEventNotifyRequest(BaseModel):
    event_type: BotEventType           # Type d'événement
    discord_id: str                    # Discord ID de l'utilisateur
    metadata: Optional[dict]           # Données additionnelles
```

### Example Request - Member Joined
```bash
curl -X POST "http://website-backend.railway.internal:8080/internal/event/notify" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "member_joined",
    "discord_id": "123456789012345678",
    "metadata": {
      "guild_id": "987654321098765432",
      "guild_name": "Moddy Server",
      "joined_at": "2024-01-20T15:30:00Z"
    }
  }'
```

### Example Request - Command Used
```bash
curl -X POST "http://website-backend.railway.internal:8080/internal/event/notify" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "command_used",
    "discord_id": "123456789012345678",
    "metadata": {
      "command": "/subscription",
      "channel_id": "111222333444555666",
      "timestamp": "2024-01-20T15:45:00Z"
    }
  }'
```

### Python Example
```python
import httpx
from app.schemas.internal import BotEventNotifyRequest, BotEventType

async def notify_backend_event(event_type: BotEventType, discord_id: str, metadata: dict = None):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://website-backend.railway.internal:8080/internal/event/notify",
            headers={"Authorization": "Bearer your_secret_key_here"},
            json={
                "event_type": event_type.value,
                "discord_id": discord_id,
                "metadata": metadata
            }
        )
        return response.json()

# Usage - Member joined
await notify_backend_event(
    event_type=BotEventType.MEMBER_JOINED,
    discord_id="123456789012345678",
    metadata={
        "guild_id": "987654321098765432",
        "joined_at": "2024-01-20T15:30:00Z"
    }
)

# Usage - Command used
await notify_backend_event(
    event_type=BotEventType.COMMAND_USED,
    discord_id="123456789012345678",
    metadata={
        "command": "/profile",
        "success": True
    }
)
```

## Response

### Success Response (200 OK)
```json
{
  "success": true,
  "message": "Event member_joined processed successfully",
  "event_received": true
}
```

### Response Schema
```python
class BotEventNotifyResponse(BaseModel):
    success: bool          # Si l'événement a été traité
    message: str           # Message de confirmation
    event_received: bool   # Si l'événement a été reçu et traité
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
  "detail": "Failed to process event"
}
```

## Implementation Notes
- **Actuellement**: Endpoint de base qui log les événements
- **TODO**: Implémenter la logique métier pour chaque type d'événement
  - Mettre à jour des statistiques en DB
  - Déclencher des webhooks
  - Envoyer des notifications
  - Logger des analytics

### Future Implementation Ideas
```python
# Exemples de traitement d'événements:

if event.event_type == BotEventType.MEMBER_JOINED:
    # Incrémenter compteur de membres
    # Envoyer email de bienvenue
    # Logger dans analytics
    pass

elif event.event_type == BotEventType.COMMAND_USED:
    # Tracker usage des commandes
    # Mettre à jour stats utilisateur
    pass

elif event.event_type == BotEventType.ROLE_UPDATED:
    # Logger changements de rôles
    # Sync avec système de permissions
    pass
```

## Event Types

### member_joined
Quand un utilisateur rejoint le serveur Discord.

**Metadata suggérées**:
- `guild_id`: ID du serveur
- `guild_name`: Nom du serveur
- `joined_at`: Date de join (ISO 8601)

### member_left
Quand un utilisateur quitte le serveur.

**Metadata suggérées**:
- `guild_id`: ID du serveur
- `left_at`: Date de départ
- `reason`: Raison (kick, ban, left)

### role_updated
Quand les rôles d'un utilisateur changent.

**Metadata suggérées**:
- `added_roles`: Liste des rôles ajoutés
- `removed_roles`: Liste des rôles retirés
- `updated_by`: Discord ID du modérateur

### command_used
Quand un utilisateur utilise une commande.

**Metadata suggérées**:
- `command`: Nom de la commande
- `success`: Si la commande a réussi
- `channel_id`: ID du canal
- `execution_time_ms`: Temps d'exécution

### message_sent
Quand un message est envoyé (si tracking activé).

**Metadata suggérées**:
- `channel_id`: ID du canal
- `message_length`: Longueur du message
- `has_attachments`: Si le message a des pièces jointes

## Logs
```
INFO: 📩 Événement reçu du bot: type=member_joined, discord_id=123456789012345678
INFO: ✅ Événement traité: member_joined
ERROR: ❌ Erreur lors du traitement de l'événement: Database connection failed
```

## Related Endpoints
- User Info: `POST /internal/user/info`
