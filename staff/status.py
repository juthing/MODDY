"""
Commande pour changer le statut du bot
Réservée aux développeurs
Utilise les composants V2
"""

import discord
from discord.ext import commands
from typing import Optional

# Import du système d'embeds V2
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse


class StatusCommand(commands.Cog):
    """Gestion du statut du bot"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.group(name="status", aliases=["presence"], invoke_without_command=True)
    async def status_group(self, ctx):
        """Commande principale pour gérer le statut"""
        if ctx.invoked_subcommand is None:
            components = [
                ModdyEmbed.heading("Utilisation", 3),
                ModdyEmbed.text("`status set <type> <texte>` - Change le statut"),
                ModdyEmbed.text("`status clear` - Retire le statut"),
                ModdyEmbed.text("`status pause` - Met en pause les changements auto"),
                ModdyEmbed.text("`status resume` - Reprend les changements auto"),
                ModdyEmbed.separator(),
                ModdyEmbed.text("**Types:** `playing`, `watching`, `listening`, `streaming`, `competing`")
            ]

            await ctx.send(**{
                "flags": ModdyEmbed.V2_FLAGS,
                "components": components
            })

    @status_group.command(name="set")
    async def set_status(self, ctx, activity_type: str, *, text: str):
        """Change le statut du bot"""
        # Map des types d'activité
        activity_types = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "streaming": discord.ActivityType.streaming,
            "competing": discord.ActivityType.competing
        }

        if activity_type.lower() not in activity_types:
            components = ModdyResponse.error(
                "Type invalide",
                f"Utilise : {', '.join(activity_types.keys())}"
            )
            await ctx.send(**{
                "flags": ModdyEmbed.V2_FLAGS,
                "components": components
            })
            return

        # Arrête la tâche de mise à jour auto si elle tourne
        if hasattr(self.bot, 'status_update') and self.bot.status_update.is_running():
            self.bot.status_update.stop()

        # Change le statut
        activity = discord.Activity(
            type=activity_types[activity_type.lower()],
            name=text
        )

        await self.bot.change_presence(activity=activity)

        components = ModdyResponse.success(
            "Statut changé",
            f"**{activity_type}** {text}"
        )

        await ctx.send(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components
        })

        # Log l'action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "status")

    @status_group.command(name="clear", aliases=["remove", "none"])
    async def clear_status(self, ctx):
        """Retire le statut du bot"""
        await self.bot.change_presence(activity=None)
        await ctx.send("✅ Statut retiré")

        # Log
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "status")

    @status_group.command(name="pause", aliases=["stop"])
    async def pause_auto_status(self, ctx):
        """Met en pause les changements automatiques de statut"""
        if hasattr(self.bot, 'status_update') and self.bot.status_update.is_running():
            self.bot.status_update.stop()
            await ctx.send("⏸️ Changements automatiques de statut mis en pause")
        else:
            await ctx.send("ℹ️ Les changements automatiques sont déjà en pause")

    @status_group.command(name="resume", aliases=["start"])
    async def resume_auto_status(self, ctx):
        """Reprend les changements automatiques de statut"""
        if hasattr(self.bot, 'status_update') and not self.bot.status_update.is_running():
            self.bot.status_update.start()
            await ctx.send("▶️ Changements automatiques de statut repris")
        else:
            await ctx.send("ℹ️ Les changements automatiques sont déjà actifs")

    @status_group.command(name="streaming")
    async def set_streaming(self, ctx, url: str, *, game: str):
        """Définit un statut de streaming"""
        # Vérifie que l'URL est Twitch ou YouTube
        if not any(domain in url.lower() for domain in ["twitch.tv", "youtube.com", "youtu.be"]):
            await ctx.send("❌ L'URL doit être un lien Twitch ou YouTube")
            return

        # Arrête les mises à jour auto
        if hasattr(self.bot, 'status_update') and self.bot.status_update.is_running():
            self.bot.status_update.stop()

        # Crée l'activité streaming
        activity = discord.Streaming(name=game, url=url)
        await self.bot.change_presence(activity=activity)

        await ctx.send(f"🔴 Statut streaming défini : **{game}**\nURL : {url}")

        # Log
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "streaming")

    @status_group.command(name="custom")
    async def set_custom(self, ctx, emoji: Optional[str] = None, *, text: str):
        """Définit un statut personnalisé (comme les utilisateurs)"""
        # Note: Les bots ne peuvent pas vraiment avoir de statut personnalisé
        # mais on peut simuler avec une activité playing

        if emoji:
            text = f"{emoji} {text}"

        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name=text
        )

        await self.bot.change_presence(activity=activity)
        await ctx.send(f"✅ Statut personnalisé : {text}")


async def setup(bot):
    await bot.add_cog(StatusCommand(bot))