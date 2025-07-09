"""
Commandes de gestion des erreurs pour développeurs
Permet de consulter et gérer les erreurs du bot
"""

import discord
from discord.ext import commands
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse
from config import COLORS


class ErrorManagement(commands.Cog):
    """Commandes de gestion des erreurs pour développeurs"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="error", aliases=["err", "debug"])
    async def error_info(self, ctx, error_code: str = None):
        """Affiche les détails d'une erreur via son code"""
        # Récupère le cog ErrorTracker
        error_tracker = self.bot.get_cog("ErrorTracker")
        if not error_tracker:
            await ctx.send("❌ Système d'erreurs non chargé")
            return

        if not error_code:
            # Affiche les dernières erreurs
            embed = discord.Embed(
                title="Dernières erreurs",
                description="Voici les 10 dernières erreurs enregistrées",
                color=COLORS["info"]
            )

            errors_list = list(error_tracker.error_cache)[-10:]

            if not errors_list:
                embed.description = "Aucune erreur enregistrée récemment"
            else:
                for error in reversed(errors_list):
                    timestamp = error['timestamp'].strftime("%H:%M:%S")
                    error_type = error['data'].get('type', 'Unknown')
                    embed.add_field(
                        name=f"`{error['code']}` - {timestamp}",
                        value=f"**Type:** `{error_type}`\n**Fichier:** `{error['data'].get('file', 'N/A')}`",
                        inline=True
                    )

            await ctx.send(embed=embed)
            return

        # Recherche l'erreur spécifique
        error_code = error_code.upper()
        found_error = None

        for error in error_tracker.error_cache:
            if error['code'] == error_code:
                found_error = error
                break

        if not found_error:
            embed = ModdyResponse.error(
                "Erreur introuvable",
                f"Aucune erreur avec le code `{error_code}` n'a été trouvée"
            )
            await ctx.send(embed=embed)
            return

        # Affiche les détails complets
        data = found_error['data']
        timestamp = found_error['timestamp']

        embed = discord.Embed(
            title=f"Détails de l'erreur {error_code}",
            color=COLORS["warning"],
            timestamp=timestamp
        )

        # Informations de base
        embed.add_field(
            name="Type d'erreur",
            value=f"`{data.get('type', 'N/A')}`",
            inline=True
        )

        embed.add_field(
            name="Fichier source",
            value=f"`{data.get('file', 'N/A')}:{data.get('line', '?')}`",
            inline=True
        )

        embed.add_field(
            name="Heure",
            value=f"`{timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            inline=True
        )

        # Message d'erreur
        embed.add_field(
            name="Message d'erreur",
            value=f"```{data.get('message', 'N/A')[:500]}```",
            inline=False
        )

        # Contexte si disponible
        if 'command' in data:
            context_value = (
                f"**Commande:** `{data.get('command', 'N/A')}`\n"
                f"**Utilisateur:** {data.get('user', 'N/A')}\n"
                f"**Serveur:** {data.get('guild', 'N/A')}\n"
                f"**Canal:** {data.get('channel', 'N/A')}"
            )
            embed.add_field(
                name="Contexte",
                value=context_value,
                inline=False
            )

        if 'message' in data:
            embed.add_field(
                name="Message original",
                value=f"```{data.get('message', 'N/A')[:300]}```",
                inline=False
            )

        # Traceback si disponible
        if 'traceback' in data:
            tb = data['traceback']
            if len(tb) > 800:
                tb = tb[:800] + "\n... (tronqué)"
            embed.add_field(
                name="Traceback",
                value=f"```py\n{tb}```",
                inline=False
            )

        await ctx.send(embed=embed)

        # Log l'action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "error")

    @commands.command(name="clearerrors", aliases=["cerr", "errorclear"])
    async def clear_errors(self, ctx):
        """Vide le cache d'erreurs"""
        error_tracker = self.bot.get_cog("ErrorTracker")
        if not error_tracker:
            await ctx.send("❌ Système d'erreurs non chargé")
            return

        count = len(error_tracker.error_cache)
        error_tracker.error_cache.clear()

        embed = ModdyResponse.success(
            "Cache vidé",
            f"`{count}` erreurs ont été supprimées du cache"
        )
        await ctx.send(embed=embed)

        # Log l'action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "clearerrors")

    @commands.command(name="errortest", aliases=["testerror", "testerr"])
    async def test_error(self, ctx, error_type: str = "basic"):
        """Génère une erreur de test pour vérifier le système"""
        embed = discord.Embed(
            title="Test d'erreur",
            description=f"Génération d'une erreur de type : `{error_type}`",
            color=COLORS["warning"]
        )
        await ctx.send(embed=embed)

        # Génère différents types d'erreurs selon le paramètre
        if error_type == "basic":
            raise Exception("Ceci est une erreur de test basique")
        elif error_type == "zerodiv":
            result = 1 / 0
        elif error_type == "keyerror":
            test_dict = {"a": 1}
            value = test_dict["b"]
        elif error_type == "attribute":
            None.undefined_method()
        elif error_type == "import":
            import module_qui_nexiste_pas
        elif error_type == "runtime":
            raise RuntimeError("Erreur runtime de test (fatale)")
        else:
            raise ValueError(f"Type d'erreur inconnu : {error_type}")

    @commands.command(name="errorstats", aliases=["errstats"])
    async def error_stats(self, ctx):
        """Affiche des statistiques sur les erreurs"""
        error_tracker = self.bot.get_cog("ErrorTracker")
        if not error_tracker:
            await ctx.send("❌ Système d'erreurs non chargé")
            return

        errors = list(error_tracker.error_cache)

        if not errors:
            embed = ModdyResponse.info(
                "Aucune erreur",
                "Aucune erreur n'a été enregistrée depuis le dernier redémarrage"
            )
            await ctx.send(embed=embed)
            return

        # Calcul des stats
        error_types = {}
        error_files = {}
        error_users = {}

        for error in errors:
            data = error['data']

            # Par type
            error_type = data.get('type', 'Unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1

            # Par fichier
            error_file = data.get('file', 'Unknown')
            error_files[error_file] = error_files.get(error_file, 0) + 1

            # Par utilisateur (si disponible)
            if 'user' in data:
                user_str = data['user'].split('(')[0].strip()
                error_users[user_str] = error_users.get(user_str, 0) + 1

        # Trie et limite
        top_types = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
        top_files = sorted(error_files.items(), key=lambda x: x[1], reverse=True)[:5]
        top_users = sorted(error_users.items(), key=lambda x: x[1], reverse=True)[:5]

        embed = discord.Embed(
            title="Statistiques des erreurs",
            description=f"Total : `{len(errors)}` erreurs enregistrées",
            color=COLORS["info"],
            timestamp=datetime.utcnow()
        )

        # Top types d'erreurs
        types_text = "\n".join([f"`{t[0]}` : **{t[1]}**" for t in top_types])
        embed.add_field(
            name="Types d'erreurs",
            value=types_text or "Aucune",
            inline=True
        )

        # Top fichiers
        files_text = "\n".join([f"`{f[0]}` : **{f[1]}**" for f in top_files])
        embed.add_field(
            name="Fichiers affectés",
            value=files_text or "Aucun",
            inline=True
        )

        # Top utilisateurs (si applicable)
        if top_users:
            users_text = "\n".join([f"{u[0]} : **{u[1]}**" for u in top_users])
            embed.add_field(
                name="Utilisateurs",
                value=users_text,
                inline=True
            )

        # Période
        if errors:
            oldest = errors[0]['timestamp']
            newest = errors[-1]['timestamp']
            duration = newest - oldest
            hours = duration.total_seconds() / 3600

            embed.add_field(
                name="Période",
                value=f"**Première:** `{oldest.strftime('%H:%M:%S')}`\n"
                      f"**Dernière:** `{newest.strftime('%H:%M:%S')}`\n"
                      f"**Durée:** `{hours:.1f}` heures",
                inline=False
            )

        await ctx.send(embed=embed)

        # Log l'action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "errorstats")


async def setup(bot):
    await bot.add_cog(ErrorManagement(bot))