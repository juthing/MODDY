# Backend User Info

## Endpoint
`POST /internal/user/info`

## Description
Permet au bot Discord de récupérer les informations d'un utilisateur depuis la base de données PostgreSQL du backend.

## Use Case
- Récupérer l'email d'un utilisateur à partir de son Discord ID
- Vérifier si un utilisateur existe dans la base de données
- Afficher les dates de création/mise à jour du compte
- Commandes Discord nécessitant des données utilisateur

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request

### Request Body Schema
```python
class BotUserInfoRequest(BaseModel):
    discord_id: str  # Discord ID de l'utilisateur (Snowflake en string)
```

### Example Request
```bash
curl -X POST "http://website-backend.railway.internal:8080/internal/user/info" \
  -H "Authorization: Bearer your_secret_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678"
  }'
```

### Python Example
```python
import httpx
from app.schemas.internal import BotUserInfoRequest

async def get_user_info(discord_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://website-backend.railway.internal:8080/internal/user/info",
            headers={"Authorization": "Bearer your_secret_key_here"},
            json={"discord_id": discord_id}
        )
        return response.json()

# Usage
result = await get_user_info("123456789012345678")
if result["user_found"]:
    print(f"Email: {result['email']}")
```

## Response

### Success Response - User Found (200 OK)
```json
{
  "success": true,
  "message": "User found",
  "user_found": true,
  "discord_id": "123456789012345678",
  "email": "user@example.com",
  "created_at": "2024-01-15T10:30:00.000Z",
  "updated_at": "2024-01-20T15:45:00.000Z"
}
```

### Success Response - User Not Found (200 OK)
```json
{
  "success": false,
  "message": "User not found",
  "user_found": false
}
```

### Response Schema
```python
class BotUserInfoResponse(BaseModel):
    success: bool                    # Indique si la requête a réussi
    message: str                     # Message de confirmation ou d'erreur
    user_found: bool                 # Si l'utilisateur existe dans la DB
    discord_id: Optional[str]        # Discord ID de l'utilisateur
    email: Optional[str]             # Email de l'utilisateur
    created_at: Optional[str]        # Date de création (ISO 8601)
    updated_at: Optional[str]        # Date de dernière mise à jour (ISO 8601)
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
  "detail": "Database connection error"
}
```

## Implementation Notes
- Le Discord ID est converti en `int` pour la requête SQL
- Les dates sont retournées au format ISO 8601 (UTC)
- Si l'utilisateur n'existe pas, `success=False` mais HTTP 200 (pas une erreur système)
- La requête utilise SQLAlchemy avec connexion à PostgreSQL

## Database Query
```python
user = db.query(User).filter(User.discord_id == int(discord_id)).first()
```

## Logs
```
INFO: 📩 Requête d'info utilisateur pour discord_id=123456789012345678
INFO: ✅ Utilisateur trouvé: discord_id=123456789012345678, email=user@example.com
WARNING: ⚠️ Utilisateur non trouvé: discord_id=999999999999999999
```

## Related Endpoints
- Subscription Info: `POST /internal/subscription/info`
