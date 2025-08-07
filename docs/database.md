# 📚 Documentation Base de Données Moddy

## 🎯 Vue d'ensemble

Moddy utilise PostgreSQL en local sur le VPS (plus Neon). La base de données est structurée en 3 parties principales :

1. **Gestion des erreurs** : Stockage des erreurs avec codes uniques
2. **Cache de lookups** : Informations sur les serveurs/utilisateurs pour les commandes lookup
3. **Données fonctionnelles** : Configuration et données des utilisateurs/serveurs

## 🏗️ Architecture des tables

### 1. Table `errors`
Stocke toutes les erreurs non-triviales avec un code unique (ex: `ABCD1234`)

```sql
errors:
- error_code (PRIMARY KEY) : Code unique à 8 caractères
- error_type : Type d'erreur (ValueError, KeyError, etc.)
- message : Message d'erreur
- file_source : Fichier où l'erreur s'est produite
- line_number : Ligne du code
- traceback : Stack trace complète
- user_id : ID Discord de l'utilisateur concerné
- guild_id : ID du serveur où c'est arrivé
- command : Commande qui a causé l'erreur
- timestamp : Moment de l'erreur
- context (JSONB) : Contexte additionnel flexible
```

### 2. Tables de cache pour lookups

#### `guilds_cache`
Cache les infos des serveurs que le bot ne peut pas obtenir via l'API (serveurs où il n'est pas)

```sql
guilds_cache:
- guild_id (PRIMARY KEY)
- name : Nom du serveur
- icon_url : URL de l'avatar
- features : Fonctionnalités Discord (COMMUNITY, etc.)
- member_count : Nombre de membres
- created_at : Date de création du serveur
- last_updated : Dernière mise à jour des infos
- update_source : Comment on a obtenu l'info (bot_join, user_profile, etc.)
- raw_data (JSONB) : Toutes les données brutes
```

**Sources d'information** :
- `bot_join` : Quand le bot rejoint le serveur
- `user_profile` : Via le profil d'un utilisateur qui a le bot en app perso
- `api_call` : Appel API direct
- `manual` : Ajouté manuellement

### 3. Tables fonctionnelles

#### `users`
Données persistantes des utilisateurs

```sql
users:
- user_id (PRIMARY KEY)
- attributes (JSONB) : Attributs système (voir section Attributs)
- data (JSONB) : Données utilisateur (voir section Data)
- created_at : Première interaction avec le bot
- updated_at : Dernière modification
```

#### `guilds`
Données persistantes des serveurs

```sql
guilds:
- guild_id (PRIMARY KEY)
- attributes (JSONB) : Attributs système
- data (JSONB) : Configuration et données du serveur
- created_at : Ajout du bot au serveur
- updated_at : Dernière modification
```

#### `attribute_changes`
Historique de tous les changements d'attributs (audit trail)

```sql
attribute_changes:
- id : ID auto-incrémenté
- entity_type : 'user' ou 'guild'
- entity_id : ID de l'entité modifiée
- attribute_name : Nom de l'attribut
- old_value : Ancienne valeur
- new_value : Nouvelle valeur
- changed_by : ID du développeur qui a fait le changement
- changed_at : Timestamp
- reason : Raison du changement
```

## 🏷️ Système d'Attributs (NOUVEAU)

Les **attributs** sont des propriétés système NON visibles par les utilisateurs, gérées uniquement par le bot ou les développeurs.

### Fonctionnement simplifié :
- **Attributs booléens** : Si présents = `true`, si absents = `false`
  - Exemple : Si un utilisateur a `PREMIUM` dans ses attributs, il a le premium
  - Pas besoin de stocker `PREMIUM: true`
- **Attributs avec valeur** : Stockent une valeur spécifique
  - Exemple : `LANG: "FR"` pour la langue

### Attributs utilisateur possibles :
- `BETA` : Accès aux fonctionnalités beta (booléen)
- `PREMIUM` : Utilisateur premium (booléen)
- `DEVELOPER` : Développeur du bot (booléen)
- `BLACKLISTED` : Utilisateur banni du bot (booléen)
- `VERIFIED` : Utilisateur vérifié (booléen)
- `SUPPORTER` : Supporte le projet (booléen)
- `TRACK` : Utilisateur suivi/tracké (booléen)
- `LANG` : Langue préférée (valeur : "FR", "EN", etc.)

### Attributs serveur possibles :
- `OFFICIAL_SERVER` : Serveur officiel/partenaire (booléen)
- `BETA_FEATURES` : Accès aux features beta (booléen)
- `PREMIUM_GUILD` : Serveur premium (booléen)
- `VERIFIED_GUILD` : Serveur vérifié (booléen)
- `LEGACY` : Serveur depuis les débuts (booléen)
- `LANG` : Langue du serveur (valeur : "FR", "EN", etc.)

### Format de stockage :
```json
{
  "BETA": true,
  "PREMIUM": true,
  "LANG": "FR"
}
```

Note : Les attributs booléens `false` ne sont PAS stockés. Si un attribut n'est pas présent, il est considéré comme `false`.

### Utilisation dans le code :
```python
# Vérifier un attribut booléen
if await db.has_attribute('user', user_id, 'BETA'):
    # L'utilisateur a accès aux features beta

# Vérifier un attribut avec valeur
lang = await db.get_attribute('user', user_id, 'LANG')
if lang == "FR":
    # L'utilisateur préfère le français

# Définir un attribut booléen
await db.set_attribute('user', user_id, 'PREMIUM', True, dev_id, "Achat premium")

# Supprimer un attribut booléen (= le mettre à false)
await db.set_attribute('user', user_id, 'PREMIUM', False, dev_id, "Fin du premium")
# ou
await db.set_attribute('user', user_id, 'PREMIUM', None, dev_id, "Fin du premium")

# Définir un attribut avec valeur
await db.set_attribute('user', user_id, 'LANG', 'FR', dev_id, "Préférence utilisateur")

# Récupérer tous les utilisateurs avec un attribut
beta_users = await db.get_users_with_attribute('BETA')  # Tous ceux qui ont BETA
french_users = await db.get_users_with_attribute('LANG', 'FR')  # Tous ceux qui ont LANG=FR
```

## 📦 Système de Data

La **data** contient les données utilisateur/serveur modifiables et structurées.

### Data utilisateur typique :
```json
{
  "reminders": [
    {
      "id": "reminder_123",
      "message": "Faire les courses",
      "time": "2024-01-15T14:00:00Z",
      "channel_id": 123456789
    }
  ],
  "preferences": {
    "dm_reminders": true,
    "timezone": "Europe/Paris"
  },
  "tags": {
    "work": "Je suis en réunion",
    "afk": "AFK pour 30 minutes"
  }
}
```

### Data serveur typique :
```json
{
  "config": {
    "prefix": "!",
    "welcome_channel": 123456789,
    "log_channel": 987654321,
    "features": {
      "welcome_message": true,
      "auto_roles": false,
      "logging": true
    }
  },
  "tags": {
    "rules": "1. Soyez respectueux\n2. Pas de spam",
    "help": "Utilisez !help pour l'aide",
    "faq": "Consultez #faq pour les questions"
  },
  "custom_commands": {
    "ping": "Pong! 🏓",
    "discord": "https://discord.gg/..."
  }
}
```

### Mise à jour de la data :
```python
# Mise à jour d'un chemin spécifique
await db.update_user_data(user_id, 'preferences.timezone', 'Europe/Paris')

# Récupération
user = await db.get_user(user_id)
timezone = user['data']['preferences']['timezone']
```

## 🔄 Flux de données

### 1. **Lookup d'un serveur** :
```
Commande /guild lookup
    ↓
Vérifie guilds_cache (données < 7 jours ?)
    ↓ Non ou pas trouvé
Tente via l'API Discord
    ↓ Succès
Met à jour guilds_cache avec update_source
    ↓
Retourne les infos
```

### 2. **Erreur dans une commande** :
```
Exception levée
    ↓
ErrorTracker génère un code unique
    ↓
Enregistre dans table errors
    ↓
Envoie log Discord avec le code
    ↓
User peut partager le code pour debug
```

### 3. **Configuration serveur** :
```
Admin utilise /config prefix ?
    ↓
Récupère guild via db.get_guild()
    ↓
Met à jour data.config.prefix
    ↓
Cache invalidé pour forcer reload
```

## 🛠️ Commandes utiles

### Pour les développeurs :
```python
# Voir les stats
stats = await db.get_stats()
# {'errors': 152, 'users': 4821, 'guilds': 234, 'beta_users': 45}

# Nettoyer les vieilles erreurs
await db.cleanup_old_errors(days=30)

# Bannir un utilisateur (ajouter l'attribut BLACKLISTED)
await db.set_attribute('user', user_id, 'BLACKLISTED', True, dev_id, "Spam")

# Retirer le ban (supprimer l'attribut)
await db.set_attribute('user', user_id, 'BLACKLISTED', False, dev_id, "Appel accepté")

# Donner le premium à un serveur
await db.set_attribute('guild', guild_id, 'PREMIUM_GUILD', True, dev_id, "Achat premium")

# Changer la langue d'un utilisateur
await db.set_attribute('user', user_id, 'LANG', 'EN', dev_id, "Changement de langue")
```

## 🔐 Sécurité et bonnes pratiques

1. **Seuls les devs** peuvent modifier les attributs
2. **Tout est tracé** dans attribute_changes
3. **Cache intelligent** avec TTL configurable
4. **JSONB** permet flexibilité sans migrations
5. **Index optimisés** pour performances
6. **Pas de DELETE** : on marque comme inactif

## 💡 Points clés à retenir

1. **Attributs = Système** (non visible users, géré par devs)
2. **Attributs booléens** : présent = true, absent = false
3. **Attributs avec valeur** : stockent une valeur spécifique (LANG=FR)
4. **Data = Utilisateur** (configs, préférences, données)
5. **Cache intelligent** pour les lookups
6. **Tout est tracé** pour l'audit
7. **PostgreSQL local** sur le VPS, pas cloud