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
from utils.components_v2 import create_error_message, create_success_message, create_info_message, create_warning_message, create_simple_message, EMOJIS

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
            view = create_error_message("Permission Denied", reason)
            await message.reply(view=view, mention_author=False)
            return

        # Route to appropriate command
        if command_name == "invite":
            await self.handle_invite_command(message, args)
        elif command_name == "serverinfo":
            await self.handle_serverinfo_command(message, args)
        elif command_name == "help":
            await self.handle_help_command(message, args)
        elif command_name == "flex":
            await self.handle_flex_command(message, args)
        else:
            view = create_error_message(
                "Unknown Command",
                f"Team command `{command_name}` not found.\n\nUse `<@1373916203814490194> t.help` for a list of available commands."
            )
            await message.reply(view=view, mention_author=False)

    async def handle_invite_command(self, message: discord.Message, args: str):
        """
        Handle t.invite command - Get an invite to a server
        Usage: <@1373916203814490194> t.invite [server_id]
        """
        if not args:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> t.invite [server_id]`\n\nProvide a server ID to get an invite link."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Parse server ID
        try:
            guild_id = int(args.strip())
        except ValueError:
            view = create_error_message(
                f"{EMOJIS['snowflake']} Invalid Server ID",
                "Please provide a valid server ID (numbers only)."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Get guild
        guild = self.bot.get_guild(guild_id)
        if not guild:
            view = create_error_message(
                "Server Not Found",
                f"MODDY is not in a server with ID `{guild_id}`."
            )
            await message.reply(view=view, mention_author=False)
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
                view = create_error_message(
                    "Cannot Create Invite",
                    f"MODDY doesn't have permission to create invites in **{guild.name}**."
                )
                await message.reply(view=view, mention_author=False)
                return

            # Create invite (7 days, 1 use, no temporary membership)
            invite = await invite_channel.create_invite(
                max_age=604800,  # 7 days
                max_uses=5,
                unique=True,
                reason=f"Staff invite requested by {message.author}"
            )

            # Create success view
            fields = [
                {
                    'name': f"{EMOJIS['web']} Server Information",
                    'value': f"**Name:** {guild.name}\n**ID:** `{guild.id}`\n**Members:** {guild.member_count:,}"
                },
                {
                    'name': "Invite Link",
                    'value': f"[Click here to join]({invite.url})\n`{invite.url}`"
                },
                {
                    'name': f"{EMOJIS['time']} Invite Details",
                    'value': f"**Channel:** {invite_channel.mention}\n**Expires:** <t:{int((datetime.now(timezone.utc).timestamp() + 604800))}:R>\n**Max Uses:** 5"
                }
            ]

            view = create_success_message(
                "Server Invite Created",
                f"Invite link for **{guild.name}**",
                fields=fields,
                footer=f"Requested by {message.author}"
            )

            await message.reply(view=view, mention_author=False)

            # Log the action
            logger.info(f"Staff {message.author} ({message.author.id}) requested invite for {guild.name} ({guild.id})")

        except discord.Forbidden:
            view = create_error_message(
                "Permission Denied",
                f"MODDY doesn't have permission to create invites in **{guild.name}**."
            )
            await message.reply(view=view, mention_author=False)

        except Exception as e:
            logger.error(f"Error creating invite: {e}")
            view = create_error_message(
                "Error",
                f"Failed to create invite: {str(e)}"
            )
            await message.reply(view=view, mention_author=False)

    async def handle_serverinfo_command(self, message: discord.Message, args: str):
        """
        Handle t.serverinfo command - Get information about a server
        Usage: <@1373916203814490194> t.serverinfo [server_id]
        """
        if not args:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> t.serverinfo [server_id]`\n\nProvide a server ID to get information."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Parse server ID
        try:
            guild_id = int(args.strip())
        except ValueError:
            view = create_error_message(
                f"{EMOJIS['snowflake']} Invalid Server ID",
                "Please provide a valid server ID (numbers only)."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Get guild
        guild = self.bot.get_guild(guild_id)
        if not guild:
            view = create_error_message(
                "Server Not Found",
                f"MODDY is not in a server with ID `{guild_id}`."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Create info view
        fields = []

        # Basic info
        fields.append({
            'name': f"{EMOJIS['info']} Basic Information",
            'value': f"**Name:** {guild.name}\n**ID:** `{guild.id}`\n**Owner:** {guild.owner.mention if guild.owner else 'Unknown'} (`{guild.owner_id}`)\n**Created:** <t:{int(guild.created_at.timestamp())}:R>"
        })

        # Member stats
        fields.append({
            'name': f"{EMOJIS['user']} Members",
            'value': f"**Total:** {guild.member_count:,}\n**Humans:** {len([m for m in guild.members if not m.bot]):,}\n**Bots:** {len([m for m in guild.members if m.bot]):,}"
        })

        # Channel stats
        fields.append({
            'name': "Channels",
            'value': f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories:** {len(guild.categories)}"
        })

        # Role count
        fields.append({
            'name': "Roles",
            'value': f"**Total:** {len(guild.roles)}"
        })

        # Boost info
        fields.append({
            'name': "Boost Status",
            'value': f"**Level:** {guild.premium_tier}\n**Boosts:** {guild.premium_subscription_count}"
        })

        # Features
        if guild.features:
            features = [f.replace('_', ' ').title() for f in guild.features[:10]]
            fields.append({
                'name': "Features",
                'value': ", ".join(features)
            })

        view = create_info_message(
            f"{EMOJIS['web']} Server Information - {guild.name}",
            f"Detailed information about **{guild.name}**",
            fields=fields,
            footer=f"Requested by {message.author}"
        )

        await message.reply(view=view, mention_author=False)

    async def handle_help_command(self, message: discord.Message, args: str):
        """
        Handle t.help command - Show available team commands
        Usage: <@1373916203814490194> t.help
        """
        # Get user roles to show relevant commands
        user_roles = await staff_permissions.get_user_roles(message.author.id)

        fields = []

        # Team commands (available to all staff)
        team_commands = [
            ("t.help", "Show this help message"),
            ("t.invite [server_id]", "Get an invite link to a server"),
            ("t.serverinfo [server_id]", "Get detailed information about a server"),
            ("t.flex", "Prove you are a member of the Moddy team")
        ]

        fields.append({
            'name': f"{EMOJIS['commands']} Team Commands (All Staff)",
            'value': "\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in team_commands])
        })

        # Management commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.MANAGEMENT):
            mgmt_commands = [
                ("m.rank @user", "Add a user to the staff team"),
                ("m.setstaff @user", "Manage staff member permissions"),
                ("m.stafflist", "List all staff members"),
                ("m.staffinfo [@user]", "Show staff member information")
            ]

            fields.append({
                'name': "👑 Management Commands",
                'value': "\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in mgmt_commands])
            })

        # Developer commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.DEV):
            dev_commands = [
                ("d.reload [extension]", "Reload bot extensions"),
                ("d.shutdown", "Shutdown the bot"),
                ("d.stats", "Show bot statistics"),
                ("d.sql [query]", "Execute SQL query"),
                ("d.jsk [code]", "Execute Python code")
            ]

            fields.append({
                'name': f"{EMOJIS['dev']} Developer Commands",
                'value': "\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in dev_commands])
            })

        # Moderator commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.MODERATOR):
            mod_commands = [
                ("mod.blacklist @user [reason]", "Blacklist a user"),
                ("mod.unblacklist @user [reason]", "Remove user from blacklist"),
                ("mod.userinfo @user", "Get detailed user information"),
                ("mod.guildinfo [guild_id]", "Get detailed guild information")
            ]

            fields.append({
                'name': "🛡️ Moderator Commands",
                'value': "\n".join([f"`<@1373916203814490194> {cmd}` - {desc}" for cmd, desc in mod_commands])
            })

        # Support commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.SUPPORT):
            fields.append({
                'name': "🎧 Support Commands",
                'value': "Support commands are in development."
            })

        # Communication commands
        if await staff_permissions.can_use_command_type(message.author.id, CommandType.COMMUNICATION):
            fields.append({
                'name': "💬 Communication Commands",
                'value': "Communication commands are in development."
            })

        view = create_info_message(
            f"{EMOJIS['commands']} MODDY Staff Commands",
            "Available staff commands based on your permissions.",
            fields=fields,
            footer=f"Requested by {message.author} | Your roles: {', '.join([r.value for r in user_roles])}"
        )

        await message.reply(view=view, mention_author=False)

    async def handle_flex_command(self, message: discord.Message, args: str):
        """
        Handle t.flex command - Prove staff membership on a server
        Usage: <@1373916203814490194> t.flex
        """
        # Get user roles
        user_roles = await staff_permissions.get_user_roles(message.author.id)

        if not user_roles:
            view = create_error_message(
                "Not a Staff Member",
                "You don't have any staff roles in the MODDY team."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Get primary role (highest in hierarchy)
        primary_role = user_roles[0]

        # Format role name for display
        role_display = ""
        if primary_role.value == "Dev":
            role_display = "developer"
        elif primary_role.value == "Manager":
            role_display = "manager"
        elif primary_role.value == "Supervisor_Mod":
            role_display = "moderation supervisor"
        elif primary_role.value == "Supervisor_Com":
            role_display = "member"  # Communication supervisor shows as member
        elif primary_role.value == "Supervisor_Sup":
            role_display = "support agents"  # Support supervisor
        elif primary_role.value == "Moderator":
            role_display = "moderator"
        elif primary_role.value == "Communication":
            role_display = "member"  # Communication shows as member
        elif primary_role.value == "Support":
            role_display = "support agents"  # Support shows as support agents
        else:
            role_display = "member"

        # Create the verification message with Components V2
        from discord.ui import LayoutView, Container, TextDisplay

        class Components(discord.ui.LayoutView):
            container1 = discord.ui.Container(
                discord.ui.TextDisplay(content=f"{EMOJIS['verified']} {message.author.mention} **is a {role_display} of the Moddy Team**"),
                discord.ui.TextDisplay(content="-# Moddy team are authorized to take action on your server.\n-# This message was sent to prevent identity theft. \n-# [Support](https://moddy.app/support) • [Documentation](https://docs.moddy.app/)"),
            )

        view = Components()

        # Send in channel (not as reply) and delete command message
        try:
            await message.channel.send(view=view)
            await message.delete()

            # Log the action
            logger.info(f"Staff {message.author} ({message.author.id}) used t.flex in {message.guild.name if message.guild else 'DM'} ({message.guild.id if message.guild else 'N/A'})")

        except discord.Forbidden:
            view_error = create_error_message(
                "Permission Denied",
                "I don't have permission to send messages or delete messages in this channel."
            )
            await message.reply(view=view_error, mention_author=False)

        except Exception as e:
            logger.error(f"Error in t.flex command: {e}")
            view_error = create_error_message(
                "Error",
                f"Failed to send verification message: {str(e)}"
            )
            await message.reply(view=view_error, mention_author=False)


async def setup(bot):
    await bot.add_cog(TeamCommands(bot))
