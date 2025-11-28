"""
Advanced Error Handling System for Moddy
Tracking, Discord logs, and notifications with database integration
"""

import discord
from discord import ui
from discord.ext import commands
import traceback
import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import asyncio
import sys
from collections import deque

from config import COLORS


class ErrorView(ui.LayoutView):
    """Error display view using Components V2"""

    def __init__(self, error_code: str):
        super().__init__(timeout=None)
        self.error_code = error_code
        self.build_view()

    def build_view(self):
        """Builds the error view with Components V2"""
        # Create main container
        container = ui.Container()

        # Add error title with emoji
        container.add_item(
            ui.TextDisplay(f"### <:error:1444049460924776478> Une erreur est survenue")
        )

        # Add error message with code
        container.add_item(
            ui.TextDisplay(
                f"**Code d'erreur :** `{self.error_code}`\n\n"
                "Cette erreur a été automatiquement enregistrée et sera analysée par notre équipe.\n"
                "Si le problème persiste, contactez le support avec ce code d'erreur."
            )
        )

        # Add button row with support link
        button_row = ui.ActionRow()
        support_btn = ui.Button(
            label="Serveur Support",
            style=discord.ButtonStyle.link,
            url="https://moddy.app/support",
            emoji="🆘"
        )
        button_row.add_item(support_btn)
        container.add_item(button_row)

        # Add container to view
        self.add_item(container)


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

        # Create error view with Components V2
        error_view = ErrorView(error_code)

        # Create a simple embed with red border
        embed = discord.Embed(color=COLORS["error"])

        try:
            # For slash commands
            if hasattr(ctx, 'interaction') and ctx.interaction:
                if ctx.interaction.response.is_done():
                    await ctx.interaction.followup.send(embed=embed, view=error_view, ephemeral=True)
                else:
                    await ctx.interaction.response.send_message(embed=embed, view=error_view, ephemeral=True)
            else:
                # For text commands
                await ctx.send(embed=embed, view=error_view)
        except Exception as send_error:
            # If we can't send in the channel, try DMs
            try:
                await ctx.author.send(embed=embed, view=error_view)
            except:
                # Last resort: log the failure
                import logging
                logger = logging.getLogger('moddy')
                logger.error(f"Failed to send error message to user: {send_error}")

    @commands.Cog.listener()
    async def on_error(self, event: str, *args, **kwargs):
        """Handles event errors (non-commands)"""
        # Get the actual exception from sys.exc_info()
        exc_type, exc_value, exc_traceback = sys.exc_info()

        if exc_value is None:
            return

        error_code = self.generate_error_code(exc_value)
        error_details = self.format_error_details(exc_value)

        error_details.update({
            "event": event,
            "context": f"Discord event: {event}"
        })

        self.store_error(error_code, error_details)

        # Store in the DB if available
        if self.bot.db:
            await self.store_error_db(error_code, error_details)

        await self.send_error_log(error_code, error_details, is_fatal=True)

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handles slash command (app command) errors"""
        # Check if the error was already handled
        if hasattr(error, '__error_handled__'):
            return

        # Mark error as handled to prevent duplicate processing
        error.__error_handled__ = True

        # Ignored errors
        if isinstance(error, discord.app_commands.CommandNotFound):
            return

        # Errors with specific handling
        if isinstance(error, discord.app_commands.MissingPermissions):
            # Create inline view for permissions error
            class PermissionErrorView(ui.LayoutView):
                def __init__(self):
                    super().__init__(timeout=None)
                    container = ui.Container()
                    container.add_item(
                        ui.TextDisplay(f"### <:error:1444049460924776478> Permissions insuffisantes")
                    )
                    container.add_item(
                        ui.TextDisplay("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
                    )
                    button_row = ui.ActionRow()
                    support_btn = ui.Button(
                        label="Serveur Support",
                        style=discord.ButtonStyle.link,
                        url="https://moddy.app/support",
                        emoji="🆘"
                    )
                    button_row.add_item(support_btn)
                    container.add_item(button_row)
                    self.add_item(container)

            embed = discord.Embed(color=COLORS["error"])
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, view=PermissionErrorView(), ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=PermissionErrorView(), ephemeral=True)
            except:
                pass
            return

        if isinstance(error, discord.app_commands.CommandOnCooldown):
            # Create inline view for cooldown error
            class CooldownErrorView(ui.LayoutView):
                def __init__(self, retry_after: float):
                    super().__init__(timeout=None)
                    container = ui.Container()
                    container.add_item(
                        ui.TextDisplay(f"### ⏱️ Cooldown actif")
                    )
                    container.add_item(
                        ui.TextDisplay(f"Réessayez dans `{retry_after:.1f}` secondes.")
                    )
                    self.add_item(container)

            embed = discord.Embed(color=COLORS["warning"])
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, view=CooldownErrorView(error.retry_after), ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, view=CooldownErrorView(error.retry_after), ephemeral=True)
            except:
                pass
            return

        # For all other errors, log them
        actual_error = error.original if hasattr(error, 'original') else error
        error_code = self.generate_error_code(actual_error)
        error_details = self.format_error_details(actual_error)

        # Add interaction context
        error_details.update({
            "command": interaction.command.name if interaction.command else "Unknown",
            "user": f"{interaction.user} ({interaction.user.id})",
            "guild": f"{interaction.guild.name} ({interaction.guild.id})" if interaction.guild else "DM",
            "channel": f"#{interaction.channel.name}" if hasattr(interaction.channel, 'name') else "DM"
        })

        # Store error
        self.store_error(error_code, error_details)
        await self.store_error_db(error_code, error_details)

        # Determine if it's fatal
        is_fatal = isinstance(actual_error, (
            RuntimeError,
            AttributeError,
            ImportError,
            MemoryError,
            SystemError
        ))

        # Log to Discord
        await self.send_error_log(error_code, error_details, is_fatal)

        # Send error to user
        error_view = ErrorView(error_code)
        embed = discord.Embed(color=COLORS["error"])

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=error_view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=error_view, ephemeral=True)
        except Exception as send_error:
            # Last resort: log the failure
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Failed to send app command error to user: {send_error}")


async def setup(bot):
    await bot.add_cog(ErrorTracker(bot))