"""
Commande shutdown pour développeurs
Permet d'arrêter le bot proprement
Utilise les composants V2
"""

import discord
from discord.ext import commands
import asyncio
import sys
from datetime import datetime, timezone

# Import du système d'embeds V2
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse


class Shutdown(commands.Cog):
    """Commande pour arrêter le bot"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="shutdown", aliases=["stop", "kill", "exit", "quit"])
    async def shutdown(self, ctx):
        """Arrête le bot proprement avec composants V2"""

        # Composants V2 de confirmation
        components = [
            ModdyEmbed.heading("Confirmation d'arrêt", 2),
            ModdyEmbed.text("Êtes-vous sûr de vouloir arrêter le bot ?"),
            ModdyEmbed.separator(),
            ModdyEmbed.heading("Informations", 3),
            ModdyEmbed.text(f"**Serveurs actifs:** `{len(self.bot.guilds)}`"),
            ModdyEmbed.text(f"**Utilisateurs:** `{len(self.bot.users)}`"),
            ModdyEmbed.text(f"**Uptime:** `{self._get_uptime()}`"),
            ModdyEmbed.separator(),
            ModdyEmbed.text("_Cette action fermera complètement le bot_"),
            ModdyEmbed.action_row([
                ModdyEmbed.button("Confirmer l'arrêt", "shutdown_confirm", style=4),
                ModdyEmbed.button("Annuler", "shutdown_cancel", style=2)
            ])
        ]

        # Vue avec boutons
        view = ShutdownView(self.bot, ctx.author)

        # Log l'action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "shutdown")

        await ctx.send(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components,
            "view": view
        })

    def _get_uptime(self):
        """Calcule l'uptime du bot"""
        if not hasattr(self.bot, 'launch_time'):
            return "N/A"

        uptime = datetime.now(timezone.utc) - self.bot.launch_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


class ShutdownView(discord.ui.View):
    """Vue pour confirmer l'arrêt"""

    def __init__(self, bot, author):
        super().__init__(timeout=30)
        self.bot = bot
        self.author = author
        self.confirmed = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Seul l'auteur peut utiliser les boutons"""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "Seul l'auteur de la commande peut confirmer l'arrêt.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(custom_id="shutdown_confirm")
    async def confirm_shutdown(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Confirme l'arrêt du bot"""
        self.confirmed = True

        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True

        # Composants V2 d'arrêt
        components = [
            ModdyEmbed.heading("Arrêt en cours...", 2),
            ModdyEmbed.text("Le bot s'arrête proprement."),
            ModdyEmbed.separator(),
            ModdyEmbed.text(f"**Action effectuée par:** {interaction.user.mention} (`{interaction.user.id}`)"),
            ModdyEmbed.text(f"_Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}_")
        ]

        await interaction.response.edit_message(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components,
            "view": self
        })

        # Log l'action
        import logging
        logger = logging.getLogger('moddy')
        logger.info(f"Arrêt confirmé par {interaction.user} ({interaction.user.id})")

        # Attendre un peu pour que le message soit mis à jour
        await asyncio.sleep(1)

        # Arrêter le bot
        await self.bot.close()
        sys.exit(0)

    @discord.ui.button(custom_id="shutdown_cancel")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Annule l'arrêt"""
        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True

        # Composants V2 d'annulation
        components = [
            ModdyEmbed.heading("Arrêt annulé", 2),
            ModdyEmbed.text("Le bot continue de fonctionner normalement."),
            ModdyEmbed.separator(),
            ModdyEmbed.text(f"_Annulé par {interaction.user}_")
        ]

        await interaction.response.edit_message(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components,
            "view": self
        })
        self.stop()

    async def on_timeout(self):
        """Appelé après le timeout"""
        if not self.confirmed and self.message:
            # Désactiver tous les boutons
            for item in self.children:
                item.disabled = True

            try:
                # Composants V2 de timeout
                components = [
                    ModdyEmbed.heading("Temps écoulé", 2),
                    ModdyEmbed.text("La demande d'arrêt a expiré."),
                    ModdyEmbed.separator(),
                    ModdyEmbed.text("_Timeout après 30 secondes_")
                ]

                await self.message.edit(**{
                    "flags": ModdyEmbed.V2_FLAGS,
                    "components": components,
                    "view": self
                })
            except:
                pass


async def setup(bot):
    await bot.add_cog(Shutdown(bot))