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
            embed = discord.Embed(
                title="❌ Permission Denied",
                description=reason,
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=10)
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
            embed = discord.Embed(
                title="❌ Unknown Command",
                description=f"Moderator command `{command_name}` not found.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=15)

    async def handle_blacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.blacklist command - Blacklist a user
        Usage: <@&1386452009678278818> mod.blacklist @user [reason]
        """
        parts = args.split(maxsplit=1)
        if not parts or not message.mentions:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@&1386452009678278818> mod.blacklist @user [reason]`\n\nMention a user to blacklist.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=15)
            return

        target_user = message.mentions[0]
        reason = parts[1] if len(parts) > 1 else "No reason provided"

        # Can't blacklist staff
        user_data = await db.get_user(target_user.id)
        if user_data['attributes'].get('TEAM') or self.bot.is_developer(target_user.id):
            embed = discord.Embed(
                title="❌ Cannot Blacklist Staff",
                description="You cannot blacklist staff members.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

        # Check if already blacklisted
        if user_data['attributes'].get('BLACKLISTED'):
            embed = discord.Embed(
                title="⚠️ Already Blacklisted",
                description=f"{target_user.mention} is already blacklisted.",
                color=COLORS["warning"]
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

        # Blacklist the user
        await db.set_attribute(
            'user', target_user.id, 'BLACKLISTED', True,
            message.author.id, reason
        )

        # Create success embed
        embed = discord.Embed(
            title="🔨 User Blacklisted",
            description=f"{target_user.mention} has been blacklisted.",
            color=COLORS["error"],
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(name="User", value=f"{target_user} (`{target_user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=message.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        embed.set_footer(text=f"Executed by {message.author}")

        await message.channel.send(embed=embed)

        logger.info(f"User {target_user} ({target_user.id}) blacklisted by {message.author} ({message.author.id})")

    async def handle_unblacklist_command(self, message: discord.Message, args: str):
        """
        Handle mod.unblacklist command - Remove user from blacklist
        Usage: <@&1386452009678278818> mod.unblacklist @user [reason]
        """
        parts = args.split(maxsplit=1)
        if not parts or not message.mentions:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@&1386452009678278818> mod.unblacklist @user [reason]`\n\nMention a user to unblacklist.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=15)
            return

        target_user = message.mentions[0]
        reason = parts[1] if len(parts) > 1 else "No reason provided"

        # Check if blacklisted
        user_data = await db.get_user(target_user.id)
        if not user_data['attributes'].get('BLACKLISTED'):
            embed = discord.Embed(
                title="⚠️ Not Blacklisted",
                description=f"{target_user.mention} is not blacklisted.",
                color=COLORS["warning"]
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

        # Remove from blacklist
        await db.set_attribute(
            'user', target_user.id, 'BLACKLISTED', None,
            message.author.id, reason
        )

        # Create success embed
        embed = discord.Embed(
            title="✅ User Unblacklisted",
            description=f"{target_user.mention} has been removed from the blacklist.",
            color=COLORS["success"],
            timestamp=datetime.now(timezone.utc)
        )

        embed.add_field(name="User", value=f"{target_user} (`{target_user.id}`)", inline=True)
        embed.add_field(name="Moderator", value=message.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)

        embed.set_footer(text=f"Executed by {message.author}")

        await message.channel.send(embed=embed)

        logger.info(f"User {target_user} ({target_user.id}) unblacklisted by {message.author} ({message.author.id})")

    async def handle_userinfo_command(self, message: discord.Message, args: str):
        """
        Handle mod.userinfo command - Get detailed user information
        Usage: <@&1386452009678278818> mod.userinfo @user
        """
        if not message.mentions:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@&1386452009678278818> mod.userinfo @user`\n\nMention a user to get information.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=15)
            return

        target_user = message.mentions[0]

        # Get user data from database
        user_data = await db.get_user(target_user.id)

        # Create info embed
        embed = discord.Embed(
            title="👤 User Information",
            color=COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_author(name=str(target_user), icon_url=target_user.display_avatar.url)

        # Basic info
        embed.add_field(
            name="Basic Information",
            value=f"**ID:** `{target_user.id}`\n**Username:** {target_user.name}\n**Created:** <t:{int(target_user.created_at.timestamp())}:R>",
            inline=False
        )

        # Attributes
        attributes = user_data['attributes']
        if attributes:
            attr_list = []
            for key, value in attributes.items():
                if value is True:
                    attr_list.append(f"• `{key}`")
                else:
                    attr_list.append(f"• `{key}`: {value}")

            embed.add_field(
                name="Attributes",
                value="\n".join(attr_list) if attr_list else "*None*",
                inline=False
            )

        # Guild count
        guilds = [g for g in self.bot.guilds if target_user in g.members]
        embed.add_field(
            name="Shared Servers",
            value=f"{len(guilds)} servers",
            inline=True
        )

        # Database timestamps
        if user_data.get('created_at'):
            embed.add_field(
                name="First Seen",
                value=f"<t:{int(user_data['created_at'].timestamp())}:R>",
                inline=True
            )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.channel.send(embed=embed)

    async def handle_guildinfo_command(self, message: discord.Message, args: str):
        """
        Handle mod.guildinfo command - Get detailed guild information
        Usage: <@&1386452009678278818> mod.guildinfo [guild_id]
        """
        if not args:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@&1386452009678278818> mod.guildinfo [guild_id]`\n\nProvide a guild ID.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=15)
            return

        try:
            guild_id = int(args.strip())
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Guild ID",
                description="Please provide a valid guild ID (numbers only).",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            embed = discord.Embed(
                title="❌ Guild Not Found",
                description=f"MODDY is not in a guild with ID `{guild_id}`.",
                color=COLORS["error"]
            )
            await message.channel.send(embed=embed, delete_after=10)
            return

        # Get guild data from database
        guild_data = await db.get_guild(guild_id)

        # Create info embed
        embed = discord.Embed(
            title="🏰 Guild Information",
            color=COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Basic info
        embed.add_field(
            name="Basic Information",
            value=f"**Name:** {guild.name}\n**ID:** `{guild.id}`\n**Owner:** {guild.owner.mention if guild.owner else 'Unknown'} (`{guild.owner_id}`)\n**Created:** <t:{int(guild.created_at.timestamp())}:R>",
            inline=False
        )

        # Members
        embed.add_field(
            name="Members",
            value=f"**Total:** {guild.member_count:,}\n**Humans:** {len([m for m in guild.members if not m.bot]):,}\n**Bots:** {len([m for m in guild.members if m.bot]):,}",
            inline=True
        )

        # Channels
        embed.add_field(
            name="Channels",
            value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories:** {len(guild.categories)}",
            inline=True
        )

        # Boost
        embed.add_field(
            name="Boost Status",
            value=f"**Level:** {guild.premium_tier}\n**Boosts:** {guild.premium_subscription_count}",
            inline=True
        )

        # Attributes
        attributes = guild_data['attributes']
        if attributes:
            attr_list = []
            for key, value in attributes.items():
                if value is True:
                    attr_list.append(f"• `{key}`")
                else:
                    attr_list.append(f"• `{key}`: {value}")

            embed.add_field(
                name="Attributes",
                value="\n".join(attr_list),
                inline=False
            )

        # Features
        if guild.features:
            features = [f.replace('_', ' ').title() for f in guild.features[:8]]
            embed.add_field(
                name="Features",
                value=", ".join(features),
                inline=False
            )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ModeratorCommands(bot))
