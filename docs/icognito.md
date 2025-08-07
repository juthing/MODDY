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