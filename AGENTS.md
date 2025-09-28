### 📄 Instructions pour les IAs – Projet Moddy

Tu aides à développer **Moddy**, un bot Discord écrit en **Python**, hébergé sur Railway. Il s'agit d'une **application publique**, orientée **assistance pour modérateurs et administrateurs**. 

#### 📦 Stack et structure

* **Langage** : Python 3.11+
* **Lib** : `discord.py` avec support des **components v2** de Discord
* **Base de données** : PostgreSQL
* **Variables d’environnement** via `.env`
* **Arborescence actuelle** :

  ```
  MODDY/
  ├── main.py          # Le cerveau du bot
  ├── init.py          # Initialisation du bot
  ├── config.py        # Configuration (token, etc.)
  ├── cogs/            # Dossier des modules utilisateurs
  │   └── __init__.py
  ├── staff/           # Dossier des commandes staff/dev
  │   └── __init__.py
  ├── requirements.txt # Dépendances Python
  └── .env             # Variables d'environnement (token Discord)
  ```

#### 🛠️ Commandes développeur

Ces commandes sont accessibles **partout (même en DM)**, en mentionnant le bot avec la commande, par ex. : `<@BOTID> reboot`. Elles sont situées dans le dossier `staff/`. Exemples :

* `reboot`
* `user`
* `server`
* `ping`
* `version`
* `sync`
* [...] d'autres commandes 

#### 🎯 Commandes slash disponibles

Commandes principales organisées en plusieurs catégories (à coder avec des cogs bien structurés) :

* **Lookup / Informations** :

  * `/user lookup`
  * `/guild lookup`
  * `/event lookup` `[Server Invite] [Event ID]`
  * `/invite lookup`
  * `/webhook lookup`
  * `/avatar` (serveur ou utilisateur)
  * `/banner`

* **Outils et utilitaires** :

  * `/translate [content] | [from] [to]`
  * `/emoji`
  * `/OCR`
  * `/dictionary`
  * `/timestamp syntax`
  * `/roll [min] [max]`

* **Rappels** :

  * `/reminder add`
  * `/reminder remove`
  * `/reminder list`

* **Tags personnalisés** :

  * `/tag send`
  * `/tag manage`

* **Moddy (infos bot)** :

  * `/moddy invite`
  * `/moddy info`
  * `/moddy code`
  * `/preferences`
  * `/help`

#### 📋 Règles et style

* Moddy doit être **modulaire, propre et scalable**.
* Réponses et messages en **français uniquement**.
* Utilise **les components V2** pour les embeds (pas d’anciens systèmes).
* Priorité à la clarté, la fiabilité et la maintenabilité du code.
* Aucun système de modération classique (pas de ban/kick/warn).
* Prévois la prise en charge d’**interactions contextuelles** (menus, boutons, réponses dynamiques).
* Les commandes peuvent être regroupées dans des cogs selon leur thème (lookup, outils, rappels, etc.).

# 🌐 Documentation - Système de langue Moddy

## Vue d'ensemble

Le système de langue de Moddy permet au bot de communiquer avec chaque utilisateur dans sa langue préférée (Français ou Anglais). La préférence est stockée dans l'attribut `LANG` de l'utilisateur et est automatiquement appliquée à toutes les interactions.

## 🎯 Fonctionnement

### 1. Détection automatique

Lors de la **première interaction** d'un utilisateur avec le bot :
1. Le système vérifie si l'utilisateur a un attribut `LANG`
2. Si non, un menu de sélection bilingue apparaît
3. L'utilisateur choisit sa langue via des boutons
4. La préférence est sauvegardée dans la base de données

### 2. Flux d'exécution

```
Utilisateur utilise une commande
        ↓
LanguageManager intercepte l'interaction
        ↓
Vérifie l'attribut LANG dans la DB/cache
        ↓
    Si LANG existe → Stocke la langue dans le dictionnaire interne
    Si LANG n'existe pas → Affiche le menu de sélection
        ↓
La commande s'exécute avec la langue appropriée
```

## ⚠️ CHANGEMENT IMPORTANT

**Discord.py n'autorise pas l'ajout d'attributs personnalisés aux objets `Interaction`**. 

Le système utilise maintenant un dictionnaire interne pour stocker les langues des interactions en cours.

## 🐛 GESTION DU BUG "Interaction already acknowledged"

### Le problème

Quand un utilisateur "vierge" (sans langue définie) utilise une commande slash, le système de langue intercepte l'interaction et répond en premier pour demander la langue. Si la commande essaie ensuite de répondre normalement avec `interaction.response.send_message()`, Discord retourne l'erreur :

```
HTTPException: 400 Bad Request (error code: 40060): Interaction has already been acknowledged.
```

### La solution

**TOUTES les commandes slash doivent vérifier si l'interaction a déjà été répondue** avant d'essayer de répondre. Voici le pattern à suivre :

```python
import asyncio

@app_commands.command(name="macommande", description="Description FR / Description EN")
async def ma_commande(self, interaction: discord.Interaction, ...):
    """Ma commande"""
    
    # IMPORTANT : Attendre un peu pour laisser le système de langue agir
    await asyncio.sleep(0.1)
    
    # Vérifier si l'interaction a déjà été répondue (par le système de langue)
    if interaction.response.is_done():
        # Le système de langue a demandé la sélection
        # On attend que l'utilisateur choisisse sa langue
        await asyncio.sleep(2)
        
        # Récupère la langue mise à jour depuis la DB
        lang = 'EN'  # Fallback par défaut
        if self.bot.db:
            try:
                user_lang = await self.bot.db.get_attribute('user', interaction.user.id, 'LANG')
                if user_lang:
                    lang = user_lang
            except:
                pass
        
        # IMPORTANT : Utiliser followup au lieu de response
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        return
    
    # Si l'interaction n'a pas été répondue, continuer normalement
    lang = get_user_lang(interaction, self.bot)
    
    # ... reste du code ...
    
    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
```

### Points clés

1. **Toujours ajouter `await asyncio.sleep(0.1)`** au début de la commande
2. **Vérifier `interaction.response.is_done()`** avant de répondre
3. **Utiliser `followup.send()`** si l'interaction a déjà été répondue
4. **Attendre 2 secondes** pour laisser l'utilisateur choisir sa langue
5. **Récupérer la langue depuis la DB** après la sélection

### Exemple complet avec gestion du bug

```python
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from cogs.language_manager import get_user_lang
from config import COLORS

class MyCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.texts = {
            "FR": {
                "title": "Titre en français",
                "description": "Description en français"
            },
            "EN": {
                "title": "English title",
                "description": "English description"
            }
        }
    
    def get_text(self, lang: str, key: str) -> str:
        return self.texts.get(lang, self.texts["EN"]).get(key, key)
    
    @app_commands.command(
        name="example",
        description="Exemple de commande / Example command"
    )
    async def example(self, interaction: discord.Interaction):
        # ÉTAPE 1 : Attendre pour le système de langue
        await asyncio.sleep(0.1)
        
        # ÉTAPE 2 : Vérifier si déjà répondu
        if interaction.response.is_done():
            # Attendre la sélection de langue
            await asyncio.sleep(2)
            
            # Récupérer la langue depuis la DB
            lang = 'EN'
            if self.bot.db:
                try:
                    user_lang = await self.bot.db.get_attribute('user', interaction.user.id, 'LANG')
                    if user_lang:
                        lang = user_lang
                except:
                    pass
            
            # Créer l'embed avec la bonne langue
            embed = discord.Embed(
                title=self.get_text(lang, "title"),
                description=self.get_text(lang, "description"),
                color=COLORS["primary"]
            )
            
            # UTILISER FOLLOWUP !
            await interaction.followup.send(embed=embed)
            return
        
        # ÉTAPE 3 : Traitement normal si pas de sélection de langue
        lang = get_user_lang(interaction, self.bot)
        
        embed = discord.Embed(
            title=self.get_text(lang, "title"),
            description=self.get_text(lang, "description"),
            color=COLORS["primary"]
        )
        
        # Réponse normale
        await interaction.response.send_message(embed=embed)
```

## 💻 Implémentation dans vos commandes

### Pour les commandes slash (app_commands)

```python
from cogs.language_manager import get_user_lang
import asyncio

@app_commands.command(name="example", description="Exemple / Example")
async def example_command(self, interaction: discord.Interaction):
    # TOUJOURS commencer par ça pour éviter le bug
    await asyncio.sleep(0.1)
    
    if interaction.response.is_done():
        await asyncio.sleep(2)
        # Récupérer la langue depuis la DB
        lang = 'EN'
        if self.bot.db:
            try:
                user_lang = await self.bot.db.get_attribute('user', interaction.user.id, 'LANG')
                if user_lang:
                    lang = user_lang
            except:
                pass
        
        # Utiliser followup
        if lang == "FR":
            await interaction.followup.send("Bonjour ! Voici un exemple en français.")
        else:
            await interaction.followup.send("Hello! This is an example in English.")
        return
    
    # Sinon, traitement normal
    lang = get_user_lang(interaction, self.bot)
    
    if lang == "FR":
        await interaction.response.send_message("Bonjour ! Voici un exemple en français.")
    else:
        await interaction.response.send_message("Hello! This is an example in English.")
```

## 🔧 API disponible

### LanguageManager - Méthodes publiques

```python
# Récupérer la langue d'un utilisateur
lang = await lang_manager.get_user_language(user_id)
# Retourne: "FR", "EN" ou None

# Définir la langue d'un utilisateur
success = await lang_manager.set_user_language(user_id, "FR", set_by_id)
# Retourne: True si succès, False sinon

# Récupérer la langue d'une interaction (nouvelle méthode)
lang = lang_manager.get_interaction_language(interaction)
# Retourne: "FR", "EN" ou None

# Fonction helper pour récupérer facilement la langue
from cogs.language_manager import get_user_lang
lang = get_user_lang(interaction, bot)
# Retourne: "FR" ou "EN" (avec fallback)
```

## 📝 Bonnes pratiques

### 1. Toujours utiliser la fonction helper

```python
# ✅ BON : Utilise la fonction helper
from cogs.language_manager import get_user_lang
lang = get_user_lang(interaction, self.bot)

# ❌ MAUVAIS : N'essaye pas d'accéder à un attribut (ça ne marche plus)
lang = getattr(interaction, 'user_lang', 'EN')  # ERREUR !
```

### 2. Toujours gérer le cas "première interaction"

```python
# ✅ BON : Gère le cas où le système de langue répond en premier
await asyncio.sleep(0.1)
if interaction.response.is_done():
    # Utiliser followup
    await interaction.followup.send(...)
else:
    # Utiliser response normale
    await interaction.response.send_message(...)

# ❌ MAUVAIS : Ne vérifie pas si déjà répondu
await interaction.response.send_message(...)  # Peut causer HTTPException 40060
```

### 3. Descriptions bilingues pour les commandes

```python
@app_commands.command(
    name="help",
    description="Affiche l'aide / Shows help"  # Les deux langues
)
```

### 4. Organiser les traductions

```python
# ❌ Mauvais : traductions éparpillées
if lang == "FR":
    title = "Bienvenue"
else:
    title = "Welcome"

# ✅ Bon : traductions centralisées
self.texts = {
    "FR": {"title": "Bienvenue"},
    "EN": {"title": "Welcome"}
}
title = self.texts[lang]["title"]
```

### 5. Gérer les formats de date/nombre

```python
from datetime import datetime

if lang == "FR":
    # Format français : 25/12/2024
    date_str = datetime.now().strftime("%d/%m/%Y")
else:
    # Format anglais : 12/25/2024
    date_str = datetime.now().strftime("%m/%d/%Y")
```

## 🎨 Éléments d'interface multilingues

### Boutons

```python
class MyView(discord.ui.View):
    def __init__(self, lang: str):
        super().__init__()
        
        # Labels selon la langue
        if lang == "FR":
            confirm_label = "Confirmer"
            cancel_label = "Annuler"
        else:
            confirm_label = "Confirm"
            cancel_label = "Cancel"
        
        # Créer les boutons avec les bons labels
        self.add_item(discord.ui.Button(label=confirm_label, style=discord.ButtonStyle.success))
        self.add_item(discord.ui.Button(label=cancel_label, style=discord.ButtonStyle.danger))
```

### Embeds complexes

```python
def create_user_info_embed(user: discord.User, lang: str) -> discord.Embed:
    if lang == "FR":
        embed = discord.Embed(
            title=f"Informations sur {user}",
            color=COLORS["primary"]
        )
        embed.add_field(name="Créé le", value=f"<t:{int(user.created_at.timestamp())}:D>")
        embed.add_field(name="Robot", value="Oui" if user.bot else "Non")
    else:
        embed = discord.Embed(
            title=f"Information about {user}",
            color=COLORS["primary"]
        )
        embed.add_field(name="Created on", value=f"<t:{int(user.created_at.timestamp())}:D>")
        embed.add_field(name="Bot", value="Yes" if user.bot else "No")
    
    return embed
```

## 🚀 Exemple complet avec gestion du bug

```python
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from cogs.language_manager import get_user_lang
from config import COLORS

class Reminder(commands.Cog):
    """Système de rappels multilingue"""
    
    def __init__(self, bot):
        self.bot = bot
        self.texts = {
            "FR": {
                "no_reminders": "Vous n'avez aucun rappel",
                "reminder_set": "Rappel créé ! Je vous rappellerai",
                "invalid_time": "Format de temps invalide",
                "reminder_list": "Vos rappels",
                "button_delete": "Supprimer",
                "button_edit": "Modifier"
            },
            "EN": {
                "no_reminders": "You have no reminders",
                "reminder_set": "Reminder created! I'll remind you",
                "invalid_time": "Invalid time format",
                "reminder_list": "Your reminders",
                "button_delete": "Delete",
                "button_edit": "Edit"
            }
        }
    
    def get_text(self, lang: str, key: str) -> str:
        return self.texts.get(lang, self.texts["EN"]).get(key, key)
    
    @app_commands.command(name="reminder", description="Gérer vos rappels / Manage your reminders")
    @app_commands.describe(
        action="add/list/remove",
        time="Dans combien de temps / In how long (ex: 1h30m)",
        message="Message du rappel / Reminder message"
    )
    async def reminder(self, interaction: discord.Interaction, 
                      action: str, time: str = None, message: str = None):
        
        # GESTION DU BUG : Attendre pour le système de langue
        await asyncio.sleep(0.1)
        
        # Vérifier si déjà répondu
        if interaction.response.is_done():
            # Attendre la sélection de langue
            await asyncio.sleep(2)
            
            # Récupérer la langue depuis la DB
            lang = 'EN'
            if self.bot.db:
                try:
                    user_lang = await self.bot.db.get_attribute('user', interaction.user.id, 'LANG')
                    if user_lang:
                        lang = user_lang
                except:
                    pass
            
            # Traiter la commande avec followup
            if action == "list":
                reminders = await self.get_user_reminders(interaction.user.id)
                
                if not reminders:
                    embed = discord.Embed(
                        description=self.get_text(lang, "no_reminders"),
                        color=COLORS["info"]
                    )
                else:
                    embed = discord.Embed(
                        title=self.get_text(lang, "reminder_list"),
                        color=COLORS["primary"]
                    )
                    
                    for reminder in reminders[:5]:
                        embed.add_field(
                            name=f"#{reminder['id']}",
                            value=f"{reminder['message']}\n<t:{reminder['timestamp']}:R>",
                            inline=False
                        )
                
                # UTILISER FOLLOWUP !
                await interaction.followup.send(embed=embed)
                return
        
        # Traitement normal si pas de sélection de langue
        lang = get_user_lang(interaction, self.bot)
        
        if action == "list":
            # Récupère les rappels de l'utilisateur
            reminders = await self.get_user_reminders(interaction.user.id)
            
            if not reminders:
                embed = discord.Embed(
                    description=self.get_text(lang, "no_reminders"),
                    color=COLORS["info"]
                )
            else:
                embed = discord.Embed(
                    title=self.get_text(lang, "reminder_list"),
                    color=COLORS["primary"]
                )
                
                for reminder in reminders[:5]:
                    embed.add_field(
                        name=f"#{reminder['id']}",
                        value=f"{reminder['message']}\n<t:{reminder['timestamp']}:R>",
                        inline=False
                    )
            
            await interaction.response.send_message(embed=embed)
```

## ⚠️ Notes importantes

1. **Les commandes staff** ne sont pas traduites (elles restent en anglais)
2. **Le cache** évite de surcharger la DB (1000 entrées max)
3. **Fallback** : Si pas de langue définie, l'anglais est utilisé par défaut
4. **Première interaction** : Le menu de sélection n'apparaît qu'une fois
5. **Nettoyage automatique** : Les langues d'interaction sont automatiquement nettoyées après 5 minutes
6. **Bug "Interaction already acknowledged"** : TOUJOURS vérifier si l'interaction a déjà été répondue

## 🔄 Migration d'anciennes commandes

Pour migrer une commande existante vers le nouveau système :

1. **Importer la fonction helper ET asyncio** :
   ```python
   from cogs.language_manager import get_user_lang
   import asyncio
   ```

2. **Ajouter la gestion du bug au début de la commande** :
   ```python
   await asyncio.sleep(0.1)
   if interaction.response.is_done():
       # Gérer avec followup
       await asyncio.sleep(2)
       # ... récupérer la langue depuis DB ...
       await interaction.followup.send(...)
       return
   ```

3. **Remplacer l'ancienne méthode** :
   ```python
   # Ancien (ne marche plus)
   lang = getattr(interaction, 'user_lang', 'EN')
   
   # Nouveau
   lang = get_user_lang(interaction, self.bot)
   ```

4. **Créer le dictionnaire de traductions** `self.texts`

5. **Remplacer les textes par** `self.get_text(lang, "key")`

6. **Tester dans les deux langues ET avec un nouvel utilisateur**

## 🐛 Résolution de problèmes

### Erreur : `HTTPException: 400 Bad Request (error code: 40060): Interaction has already been acknowledged`

**Cause** : La commande essaie de répondre après que le système de langue ait déjà répondu.

**Solution** : Ajouter la vérification `interaction.response.is_done()` et utiliser `followup.send()` si c'est le cas.

### Erreur : `AttributeError: 'Interaction' object has no attribute 'user_lang'`

**Cause** : Utilisation de l'ancienne méthode qui essaye d'ajouter un attribut à l'objet Interaction.

**Solution** : Utiliser la nouvelle fonction helper `get_user_lang(interaction, bot)`.

### La langue n'est pas détectée

**Causes possibles** :
- Le cog `LanguageManager` n'est pas chargé
- La base de données n'est pas connectée
- L'utilisateur n'a pas encore choisi sa langue

**Solution** : Vérifier que le cog est bien chargé et que la DB est connectée. Le fallback sur l'anglais devrait toujours fonctionner.

### L'utilisateur reste bloqué après la sélection de langue

**Cause** : La commande n'attend pas assez longtemps après la sélection.

**Solution** : S'assurer que `await asyncio.sleep(2)` est présent après la détection de `interaction.response.is_done()`.

## 📋 Checklist pour éviter les bugs

Pour chaque commande slash :
- [ ] Importer `asyncio`
- [ ] Ajouter `await asyncio.sleep(0.1)` au début
- [ ] Vérifier `interaction.response.is_done()`
- [ ] Si oui, attendre 2 secondes et utiliser `followup.send()`
- [ ] Si non, utiliser `response.send_message()` normalement
- [ ] Tester avec un nouvel utilisateur sans langue définie
- [ ] Tester avec un utilisateur ayant déjà une langue

C'est tout ! Le système gère automatiquement le reste 🎉

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

# 🔒 Documentation - Système Incognito Moddy

## ⚠️ IMPORTANT : Le décorateur ne fonctionne PAS avec Discord.py

Le décorateur `@add_incognito_option()` **ne peut pas** modifier automatiquement les paramètres des commandes slash Discord.py. Il faut implémenter manuellement le système dans chaque commande.

## ✅ Méthode correcte d'intégration

### 1. Structure de base pour TOUTE commande slash avec incognito

```python
from typing import Optional

@app_commands.command(name="macommande", description="Description FR / Description EN")
@app_commands.describe(
    # ... autres paramètres ...
    incognito="Rendre la réponse visible uniquement pour vous / Make response visible only to you"
)
async def ma_commande(
    self, 
    interaction: discord.Interaction,
    # ... autres paramètres ...
    incognito: Optional[bool] = None  # TOUJOURS à la fin, TOUJOURS Optional avec = None
):
    """Docstring de la commande"""
    
    # === BLOC INCOGNITO - À copier au début de chaque commande ===
    if incognito is None and self.bot.db:
        try:
            user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
            ephemeral = True if user_pref is None else user_pref
        except:
            ephemeral = True
    else:
        ephemeral = incognito if incognito is not None else True
    # === FIN DU BLOC INCOGNITO ===
    
    # Récupération de la langue (si nécessaire)
    lang = getattr(interaction, 'user_lang', 'EN')
    
    # ... reste du code ...
    
    # Utiliser ephemeral dans TOUS les send_message
    await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
```

### 2. Points critiques à respecter

#### ✅ TOUJOURS faire :
- Paramètre `incognito` en **dernier** dans la signature
- Type `Optional[bool] = None` (jamais juste `bool`)
- Description bilingue dans `@app_commands.describe`
- Vérifier `if incognito is None` pour utiliser la préférence utilisateur
- Utiliser `ephemeral=ephemeral` dans **TOUS** les `send_message()` et `followup.send()`

#### ❌ NE JAMAIS faire :
- Utiliser `@add_incognito_option()` - ça ne marche pas avec Discord.py
- Mettre `incognito` avant d'autres paramètres optionnels
- Oublier le `= None` par défaut
- Utiliser `get_incognito_setting()` - ça ne fonctionne pas correctement

### 3. Cas spéciaux

#### Pour les messages d'erreur (toujours privés) :
```python
# Les erreurs sont TOUJOURS ephemeral, peu importe la préférence
await interaction.response.send_message(
    "<:undone:1398729502028333218> Erreur...",
    ephemeral=True  # Toujours True pour les erreurs
)
```

#### Pour les followups :
```python
# Le followup doit avoir la même visibilité que la réponse initiale
await interaction.response.send_message("Chargement...", ephemeral=ephemeral)
# Plus tard...
await interaction.followup.send("Résultat", ephemeral=ephemeral)  # Même valeur !
```

#### Pour les commandes avec defer :
```python
await interaction.response.defer(ephemeral=ephemeral)
# Plus tard...
await interaction.edit_original_response(embed=embed)  # Pas besoin de ephemeral ici
```

## 📊 Système de préférences

### Stockage dans la BDD
- **Table :** `users`
- **Colonne :** `attributes` (JSONB)
- **Clé :** `DEFAULT_INCOGNITO`
- **Valeurs :**
  - `true` = Messages privés par défaut
  - `false` = Messages publics par défaut
  - `null` ou absent = Considéré comme `true`

### Modification via `/preferences`
```python
# Dans cogs/preferences.py
await self.bot.db.set_attribute(
    'user', user_id, 'DEFAULT_INCOGNITO', True/False,
    user_id, "Changement via préférences"
)
```

## 🎯 Commandes qui DOIVENT avoir incognito

- ✅ `/ping` - Information personnelle
- ✅ `/translate` - Contenu potentiellement privé
- ✅ `/preferences` - Toujours privé (pas d'option)
- ✅ `/help` - Aide personnalisée
- ✅ `/reminder` - Rappels personnels
- ✅ `/userinfo` - Informations utilisateur
- ✅ `/serverinfo` - Informations serveur

## 🚫 Commandes qui NE doivent PAS avoir incognito

- ❌ Commandes de modération (ban, kick, warn)
- ❌ Commandes de configuration serveur
- ❌ Commandes publiques par nature (annonces, etc.)
- ❌ Commandes staff/dev

## 🔧 Template complet pour nouvelle commande

```python
import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from utils.embeds import ModdyEmbed, ModdyResponse
from config import COLORS

class MonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="macommande",
        description="Description en français / English description"
    )
    @app_commands.describe(
        param1="Description param1 FR / Param1 description EN",
        incognito="Rendre la réponse visible uniquement pour vous / Make response visible only to you"
    )
    async def ma_commande(
        self,
        interaction: discord.Interaction,
        param1: str,
        incognito: Optional[bool] = None
    ):
        """Ma super commande"""
        
        # Gestion incognito
        if incognito is None and self.bot.db:
            try:
                user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                ephemeral = True if user_pref is None else user_pref
            except:
                ephemeral = True
        else:
            ephemeral = incognito if incognito is not None else True
        
        # Récupération langue
        lang = getattr(interaction, 'user_lang', 'EN')
        
        # Logique de la commande
        if lang == "FR":
            embed = ModdyEmbed.create(
                title="Titre français",
                description=f"Voici : {param1}",
                color=COLORS["primary"]
            )
        else:
            embed = ModdyEmbed.create(
                title="English title",
                description=f"Here is: {param1}",
                color=COLORS["primary"]
            )
        
        # Envoi avec la bonne visibilité
        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)
```

## 📝 Checklist d'intégration

Pour chaque commande :
- [ ] Ajouter `incognito: Optional[bool] = None` en **dernier** paramètre
- [ ] Ajouter la description bilingue dans `@app_commands.describe`
- [ ] Copier le bloc de gestion incognito au début de la fonction
- [ ] Utiliser `ephemeral=ephemeral` dans **TOUS** les envois
- [ ] Tester avec et sans l'option incognito
- [ ] Vérifier que la préférence utilisateur est respectée

## ⚠️ Erreurs communes à éviter

1. **Oublier `= None`** → L'option devient obligatoire
2. **Mettre incognito avant d'autres params optionnels** → Ordre incorrect
3. **Utiliser le décorateur** → Ne fonctionne pas
4. **Oublier ephemeral dans followup** → Incohérence de visibilité
5. **Ne pas gérer le cas `incognito is None`** → Préférence ignorée

---

**Note pour l'IA :** Cette documentation remplace complètement l'ancienne. Le système de décorateur ne fonctionne PAS. Il faut TOUJOURS implémenter manuellement comme décrit ci-dessus.

# Emojis

Tu ne dois utiliser aucun émoji standard Unicode. On utilise uniquement les émojis personnalisés. Tu trouveras ci-dessous notre liste avec le nom, l’ID et la syntaxe à utiliser. L’équivalence en Unicode est là juste pour te donner une idée visuelle, mais elle ne doit jamais être utilisée. Même si tu corriges un code qui n’a rien à voir avec les émojis, pense à remplacer les embeds avec les bons émojis custom.
Si tu remarques qu’il en manque ou qu’il en faudrait un autre, n’hésite pas à me le dire.
sync – 1398729150885269546 – <:sync:1398729150885269546> – 🔄  
commit – 1398728993284296806 – <:commit:1398728993284296806> – *(pas d’équivalent)*   
suggestion – 1398720180237893803 – <:suggestion:1398720180237893803> – 💡  
panel – 1398720151980998789 – <:panel:1398720151980998789> – *(pas d’équivalent)*  
translate – 1398720130950627600 – <:translate:1398720130950627600> – 🌐  
moddy – 1396880909117947924 – <:moddy:1396880909117947924> – *(pas d’équivalent)* - Logo de moddy
translatemt – 1395048813353242735 – <:translatemt:1395048813353242735> – *(pas d’équivalent)*  
loading – 1395047662092550194 – <:loading:1395047662092550194> – *(pas d’équivalent)*  - à utiliser quand ça charge c'est le truc en rond qui tourne  
support – 1398734366670065726 – <:support:1398734366670065726> – 🛟  
snowflake – 1398729841938792458 – <:snowflake:1398729841938792458> – ❄️  
invalidsnowflake – 1398729819855913143 – <:invalidsnowflake:1398729819855913143> – *(pas d’équivalent)*  (flocon avec un point d'exclamation) (à utiliser quand un snowflake, donc un id discord, est invalide)
web – 1398729801061240883 – <:web:1398729801061240883> – 🌐  
time – 1398729780723060736 – <:time:1398729780723060736> – 🕒  
manageuser – 1398729745293774919 – <:manageuser:1398729745293774919> – *(pas d’équivalent)*  
user – 1398729712204779571 – <:user:1398729712204779571> – 👤  
verified – 1398729677601902635 – <:verified:1398729677601902635> – ✅ 
dev – 1398729645557285066 – <:dev:1398729645557285066> – *(pas d’équivalent)*   
explore – 1398729622320840834 – <:explore:1398729622320840834> – (ça sorrespond à une boussole)
look – 1398729593074094090 – <:look:1398729593074094090> – (cadenas fermé)
cooldown – 1398729573922767043 – <:cooldown:1398729573922767043> – *(pas d’équivalent)*  
settings – 1398729549323440208 – <:settings:1398729549323440208> – ⚙️  
done – 1398729525277229066 – <:done:1398729525277229066> – ✅ - à utiliser quand quelque chose s'est bien passé par exemple : <:done:1398729525277229066> Les permissions ont bien été configurés
undone – 1398729502028333218 – <:undone:1398729502028333218> – ❌ - à utiliser quand il y a un problème (de permission, un bug etc), par exemple <:undone:1398729502028333218> Tu n'as pas la permissions pour accéder à cette commande. 
label – 1398729473649676440 – <:label:1398729473649676440> – 🏷️  
color – 1398729435565396008 – <:color:1398729435565396008> – 🎨  
emoji – 1398729407065100359 – <:emoji:1398729407065100359> – 😄  
idea – 1398729314597343313 – <:idea:1398729314597343313> – 💡  
legal – 1398729293554782324 – <:legal:1398729293554782324> – ⚖️  
policy – 1398729271979020358 – <:policy:1398729271979020358> – 📜  
copyright – 1398729248063230014 – <:copyright:1398729248063230014> – ©️  
balance – 1398729232862941445 – <:balance:1398729232862941445> – ⚖️  
update – 1398729214064201922 – <:update:1398729214064201922> – 🔄  
import – 1398729171584421958 – <:import:1398729171584421958> – 📥  
back – 1401600847733067806 – <:back:1401600847733067806> – 🔙  
data_object – 1401600908323852318 – <:data_object:1401600908323852318> – {}  
premium – 1401602724801548381 – <:premium:1401602724801548381> – 💎  
logout – 1401603690858676224 – <:logout:1401603690858676224> – 🔚  
add – 1401608434230493254 – <:add:1401608434230493254> – ➕  
commands – 1401610449136648283 – <:commands:1401610449136648283> – *pas d'équivalent* 
code – 1401610523803652196 – <:code:1401610523803652196> – *pas d'équivalent*
bug – 1401614189482475551 – <:bug:1401614189482475551> – 🐞  
info – 1401614681440784477 – <:info:1401614681440784477> – ℹ️  
blacklist – 1401596864784777363 – <:blacklist:1401596864784777363> – *pas d'équivalent*
track – 140159633222695002 – <:track:140159633222695002> – *pas d'équivalent*
history – 1401600464587456512 – <:history:1401600464587456512> – *pas d'équivalent*  
download – 1401600503867248730 – <:download:1401600503867248730> – ⬇️  
ia – 1401600562906005564 – <:ia:1401600562906005564> – ✨  
person_off – 1401600620284219412 – <:person_off:1401600620284219412> – *pas d'équivalent*
edit – 1401600709824086169 – <:edit:1401600709824086169> – ✏️  
delete – 1401600770431909939 – <:delete:1401600770431909939> – 🗑️
notifications - 1402261437493022775 - <:notifications:1402261437493022775> - 🔔
eye_m - 1402261502492151878 - <:eye_m:1402261502492151878> - 👁️