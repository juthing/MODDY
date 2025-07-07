"""
Commande ping pour développeurs
Affiche des informations détaillées sur le statut du bot
"""

import discord
from discord.ext import commands
import asyncio
import time
import platform
import psutil
from datetime import datetime, timezone
from typing import Optional

from config import COLORS, EMOJIS


class DevPing(commands.Cog):
    """Commandes de diagnostic pour développeurs"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="ping", aliases=["p", "status", "diag"])
    async def ping_detailed(self, ctx):
        """Affiche le statut détaillé du bot"""

        # Message de chargement
        embed_loading = discord.Embed(
            description=f"{EMOJIS['loading']} Diagnostic en cours...",
            color=COLORS["info"]
        )
        msg = await ctx.send(embed=embed_loading)

        # Mesure de la latence du message
        start_time = time.perf_counter()

        # Tests de latence
        api_latency = round(self.bot.latency * 1000, 2)

        # Latence du message
        end_time = time.perf_counter()
        message_latency = round((end_time - start_time) * 1000, 2)

        # Test de la base de données
        db_status = "❌ Non connectée"
        db_latency = "N/A"

        if self.bot.db_pool:
            try:
                db_start = time.perf_counter()
                async with self.bot.db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                db_end = time.perf_counter()
                db_latency = f"{round((db_end - db_start) * 1000, 2)}ms"
                db_status = "✅ Opérationnelle"
            except Exception as e:
                db_status = f"❌ Erreur : {type(e).__name__}"

        # Informations système
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = process.cpu_percent(interval=0.1)

        # Uptime
        uptime = datetime.now(timezone.utc) - self.bot.launch_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Création de l'embed principal
        embed = discord.Embed(
            title="📊 Diagnostic Système",
            color=COLORS["developer"],
            timestamp=datetime.now(timezone.utc)
        )

        # Statut général avec emojis conditionnels
        api_emoji = "🟢" if api_latency < 100 else "🟡" if api_latency < 200 else "🔴"
        msg_emoji = "🟢" if message_latency < 100 else "🟡" if message_latency < 200 else "🔴"

        embed.add_field(
            name="🌐 Discord API",
            value=f"{api_emoji} **Statut**: En ligne\n"
                  f"⏱️ **Latence**: {api_latency}ms\n"
                  f"🔗 **Gateway**: v{discord.__version__}",
            inline=True
        )

        embed.add_field(
            name="🤖 Bot",
            value=f"{msg_emoji} **Statut**: Opérationnel\n"
                  f"⏱️ **Réponse**: {message_latency}ms\n"
                  f"⏳ **Uptime**: {uptime_str}",
            inline=True
        )

        embed.add_field(
            name="🗄️ Base de données",
            value=f"**Statut**: {db_status}\n"
                  f"⏱️ **Latence**: {db_latency}\n"
                  f"💾 **Type**: PostgreSQL (Neon)",
            inline=True
        )

        # Deuxième ligne
        embed.add_field(
            name="📈 Performance",
            value=f"💻 **CPU**: {cpu_percent}%\n"
                  f"🧠 **RAM**: {memory_usage:.1f} MB\n"
                  f"⚙️ **Threads**: {len(self.bot.guilds)} actifs",
            inline=True
        )

        embed.add_field(
            name="📊 Statistiques",
            value=f"🏢 **Serveurs**: {len(self.bot.guilds)}\n"
                  f"👥 **Utilisateurs**: {len(self.bot.users)}\n"
                  f"📝 **Commandes**: {len(self.bot.commands)}",
            inline=True
        )

        embed.add_field(
            name="🖥️ Système",
            value=f"**OS**: {platform.system()} {platform.release()}\n"
                  f"**Python**: {platform.python_version()}\n"
                  f"**Node**: {platform.node()}",
            inline=True
        )

        # Footer avec info développeur
        embed.set_footer(
            text=f"Demandé par {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        # Boutons d'action
        view = DiagnosticView(self.bot, ctx.author)

        await msg.edit(embed=embed, view=view)

    @commands.command(name="fastping", aliases=["fp"])
    async def fast_ping(self, ctx):
        """Ping rapide sans détails"""
        start = time.perf_counter()
        msg = await ctx.send("🏓 Pong!")
        end = time.perf_counter()

        await msg.edit(
            content=f"🏓 Pong! | "
                    f"API: `{round(self.bot.latency * 1000)}ms` | "
                    f"Message: `{round((end - start) * 1000)}ms`"
        )


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
                "❌ Seul l'auteur de la commande peut utiliser ces boutons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Rafraîchir", style=discord.ButtonStyle.primary, emoji="🔄")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rafraîchit les statistiques"""
        await interaction.response.send_message("♻️ Rafraîchissement...", ephemeral=True)

        # Relance la commande
        ctx = await self.bot.get_context(interaction.message)
        ctx.author = self.author
        await self.bot.get_command("ping").invoke(ctx)

    @discord.ui.button(label="Collecter les déchets", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def garbage_collect(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Force le garbage collector Python"""
        import gc
        collected = gc.collect()
        await interaction.response.send_message(
            f"🗑️ Garbage collector exécuté : {collected} objets libérés",
            ephemeral=True
        )

    @discord.ui.button(label="Logs", style=discord.ButtonStyle.secondary, emoji="📋")
    async def show_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche les derniers logs"""
        from config import LOG_FILE

        if LOG_FILE.exists():
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_logs = ''.join(lines[-10:])  # 10 dernières lignes

            await interaction.response.send_message(
                f"📋 **Derniers logs :**\n```\n{last_logs[-1900:]}\n```",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ Aucun fichier de log trouvé",
                ephemeral=True
            )

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.danger, emoji="❌")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ferme le diagnostic"""
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


async def setup(bot):
    await bot.add_cog(DevPing(bot))