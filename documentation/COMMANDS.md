# Guide de Création de Commandes Moddy

Ce document explique comment créer et gérer les commandes slash (app commands) dans Moddy, notamment la différence entre les commandes globales et les commandes spécifiques aux serveurs.

## Table des matières

1. [Types de Commandes](#types-de-commandes)
2. [Commandes Globales](#commandes-globales)
3. [Commandes Guild-Only](#commandes-guild-only)
4. [Comment ça fonctionne ?](#comment-ça-fonctionne)
5. [Exemples Pratiques](#exemples-pratiques)
6. [Bonnes Pratiques](#bonnes-pratiques)

---

## Types de Commandes

Moddy supporte deux types de commandes slash :

### 1. **Commandes Globales** (App-Perso)
- Accessibles **partout** : DMs, tous les serveurs Discord (même sans Moddy)
- Synchronisées globalement par Discord
- Exemples : `/ping`, `/user`, `/webhook`, `/avatar`, `/translate`

### 2. **Commandes Guild-Only** (Spécifiques aux serveurs)
- Accessibles **uniquement dans les serveurs où Moddy est présent**
- **Non accessibles** en DM
- **Non accessibles** dans les serveurs sans Moddy
- Synchronisées serveur par serveur
- Exemples : `/config`

---

## Commandes Globales

### Quand utiliser une commande globale ?

Utilisez une commande globale quand :
- ✅ La commande peut fonctionner en DM
- ✅ La commande ne nécessite pas de configuration serveur
- ✅ La commande est une fonctionnalité personnelle (profil utilisateur, traduction, etc.)
- ✅ Vous voulez que la commande soit accessible partout

### Comment créer une commande globale ?

**Simple : N'ajoutez PAS le décorateur `@app_commands.guild_only()`**

```python
import discord
from discord import app_commands
from discord.ext import commands

class MonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="Check the bot's latency"
    )
    async def ping(self, interaction: discord.Interaction):
        """Cette commande sera GLOBALE - accessible partout"""
        await interaction.response.send_message(f"Pong! {round(self.bot.latency * 1000)}ms")

async def setup(bot):
    await bot.add_cog(MonCog(bot))
```

**Résultat** : `/ping` est disponible partout (DMs + tous les serveurs)

---

## Commandes Guild-Only

### Quand utiliser une commande guild-only ?

Utilisez une commande guild-only quand :
- ✅ La commande nécessite un serveur (ex: configuration, modération)
- ✅ La commande utilise des données spécifiques au serveur
- ✅ La commande ne doit être accessible que là où Moddy est installé
- ✅ La commande ne peut pas fonctionner en DM

### Comment créer une commande guild-only ?

**Ajoutez le décorateur `@app_commands.guild_only()`**

```python
import discord
from discord import app_commands
from discord.ext import commands

class MonCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="config",
        description="Configure server modules"
    )
    @app_commands.guild_only()  # ← Voici la ligne importante !
    async def config(self, interaction: discord.Interaction):
        """Cette commande sera GUILD-ONLY - uniquement dans les serveurs avec Moddy"""

        # Vous pouvez utiliser interaction.guild en toute sécurité
        # car guild_only garantit que interaction.guild n'est jamais None
        guild_name = interaction.guild.name
        await interaction.response.send_message(f"Configuration pour {guild_name}")

async def setup(bot):
    await bot.add_cog(MonCog(bot))
```

**Résultat** : `/config` est uniquement disponible dans les serveurs où Moddy est présent

---

## Comment ça fonctionne ?

### Système de Synchronisation Automatique

Le bot détecte automatiquement le type de commande grâce au décorateur `@app_commands.guild_only()` et synchronise les commandes de manière appropriée.

#### Au démarrage du bot (`bot.py:182-231`)

```python
async def sync_commands(self):
    """
    1. Identifie les commandes guild-only
    2. Les retire de l'arbre global
    3. Synchronise les commandes globales (accessibles partout via Discord)
    4. Pour chaque serveur où Moddy est présent:
       - Ajoute temporairement les guild-only
       - Sync uniquement les guild-only pour ce serveur
       - Retire les guild-only pour le prochain serveur
    5. Restaure l'arbre complet avec toutes les commandes
    """
```

**Important** : On n'utilise **PAS** `copy_global_to()` ! Les commandes synchronisées globalement sont automatiquement accessibles dans tous les serveurs via Discord. On sync uniquement les guild-only par serveur.

#### Quand Moddy rejoint un serveur (`bot.py:527-533`)

```python
async def on_guild_join(self, guild: discord.Guild):
    # ...
    # Synchronise uniquement les commandes guild-only pour ce serveur
    # Les commandes globales sont déjà accessibles via la sync globale
    await self.sync_guild_commands(guild)
```

**Résultat** : `/config` devient immédiatement disponible dans ce nouveau serveur (mais pas ailleurs)

#### Quand Moddy quitte un serveur (`bot.py:535-549`)

```python
async def on_guild_remove(self, guild: discord.Guild):
    # ...
    # Nettoie toutes les commandes du serveur
    self.tree.clear_commands(guild=guild)
    await self.tree.sync(guild=guild)
```

**Résultat** : `/config` n'est plus accessible dans ce serveur

### Détection du décorateur

Discord.py ajoute automatiquement un attribut `guild_only` à la commande :

```python
# Dans bot.py
for command in self.tree.walk_commands():
    if hasattr(command, 'guild_only') and command.guild_only:
        # Cette commande est guild-only
        guild_only_commands.append(command)
```

**Vous n'avez rien à faire** - le système détecte automatiquement le décorateur !

---

## Exemples Pratiques

### Exemple 1 : Commande de profil utilisateur (GLOBALE)

```python
from discord import app_commands, ui
from discord.ext import commands

class UserProfile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View a user's profile")
    async def profile(self, interaction: discord.Interaction, user: discord.User = None):
        """Commande GLOBALE - accessible partout"""
        target = user or interaction.user

        embed = discord.Embed(
            title=f"Profile de {target.name}",
            description=f"ID: {target.id}"
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(UserProfile(bot))
```

**Pourquoi GLOBALE ?**
- ✅ Peut fonctionner en DM
- ✅ Ne nécessite pas de configuration serveur
- ✅ Affiche des infos utilisateur universelles

---

### Exemple 2 : Commande de modération (GUILD-ONLY)

```python
from discord import app_commands
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.guild_only()  # ← Guild-only car c'est de la modération
    @app_commands.default_permissions(moderate_members=True)
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str
    ):
        """Commande GUILD-ONLY - uniquement dans les serveurs"""

        # interaction.guild est garanti d'exister grâce à @guild_only()
        # interaction.guild n'est jamais None ici

        await interaction.response.send_message(
            f"⚠️ {member.mention} a été averti pour : {reason}"
        )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
```

**Pourquoi GUILD-ONLY ?**
- ✅ Nécessite un serveur (on ne peut pas modérer en DM)
- ✅ Utilise `discord.Member` (spécifique aux serveurs)
- ✅ Ne doit être accessible que là où Moddy gère la modération

---

### Exemple 3 : Commande de configuration de module (GUILD-ONLY)

```python
from discord import app_commands, ui
from discord.ext import commands

class WelcomeConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="setup-welcome",
        description="Configure the welcome module"
    )
    @app_commands.guild_only()  # ← Guild-only car configuration serveur
    @app_commands.default_permissions(manage_guild=True)
    async def setup_welcome(self, interaction: discord.Interaction):
        """Commande GUILD-ONLY - configuration serveur"""

        # Récupère la config du serveur
        config = await self.bot.module_manager.get_module_config(
            interaction.guild.id,
            'welcome'
        )

        view = WelcomeConfigView(self.bot, interaction.guild.id)
        await interaction.response.send_message(
            "Configure le module de bienvenue :",
            view=view,
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(WelcomeConfig(bot))
```

**Pourquoi GUILD-ONLY ?**
- ✅ Configure un module spécifique au serveur
- ✅ Utilise des données serveur (`guild.id`)
- ✅ Ne peut pas fonctionner en DM

---

## Bonnes Pratiques

### ✅ DO (À FAIRE)

1. **Utilisez `@guild_only()` pour les commandes serveur**
   ```python
   @app_commands.command(name="setup")
   @app_commands.guild_only()  # ← Bon !
   async def setup(self, interaction):
       pass
   ```

2. **Vérifiez `interaction.guild` pour les commandes globales si nécessaire**
   ```python
   @app_commands.command(name="serverinfo")
   async def serverinfo(self, interaction):
       if not interaction.guild:
           await interaction.response.send_message(
               "Cette commande doit être utilisée dans un serveur",
               ephemeral=True
           )
           return
       # ...
   ```

3. **Utilisez `@default_permissions()` avec `@guild_only()` pour la modération**
   ```python
   @app_commands.command(name="ban")
   @app_commands.guild_only()
   @app_commands.default_permissions(ban_members=True)
   async def ban(self, interaction, member: discord.Member):
       pass
   ```

### ❌ DON'T (À ÉVITER)

1. **N'utilisez PAS `@guild_only()` sur des commandes DM-friendly**
   ```python
   # ❌ Mauvais - empêche l'utilisation en DM
   @app_commands.command(name="ping")
   @app_commands.guild_only()  # ← Pas nécessaire pour ping !
   async def ping(self, interaction):
       pass
   ```

2. **N'oubliez PAS `@guild_only()` sur les commandes de configuration**
   ```python
   # ❌ Mauvais - config sera accessible partout
   @app_commands.command(name="config")
   # @app_commands.guild_only()  ← Manquant !
   async def config(self, interaction):
       # interaction.guild peut être None en DM !
       pass
   ```

3. **N'utilisez PAS `discord.Member` dans les commandes globales**
   ```python
   # ❌ Mauvais - Member ne fonctionne pas en DM
   @app_commands.command(name="profile")
   async def profile(self, interaction, member: discord.Member):
       pass

   # ✅ Bon - User fonctionne partout
   @app_commands.command(name="profile")
   async def profile(self, interaction, user: discord.User):
       pass
   ```

---

## Récapitulatif Rapide

| Type | Décorateur | Accessible en DM ? | Accessible sans Moddy ? | Exemples |
|------|------------|-------------------|------------------------|----------|
| **Globale** | *(aucun)* | ✅ Oui | ✅ Oui | `/ping`, `/user`, `/avatar` |
| **Guild-Only** | `@guild_only()` | ❌ Non | ❌ Non | `/config`, `/setup-welcome` |

---

## Questions Fréquentes

### Q: Comment savoir si ma commande doit être globale ou guild-only ?

**R:** Posez-vous ces questions :
- La commande peut-elle fonctionner en DM ? → Globale
- La commande nécessite-t-elle un serveur ? → Guild-only
- La commande configure-t-elle quelque chose sur le serveur ? → Guild-only
- La commande est-elle personnelle à l'utilisateur ? → Globale

### Q: Que se passe-t-il si j'oublie `@guild_only()` ?

**R:** La commande sera synchronisée globalement et accessible partout, même dans les serveurs sans Moddy. Cela peut causer des erreurs si la commande utilise `interaction.guild` sans vérifier qu'il n'est pas `None`.

### Q: Puis-je changer une commande de globale à guild-only ?

**R:** Oui ! Ajoutez simplement `@guild_only()` et redémarrez le bot. La prochaine synchronisation la rendra guild-only automatiquement.

### Q: Les changements sont-ils immédiats ?

**R:**
- **Au démarrage** : La synchronisation prend ~5-10 secondes
- **Guild join/remove** : Instantané (synchronisation automatique)
- **Modification de code** : Nécessite un redémarrage du bot

### Q: Pourquoi n'utilise-t-on pas `copy_global_to()` ?

**R:** Dans les versions précédentes, `copy_global_to()` copiait tout l'arbre (y compris les commandes guild-only) vers chaque serveur, ce qui rendait les commandes guild-only visibles partout.

Maintenant, on utilise une approche différente :
- Les commandes **globales** synced globalement sont **automatiquement accessibles** dans tous les serveurs via Discord
- On sync **uniquement les guild-only** pour chaque serveur individuellement
- Pas besoin de copier quoi que ce soit !

Cette approche garantit que les guild-only ne sont jamais exposées globalement.

---

## Contributeurs

Ce système a été développé pour résoudre le problème où les commandes guild-only (comme `/config`) étaient accessibles dans tous les serveurs, même ceux sans Moddy.

**Documentation créée le** : 29 novembre 2025
**Dernière mise à jour** : 29 novembre 2025 (corrigé pour refléter le système sans `copy_global_to()`)
