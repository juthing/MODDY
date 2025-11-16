"""
Advanced Error Handling System for Moddy
Tracking, Discord logs, and notifications with database integration
"""

import discord
from discord.ext import commands
import traceback
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import asyncio
from collections import deque

from config import COLORS


class ErrorTracker(commands.Cog):
    """Error tracking and management system"""

    def __init__(self, bot):
        self.bot = bot
        self.error_cache = deque(maxlen=100)  # Keeps the last 100 errors in memory
        self.error_channel_id = 1392439223717724160
        self.dev_user_id = 1164597199594852395

    def generate_error_code(self, error: Exception, ctx: Optional[commands.Context] = None) -> str:
        """Generates a unique error code"""
        # Use the hash of the error + timestamp for uniqueness
        error_str = f"{type(error).__name__}:{str(error)}:{datetime.now().timestamp()}"
        hash_obj = hashlib.md5(error_str.encode())
        return hash_obj.hexdigest()[:8].upper()

    def store_error(self, error_code: str, error_data: Dict[str, Any]):
        """Stores the error in the memory cache"""
        self.error_cache.append({
            "code": error_code,
            "timestamp": datetime.now(timezone.utc),
            "data": error_data
        })

    async def store_error_db(self, error_code: str, error_data: Dict[str, Any], ctx: Optional[commands.Context] = None):
        """Stores the error in the database"""
        if not self.bot.db:
            return

        try:
            # Prepare data for the DB
            db_data = {
                "type": error_data.get("type"),
                "message": error_data.get("message"),
                "file": error_data.get("file"),
                "line": int(error_data.get("line")) if error_data.get("line", "").isdigit() else None,
                "traceback": error_data.get("traceback"),
                "user_id": None,
                "guild_id": None,
                "command": error_data.get("command"),
                "context": None
            }

            # Add context info if available
            if ctx:
                db_data["user_id"] = ctx.author.id
                db_data["guild_id"] = ctx.guild.id if ctx.guild else None
                db_data["context"] = json.dumps({
                    "channel": str(ctx.channel),
                    "message": ctx.message.content[:200] if hasattr(ctx, 'message') else None
                })

            # Store in the DB
            await self.bot.db.log_error(error_code, db_data)

        except Exception as e:
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Error while storing in DB: {e}")

    async def get_error_channel(self) -> Optional[discord.TextChannel]:
        """Gets the error channel"""
        return self.bot.get_channel(self.error_channel_id)

    def format_error_details(self, error: Exception, ctx: Optional[commands.Context] = None) -> Dict[str, Any]:
        """Formats the error details"""
        tb = traceback.format_exception(type(error), error, error.__traceback__)

        # Find the source file
        source_file = "Unknown"
        line_number = "?"
        for line in tb:
            if "File" in line and "site-packages" not in line:
                parts = line.strip().split('"')
                if len(parts) >= 2:
                    source_file = parts[1].split('/')[-1]
                    line_parts = line.split("line ")
                    if len(line_parts) >= 2:
                        line_number = line_parts[1].split(",")[0]
                    break

        details = {
            "type": type(error).__name__,
            "message": str(error),
            "file": source_file,
            "line": line_number,
            "traceback": ''.join(tb[-3:])  # Last 3 lines of the traceback
        }

        if ctx:
            details.update({
                "command": str(ctx.command) if ctx.command else "None",
                "user": f"{ctx.author} ({ctx.author.id})",
                "guild": f"{ctx.guild.name} ({ctx.guild.id})" if ctx.guild else "DM",
                "channel": f"#{ctx.channel.name}" if hasattr(ctx.channel, 'name') else "DM",
                "message": ctx.message.content[:100] + "..." if len(ctx.message.content) > 100 else ctx.message.content
            })

        return details

    async def send_error_log(self, error_code: str, error_details: Dict[str, Any], is_fatal: bool = False):
        """Sends the error log to the Discord channel"""
        channel = await self.get_error_channel()
        if not channel:
            return

        # Determine the color based on severity
        color = COLORS["error"] if is_fatal else COLORS["warning"]

        embed = discord.Embed(
            title=f"{'Fatal Error' if is_fatal else 'Error'} Detected",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )

        # Header with the error code
        embed.add_field(
            name="Error Code",
            value=f"`{error_code}`",
            inline=True
        )

        embed.add_field(
            name="Type",
            value=f"`{error_details['type']}`",
            inline=True
        )

        embed.add_field(
            name="File",
            value=f"`{error_details['file']}:{error_details['line']}`",
            inline=True
        )

        # Error message
        embed.add_field(
            name="Message",
            value=f"```{error_details['message'][:500]}```",
            inline=False
        )

        # Context if available
        if 'command' in error_details:
            embed.add_field(
                name="Context",
                value=(
                    f"**Command:** `{error_details['command']}`\n"
                    f"**User:** {error_details['user']}\n"
                    f"**Server:** {error_details['guild']}\n"
                    f"**Channel:** {error_details['channel']}"
                ),
                inline=False
            )

            if 'message' in error_details:
                embed.add_field(
                    name="Original Message",
                    value=f"```{error_details['message']}```",
                    inline=False
                )

        # Traceback for fatal errors
        if is_fatal and 'traceback' in error_details:
            embed.add_field(
                name="Traceback",
                value=f"```py\n{error_details['traceback'][:500]}```",
                inline=False
            )

        # Note about the DB
        if self.bot.db:
            embed.set_footer(text="✅ Error saved to the database")
        else:
            embed.set_footer(text="⚠️ Database not connected - Error cached only")

        # Ping for fatal errors
        content = f"<@{self.dev_user_id}> Fatal error detected!" if is_fatal else None

        await channel.send(content=content, embed=embed)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Handles command errors"""
        # Ignored errors (already handled)
        ignored = (
            commands.CommandNotFound,
            commands.NotOwner,
            commands.CheckFailure,
            commands.DisabledCommand,
            commands.NoPrivateMessage
        )

        if isinstance(error, ignored):
            return

        # Errors with specific handling (no log)
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="Insufficient Permissions",
                description=f"Missing permissions: `{', '.join(error.missing_permissions)}`",
                color=COLORS["error"]
            )
            await ctx.send(embed=embed)
            return

        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                title="Cooldown Active",
                description=f"Try again in `{error.retry_after:.1f}` seconds",
                color=COLORS["warning"]
            )
            await ctx.send(embed=embed)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Missing Argument",
                description=f"The argument `{error.param.name}` is required",
                color=COLORS["error"]
            )
            await ctx.send(embed=embed)
            return

        # For all other errors, we log
        error_code = self.generate_error_code(error, ctx)
        error_details = self.format_error_details(error.original if hasattr(error, 'original') else error, ctx)

        # Store the error in memory
        self.store_error(error_code, error_details)

        # Store in the DB if available
        await self.store_error_db(error_code, error_details, ctx)

        # Determine if it's fatal
        is_fatal = isinstance(error.original if hasattr(error, 'original') else error, (
            RuntimeError,
            AttributeError,
            ImportError,
            MemoryError,
            SystemError
        ))

        # Log to Discord
        await self.send_error_log(error_code, error_details, is_fatal)

        # Message to the user
        embed = discord.Embed(
            title="An error occurred",
            description=(
                f"**Error Code:** `{error_code}`\n\n"
                "This error has been logged and will be analyzed.\n"
                "You can provide this code to the developer if needed."
            ),
            color=COLORS["error"],
            timestamp=datetime.now(timezone.utc)
        )

        try:
            # For slash commands
            if hasattr(ctx, 'interaction') and ctx.interaction:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await ctx.interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                # For text commands
                await ctx.send(embed=embed)
        except:
            # If we can't send in the channel, try DMs
            try:
                await ctx.author.send(embed=embed)
            except:
                pass

    @commands.Cog.listener()
    async def on_error(self, event: str, *args, **kwargs):
        """Handles event errors (non-commands)"""
        error = asyncio.get_event_loop().get_exception_handler()

        error_code = self.generate_error_code(Exception(f"Event error: {event}"))

        error_details = {
            "type": "EventError",
            "message": f"Error in event: {event}",
            "file": "Discord Event",
            "line": "N/A",
            "event": event,
            "traceback": traceback.format_exc()
        }

        self.store_error(error_code, error_details)

        # Store in the DB if available
        if self.bot.db:
            await self.store_error_db(error_code, error_details)

        await self.send_error_log(error_code, error_details, is_fatal=True)


async def setup(bot):
    await bot.add_cog(ErrorTracker(bot))