"""
Support Commands (sup. prefix)
Commands for support staff (Manager, Supervisor_Sup, Support)
"""

import discord
from discord.ext import commands
from typing import Optional
import logging
from datetime import datetime, timezone

from utils.staff_permissions import staff_permissions, CommandType
from database import db
from config import COLORS

logger = logging.getLogger('moddy.support_commands')


class SupportCommands(commands.Cog):
    """Support commands (sup. prefix)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for support commands with new syntax"""
        # Ignore bots
        if message.author.bot:
            return

        # Check if staff permissions system is ready
        if not staff_permissions or not db:
            return

        # Parse command
        parsed = staff_permissions.parse_staff_command(message.content)
        if not parsed:
            return

        command_type, command_name, args = parsed

        # Only handle support commands in this cog
        if command_type != CommandType.SUPPORT:
            return

        # Check permissions
        allowed, reason = await staff_permissions.check_command_permission(
            message.author.id, command_type, command_name
        )

        if not allowed:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description=reason,
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

        # Route to appropriate command
        if command_name == "help":
            await self.handle_help_command(message, args)
        else:
            embed = discord.Embed(
                title="❌ Unknown Command",
                description=f"Support command `{command_name}` not found.\n\nSupport commands are in development.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=15)

    async def handle_help_command(self, message: discord.Message, args: str):
        """
        Handle sup.help command - Show available support commands
        Usage: <@&1386452009678278818> sup.help
        """
        embed = discord.Embed(
            title="🎧 Support Commands",
            description="Support command system is in development.\n\nAvailable commands will be added soon.",
            color=COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(SupportCommands(bot))
