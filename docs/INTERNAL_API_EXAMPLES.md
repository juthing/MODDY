# Exemples d'utilisation de l'API interne

Ce document fournit des exemples concrets d'utilisation de l'API interne pour la communication entre le backend et le bot Discord.

## 📝 Configuration

**Serveur Discord principal :** `1394001780148535387`
**Rôle premium "Moddy Max" :** `1424149819185827954`

## 🎯 Cas d'usage 1 : Utilisateur achète un abonnement

### Flux complet

```
1. Utilisateur paie sur le site web (Stripe)
2. Backend reçoit le webhook Stripe
3. Backend envoie une requête au bot pour :
   - Notifier l'utilisateur
   - Lui donner le rôle premium
4. Bot envoie un DM à l'utilisateur
5. Bot ajoute le rôle "Moddy Max" sur le serveur principal
```

### Requête 1 : Notifier l'utilisateur

**Endpoint :** `POST http://moddy.railway.internal:3000/internal/notify`

**Headers :**
```http
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Body :**
```json
{
  "discord_id": "123456789012345678",
  "action": "subscription_created",
  "plan": "moddy_max",
  "metadata": {
    "customer_id": "cus_ABC123",
    "email": "user@example.com",
    "subscription_type": "month"
  }
}
```

**Réponse attendue :**
```json
{
  "success": true,
  "message": "User notified successfully",
  "notification_sent": true
}
```

**Message DM reçu par l'utilisateur :**
```
🎉 Votre abonnement moddy_max a été activé avec succès !

📧 Email: user@example.com

Merci d'utiliser Moddy ! 🤖
```

### Requête 2 : Ajouter le rôle premium

**Endpoint :** `POST http://moddy.railway.internal:3000/internal/roles/update`

**Headers :**
```http
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Body :**
```json
{
  "discord_id": "123456789012345678",
  "plan": "moddy_max",
  "add_roles": ["1424149819185827954"],
  "remove_roles": []
}
```

**Réponse attendue :**
```json
{
  "success": true,
  "message": "Roles updated successfully",
  "roles_updated": true,
  "guild_id": "1394001780148535387"
}
```

**Ce qui se passe sur Discord :**
- L'utilisateur reçoit automatiquement le rôle "Moddy Max" ⭐
- Il a accès aux salons réservés aux abonnés
- Son nom apparaît avec la couleur du rôle premium

---

## 🎯 Cas d'usage 2 : Annulation d'abonnement

### Requête 1 : Notifier l'utilisateur

**Body :**
```json
{
  "discord_id": "123456789012345678",
  "action": "subscription_cancelled",
  "plan": "free",
  "metadata": {
    "reason": "User cancelled",
    "cancelled_at": "2026-01-07T12:00:00Z"
  }
}
```

**Message DM reçu :**
```
❌ Votre abonnement a été annulé.

Merci d'utiliser Moddy ! 🤖
```

### Requête 2 : Retirer le rôle premium

**Body :**
```json
{
  "discord_id": "123456789012345678",
  "plan": "free",
  "add_roles": [],
  "remove_roles": ["1424149819185827954"]
}
```

**Ce qui se passe sur Discord :**
- Le rôle "Moddy Max" est retiré automatiquement
- L'utilisateur perd l'accès aux salons premium
- Il redevient un utilisateur gratuit

---

## 🎯 Cas d'usage 3 : Upgrade de plan

### Requête 1 : Notifier l'upgrade

**Body :**
```json
{
  "discord_id": "123456789012345678",
  "action": "plan_upgraded",
  "plan": "moddy_max",
  "metadata": {
    "old_plan": "moddy_basic",
    "new_plan": "moddy_max"
  }
}
```

**Message DM reçu :**
```
⬆️ Votre plan a été amélioré vers moddy_max !

Merci d'utiliser Moddy ! 🤖
```

### Requête 2 : Mettre à jour les rôles

Si vous avez plusieurs niveaux de rôles (Basic, Max, etc.) :

**Body :**
```json
{
  "discord_id": "123456789012345678",
  "plan": "moddy_max",
  "add_roles": ["1424149819185827954"],
  "remove_roles": ["1234567890123456789"]
}
```

**Explication :**
- `add_roles` : Ajoute le rôle "Moddy Max"
- `remove_roles` : Retire le rôle "Moddy Basic"

---

## 🔍 Cas d'usage 4 : Le bot récupère des infos utilisateur

Le bot peut récupérer les informations d'un utilisateur depuis la base de données du backend.

### Exemple : Commande Discord `/premium`

**Code dans le bot :**
```python
@app_commands.command(name="premium")
async def premium_command(interaction: discord.Interaction):
    """Affiche les informations de votre abonnement"""

    # Récupérer le client backend
    from services import get_backend_client, BackendClientError
    backend_client = get_backend_client()

    try:
        # Récupérer les infos utilisateur depuis le backend
        user_info = await backend_client.get_user_info(str(interaction.user.id))

        if user_info["user_found"]:
            await interaction.response.send_message(
                f"📧 Email: {user_info['email']}\n"
                f"📅 Compte créé: {user_info['created_at']}\n"
                f"✅ Vous avez un abonnement actif !",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Vous n'avez pas de compte sur le site.\n"
                "Créez-en un sur https://moddy.gg",
                ephemeral=True
            )
    except BackendClientError as e:
        await interaction.response.send_message(
            f"❌ Erreur de connexion au backend: {e}",
            ephemeral=True
        )
```

**Requête effectuée par le bot :**

**Endpoint :** `POST http://website-backend.railway.internal:8080/internal/user/info`

**Headers :**
```http
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Body :**
```json
{
  "discord_id": "123456789012345678"
}
```

**Réponse si trouvé :**
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

**Réponse si non trouvé :**
```json
{
  "success": false,
  "message": "User not found",
  "user_found": false
}
```

---

## 🔍 Cas d'usage 5 : Le bot notifie le backend d'événements Discord

Le bot peut notifier le backend quand des événements Discord se produisent.

### Exemple : Un membre rejoint le serveur

**Code dans le bot :**
```python
@bot.event
async def on_member_join(member):
    """Notifie le backend quand un membre rejoint"""

    from services import get_backend_client, BackendClientError
    backend_client = get_backend_client()

    try:
        await backend_client.notify_event(
            event_type="member_joined",
            discord_id=str(member.id),
            metadata={
                "guild_id": str(member.guild.id),
                "username": str(member),
                "joined_at": member.joined_at.isoformat()
            }
        )
    except BackendClientError as e:
        logger.error(f"Failed to notify backend: {e}")
```

**Requête effectuée par le bot :**

**Endpoint :** `POST http://website-backend.railway.internal:8080/internal/event/notify`

**Headers :**
```http
Authorization: Bearer {INTERNAL_API_SECRET}
Content-Type: application/json
```

**Body :**
```json
{
  "event_type": "member_joined",
  "discord_id": "123456789012345678",
  "metadata": {
    "guild_id": "1394001780148535387",
    "username": "JohnDoe#1234",
    "joined_at": "2026-01-07T12:00:00Z"
  }
}
```

**Réponse :**
```json
{
  "success": true,
  "message": "Event member_joined processed successfully",
  "event_received": true
}
```

---

## 🔒 Sécurité : Exemples de requêtes rejetées

### Erreur 401 : Header Authorization manquant

**Requête :**
```http
POST http://moddy.railway.internal:3000/internal/notify
Content-Type: application/json

{
  "discord_id": "123456789012345678",
  "action": "subscription_created",
  "plan": "moddy_max"
}
```

**Réponse :**
```json
{
  "error": "Missing Authorization header"
}
```

### Erreur 403 : Secret invalide

**Requête :**
```http
POST http://moddy.railway.internal:3000/internal/notify
Authorization: Bearer wrong-secret-here
Content-Type: application/json

{
  "discord_id": "123456789012345678",
  "action": "subscription_created",
  "plan": "moddy_max"
}
```

**Réponse :**
```json
{
  "error": "Invalid secret"
}
```

---

## 🧪 Tests avec curl

### Test du health check

```bash
curl -X GET http://moddy.railway.internal:3000/internal/health \
  -H "Authorization: Bearer ${INTERNAL_API_SECRET}"
```

### Test de notification

```bash
curl -X POST http://moddy.railway.internal:3000/internal/notify \
  -H "Authorization: Bearer ${INTERNAL_API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "action": "subscription_created",
    "plan": "moddy_max"
  }'
```

### Test de mise à jour des rôles

```bash
curl -X POST http://moddy.railway.internal:3000/internal/roles/update \
  -H "Authorization: Bearer ${INTERNAL_API_SECRET}" \
  -H "Content-Type: application/json" \
  -d '{
    "discord_id": "123456789012345678",
    "plan": "moddy_max",
    "add_roles": ["1424149819185827954"],
    "remove_roles": []
  }'
```

---

## 📊 Monitoring et logs

### Logs côté bot

Lors d'une notification réussie :
```
📩 Notification reçue pour discord_id=123456789012345678, action=subscription_created
✅ Notification envoyée à User#1234 (123456789012345678)
```

Lors d'une mise à jour de rôles réussie :
```
📝 Mise à jour des rôles pour discord_id=123456789012345678, plan=moddy_max
✅ Added role Moddy Max to User#1234
```

### Logs côté backend

Lors d'un appel réussi :
```
✅ Bot notified for discord_id=123456789012345678
✅ Roles updated for discord_id=123456789012345678
```

---

**Version :** 1.0
**Dernière mise à jour :** 2026-01-07
**Auteur :** Claude
