# Communication Interne Backend ↔ Bot Discord

Documentation complète du système de communication interne entre le backend et le bot Discord via Railway Private Networking.

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture](#architecture)
3. [Sécurité](#sécurité)
4. [Endpoints du Bot (À implémenter)](#endpoints-du-bot-à-implémenter)
5. [Schémas de données](#schémas-de-données)
6. [Configuration Railway](#configuration-railway)
7. [Exemples d'utilisation](#exemples-dutilisation)
8. [Guide d'implémentation pour le Bot](#guide-dimplémentation-pour-le-bot)

---

## Vue d'ensemble

Le backend et le bot Discord communiquent via **Railway Private Networking** en utilisant HTTP + JSON de manière **BIDIRECTIONNELLE**.

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

### Communication bidirectionnelle

**Backend → Bot (Port 3000):**
- Notifier le bot d'événements (paiements, upgrades)
- Mettre à jour les rôles Discord
- Health checks

**Bot → Backend (Port 8080):**
- Récupérer les informations utilisateur de la DB
- Notifier le backend d'événements Discord
- Health checks

### Caractéristiques

- ✅ **HTTP + JSON uniquement** - Simple et universel
- ✅ **Railway Private Networking** - URLs `.railway.internal`
- ✅ **Un seul secret partagé** - `INTERNAL_API_SECRET`
- ✅ **Middleware global** - Pas d'auth par endpoint
- ✅ **Endpoints non exposés** - Réseau interne uniquement
- ✅ **Communication bidirectionnelle** - Backend ↔ Bot
- ✅ **Production-ready** - Gestion d'erreurs complète

---

## Architecture

### Côté Backend (Déjà implémenté)

Le backend dispose d'un **client HTTP** pour communiquer avec le bot :

```python
# app/services/bot_client.py
class BotClient:
    def __init__(self, bot_url: str, api_secret: str):
        self.bot_url = bot_url  # http://moddy.railway.internal:3000
        self.api_secret = api_secret
        self.client = httpx.AsyncClient(base_url=self.bot_url, timeout=10.0)

    def _get_auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_secret}"}

    async def notify_user(self, discord_id, action, plan, metadata):
        # Envoie une notification au bot
        ...

    async def update_user_role(self, discord_id, plan, add_roles, remove_roles):
        # Demande au bot de mettre à jour les rôles
        ...

    async def health_check(self):
        # Vérifie que le bot est accessible
        ...
```

**Le client ajoute automatiquement le header `Authorization: Bearer {SECRET}` à toutes les requêtes.**

### Côté Bot (À implémenter)

Le bot doit :

1. **Démarrer un serveur HTTP** (FastAPI, Flask, aiohttp, etc.)
2. **Écouter sur un port SÉPARÉ** (recommandé: 3000) uniquement pour les endpoints internes
3. **Implémenter un middleware d'authentification global**
4. **Exposer 3 endpoints internes**

**⚠️ Architecture recommandée :**
- **Port 8080** (ou `$PORT`) : Bot Discord standard (public)
- **Port 3000** : Serveur HTTP interne (privé, uniquement accessible via Railway Private Network)

---

## Sécurité

### Principe

Toutes les requêtes entre services utilisent un **secret partagé** pour s'authentifier.

```
Backend                                 Bot Discord
  │                                        │
  │  POST /internal/notify                 │
  │  Authorization: Bearer abc123...       │
  ├────────────────────────────────────────>│
  │                                        │
  │                          ✅ Vérifie le secret
  │                          ✅ Traite la requête
  │                                        │
  │  {"success": true, "message": "OK"}    │
  │<────────────────────────────────────────┤
  │                                        │
```

### Variables d'environnement

Les deux services doivent avoir :

| Variable | Valeur | Description |
|----------|--------|-------------|
| `INTERNAL_API_SECRET` | `<secret-partagé>` | Secret pour authentifier les requêtes internes |
| `BOT_INTERNAL_URL` | `http://moddy.railway.internal:3000` | (Backend uniquement) URL interne du bot |
| `INTERNAL_PORT` | `3000` | (Bot uniquement) Port du serveur HTTP interne |

**⚠️ Important :**
- Le secret doit être **identique** dans les deux services
- Ne **jamais** commiter ce secret dans le code
- Configurer via Railway Environment Variables

### Génération du secret

```bash
# Générer un secret sécurisé
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Exemple de sortie:
# k8j2h3g4f5d6s7a8p9o0i1u2y3t4r5e6w7q8z9x0c1v2b3n4m5
```

---

## Endpoints du Bot (À implémenter)

Le bot Discord doit exposer ces 3 endpoints sur son réseau interne.

### 1. Health Check

**Endpoint:** `GET /internal/health`

**Description:** Vérifie que le bot est accessible et en bonne santé.

**Headers requis:**
```
Authorization: Bearer {INTERNAL_API_SECRET}
```

**Réponse (200 OK):**
```json
{
  "status": "healthy",
  "service": "discord-bot",
  "version": "1.0.0"
}
```

**Exemple d'appel depuis le backend:**
```python
bot_client = get_bot_client()
response = await bot_client.health_check()
# response = InternalHealthResponse(status="healthy", service="discord-bot", version="1.0.0")
```

---

### 2. Notifier un utilisateur

**Endpoint:** `POST /internal/notify`

**Description:** Notifie le bot d'un événement utilisateur (paiement, upgrade, etc.)

**Headers requis:**
```
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Payload (Request Body):**
```json
{
  "discord_id": "123456789012345678",
  "action": "subscription_created",
  "plan": "moddy_max",
  "metadata": {
    "customer_id": "cus_ABC123",
    "email": "user@example.com",
    "phone": "+33612345678",
    "subscription_type": "month"
  }
}
```

**Champs:**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `discord_id` | string | ✅ | Discord ID de l'utilisateur (Snowflake) |
| `action` | string | ✅ | Action effectuée (voir [Actions possibles](#actions-possibles)) |
| `plan` | string | ❌ | Nom du plan (`"moddy_max"`, `"free"`) |
| `metadata` | object | ❌ | Métadonnées additionnelles |

**Actions possibles:**

| Action | Description |
|--------|-------------|
| `subscription_created` | Nouvelle souscription créée |
| `subscription_updated` | Souscription mise à jour |
| `subscription_cancelled` | Souscription annulée |
| `plan_upgraded` | Plan amélioré |
| `plan_downgraded` | Plan rétrogradé |

**Réponse (200 OK):**
```json
{
  "success": true,
  "message": "User notified successfully",
  "notification_sent": true
}
```

**Exemple d'appel depuis le backend:**
```python
bot_client = get_bot_client()
response = await bot_client.notify_user(
    discord_id="123456789012345678",
    action="subscription_created",
    plan="moddy_max",
    metadata={
        "customer_id": "cus_ABC123",
        "email": "user@example.com"
    }
)
# response.success = True
# response.notification_sent = True
```

---

### 3. Mettre à jour les rôles Discord

**Endpoint:** `POST /internal/roles/update`

**Description:** Demande au bot de mettre à jour les rôles Discord d'un utilisateur.

**Headers requis:**
```
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Payload (Request Body):**
```json
{
  "discord_id": "123456789012345678",
  "plan": "moddy_max",
  "add_roles": ["987654321098765432"],
  "remove_roles": ["111222333444555666"]
}
```

**Champs:**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `discord_id` | string | ✅ | Discord ID de l'utilisateur |
| `plan` | string | ✅ | Nouveau plan de l'utilisateur |
| `add_roles` | array[string] | ❌ | Liste des IDs de rôles à ajouter |
| `remove_roles` | array[string] | ❌ | Liste des IDs de rôles à retirer |

**Réponse (200 OK):**
```json
{
  "success": true,
  "message": "Roles updated successfully",
  "roles_updated": true,
  "guild_id": "999888777666555444"
}
```

**Exemple d'appel depuis le backend:**
```python
bot_client = get_bot_client()
response = await bot_client.update_user_role(
    discord_id="123456789012345678",
    plan="moddy_max"
)
# response.success = True
# response.roles_updated = True
```

---

## Endpoints du Backend (Déjà implémentés)

Le backend expose ces 3 endpoints pour que le bot puisse communiquer avec lui.

### 1. Health Check (Backend)

**Endpoint:** `GET /internal/health`

**Description:** Vérifie que le backend est accessible depuis le bot.

**Headers requis:**
```
Authorization: Bearer {INTERNAL_API_SECRET}
```

**Réponse (200 OK):**
```json
{
  "status": "healthy",
  "service": "website-backend",
  "version": "1.0.0"
}
```

**Exemple d'appel depuis le bot:**
```python
# Dans le bot, créer un client HTTP similaire à BotClient
backend_client = BackendClient()
response = await backend_client.health_check()
```

---

### 2. Récupérer les informations utilisateur

**Endpoint:** `POST /internal/user/info`

**Description:** Permet au bot de récupérer les informations d'un utilisateur depuis la base de données du backend.

**Headers requis:**
```
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Payload (Request Body):**
```json
{
  "discord_id": "123456789012345678"
}
```

**Champs:**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `discord_id` | string | ✅ | Discord ID de l'utilisateur à récupérer |

**Réponse (200 OK) - Utilisateur trouvé:**
```json
{
  "success": true,
  "message": "User found",
  "user_found": true,
  "discord_id": "123456789012345678",
  "email": "user@example.com",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-20T14:25:00Z"
}
```

**Réponse (200 OK) - Utilisateur non trouvé:**
```json
{
  "success": false,
  "message": "User not found",
  "user_found": false
}
```

**Exemple d'appel depuis le bot:**
```python
backend_client = BackendClient()
response = await backend_client.get_user_info(discord_id="123456789012345678")
if response.user_found:
    print(f"Email: {response.email}")
else:
    print("Utilisateur non trouvé dans la DB")
```

**Cas d'usage:**
- Vérifier si un utilisateur a un compte sur le site
- Récupérer l'email d'un utilisateur
- Afficher les informations du compte dans une commande Discord

---

### 3. Notifier le backend d'un événement Discord

**Endpoint:** `POST /internal/event/notify`

**Description:** Permet au bot de notifier le backend d'événements Discord (membre qui rejoint, commande utilisée, etc.)

**Headers requis:**
```
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Payload (Request Body):**
```json
{
  "event_type": "member_joined",
  "discord_id": "123456789012345678",
  "metadata": {
    "guild_id": "999888777666555444",
    "timestamp": "2024-01-20T15:30:00Z"
  }
}
```

**Champs:**

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `event_type` | string | ✅ | Type d'événement (voir types ci-dessous) |
| `discord_id` | string | ✅ | Discord ID de l'utilisateur concerné |
| `metadata` | object | ❌ | Métadonnées additionnelles |

**Types d'événements possibles:**

| Événement | Description |
|-----------|-------------|
| `member_joined` | Un membre a rejoint le serveur Discord |
| `member_left` | Un membre a quitté le serveur Discord |
| `role_updated` | Les rôles d'un membre ont été modifiés |
| `command_used` | Une commande bot a été utilisée |
| `message_sent` | Un message a été envoyé (si logging activé) |

**Réponse (200 OK):**
```json
{
  "success": true,
  "message": "Event member_joined processed successfully",
  "event_received": true
}
```

**Exemple d'appel depuis le bot:**
```python
# Dans un event listener Discord
@bot.event
async def on_member_join(member):
    backend_client = BackendClient()
    await backend_client.notify_event(
        event_type="member_joined",
        discord_id=str(member.id),
        metadata={
            "guild_id": str(member.guild.id),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

**Cas d'usage:**
- Logger les événements Discord dans la base de données du backend
- Déclencher des actions backend lors d'événements Discord
- Analytics et statistiques

---

## Schémas de données

Les schémas Pydantic sont définis dans `app/schemas/internal.py` côté backend.

**Pour le bot, vous devez créer les mêmes schémas.**

### Schémas Backend → Bot

### UserAction (Enum)

```python
class UserAction(str, Enum):
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PLAN_UPGRADED = "plan_upgraded"
    PLAN_DOWNGRADED = "plan_downgraded"
```

### InternalNotifyUserRequest

```python
class InternalNotifyUserRequest(BaseModel):
    discord_id: str
    action: UserAction
    plan: Optional[str] = None
    metadata: Optional[dict] = None
```

### InternalNotifyUserResponse

```python
class InternalNotifyUserResponse(BaseModel):
    success: bool
    message: str
    notification_sent: bool = False
```

### InternalUpdateRoleRequest

```python
class InternalUpdateRoleRequest(BaseModel):
    discord_id: str
    plan: str
    add_roles: Optional[list[str]] = None
    remove_roles: Optional[list[str]] = None
```

### InternalUpdateRoleResponse

```python
class InternalUpdateRoleResponse(BaseModel):
    success: bool
    message: str
    roles_updated: bool = False
    guild_id: Optional[str] = None
```

### InternalHealthResponse

```python
class InternalHealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    service: str
    version: Optional[str] = None
```

### Schémas Bot → Backend

### BotUserInfoRequest

```python
class BotUserInfoRequest(BaseModel):
    discord_id: str  # Discord ID de l'utilisateur à récupérer
```

### BotUserInfoResponse

```python
class BotUserInfoResponse(BaseModel):
    success: bool
    message: str
    user_found: bool
    discord_id: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

### BotEventType (Enum)

```python
class BotEventType(str, Enum):
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    ROLE_UPDATED = "role_updated"
    COMMAND_USED = "command_used"
    MESSAGE_SENT = "message_sent"
```

### BotEventNotifyRequest

```python
class BotEventNotifyRequest(BaseModel):
    event_type: BotEventType
    discord_id: str
    metadata: Optional[dict] = None
```

### BotEventNotifyResponse

```python
class BotEventNotifyResponse(BaseModel):
    success: bool
    message: str
    event_received: bool
```

---

## Configuration Railway

### Variables d'environnement à configurer

#### Backend (website-backend)

```bash
# Déjà configurées
DATABASE_URL=...
A_API_KEY=...
DISCORD_CLIENT_ID=...
DISCORD_CLIENT_SECRET=...
STRIPE_API_KEY=...

# À AJOUTER pour la communication interne
INTERNAL_API_SECRET=<générer-avec-secrets.token_urlsafe(32)>
BOT_INTERNAL_URL=http://moddy.railway.internal:3000
```

#### Bot Discord (moddy)

```bash
# Déjà configurées
DISCORD_TOKEN=...
PORT=8080  # Port pour le bot Discord standard (public)
# ... autres variables du bot ...

# À AJOUTER pour la communication interne
INTERNAL_API_SECRET=<même-secret-que-backend>
INTERNAL_PORT=3000  # Port SÉPARÉ pour l'API interne (privé)
BACKEND_INTERNAL_URL=http://website-backend.railway.internal:8080  # Pour appeler le backend
```

### Railway Private Networking

Les DNS internes sont automatiquement configurés par Railway :

- Backend: `website-backend.railway.internal`
- Bot: `moddy.railway.internal`

Ces URLs sont **uniquement accessibles** entre services du même projet Railway.

**⚠️ Séparation Public/Privé :**

Pour des raisons de sécurité, le bot doit écouter sur **deux ports différents** :

1. **Port 8080** (`$PORT`) : Exposé publiquement via Railway Public Networking
   - Utilisé pour le bot Discord standard (interactions, commandes, etc.)

2. **Port 3000** (`$INTERNAL_PORT`) : Uniquement accessible via Railway Private Network
   - Utilisé uniquement pour les endpoints `/internal/*`
   - **Jamais exposé publiquement**
   - Accessible uniquement par le backend via `moddy.railway.internal:3000`

**⚠️ Important pour Python/Uvicorn :**

Chaque serveur doit écouter sur `::` (toutes les interfaces) pour supporter IPv4 et IPv6 :

```bash
# Serveur interne (port 3000)
uvicorn internal_server:app --host :: --port ${INTERNAL_PORT:-3000}
```

---

## Exemples d'utilisation

### Côté Backend (Déjà implémenté)

#### Exemple 1: Notifier après un paiement Stripe

```python
# app/routes/payments.py

from app.services.bot_client import get_bot_client, BotClientError
from app.schemas.internal import UserAction

@payment_router.post("/webhook")
async def stripe_webhook(request: Request):
    # ... traitement du webhook Stripe ...

    if payment_status == "paid":
        discord_id = session.get("metadata", {}).get("discord_id")

        if discord_id:
            try:
                bot_client = get_bot_client()

                # Notifier le bot
                await bot_client.notify_user(
                    discord_id=discord_id,
                    action=UserAction.SUBSCRIPTION_CREATED,
                    plan="moddy_max",
                    metadata={
                        "customer_id": customer_id,
                        "email": email
                    }
                )

                # Mettre à jour les rôles
                await bot_client.update_user_role(
                    discord_id=discord_id,
                    plan="moddy_max"
                )

                logger.info(f"✅ Bot notifié pour discord_id={discord_id}")

            except BotClientError as e:
                logger.error(f"❌ Erreur: {e}")
```

#### Exemple 2: Vérifier la santé du bot

```python
from app.services.bot_client import get_bot_client

bot_client = get_bot_client()
try:
    health = await bot_client.health_check()
    print(f"Bot status: {health.status}")
except BotClientError as e:
    print(f"Bot inaccessible: {e}")
```

---

## Guide d'implémentation pour le Bot

Cette section explique **comment implémenter le serveur HTTP interne dans le bot Discord**.

### Prérequis

- Bot Discord fonctionnel (discord.py, discord.js, etc.)
- Framework web Python (FastAPI recommandé, ou Flask, aiohttp)
- httpx ou requests pour les tests

### Étapes d'implémentation

#### 1. Installer les dépendances

```bash
# Si vous utilisez FastAPI
pip install fastapi uvicorn pydantic

# Ajouter à requirements.txt
fastapi==0.115.0
uvicorn==0.32.0
pydantic==2.10.0
```

#### 2. Créer les schémas Pydantic

Créer un fichier `schemas/internal.py` dans votre bot :

```python
"""
Schémas pour la communication interne avec le backend.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


class UserAction(str, Enum):
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PLAN_UPGRADED = "plan_upgraded"
    PLAN_DOWNGRADED = "plan_downgraded"


class InternalNotifyUserRequest(BaseModel):
    discord_id: str
    action: UserAction
    plan: Optional[str] = None
    metadata: Optional[dict] = None


class InternalNotifyUserResponse(BaseModel):
    success: bool
    message: str
    notification_sent: bool = False


class InternalUpdateRoleRequest(BaseModel):
    discord_id: str
    plan: str
    add_roles: Optional[list[str]] = None
    remove_roles: Optional[list[str]] = None


class InternalUpdateRoleResponse(BaseModel):
    success: bool
    message: str
    roles_updated: bool = False
    guild_id: Optional[str] = None


class InternalHealthResponse(BaseModel):
    status: Literal["healthy", "unhealthy"]
    service: str
    version: Optional[str] = None
```

#### 3. Créer le middleware d'authentification

Créer un fichier `middleware/auth.py` :

```python
"""
Middleware d'authentification pour les endpoints internes.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import os
import logging

logger = logging.getLogger(__name__)

INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET")

if not INTERNAL_API_SECRET:
    raise ValueError("INTERNAL_API_SECRET environment variable is required")


async def verify_internal_auth(request: Request, call_next):
    """
    Middleware global pour vérifier l'authentification des requêtes internes.

    Vérifie que le header Authorization contient le bon secret.
    """
    # Ne vérifier que les endpoints /internal/*
    if request.url.path.startswith("/internal"):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            logger.warning(f"❌ Missing Authorization header on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Missing Authorization header"}
            )

        # Format attendu: "Bearer {SECRET}"
        if not auth_header.startswith("Bearer "):
            logger.warning(f"❌ Invalid Authorization format on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "Invalid Authorization format"}
            )

        token = auth_header.replace("Bearer ", "")

        if token != INTERNAL_API_SECRET:
            logger.warning(f"❌ Invalid secret on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Invalid secret"}
            )

        logger.info(f"✅ Internal auth verified for {request.url.path}")

    # Authentification réussie, continuer
    response = await call_next(request)
    return response
```

#### 4. Créer les endpoints internes

Créer un fichier `routes/internal.py` :

```python
"""
Endpoints internes pour la communication avec le backend.
"""

from fastapi import APIRouter, HTTPException
import logging
from schemas.internal import (
    InternalNotifyUserRequest,
    InternalNotifyUserResponse,
    InternalUpdateRoleRequest,
    InternalUpdateRoleResponse,
    InternalHealthResponse,
)

router = APIRouter(prefix="/internal", tags=["Internal"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=InternalHealthResponse)
async def health_check():
    """
    Health check pour vérifier que le bot est accessible.
    """
    return InternalHealthResponse(
        status="healthy",
        service="discord-bot",
        version="1.0.0"
    )


@router.post("/notify", response_model=InternalNotifyUserResponse)
async def notify_user(payload: InternalNotifyUserRequest):
    """
    Notifie le bot d'un événement utilisateur.

    Cette fonction doit:
    1. Récupérer l'utilisateur Discord par son ID
    2. Lui envoyer un message privé (DM) avec les informations
    3. Logger l'événement
    """
    logger.info(f"📩 Notification reçue pour discord_id={payload.discord_id}, action={payload.action}")

    try:
        # TODO: Implémenter la logique de notification
        # Exemple:
        # user = await bot.fetch_user(int(payload.discord_id))
        # await user.send(f"🎉 Votre abonnement {payload.plan} a été activé !")

        # Pour l'instant, on simule le succès
        notification_sent = True

        return InternalNotifyUserResponse(
            success=True,
            message="User notified successfully",
            notification_sent=notification_sent
        )

    except Exception as e:
        logger.error(f"❌ Erreur lors de la notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/roles/update", response_model=InternalUpdateRoleResponse)
async def update_user_role(payload: InternalUpdateRoleRequest):
    """
    Met à jour les rôles Discord d'un utilisateur.

    Cette fonction doit:
    1. Récupérer le membre du serveur Discord
    2. Ajouter/retirer les rôles spécifiés
    3. Retourner le statut
    """
    logger.info(f"📝 Mise à jour des rôles pour discord_id={payload.discord_id}, plan={payload.plan}")

    try:
        # TODO: Implémenter la logique de mise à jour des rôles
        # Exemple:
        # guild = bot.get_guild(GUILD_ID)
        # member = await guild.fetch_member(int(payload.discord_id))
        #
        # if payload.add_roles:
        #     for role_id in payload.add_roles:
        #         role = guild.get_role(int(role_id))
        #         await member.add_roles(role)
        #
        # if payload.remove_roles:
        #     for role_id in payload.remove_roles:
        #         role = guild.get_role(int(role_id))
        #         await member.remove_roles(role)

        # Pour l'instant, on simule le succès
        roles_updated = True
        guild_id = "999888777666555444"  # Remplacer par votre guild ID

        return InternalUpdateRoleResponse(
            success=True,
            message="Roles updated successfully",
            roles_updated=roles_updated,
            guild_id=guild_id
        )

    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour des rôles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

#### 5. Créer le client HTTP pour appeler le backend (BackendClient)

Créer un fichier `services/backend_client.py` :

```python
"""
Client HTTP pour la communication Bot → Backend.
Permet au bot d'appeler les endpoints internes du backend.
"""

import httpx
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)

BACKEND_INTERNAL_URL = os.getenv("BACKEND_INTERNAL_URL", "http://website-backend.railway.internal:8080")
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET")

if not INTERNAL_API_SECRET:
    raise ValueError("INTERNAL_API_SECRET environment variable is required")


class BackendClient:
    """
    Client HTTP pour communiquer avec le backend via Railway Private Network.
    """

    def __init__(self, backend_url: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialise le client backend.

        Args:
            backend_url: URL interne du backend
            api_secret: Secret partagé pour l'authentification
        """
        self.backend_url = backend_url or BACKEND_INTERNAL_URL
        self.api_secret = api_secret or INTERNAL_API_SECRET

        self.client = httpx.AsyncClient(
            base_url=self.backend_url,
            timeout=10.0,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Moddy-Bot/1.0",
            }
        )

        logger.info(f"🌐 BackendClient initialisé avec URL: {self.backend_url}")

    def _get_auth_headers(self) -> dict:
        """Génère les headers d'authentification."""
        return {
            "Authorization": f"Bearer {self.api_secret}"
        }

    async def health_check(self):
        """Vérifie si le backend est accessible."""
        try:
            response = await self.client.get(
                "/internal/health",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Backend health check failed: {e}")
            raise

    async def get_user_info(self, discord_id: str):
        """
        Récupère les informations d'un utilisateur depuis le backend.

        Args:
            discord_id: Discord ID de l'utilisateur

        Returns:
            dict: Informations utilisateur
        """
        try:
            response = await self.client.post(
                "/internal/user/info",
                headers=self._get_auth_headers(),
                json={"discord_id": discord_id}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Failed to get user info: {e}")
            raise

    async def notify_event(self, event_type: str, discord_id: str, metadata: Optional[dict] = None):
        """
        Notifie le backend d'un événement Discord.

        Args:
            event_type: Type d'événement (member_joined, etc.)
            discord_id: Discord ID concerné
            metadata: Métadonnées additionnelles
        """
        try:
            response = await self.client.post(
                "/internal/event/notify",
                headers=self._get_auth_headers(),
                json={
                    "event_type": event_type,
                    "discord_id": discord_id,
                    "metadata": metadata or {}
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"❌ Failed to notify event: {e}")
            raise

    async def close(self):
        """Ferme le client HTTP."""
        await self.client.aclose()


# Instance globale
_backend_client: Optional[BackendClient] = None


def get_backend_client() -> BackendClient:
    """Retourne une instance singleton du BackendClient."""
    global _backend_client
    if _backend_client is None:
        _backend_client = BackendClient()
    return _backend_client
```

**Exemple d'utilisation dans le bot:**

```python
# Dans une commande Discord
@bot.command()
async def userinfo(ctx, member: discord.Member):
    """Affiche les informations d'un membre depuis la DB backend."""
    backend_client = get_backend_client()

    try:
        user_info = await backend_client.get_user_info(str(member.id))

        if user_info["user_found"]:
            await ctx.send(f"Email: {user_info['email']}")
        else:
            await ctx.send("Cet utilisateur n'a pas de compte sur le site.")
    except Exception as e:
        await ctx.send(f"Erreur: {e}")


# Dans un event listener
@bot.event
async def on_member_join(member):
    """Notifie le backend quand un membre rejoint."""
    backend_client = get_backend_client()

    try:
        await backend_client.notify_event(
            event_type="member_joined",
            discord_id=str(member.id),
            metadata={
                "guild_id": str(member.guild.id),
                "username": str(member)
            }
        )
    except Exception as e:
        logger.error(f"Failed to notify backend: {e}")
```

---

#### 6. Créer l'application FastAPI

Créer un fichier `internal_server.py` :

```python
"""
Serveur HTTP interne pour recevoir les requêtes du backend.
Ce serveur écoute sur un port SÉPARÉ (3000) pour éviter d'exposer
les endpoints internes publiquement.
"""

from fastapi import FastAPI
import logging
import os
from middleware.auth import verify_internal_auth
from routes.internal import router as internal_router

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Créer l'application FastAPI
app = FastAPI(
    title="Moddy Bot Internal API",
    description="API interne pour la communication avec le backend",
    version="1.0.0"
)

# Ajouter le middleware d'authentification
app.middleware("http")(verify_internal_auth)

# Ajouter les routes internes
app.include_router(internal_router)


@app.get("/")
async def root():
    """Endpoint racine."""
    return {
        "service": "moddy-bot-internal",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn

    # Lancer le serveur sur :: (IPv4 + IPv6)
    # Port 3000 par défaut (privé, non exposé publiquement)
    port = int(os.getenv("INTERNAL_PORT", 3000))
    logger.info(f"🚀 Démarrage du serveur interne sur le port {port}")
    uvicorn.run(
        "internal_server:app",
        host="::",
        port=port,
        log_level="info"
    )
```

#### 6. Lancer le serveur HTTP en parallèle du bot Discord

Vous avez deux options :

**Option A: Même processus (recommandé)**

Lancer le serveur HTTP interne dans un thread séparé, sur le port 3000 :

```python
# main.py (votre fichier principal du bot)

import discord
from discord.ext import commands
import threading
import uvicorn
from internal_server import app
import os
import logging

logger = logging.getLogger(__name__)

# Créer le bot Discord
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Lancer le serveur HTTP interne dans un thread
def run_internal_server():
    internal_port = int(os.getenv("INTERNAL_PORT", 3000))
    logger.info(f"🚀 Démarrage du serveur HTTP interne sur le port {internal_port}")
    uvicorn.run(app, host="::", port=internal_port, log_level="info")

# Démarrer le serveur HTTP interne
http_thread = threading.Thread(target=run_internal_server, daemon=True)
http_thread.start()

logger.info("🤖 Démarrage du bot Discord...")
# Démarrer le bot Discord
bot.run(os.getenv("DISCORD_TOKEN"))
```

**Option B: Processus séparés (avec Procfile Railway)**

```procfile
# Procfile
web: python main.py
internal: uvicorn internal_server:app --host :: --port ${INTERNAL_PORT:-3000}
```

**Note:** Railway ne supporte qu'un seul processus par service par défaut. L'option A (même processus) est donc recommandée.

#### 7. Tester localement

```bash
# Terminal 1: Lancer le bot avec le serveur interne
export INTERNAL_PORT=3000
export INTERNAL_API_SECRET=test-secret-local
python main.py

# Terminal 2: Tester le health check
curl -H "Authorization: Bearer test-secret-local" http://localhost:3000/internal/health

# Tester la notification
curl -X POST http://localhost:3000/internal/notify \
  -H "Authorization: Bearer test-secret-local" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789",
    "action": "subscription_created",
    "plan": "moddy_max"
  }'
```

### Checklist d'implémentation

- [ ] Installer FastAPI et uvicorn
- [ ] Créer les schémas Pydantic (`schemas/internal.py`)
- [ ] Créer le middleware d'authentification (`middleware/auth.py`)
- [ ] Créer les endpoints internes (`routes/internal.py`)
- [ ] Créer le serveur FastAPI (`internal_server.py`)
- [ ] Intégrer le serveur HTTP au bot Discord dans un thread (`main.py`)
- [ ] Configurer `INTERNAL_API_SECRET` dans Railway (même secret que le backend)
- [ ] Configurer `INTERNAL_PORT=3000` dans Railway
- [ ] S'assurer que le serveur interne écoute sur `::`
- [ ] Tester le health check depuis le backend
- [ ] Implémenter la logique de notification (envoyer DM à l'utilisateur)
- [ ] Implémenter la logique de mise à jour des rôles Discord
- [ ] Tester un paiement complet (Stripe → Backend → Bot → Notification Discord)

---

## Troubleshooting

### Le bot ne reçoit pas les requêtes

1. Vérifier que `INTERNAL_API_SECRET` est identique dans les deux services
2. Vérifier que le serveur HTTP interne écoute sur `::` (toutes interfaces)
3. Vérifier que `BOT_INTERNAL_URL` pointe vers `http://moddy.railway.internal:3000`
4. Vérifier que `INTERNAL_PORT=3000` est configuré dans Railway
5. Vérifier les logs du bot pour voir si le serveur interne a démarré
6. Utiliser `railway logs moddy` pour voir les logs en temps réel

### Erreur 401 Unauthorized

Le secret ne correspond pas. Vérifier :
- `INTERNAL_API_SECRET` est identique dans les deux services (backend et bot)
- Le header `Authorization` est bien `Bearer {SECRET}` (avec "Bearer " au début)
- Pas d'espaces supplémentaires dans le secret

### Erreur de connexion (Connection refused)

Le bot n'est pas accessible :
- Vérifier que le serveur HTTP interne écoute bien sur le port 3000
- Vérifier que le thread du serveur HTTP a bien démarré (logs)
- Vérifier que le serveur écoute sur `::` et non `0.0.0.0` ou `localhost`
- Vérifier que Railway Private Networking est activé pour le projet

### Le serveur interne ne démarre pas

- Vérifier qu'il n'y a pas de conflit de port (aucun autre service sur le port 3000)
- Vérifier les logs du bot pour voir les erreurs de démarrage
- S'assurer que FastAPI et uvicorn sont installés dans les dépendances

### Le bot reçoit la requête mais ne peut pas traiter

- Vérifier que le bot a accès au Discord client (si vous utilisez des threads)
- Partager l'instance du bot entre le serveur HTTP et le bot Discord
- Utiliser des variables globales ou dependency injection

---

## Ressources

- [Railway Private Networking Docs](https://docs.railway.app/reference/private-networking)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Discord.py Documentation](https://discordpy.readthedocs.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

---

## Support

Pour toute question ou problème d'implémentation, consulter :
- Documentation backend: `/docs/`
- Logs Railway: `railway logs <service-name>`
- Discord.py support: https://discord.gg/dpy
