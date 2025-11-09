"""
Moderator Commands (mod. prefix)
Commands for moderation staff (Manager, Supervisor_Mod, Moderator)
"""

import discord
from discord.ext import commands
from typing import Optional
import logging
from datetime import datetime, timezone

from utils.staff_permissions import staff_permissions, CommandType
from database import db
from config import COLORS
from utils.components_v2 import create_error_message, create_success_message, create_info_message, create_warning_message, EMOJIS

logger = logging.getLogger('moddy.moderator_commands')


class ModeratorCommands(commands.Cog):
    """Moderator commands (mod. prefix)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for moderator commands with new syntax"""
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

        # Only handle moderator commands in this cog
        if command_type != CommandType.MODERATOR:
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
        if command_name == "blacklist":
            await self.handle_blacklist_command(message, args)
        elif command_name == "unblacklist":
            await self.handle_unblacklist_command(message, args)
        elif command_name == "userinfo":
            await self.handle_userinfo_command(message, args)
        elif command_name == "guildinfo":
            await self.handle_guildinfo_command(message, args)
        else:
            view = create_error_message("Unknown Command", f"Moderator command `{command_name}` not found.")
            await message.reply(view=view, mention_author=False)

    async def handle_blacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.blacklist command - Blacklist a user
        Usage: <@1373916203814490194> mod.blacklist @user [reason]
        """
        parts = args.split(maxsplit=1)
        if not parts or not message.mentions:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.blacklist @user [reason]`\n\nMention a user to blacklist."
            )
            await message.reply(view=view, mention_author=False)
            return

        target_user = message.mentions[0]
        reason = parts[1] if len(parts) > 1 else "No reason provided"

        # Can't blacklist staff
        user_data = await db.get_user(target_user.id)
        if user_data['attributes'].get('TEAM') or self.bot.is_developer(target_user.id):
            view = create_error_message(
                "Cannot Blacklist Staff",
                "You cannot blacklist staff members."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Check if already blacklisted
        if user_data['attributes'].get('BLACKLISTED'):
            view = create_warning_message(
                "Already Blacklisted",
                f"{target_user.mention} is already blacklisted."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Blacklist the user
        await db.set_attribute(
            'user', target_user.id, 'BLACKLISTED', True,
            message.author.id, reason
        )

        # Create success view
        fields = [
            {'name': 'User', 'value': f"{target_user} (`{target_user.id}`)"},
            {'name': 'Moderator', 'value': message.author.mention},
            {'name': 'Reason', 'value': reason}
        ]

        view = create_success_message(
            f"{EMOJIS['blacklist']} User Blacklisted",
            f"{target_user.mention} has been blacklisted.",
            fields=fields,
            footer=f"Executed by {message.author}"
        )

        await message.reply(view=view, mention_author=False)

        logger.info(f"User {target_user} ({target_user.id}) blacklisted by {message.author} ({message.author.id})")

    async def handle_unblacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.unblacklist command - Remove user from blacklist
        Usage: <@1373916203814490194> mod.unblacklist @user [reason]
        """
        parts = args.split(maxsplit=1)
        if not parts or not message.mentions:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.unblacklist @user [reason]`\n\nMention a user to unblacklist."
            )
            await message.reply(view=view, mention_author=False)
            return

        target_user = message.mentions[0]
        reason = parts[1] if len(parts) > 1 else "No reason provided"

        # Check if blacklisted
        user_data = await db.get_user(target_user.id)
        if not user_data['attributes'].get('BLACKLISTED'):
            view = create_warning_message(
                "Not Blacklisted",
                f"{target_user.mention} is not blacklisted."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Remove from blacklist
        await db.set_attribute(
            'user', target_user.id, 'BLACKLISTED', None,
            message.author.id, reason
        )

        # Create success view
        fields = [
            {'name': 'User', 'value': f"{target_user} (`{target_user.id}`)"},
            {'name': 'Moderator', 'value': message.author.mention},
            {'name': 'Reason', 'value': reason}
        ]

        view = create_success_message(
            "User Unblacklisted",
            f"{target_user.mention} has been removed from the blacklist.",
            fields=fields,
            footer=f"Executed by {message.author}"
        )

        await message.reply(view=view, mention_author=False)

        logger.info(f"User {target_user} ({target_user.id}) unblacklisted by {message.author} ({message.author.id})")

    async def handle_userinfo_command(self, message: discord.Message, args: str):
        """
        Handle mod.userinfo command - Get detailed user information
        Usage: <@1373916203814490194> mod.userinfo @user
        """
        if not message.mentions:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.userinfo @user`\n\nMention a user to get information."
            )
            await message.reply(view=view, mention_author=False)
            return

        target_user = message.mentions[0]

        # Get user data from database
        user_data = await db.get_user(target_user.id)

        fields = []

        # Basic info
        fields.append({
            'name': f"{EMOJIS['user']} Basic Information",
            'value': f"**ID:** `{target_user.id}`\n**Username:** {target_user.name}\n**Created:** <t:{int(target_user.created_at.timestamp())}:R>"
        })

        # Attributes
        attributes = user_data['attributes']
        if attributes:
            attr_list = []
            for key, value in attributes.items():
                if value is True:
                    attr_list.append(f"• `{key}`")
                else:
                    attr_list.append(f"• `{key}`: {value}")

            fields.append({
                'name': "Attributes",
                'value': "\n".join(attr_list) if attr_list else "*None*"
            })

        # Guild count
        guilds = [g for g in self.bot.guilds if target_user in g.members]
        fields.append({
            'name': f"{EMOJIS['web']} Shared Servers",
            'value': f"{len(guilds)} servers"
        })

        # Database timestamps
        if user_data.get('created_at'):
            fields.append({
                'name': f"{EMOJIS['time']} First Seen",
                'value': f"<t:{int(user_data['created_at'].timestamp())}:R>"
            })

        view = create_info_message(
            f"{EMOJIS['user']} User Information - {str(target_user)}",
            f"Information about {target_user.mention}",
            fields=fields,
            footer=f"Requested by {message.author}"
        )

        await message.reply(view=view, mention_author=False)

    async def handle_guildinfo_command(self, message: discord.Message, args: str):
        """
        Handle mod.guildinfo command - Get detailed guild information
        Usage: <@1373916203814490194> mod.guildinfo [guild_id]
        """
        if not args:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.guildinfo [guild_id]`\n\nProvide a guild ID."
            )
            await message.reply(view=view, mention_author=False)
            return

        try:
            guild_id = int(args.strip())
        except ValueError:
            view = create_error_message(
                f"{EMOJIS['snowflake']} Invalid Guild ID",
                "Please provide a valid guild ID (numbers only)."
            )
            await message.reply(view=view, mention_author=False)
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            view = create_error_message(
                "Guild Not Found",
                f"MODDY is not in a guild with ID `{guild_id}`."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Get guild data from database
        guild_data = await db.get_guild(guild_id)

        fields = []

        # Basic info
        fields.append({
            'name': f"{EMOJIS['info']} Basic Information",
            'value': f"**Name:** {guild.name}\n**ID:** `{guild.id}`\n**Owner:** {guild.owner.mention if guild.owner else 'Unknown'} (`{guild.owner_id}`)\n**Created:** <t:{int(guild.created_at.timestamp())}:R>"
        })

        # Members
        fields.append({
            'name': f"{EMOJIS['user']} Members",
            'value': f"**Total:** {guild.member_count:,}\n**Humans:** {len([m for m in guild.members if not m.bot]):,}\n**Bots:** {len([m for m in guild.members if m.bot]):,}"
        })

        # Channels
        fields.append({
            'name': "Channels",
            'value': f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories:** {len(guild.categories)}"
        })

        # Boost
        fields.append({
            'name': "Boost Status",
            'value': f"**Level:** {guild.premium_tier}\n**Boosts:** {guild.premium_subscription_count}"
        })

        # Attributes
        attributes = guild_data['attributes']
        if attributes:
            attr_list = []
            for key, value in attributes.items():
                if value is True:
                    attr_list.append(f"• `{key}`")
                else:
                    attr_list.append(f"• `{key}`: {value}")

            fields.append({
                'name': "Attributes",
                'value': "\n".join(attr_list)
            })

        # Features
        if guild.features:
            features = [f.replace('_', ' ').title() for f in guild.features[:8]]
            fields.append({
                'name': "Features",
                'value': ", ".join(features)
            })

        view = create_info_message(
            f"🏰 Guild Information - {guild.name}",
            f"Detailed information about **{guild.name}**",
            fields=fields,
            footer=f"Requested by {message.author}"
        )

        await message.reply(view=view, mention_author=False)


async def setup(bot):
    await bot.add_cog(ModeratorCommands(bot))
