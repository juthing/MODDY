"""
Ping command for developers.
Displays detailed information about the bot's status.
Clean style without system emojis.
"""

import discord
from discord.ext import commands
import asyncio
import time
import platform
import psutil
from datetime import datetime, timezone
from typing import Optional

# Import the clean embed system
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse, format_diagnostic_embed
from config import COLORS


class StaffDiagnostic(commands.Cog):
    """Diagnostic commands for developers."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Checks if the user is a developer."""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="diag", aliases=["diagnostic", "sysinfo"])
    async def diagnostic(self, ctx):
        """Displays the detailed status of the bot."""

        # Loading message
        loading_embed = ModdyResponse.loading("Running diagnostic...")
        msg = await ctx.send(embed=loading_embed)

        # Measure message latency
        start_time = time.perf_counter()

        # Latency tests
        api_latency = round(self.bot.latency * 1000, 2)

        # Message latency
        end_time = time.perf_counter()
        message_latency = round((end_time - start_time) * 1000, 2)

        # Database test
        db_status = "Not Connected"
        db_latency = "N/A"

        if self.bot.db_pool:
            try:
                db_start = time.perf_counter()
                async with self.bot.db_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                db_end = time.perf_counter()
                db_latency = f"`{round((db_end - db_start) * 1000, 2)}ms`"
                db_status = "Operational"
            except Exception as e:
                db_status = f"Error: `{type(e).__name__}`"

        # System information
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = process.cpu_percent(interval=0.1)

        # Uptime
        uptime = datetime.now(timezone.utc) - self.bot.launch_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # Data for the embed
        diagnostic_data = {
            'api_latency': api_latency,
            'message_latency': message_latency,
            'discord_version': discord.__version__,
            'db_status': db_status,
            'db_latency': db_latency,
            'uptime': uptime_str,
            'cpu_percent': cpu_percent,
            'memory_usage': memory_usage,
            'threads': len(self.bot.guilds),
            'guilds': len(self.bot.guilds),
            'users': len(self.bot.users),
            'commands': len(self.bot.commands),
            'os': f"{platform.system()} {platform.release()}",
            'python_version': platform.python_version(),
            'node': platform.node(),
            'author': str(ctx.author)
        }

        # Create the diagnostic embed
        embed = format_diagnostic_embed(diagnostic_data)

        # Create the view with buttons
        view = DiagnosticView(self.bot, ctx.author)

        await msg.edit(embed=embed, view=view)

    @commands.command(name="ping", aliases=["p"])
    async def fast_ping(self, ctx):
        """Quick ping without details."""
        start = time.perf_counter()
        msg = await ctx.send("Pong!")
        end = time.perf_counter()

        await msg.edit(
            content=f"Pong! | API: `{round(self.bot.latency * 1000)}ms` | Message: `{round((end - start) * 1000)}ms`"
        )


class DiagnosticView(discord.ui.View):
    """View with buttons for the diagnostic."""

    def __init__(self, bot, author):
        super().__init__(timeout=60)
        self.bot = bot
        self.author = author

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Checks that only the author can use the buttons."""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "Only the command author can use these buttons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Refreshes the statistics."""
        await interaction.response.send_message("Refreshing...", ephemeral=True)

        # Rerun the command
        ctx = await self.bot.get_context(interaction.message)
        ctx.author = self.author
        await self.bot.get_command("diag").invoke(ctx)

    @discord.ui.button(label="Garbage Collect", style=discord.ButtonStyle.secondary)
    async def garbage_collect(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Forces the Python garbage collector."""
        import gc
        collected = gc.collect()
        await interaction.response.send_message(
            f"Garbage collector run: `{collected}` objects freed.",
            ephemeral=True
        )

    @discord.ui.button(label="Logs", style=discord.ButtonStyle.secondary)
    async def show_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Displays the latest logs."""
        from config import LOG_FILE

        if LOG_FILE.exists():
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                last_logs = ''.join(lines[-10:])  # 10 last lines

            embed = discord.Embed(
                title="Latest Logs",
                description=f"```\n{last_logs[-1900:]}\n```",
                color=COLORS["developer"]
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "No log file found.",
                ephemeral=True
            )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Closes the diagnostic."""
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


async def setup(bot):
    await bot.add_cog(StaffDiagnostic(bot))