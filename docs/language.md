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