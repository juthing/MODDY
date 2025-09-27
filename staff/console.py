"""
Developer console management commands.
Allows control over console logs.
"""

import discord
from discord.ext import commands
from datetime import datetime
import logging
import sys
from pathlib import Path
import asyncio

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse
from config import COLORS


class ConsoleCommands(commands.Cog):
    """Commands to manage the console."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Checks if the user is a developer."""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="console", aliases=["logs", "output"])
    async def show_console(self, ctx, lines: int = 20):
        """Displays the latest console logs."""
        console_logger = self.bot.get_cog("ConsoleLogger")
        if not console_logger:
            await ctx.send("<:undone:1398729502028333218> Console logger system not loaded.")
            return

        if lines > 50:
            lines = 50
        elif lines < 1:
            lines = 1

        # Retrieve the latest logs
        recent_logs = list(console_logger.log_buffer)[-lines:]

        if not recent_logs:
            embed = ModdyResponse.info(
                "Empty Console",
                "No recent logs in the buffer."
            )
            await ctx.send(embed=embed)
            return

        # Format the logs
        log_content = []
        for log in recent_logs:
            log_content.append(log['content'])

        # Create the embed
        content = '\n'.join(log_content)
        if len(content) > 4000:
            content = content[:3997] + '...'

        embed = discord.Embed(
            title=f"Console - Last {len(recent_logs)} logs",
            description=f"```\n{content}\n```",
            color=COLORS["primary"],
            timestamp=datetime.now()
        )

        embed.set_footer(text=f"Buffer: {len(console_logger.log_buffer)}/50 logs")

        await ctx.send(embed=embed)

    @commands.command(name="clearconsole", aliases=["clc", "clearcon"])
    async def clear_console(self, ctx):
        """Clears the console buffer."""
        console_logger = self.bot.get_cog("ConsoleLogger")
        if not console_logger:
            await ctx.send("<:undone:1398729502028333218> Console logger system not loaded.")
            return

        count = len(console_logger.log_buffer)
        console_logger.log_buffer.clear()

        # Also clear the queue
        while not console_logger.log_queue.empty():
            try:
                console_logger.log_queue.get_nowait()
            except:
                break

        embed = ModdyResponse.success(
            "Console Cleared",
            f"`{count}` logs have been cleared from the buffer."
        )
        await ctx.send(embed=embed)

    @commands.command(name="loglevel", aliases=["ll", "level"])
    async def set_log_level(self, ctx, level: str = None):
        """Changes the logging level."""
        if not level:
            current = logging.getLogger().getEffectiveLevel()
            embed = discord.Embed(
                title="Logging Level",
                description=f"**Current level:** `{logging.getLevelName(current)}`\n\n"
                            "**Available levels:**\n"
                            "`DEBUG` - All details\n"
                            "`INFO` - General information\n"
                            "`WARNING` - Warnings\n"
                            "`ERROR` - Errors only\n"
                            "`CRITICAL` - Critical errors only",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }

        level_upper = level.upper()
        if level_upper not in levels:
            embed = ModdyResponse.error(
                "Invalid Level",
                f"Use one of these levels: {', '.join(levels.keys())}"
            )
            await ctx.send(embed=embed)
            return

        # Change the level
        logging.getLogger().setLevel(levels[level_upper])

        embed = ModdyResponse.success(
            "Level Changed",
            f"New logging level: `{level_upper}`"
        )
        await ctx.send(embed=embed)

    @commands.command(name="print", aliases=["echo"])
    async def print_to_console(self, ctx, *, message: str):
        """Prints a message to the console."""
        print(f"[DEV {ctx.author}] {message}")

        embed = ModdyResponse.success(
            "Message Sent",
            "The message has been displayed in the console."
        )
        await ctx.send(embed=embed)

    @commands.command(name="logstats", aliases=["lstats"])
    async def log_stats(self, ctx):
        """Displays statistics about the logs."""
        console_logger = self.bot.get_cog("ConsoleLogger")
        if not console_logger:
            await ctx.send("<:undone:1398729502028333218> Console logger system not loaded.")
            return

        # Count logs by type
        log_types = {}
        for log in console_logger.log_buffer:
            log_type = log.get('type', 'unknown')
            log_types[log_type] = log_types.get(log_type, 0) + 1

        embed = discord.Embed(
            title="Log Statistics",
            description=f"**Total:** `{len(console_logger.log_buffer)}` logs in buffer",
            color=COLORS["info"],
            timestamp=datetime.now()
        )

        # Log types
        if log_types:
            types_text = "\n".join(
                [f"`{t}` : **{c}**" for t, c in sorted(log_types.items(), key=lambda x: x[1], reverse=True)])
            embed.add_field(
                name="By Type",
                value=types_text,
                inline=True
            )

        # Sending queue state
        embed.add_field(
            name="Sending Queue",
            value=f"`{console_logger.log_queue.qsize()}` logs pending",
            inline=True
        )

        # Log channel
        embed.add_field(
            name="Discord Channel",
            value=f"<#{console_logger.console_channel_id}>",
            inline=True
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ConsoleCommands(bot))