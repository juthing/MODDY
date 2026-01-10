# Backend Health Check

## Endpoint
`GET /internal/health`

## Description
Health check endpoint pour vérifier que le backend est accessible depuis le bot Discord via Railway Private Network.

## Use Case
- Vérifier la disponibilité du backend avant d'effectuer des opérations critiques
- Monitoring et alertes de santé du service
- Validation de la configuration Railway Private Network

## Authentication
**Requis**: Bearer Token dans l'en-tête `Authorization`

```
Authorization: Bearer <INTERNAL_API_SECRET>
```

## Request
Aucun paramètre requis.

### Example Request
```bash
curl -X GET "http://website-backend.railway.internal:8080/internal/health" \
  -H "Authorization: Bearer your_secret_key_here"
```

### Python Example
```python
import httpx

async def check_backend_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://website-backend.railway.internal:8080/internal/health",
            headers={"Authorization": "Bearer your_secret_key_here"}
        )
        return response.json()
```

## Response

### Success Response (200 OK)
```json
{
  "status": "healthy",
  "service": "website-backend",
  "version": "1.0.0"
}
```

### Response Schema
```python
class InternalHealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]  # État du service
    service: str                              # Nom du service
    version: Optional[str]                    # Version du service
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

## Implementation Notes
- Ce endpoint est protégé par `InternalAuthMiddleware`
- Toujours disponible (pas de dépendances externes)
- Temps de réponse < 50ms typiquement
- Utilisé pour les health checks Railway

## Related Endpoints
- Bot Health Check: `GET http://moddy.railway.internal:3000/internal/health`
