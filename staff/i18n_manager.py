"""
Commande pour gérer le système i18n
Réservée aux développeurs
"""

import discord
from discord.ext import commands
from pathlib import Path
import json

from utils.i18n import i18n
from config import COLORS, EMOJIS


class I18nManagement(commands.Cog):
    """Gestion du système de traduction"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.group(name="i18n", aliases=["lang", "locales"])
    async def i18n_group(self, ctx):
        """Commandes de gestion i18n"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title=f"{EMOJIS['settings']} Système i18n",
                description=(
                    "**Commandes disponibles :**\n"
                    "`i18n reload` - Recharger les traductions\n"
                    "`i18n list` - Lister les langues disponibles\n"
                    "`i18n stats` - Statistiques des traductions\n"
                    "`i18n test <locale>` - Tester une langue"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)

    @i18n_group.command(name="reload")
    async def reload_translations(self, ctx):
        """Recharge toutes les traductions"""
        embed = discord.Embed(
            description=f"{EMOJIS['loading']} Rechargement des traductions...",
            color=COLORS["warning"]
        )
        msg = await ctx.send(embed=embed)

        try:
            i18n.reload_translations()

            embed = discord.Embed(
                title=f"{EMOJIS['done']} Traductions rechargées",
                description=f"**Langues disponibles :** {len(i18n.supported_locales)}",
                color=COLORS["success"]
            )

            # Lister les langues
            locales_list = "\n".join([f"• `{locale}`" for locale in sorted(i18n.supported_locales)])
            if locales_list:
                embed.add_field(name="Langues chargées", value=locales_list[:1024], inline=False)

            await msg.edit(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title=f"{EMOJIS['error']} Erreur",
                description=f"```py\n{str(e)[:500]}\n```",
                color=COLORS["error"]
            )
            await msg.edit(embed=embed)

    @i18n_group.command(name="list")
    async def list_locales(self, ctx):
        """Liste toutes les langues disponibles"""
        embed = discord.Embed(
            title=f"🌐 Langues disponibles",
            color=COLORS["info"]
        )

        locales_dir = Path(__file__).parent.parent / 'locales'

        if not locales_dir.exists():
            embed.description = "Aucun fichier de traduction trouvé"
            await ctx.send(embed=embed)
            return

        loaded_locales = []
        missing_keys = {}

        # Charger la référence (en-US)
        reference_file = locales_dir / 'en-US.json'
        reference_keys = set()

        if reference_file.exists():
            with open(reference_file, 'r', encoding='utf-8') as f:
                reference_data = json.load(f)
                reference_keys = self._get_all_keys(reference_data)

        # Vérifier chaque langue
        for locale_file in sorted(locales_dir.glob('*.json')):
            locale_code = locale_file.stem
            file_size = locale_file.stat().st_size / 1024  # En KB

            # Charger et compter les clés
            with open(locale_file, 'r', encoding='utf-8') as f:
                locale_data = json.load(f)
                locale_keys = self._get_all_keys(locale_data)

            # Calculer les clés manquantes
            if locale_code != 'en-US' and reference_keys:
                missing = reference_keys - locale_keys
                if missing:
                    missing_keys[locale_code] = len(missing)

            status = "✅" if locale_code in i18n.supported_locales else "❌"
            missing_count = missing_keys.get(locale_code, 0)
            missing_text = f" ⚠️ ({missing_count} manquantes)" if missing_count > 0 else ""

            loaded_locales.append(
                f"{status} **{locale_code}** - {file_size:.1f}KB - {len(locale_keys)} clés{missing_text}"
            )

        if loaded_locales:
            # Diviser en chunks si trop long
            chunks = []
            current_chunk = []
            current_length = 0

            for locale in loaded_locales:
                if current_length + len(locale) > 900:  # Garde de la marge
                    chunks.append("\n".join(current_chunk))
                    current_chunk = [locale]
                    current_length = len(locale)
                else:
                    current_chunk.append(locale)
                    current_length += len(locale)

            if current_chunk:
                chunks.append("\n".join(current_chunk))

            for i, chunk in enumerate(chunks[:3]):  # Max 3 fields
                embed.add_field(
                    name=f"Fichiers ({i + 1}/{len(chunks)})" if len(chunks) > 1 else "Fichiers",
                    value=chunk,
                    inline=False
                )

        embed.set_footer(text=f"Total : {len(loaded_locales)} langues")
        await ctx.send(embed=embed)

    @i18n_group.command(name="stats")
    async def translation_stats(self, ctx):
        """Affiche les statistiques des traductions"""
        embed = discord.Embed(
            title="📊 Statistiques i18n",
            color=COLORS["info"]
        )

        locales_dir = Path(__file__).parent.parent / 'locales'

        if not locales_dir.exists():
            embed.description = "Aucun fichier de traduction trouvé"
            await ctx.send(embed=embed)
            return

        total_keys = 0
        total_size = 0
        locale_stats = []

        # Charger la référence
        reference_file = locales_dir / 'en-US.json'
        reference_keys = set()

        if reference_file.exists():
            with open(reference_file, 'r', encoding='utf-8') as f:
                reference_data = json.load(f)
                reference_keys = self._get_all_keys(reference_data)

        for locale_file in sorted(locales_dir.glob('*.json')):
            with open(locale_file, 'r', encoding='utf-8') as f:
                locale_data = json.load(f)
                locale_keys = self._get_all_keys(locale_data)

            total_keys += len(locale_keys)
            file_size = locale_file.stat().st_size
            total_size += file_size

            # Calculer la complétude
            if reference_keys and locale_file.stem != 'en-US':
                completeness = (len(locale_keys) / len(reference_keys)) * 100
                locale_stats.append((locale_file.stem, completeness))

        embed.add_field(
            name="Vue d'ensemble",
            value=(
                f"**Langues :** {len(list(locales_dir.glob('*.json')))}\n"
                f"**Total clés :** {total_keys}\n"
                f"**Taille totale :** {total_size / 1024:.1f}KB\n"
                f"**Clés référence :** {len(reference_keys)}"
            ),
            inline=False
        )

        if locale_stats:
            completeness_text = "\n".join([
                f"`{locale:6}` {self._progress_bar(comp)} {comp:.1f}%"
                for locale, comp in sorted(locale_stats, key=lambda x: x[1], reverse=True)[:10]
            ])
            embed.add_field(
                name="Complétude des traductions",
                value=completeness_text,
                inline=False
            )

        await ctx.send(embed=embed)

    @i18n_group.command(name="test")
    async def test_locale(self, ctx, locale: str = None):
        """Teste une langue spécifique"""
        if not locale:
            # Utiliser la langue de l'utilisateur Discord
            locale = str(ctx.interaction.locale) if hasattr(ctx, 'interaction') else 'en-US'

        embed = discord.Embed(
            title=f"🧪 Test de la langue : {locale}",
            color=COLORS["info"]
        )

        # Créer une fausse interaction pour tester
        class FakeInteraction:
            def __init__(self, locale_str):
                self.locale = locale_str

        fake_interaction = FakeInteraction(locale)

        # Tester quelques traductions
        test_keys = [
            "common.loading",
            "common.success",
            "common.error",
            "commands.ping.response.title",
            "errors.generic.title"
        ]

        results = []
        for key in test_keys:
            value = i18n.get(key, fake_interaction)
            status = "✅" if not value.startswith("[") else "❌"
            results.append(f"{status} `{key}`\n→ {value[:100]}")

        embed.add_field(
            name="Résultats des tests",
            value="\n".join(results),
            inline=False
        )

        # Vérifier si la langue est supportée
        is_supported = i18n.is_supported(locale)
        detected_locale = i18n.get_user_locale(fake_interaction)

        embed.add_field(
            name="Informations",
            value=(
                f"**Supportée :** {'✅ Oui' if is_supported else '❌ Non'}\n"
                f"**Locale détectée :** `{detected_locale}`\n"
                f"**Fallback :** `en-US`"
            ),
            inline=False
        )

        await ctx.send(embed=embed)

    def _get_all_keys(self, data: dict, prefix: str = "") -> set:
        """Récupère toutes les clés d'un dictionnaire de manière récursive"""
        keys = set()
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                keys.update(self._get_all_keys(value, full_key))
            else:
                keys.add(full_key)
        return keys

    def _progress_bar(self, percentage: float, length: int = 10) -> str:
        """Crée une barre de progression"""
        filled = int(length * percentage / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}]"


async def setup(bot):
    await bot.add_cog(I18nManagement(bot))