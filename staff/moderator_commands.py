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
from utils.staff_logger import staff_logger
from staff.base import StaffCommandsCog

logger = logging.getLogger('moddy.moderator_commands')


class ModeratorCommands(StaffCommandsCog):
    """Moderator commands (mod. prefix)"""

    def __init__(self, bot):
        super().__init__(bot)

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
        elif command_name == "interserver_info":
            await self.handle_interserver_info_command(message, args)
        elif command_name == "interserver_delete":
            await self.handle_interserver_delete_command(message, args)
        elif command_name == "interserver_blacklist":
            await self.handle_interserver_blacklist_command(message, args)
        elif command_name == "interserver_unblacklist":
            await self.handle_interserver_unblacklist_command(message, args)
        else:
            view = create_error_message("Unknown Command", f"Moderator command `{command_name}` not found.")
            await message.reply(view=view, mention_author=False)

    async def handle_blacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.blacklist command - Blacklist a user
        Usage: <@1373916203814490194> mod.blacklist @user [reason]
        """
        # Log the command
        if staff_logger:
            await staff_logger.log_command("mod", "blacklist", message.author, args=args)

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

        # Log the action
        if staff_logger:
            await staff_logger.log_action(
                "User Blacklisted",
                message.author,
                f"Blacklisted user {target_user} ({target_user.id})",
                target=f"{target_user.mention} (`{target_user.id}`)",
                additional_info={"Reason": reason}
            )

        # Create success view
        fields = [
            {'name': 'User', 'value': f"{target_user} (`{target_user.id}`)"},
            {'name': 'Moderator', 'value': message.author.mention},
            {'name': 'Reason', 'value': reason}
        ]

        view = create_success_message(
            "User Blacklisted",
            f"{target_user.mention} has been blacklisted.",
            fields=fields
        )

        await self.reply_with_tracking(message, view)

        logger.info(f"User {target_user} ({target_user.id}) blacklisted by {message.author} ({message.author.id})")

    async def handle_unblacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.unblacklist command - Remove user from blacklist
        Usage: <@1373916203814490194> mod.unblacklist @user [reason]
        """
        # Log the command
        if staff_logger:
            await staff_logger.log_command("mod", "unblacklist", message.author, args=args)

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

        # Log the action
        if staff_logger:
            await staff_logger.log_action(
                "User Unblacklisted",
                message.author,
                f"Removed {target_user} ({target_user.id}) from blacklist",
                target=f"{target_user.mention} (`{target_user.id}`)",
                additional_info={"Reason": reason}
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
            fields=fields
        )

        await self.reply_with_tracking(message, view)

        logger.info(f"User {target_user} ({target_user.id}) unblacklisted by {message.author} ({message.author.id})")

    async def handle_interserver_info_command(self, message: discord.Message, args: str):
        """
        Handle mod.interserver_info command - Get info about an inter-server message
        Usage: <@1373916203814490194> mod.interserver_info [moddy_id]
        """
        # Log the command
        if staff_logger:
            await staff_logger.log_command("mod", "interserver_info", message.author, args=args)

        moddy_id = args.strip().upper()
        if not moddy_id:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.interserver_info [moddy_id]`\n\nProvide a Moddy message ID."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Get message info
        msg_data = await db.get_interserver_message(moddy_id)
        if not msg_data:
            view = create_error_message(
                "Message Not Found",
                f"No inter-server message found with ID `{moddy_id}`."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Fetch author info
        author = self.bot.get_user(msg_data['author_id']) or await self.bot.fetch_user(msg_data['author_id'])

        # Format relayed messages info
        relayed_count = len(msg_data.get('relayed_messages', []))
        relayed_info = f"{relayed_count} servers"

        # Format timestamp
        timestamp = msg_data.get('timestamp', msg_data.get('created_at'))
        if timestamp:
            timestamp_str = f"<t:{int(timestamp.timestamp())}:F>"
        else:
            timestamp_str = "Unknown"

        # Create info view
        fields = [
            {'name': 'Moddy ID', 'value': f"`{msg_data['moddy_id']}`"},
            {'name': 'Author', 'value': f"{author.mention} (`{author.id}`)"},
            {'name': 'Original Server ID', 'value': f"`{msg_data['original_guild_id']}`"},
            {'name': 'Original Channel ID', 'value': f"`{msg_data['original_channel_id']}`"},
            {'name': 'Original Message ID', 'value': f"`{msg_data['original_message_id']}`"},
            {'name': 'Content', 'value': (msg_data['content'][:500] + '...' if len(msg_data['content']) > 500 else msg_data['content']) or "*No content*"},
            {'name': 'Timestamp', 'value': timestamp_str},
            {'name': 'Status', 'value': msg_data['status']},
            {'name': 'Moddy Team Message', 'value': "✅ Yes" if msg_data.get('is_moddy_team') else "❌ No"},
            {'name': 'Relayed To', 'value': relayed_info}
        ]

        view = create_info_message(
            "Inter-Server Message Info",
            f"Information about message `{moddy_id}`",
            fields=fields
        )

        await self.reply_with_tracking(message, view)

    async def handle_interserver_delete_command(self, message: discord.Message, args: str):
        """
        Handle mod.interserver_delete command - Delete an inter-server message
        Usage: <@1373916203814490194> mod.interserver_delete [moddy_id]
        """
        # Log the command
        if staff_logger:
            await staff_logger.log_command("mod", "interserver_delete", message.author, args=args)

        moddy_id = args.strip().upper()
        if not moddy_id:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.interserver_delete [moddy_id]`\n\nProvide a Moddy message ID."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Get message info
        msg_data = await db.get_interserver_message(moddy_id)
        if not msg_data:
            view = create_error_message(
                "Message Not Found",
                f"No inter-server message found with ID `{moddy_id}`."
            )
            await message.reply(view=view, mention_author=False)
            return

        if msg_data['status'] == 'deleted':
            view = create_warning_message(
                "Already Deleted",
                f"Message `{moddy_id}` is already deleted."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Delete all relayed messages
        deleted_count = 0
        relayed_messages = msg_data.get('relayed_messages', [])
        for relayed in relayed_messages:
            try:
                guild = self.bot.get_guild(relayed['guild_id'])
                if not guild:
                    continue

                channel = guild.get_channel(relayed['channel_id'])
                if not channel:
                    continue

                # Delete the message
                msg = await channel.fetch_message(relayed['message_id'])
                await msg.delete()
                deleted_count += 1
            except discord.NotFound:
                # Message already deleted
                pass
            except Exception as e:
                logger.error(f"Error deleting relayed message {relayed['message_id']}: {e}")

        # Delete original message if possible
        try:
            guild = self.bot.get_guild(msg_data['original_guild_id'])
            if guild:
                channel = guild.get_channel(msg_data['original_channel_id'])
                if channel:
                    original_msg = await channel.fetch_message(msg_data['original_message_id'])
                    await original_msg.delete()
        except:
            pass

        # Mark as deleted in DB
        await db.delete_interserver_message(moddy_id)

        # Log the action
        if staff_logger:
            await staff_logger.log_action(
                "Inter-Server Message Deleted",
                message.author,
                f"Deleted inter-server message {moddy_id}",
                additional_info={"Deleted Count": f"{deleted_count} messages"}
            )

        # Create success view
        fields = [
            {'name': 'Moddy ID', 'value': f"`{moddy_id}`"},
            {'name': 'Deleted By', 'value': message.author.mention},
            {'name': 'Messages Deleted', 'value': f"{deleted_count} relayed messages"}
        ]

        view = create_success_message(
            "Message Deleted",
            f"Inter-server message `{moddy_id}` has been deleted from all servers.",
            fields=fields
        )

        await self.reply_with_tracking(message, view)

        logger.info(f"Inter-server message {moddy_id} deleted by {message.author} ({message.author.id})")

    async def handle_interserver_blacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.interserver_blacklist command - Blacklist a user from inter-server
        Usage: <@1373916203814490194> mod.interserver_blacklist @user [reason]
        """
        # Log the command
        if staff_logger:
            await staff_logger.log_command("mod", "interserver_blacklist", message.author, args=args)

        parts = args.split(maxsplit=1)
        if not parts or not message.mentions:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.interserver_blacklist @user [reason]`\n\nMention a user to blacklist from inter-server."
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
                "You cannot blacklist staff members from inter-server."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Check if already blacklisted
        if user_data['attributes'].get('INTERSERVER_BLACKLISTED'):
            view = create_warning_message(
                "Already Blacklisted",
                f"{target_user.mention} is already blacklisted from inter-server."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Blacklist the user from inter-server
        await db.set_attribute(
            'user', target_user.id, 'INTERSERVER_BLACKLISTED', True,
            message.author.id, reason
        )

        # Log the action
        if staff_logger:
            await staff_logger.log_action(
                "User Inter-Server Blacklisted",
                message.author,
                f"Blacklisted {target_user} ({target_user.id}) from inter-server",
                target=f"{target_user.mention} (`{target_user.id}`)",
                additional_info={"Reason": reason}
            )

        # Create success view
        fields = [
            {'name': 'User', 'value': f"{target_user} (`{target_user.id}`)"},
            {'name': 'Moderator', 'value': message.author.mention},
            {'name': 'Reason', 'value': reason}
        ]

        view = create_success_message(
            "User Blacklisted from Inter-Server",
            f"{target_user.mention} has been blacklisted from using inter-server chat.",
            fields=fields
        )

        await self.reply_with_tracking(message, view)

        logger.info(f"User {target_user} ({target_user.id}) blacklisted from inter-server by {message.author} ({message.author.id})")

    async def handle_interserver_unblacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.interserver_unblacklist command - Remove user from inter-server blacklist
        Usage: <@1373916203814490194> mod.interserver_unblacklist @user [reason]
        """
        # Log the command
        if staff_logger:
            await staff_logger.log_command("mod", "interserver_unblacklist", message.author, args=args)

        parts = args.split(maxsplit=1)
        if not parts or not message.mentions:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> mod.interserver_unblacklist @user [reason]`\n\nMention a user to unblacklist from inter-server."
            )
            await message.reply(view=view, mention_author=False)
            return

        target_user = message.mentions[0]
        reason = parts[1] if len(parts) > 1 else "No reason provided"

        # Check if blacklisted
        user_data = await db.get_user(target_user.id)
        if not user_data['attributes'].get('INTERSERVER_BLACKLISTED'):
            view = create_warning_message(
                "Not Blacklisted",
                f"{target_user.mention} is not blacklisted from inter-server."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Remove from blacklist
        await db.set_attribute(
            'user', target_user.id, 'INTERSERVER_BLACKLISTED', None,
            message.author.id, reason
        )

        # Log the action
        if staff_logger:
            await staff_logger.log_action(
                "User Inter-Server Unblacklisted",
                message.author,
                f"Removed {target_user} ({target_user.id}) from inter-server blacklist",
                target=f"{target_user.mention} (`{target_user.id}`)",
                additional_info={"Reason": reason}
            )

        # Create success view
        fields = [
            {'name': 'User', 'value': f"{target_user} (`{target_user.id}`)"},
            {'name': 'Moderator', 'value': message.author.mention},
            {'name': 'Reason', 'value': reason}
        ]

        view = create_success_message(
            "User Unblacklisted from Inter-Server",
            f"{target_user.mention} has been removed from the inter-server blacklist.",
            fields=fields
        )

        await self.reply_with_tracking(message, view)

        logger.info(f"User {target_user} ({target_user.id}) unblacklisted from inter-server by {message.author} ({message.author.id})")


async def setup(bot):
    await bot.add_cog(ModeratorCommands(bot))
