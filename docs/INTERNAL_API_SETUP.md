# Configuration de l'API Interne

Ce document explique comment configurer l'API interne pour la communication bidirectionnelle entre le bot Discord et le backend.

## Architecture

Le bot Discord et le backend communiquent via **Railway Private Networking** en utilisant HTTP + JSON de manière **BIDIRECTIONNELLE**.

```
┌─────────────────────────────────────────────┐
│         Railway Project: Moddy              │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────┐                      │
│  │     Backend      │                      │
│  │  (Python/FastAPI)│                      │
│  │  website-backend │                      │
│  │ .railway.internal│                      │
│  │   Port: 8080     │                      │
│  └───────┬──────────┘                      │
│          │  ▲                               │
│          │  │                               │
│          │  │  HTTP + JSON                  │
│          │  │  Authorization: Bearer SECRET │
│          │  │  (via Private Network)        │
│          ▼  │                               │
│  ┌──────────────────┐                      │
│  │   Bot Discord    │                      │
│  │   (Python)       │                      │
│  │     moddy        │                      │
│  │ .railway.internal│                      │
│  │                  │                      │
│  │  Port 8080 (Public) ← Discord API      │
│  │  Port 3000 (Privé)  ← Communication    │
│  │                       interne           │
│  └──────────────────┘                      │
│                                             │
└─────────────────────────────────────────────┘
```

## Variables d'environnement requises

### Pour le Bot Discord

Ajouter ces variables dans Railway pour le service `moddy` (bot Discord) :

```bash
# Secret partagé pour l'authentification (DOIT être identique au backend)
INTERNAL_API_SECRET=<générer-avec-secrets.token_urlsafe(32)>

# Port du serveur HTTP interne (privé, non exposé publiquement)
INTERNAL_PORT=3000

# URL du backend pour que le bot puisse communiquer avec lui
BACKEND_INTERNAL_URL=http://website-backend.railway.internal:8080

# ID du serveur Discord principal (pour la gestion des rôles)
MODDY_GUILD_ID=<id-du-serveur-discord>
```

### Génération du secret

Le secret doit être **identique** dans les deux services (backend et bot). Générer un secret sécurisé :

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Exemple de sortie :
```
k8j2h3g4f5d6s7a8p9o0i1u2y3t4r5e6w7q8z9x0c1v2b3n4m5
```

⚠️ **Important :**
- Ne **jamais** commiter ce secret dans le code
- Le secret doit être **identique** dans le backend et le bot
- Configurer via Railway Environment Variables

## Endpoints exposés par le bot

Le bot expose 3 endpoints internes sur le port 3000 (privé) :

### 1. GET `/internal/health`

Health check pour vérifier que le bot est accessible.

**Headers requis :**
```
Authorization: Bearer {INTERNAL_API_SECRET}
```

**Réponse (200 OK) :**
```json
{
  "status": "healthy",
  "service": "discord-bot",
  "version": "1.0.0"
}
```

### 2. POST `/internal/notify`

Notifie le bot d'un événement utilisateur (paiement, upgrade, etc.).

**Headers requis :**
```
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Payload :**
```json
{
  "discord_id": "123456789012345678",
  "action": "subscription_created",
  "plan": "moddy_max",
  "metadata": {
    "customer_id": "cus_ABC123",
    "email": "user@example.com"
  }
}
```

**Réponse (200 OK) :**
```json
{
  "success": true,
  "message": "User notified successfully",
  "notification_sent": true
}
```

### 3. POST `/internal/roles/update`

Met à jour les rôles Discord d'un utilisateur.

**Headers requis :**
```
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Payload :**
```json
{
  "discord_id": "123456789012345678",
  "plan": "moddy_max",
  "add_roles": ["987654321098765432"],
  "remove_roles": ["111222333444555666"]
}
```

**Réponse (200 OK) :**
```json
{
  "success": true,
  "message": "Roles updated successfully",
  "roles_updated": true,
  "guild_id": "999888777666555444"
}
```

## Client HTTP pour le backend

Le bot peut également communiquer avec le backend via le `BackendClient` :

### Utilisation dans le code

```python
from services import get_backend_client, BackendClientError

# Récupérer l'instance singleton du client
backend_client = get_backend_client()

# Vérifier le health du backend
try:
    health = await backend_client.health_check()
    print(f"Backend status: {health['status']}")
except BackendClientError as e:
    print(f"Backend unreachable: {e}")

# Récupérer les informations d'un utilisateur
try:
    user_info = await backend_client.get_user_info("123456789012345678")
    if user_info["user_found"]:
        print(f"Email: {user_info['email']}")
    else:
        print("User not found in database")
except BackendClientError as e:
    print(f"Error: {e}")

# Notifier le backend d'un événement Discord
try:
    response = await backend_client.notify_event(
        event_type="member_joined",
        discord_id="123456789012345678",
        metadata={
            "guild_id": "999888777666555444",
            "username": "JohnDoe"
        }
    )
    print(f"Event notified: {response}")
except BackendClientError as e:
    print(f"Error: {e}")
```

## Sécurité

### Middleware d'authentification

Toutes les requêtes vers `/internal/*` sont protégées par un middleware d'authentification global qui :

1. Vérifie la présence du header `Authorization`
2. Vérifie le format `Bearer {SECRET}`
3. Vérifie que le secret correspond à `INTERNAL_API_SECRET`

Si l'une de ces vérifications échoue, la requête est rejetée avec une erreur 401 ou 403.

### Railway Private Networking

Les DNS internes sont automatiquement configurés par Railway :

- Backend: `website-backend.railway.internal`
- Bot: `moddy.railway.internal`

Ces URLs sont **uniquement accessibles** entre services du même projet Railway et ne sont jamais exposées publiquement.

### Séparation Public/Privé

Le bot écoute sur **deux ports différents** :

1. **Port 8080** (`$PORT`) : Exposé publiquement via Railway Public Networking
   - Utilisé pour le bot Discord standard (interactions, commandes, etc.)

2. **Port 3000** (`$INTERNAL_PORT`) : Uniquement accessible via Railway Private Network
   - Utilisé uniquement pour les endpoints `/internal/*`
   - **Jamais exposé publiquement**
   - Accessible uniquement par le backend via `moddy.railway.internal:3000`

## Architecture du code

### Structure des fichiers

```
/home/user/MODDY/
├── schemas/
│   ├── __init__.py
│   └── internal.py              # Schémas Pydantic pour l'API interne
├── internal_api/
│   ├── __init__.py
│   ├── server.py                # Serveur FastAPI interne
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── auth.py              # Middleware d'authentification
│   └── routes/
│       ├── __init__.py
│       └── internal.py          # Endpoints internes
├── services/
│   ├── __init__.py
│   └── backend_client.py        # Client HTTP pour le backend
├── bot.py                       # Classe principale du bot (intégration serveur interne)
└── requirements.txt             # Dépendances (httpx ajouté)
```

### Démarrage du serveur interne

Le serveur HTTP interne est démarré automatiquement dans un thread séparé lors du démarrage du bot (méthode `setup_hook()` dans `bot.py`).

Le thread est configuré en mode `daemon=True`, ce qui signifie qu'il s'arrête automatiquement quand le bot s'arrête.

## Troubleshooting

### Le bot ne reçoit pas les requêtes du backend

1. Vérifier que `INTERNAL_API_SECRET` est identique dans les deux services
2. Vérifier que le serveur interne écoute bien sur le port 3000
3. Vérifier les logs du bot pour voir si le serveur a démarré
4. Utiliser `railway logs moddy` pour voir les logs en temps réel

### Erreur 401 Unauthorized

Le secret ne correspond pas. Vérifier :
- `INTERNAL_API_SECRET` est identique dans le backend et le bot
- Le header `Authorization` est bien `Bearer {SECRET}` (avec "Bearer " au début)
- Pas d'espaces supplémentaires dans le secret

### Erreur de connexion (Connection refused)

Le serveur interne n'est pas accessible :
- Vérifier que le serveur HTTP interne écoute bien sur le port 3000
- Vérifier les logs du bot pour voir si le thread a bien démarré
- Vérifier que le serveur écoute sur `::` et non `0.0.0.0` ou `localhost`
- Vérifier que Railway Private Networking est activé pour le projet

### Le serveur interne ne démarre pas

- Vérifier qu'il n'y a pas de conflit de port
- Vérifier les logs du bot pour voir les erreurs de démarrage
- S'assurer que FastAPI et uvicorn sont installés dans les dépendances

## Documentation complète

Pour plus d'informations, consulter `/documentation/internal-api.md` qui contient la documentation complète de l'API interne.

## Support

Pour toute question sur l'API interne, contactez l'équipe de développement de Moddy.

**Version de la documentation:** 1.0
**Date:** 2026-01-07
**Auteur:** Claude (intégration basée sur internal-api.md)
