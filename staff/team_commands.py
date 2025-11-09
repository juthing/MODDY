"""
Team Commands (t. prefix)
Common commands accessible to all staff members
"""

import discord
from discord.ext import commands
from typing import Optional
import logging
from datetime import datetime, timezone

from utils.staff_permissions import staff_permissions, CommandType
from database import db
from config import COLORS
from utils.components_v2 import create_error_message, create_success_message, create_info_message, create_warning_message

logger = logging.getLogger('moddy.team_commands')


class TeamCommands(commands.Cog):
    """Team commands accessible to all staff (t. prefix)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for team commands with new syntax"""
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

        # Only handle team commands in this cog
        if command_type != CommandType.TEAM:
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
            await message.reply(embed=embed, mention_author=False)
            return

        # Route to appropriate command
        if command_name == "invite":
            await self.handle_invite_command(message, args)
        elif command_name == "serverinfo":
            await self.handle_serverinfo_command(message, args)
        elif command_name == "help":
            await self.handle_help_command(message, args)
        else:
            embed = discord.Embed(
                title="❌ Unknown Command",
                description=f"Team command `{command_name}` not found.\n\nUse `<@1373916203814490194> t.help` for a list of available commands.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)

    async def handle_invite_command(self, message: discord.Message, args: str):
        """
        Handle t.invite command - Get an invite to a server
        Usage: <@1373916203814490194> t.invite [server_id]
        """
        if not args:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@1373916203814490194> t.invite [server_id]`\n\nProvide a server ID to get an invite link.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Parse server ID
        try:
            guild_id = int(args.strip())
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Server ID",
                description="Please provide a valid server ID (numbers only).",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Get guild
        guild = self.bot.get_guild(guild_id)
        if not guild:
            embed = discord.Embed(
                title="❌ Server Not Found",
                description=f"MODDY is not in a server with ID `{guild_id}`.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Try to create an invite
        try:
            # Find a suitable channel (preferably system channel or first text channel)
            invite_channel = guild.system_channel

            if not invite_channel:
                # Find first text channel where bot can create invites
                for channel in guild.text_channels:
                    if channel.permissions_for(guild.me).create_instant_invite:
                        invite_channel = channel
                        break

            if not invite_channel:
                embed = discord.Embed(
                    title="❌ Cannot Create Invite",
                    description=f"MODDY doesn't have permission to create invites in **{guild.name}**.",
                    color=COLORS["error"]
                )
                await message.reply(embed=embed, mention_author=False)
                return

            # Create invite (7 days, 1 use, no temporary membership)
            invite = await invite_channel.create_invite(
                max_age=604800,  # 7 days
                max_uses=5,
                unique=True,
                reason=f"Staff invite requested by {message.author}"
            )

            # Create success embed
            embed = discord.Embed(
                title="✅ Server Invite Created",
                description=f"Invite link for **{guild.name}**",
                color=COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Server Information",
                value=f"**Name:** {guild.name}\n**ID:** `{guild.id}`\n**Members:** {guild.member_count:,}",
                inline=False
            )

            embed.add_field(
                name="Invite Link",
                value=f"[Click here to join]({invite.url})\n`{invite.url}`",
                inline=False
            )

            embed.add_field(
                name="Invite Details",
                value=f"**Channel:** {invite_channel.mention}\n**Expires:** <t:{int((datetime.now(timezone.utc).timestamp() + 604800))}:R>\n**Max Uses:** 5",
                inline=False
            )

            if guild.icon:
                embed.set_thumbnail(url=guild.icon.url)

            embed.set_footer(text=f"Requested by {message.author}")

            await message.reply(embed=embed, mention_author=False)

            # Log the action
            logger.info(f"Staff {message.author} ({message.author.id}) requested invite for {guild.name} ({guild.id})")

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description=f"MODDY doesn't have permission to create invites in **{guild.name}**.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)

        except Exception as e:
            logger.error(f"Error creating invite: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"Failed to create invite: {str(e)}",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)

    async def handle_serverinfo_command(self, message: discord.Message, args: str):
        """
        Handle t.serverinfo command - Get information about a server
        Usage: <@1373916203814490194> t.serverinfo [server_id]
        """
        if not args:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@1373916203814490194> t.serverinfo [server_id]`\n\nProvide a server ID to get information.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Parse server ID
        try:
            guild_id = int(args.strip())
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Server ID",
                description="Please provide a valid server ID (numbers only).",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Get guild
        guild = self.bot.get_guild(guild_id)
        if not guild:
            embed = discord.Embed(
                title="❌ Server Not Found",
                description=f"MODDY is not in a server with ID `{guild_id}`.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Create info embed
        embed = discord.Embed(
            title=f"📊 Server Information",
            color=COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )

        # Basic info
        embed.add_field(
            name="Basic Information",
            value=f"**Name:** {guild.name}\n**ID:** `{guild.id}`\n**Owner:** {guild.owner.mention if guild.owner else 'Unknown'} (`{guild.owner_id}`)\n**Created:** <t:{int(guild.created_at.timestamp())}:R>",
            inline=False
        )

        # Member stats
        embed.add_field(
            name="Members",
            value=f"**Total:** {guild.member_count:,}\n**Humans:** {len([m for m in guild.members if not m.bot]):,}\n**Bots:** {len([m for m in guild.members if m.bot]):,}",
            inline=True
        )

        # Channel stats
        embed.add_field(
            name="Channels",
            value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories:** {len(guild.categories)}",
            inline=True
        )

        # Role count
        embed.add_field(
            name="Roles",
            value=f"**Total:** {len(guild.roles)}",
            inline=True
        )

        # Boost info
        embed.add_field(
            name="Boost Status",
            value=f"**Level:** {guild.premium_tier}\n**Boosts:** {guild.premium_subscription_count}",
            inline=True
        )

        # Features
        if guild.features:
            features = [f.replace('_', ' ').title() for f in guild.features[:10]]
            embed.add_field(
                name="Features",
                value=", ".join(features),
                inline=False
            )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.set_footer(text=f"Requested by {message.author}")

        await message.reply(embed=embed, mention_author=False)

    async def handle_help_command(self, message: discord.Message, args: str):
        """
        Handle t.help command - Show available team commands
        Usage: <@1373916203814490194> t.help
        """
        # Get user roles to show relevant commands
        user_roles = await staff_permissions.get_user_roles(message.author.id)

        embed = discord.Embed(
            title="📚 MODDY Staff Commands",
            description="Available staff commands based on your permissions.",
            color=COLORS["primary"],
            timestamp=datetime.now(timezone.utc)
        )

        # Team commands (available to all staff)
        team_commands = [
            ("t.help", "Show this help message"),
            ("t.invite [server_id]", "Get an invite link to a server"),
            ("t.serverinfo [server_id]", "Get detailed information about a server")
        ]

        embed.add_field(
            name="🌐 Team Commands (All Staff)",
            value="\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in team_commands]),
            inline=False
        )

        # Management commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.MANAGEMENT):
            mgmt_commands = [
                ("m.rank @user", "Add a user to the staff team"),
                ("m.setstaff @user", "Manage staff member permissions"),
                ("m.stafflist", "List all staff members"),
                ("m.staffinfo [@user]", "Show staff member information")
            ]

            embed.add_field(
                name="👑 Management Commands",
                value="\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in mgmt_commands]),
                inline=False
            )

        # Developer commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.DEV):
            dev_commands = [
                ("d.reload [extension]", "Reload bot extensions"),
                ("d.shutdown", "Shutdown the bot"),
                ("d.stats", "Show bot statistics"),
                ("d.sql [query]", "Execute SQL query"),
                ("d.jsk [code]", "Execute Python code")
            ]

            embed.add_field(
                name="💻 Developer Commands",
                value="\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in dev_commands]),
                inline=False
            )

        # Moderator commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.MODERATOR):
            mod_commands = [
                ("mod.blacklist @user [reason]", "Blacklist a user"),
                ("mod.unblacklist @user [reason]", "Remove user from blacklist"),
                ("mod.userinfo @user", "Get detailed user information"),
                ("mod.guildinfo [guild_id]", "Get detailed guild information")
            ]

            embed.add_field(
                name="🛡️ Moderator Commands",
                value="\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in mod_commands]),
                inline=False
            )

        # Support commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.SUPPORT):
            embed.add_field(
                name="🎧 Support Commands",
                value="Support commands are in development.",
                inline=False
            )

        # Communication commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.COMMUNICATION):
            embed.add_field(
                name="💬 Communication Commands",
                value="Communication commands are in development.",
                inline=False
            )

        embed.set_footer(text=f"Requested by {message.author} | Your roles: {', '.join([r.value for r in user_roles])}")

        await message.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(TeamCommands(bot))
