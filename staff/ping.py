"""
Commande ping pour développeurs
Affiche des informations détaillées sur le statut du bot
Utilise les composants V2 sans bordure colorée
"""

import discord
from discord.ext import commands
import asyncio
import time
import platform
import psutil
from datetime import datetime, timezone
from typing import Optional

# Import du système d'embeds V2
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse


class StaffDiagnostic(commands.Cog):
    """Commandes de diagnostic pour développeurs"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="diag", aliases=["diagnostic", "sysinfo"])
    async def diagnostic(self, ctx):
        """Affiche le statut détaillé du bot avec composants V2"""

        # Message de chargement V2
        loading_msg = {
            "flags": ModdyEmbed.V2_FLAGS,
            "components": ModdyResponse.loading("Diagnostic en cours...")
        }
        msg = await ctx.send(**loading_msg)

        # Mesure de la latence du message
        start_time = time.perf_counter()

        # Tests de latence
        api_latency = round(self.bot.latency * 1000, 2)

        # Latence du message
        end_time = time.perf_counter()
        message_latency = round((end_time - start_time) * 1000, 2)

        # Test de la base de données
        db_status = "Non connectée"
        db_latency = "N/A"

        if self.bot.db_pool:
            try:
                db_start = time.perf_counter()
                async with self.bot.db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                db_end = time.perf_counter()
                db_latency = f"`{round((db_end - db_start) * 1000, 2)}ms`"
                db_status = "Opérationnelle"
            except Exception as e:
                db_status = f"Erreur : `{type(e).__name__}`"

        # Informations système
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = process.cpu_percent(interval=0.1)

        # Uptime
        uptime = datetime.now(timezone.utc) - self.bot.launch_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"`{hours}h {minutes}m {seconds}s`"

        # Création des composants V2
        components = [
            ModdyEmbed.heading("Diagnostic Système", 1),
            ModdyEmbed.separator(),

            # Discord API
            ModdyEmbed.heading("Discord API", 3),
            ModdyEmbed.text(f"**Statut**: En ligne"),
            ModdyEmbed.text(f"**Latence**: `{api_latency}ms`"),
            ModdyEmbed.text(f"**Gateway**: `v{discord.__version__}`"),
            ModdyEmbed.separator(),

            # Bot
            ModdyEmbed.heading("Bot", 3),
            ModdyEmbed.text(f"**Statut**: Opérationnel"),
            ModdyEmbed.text(f"**Réponse**: `{message_latency}ms`"),
            ModdyEmbed.text(f"**Uptime**: {uptime_str}"),
            ModdyEmbed.separator(),

            # Base de données
            ModdyEmbed.heading("Base de données", 3),
            ModdyEmbed.text(f"**Statut**: {db_status}"),
            ModdyEmbed.text(f"**Latence**: {db_latency}"),
            ModdyEmbed.text(f"**Type**: PostgreSQL (Neon)"),
            ModdyEmbed.separator(),

            # Performance
            ModdyEmbed.heading("Performance", 3),
            ModdyEmbed.text(f"**CPU**: `{cpu_percent}%`"),
            ModdyEmbed.text(f"**RAM**: `{memory_usage:.1f} MB`"),
            ModdyEmbed.text(f"**Threads**: `{len(self.bot.guilds)}` actifs"),
            ModdyEmbed.separator(),

            # Statistiques
            ModdyEmbed.heading("Statistiques", 3),
            ModdyEmbed.text(f"**Serveurs**: `{len(self.bot.guilds)}`"),
            ModdyEmbed.text(f"**Utilisateurs**: `{len(self.bot.users)}`"),
            ModdyEmbed.text(f"**Commandes**: `{len(self.bot.commands)}`"),
            ModdyEmbed.separator(),

            # Système
            ModdyEmbed.heading("Système", 3),
            ModdyEmbed.text(f"**OS**: `{platform.system()} {platform.release()}`"),
            ModdyEmbed.text(f"**Python**: `{platform.python_version()}`"),
            ModdyEmbed.text(f"**Node**: `{platform.node()}`"),
            ModdyEmbed.separator(),

            ModdyEmbed.text(f"_Demandé par {ctx.author}_")
        ]

        # Boutons d'action
        buttons = ModdyEmbed.action_row([
            ModdyEmbed.button("Rafraîchir", "diag_refresh", style=1),
            ModdyEmbed.button("Collecter les déchets", "diag_gc", style=2),
            ModdyEmbed.button("Logs", "diag_logs", style=2),
            ModdyEmbed.button("Fermer", "diag_close", style=4)
        ])

        components.append(buttons)

        # Mettre à jour le message avec les composants V2
        await msg.edit(**{
            "content": None,
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components,
            "view": DiagnosticView(self.bot, ctx.author)
        })

    @commands.command(name="ping", aliases=["p"])
    async def fast_ping(self, ctx):
        """Ping rapide sans détails en V2"""
        start = time.perf_counter()

        # Message initial V2
        initial_components = [
            ModdyEmbed.text("Pong!")
        ]

        msg = await ctx.send(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": initial_components
        })

        end = time.perf_counter()

        # Mise à jour avec les latences
        updated_components = [
            ModdyEmbed.text(
                f"Pong! | API: `{round(self.bot.latency * 1000)}ms` | Message: `{round((end - start) * 1000)}ms`")
        ]

        await msg.edit(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": updated_components
        })


class DiagnosticView(discord.ui.View):
    """Vue avec boutons pour le diagnostic"""

    def __init__(self, bot, author):
        super().__init__(timeout=60)
        self.bot = bot
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie que seul l'auteur peut utiliser les boutons"""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "Seul l'auteur de la commande peut utiliser ces boutons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(custom_id="diag_refresh")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rafraîchit les statistiques"""
        await interaction.response.send_message("Rafraîchissement...", ephemeral=True)

        # Relance la commande
        ctx = await self.bot.get_context(interaction.message)
        ctx.author = self.author
        await self.bot.get_command("diag").invoke(ctx)

    @discord.ui.button(custom_id="diag_gc")
    async def garbage_collect(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Force le garbage collector Python"""
        import gc
        collected = gc.collect()
        await interaction.response.send_message(
            f"Garbage collector exécuté : `{collected}` objets libérés",
            ephemeral=True
        )

    @discord.ui.button(custom_id="diag_logs")
    async def show_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche les derniers logs"""
        from config import LOG_FILE

        if LOG_FILE.exists():
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_logs = ''.join(lines[-10:])  # 10 dernières lignes

            components = [
                ModdyEmbed.heading("Derniers logs", 3),
                ModdyEmbed.code_block(last_logs[-1900:], "")
            ]

            await interaction.response.send_message(**{
                "flags": ModdyEmbed.V2_FLAGS,
                "components": components,
                "ephemeral": True
            })
        else:
            await interaction.response.send_message(
                "Aucun fichier de log trouvé",
                ephemeral=True
            )

    @discord.ui.button(custom_id="diag_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ferme le diagnostic"""
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


async def setup(bot):
    await bot.add_cog(StaffDiagnostic(bot))