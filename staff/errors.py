"""
Error management commands for developers.
Allows viewing and managing bot errors.
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse
from config import COLORS


class ErrorManagement(commands.Cog):
    """Error management commands for developers."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Checks if the user is a developer."""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="error", aliases=["err", "debug"])
    async def error_info(self, ctx, error_code: str = None):
        """Displays details of an error via its code."""
        # Get the ErrorTracker cog
        error_tracker = self.bot.get_cog("ErrorTracker")
        if not error_tracker:
            await ctx.send("<:undone:1398729502028333218> Error system not loaded.")
            return

        if not error_code:
            # Display the latest errors
            embed = discord.Embed(
                title="<:bug:1401614189482475551> Latest Errors",
                description="Here are the last 10 recorded errors.",
                color=COLORS["info"]
            )

            # First, search in memory cache
            errors_list = list(error_tracker.error_cache)[-10:]

            if not errors_list:
                embed.description = "No errors in memory cache."
            else:
                for error in reversed(errors_list):
                    timestamp = error['timestamp'].strftime("%H:%M:%S")
                    error_type = error['data'].get('type', 'Unknown')
                    embed.add_field(
                        name=f"`{error['code']}` - {timestamp}",
                        value=f"**Type:** `{error_type}`\n**File:** `{error['data'].get('file', 'N/A')}`",
                        inline=True
                    )

            # Note about the DB
            if self.bot.db:
                embed.set_footer(text="💡 Use the error code for more details from the DB.")
            else:
                embed.set_footer(text="⚠️ Database not connected.")

            await ctx.send(embed=embed)
            return

        # Search for the specific error
        error_code = error_code.upper()
        found_error = None

        # First in memory cache
        for error in error_tracker.error_cache:
            if error['code'] == error_code:
                found_error = error
                source = "cache"
                break

        # If not found and we have a DB, search in it
        if not found_error and self.bot.db:
            try:
                db_error = await self.bot.db.get_error(error_code)
                if db_error:
                    found_error = {
                        'code': db_error['error_code'],
                        'timestamp': db_error['timestamp'],
                        'data': {
                            'type': db_error['error_type'],
                            'message': db_error['message'],
                            'file': db_error['file_source'],
                            'line': str(db_error['line_number']),
                            'traceback': db_error['traceback'],
                            'command': db_error['command'],
                            'user': f"<@{db_error['user_id']}>" if db_error['user_id'] else 'N/A',
                            'guild': f"ID: {db_error['guild_id']}" if db_error['guild_id'] else 'N/A',
                            'context': db_error.get('context', {})
                        }
                    }
                    source = "database"
            except Exception as e:
                import logging
                logger = logging.getLogger('moddy')
                logger.error(f"DB search error: {e}")

        if not found_error:
            embed = ModdyResponse.error(
                "Error Not Found",
                f"No error with the code `{error_code}` was found.\n\n"
                f"**Searched in:** Memory cache{' and database' if self.bot.db else ''}"
            )
            await ctx.send(embed=embed)
            return

        # Display full details
        data = found_error['data']
        timestamp = found_error['timestamp']

        embed = discord.Embed(
            title=f"Error Details {error_code}",
            color=COLORS["warning"],
            timestamp=timestamp
        )

        # Source badge
        embed.set_author(name=f"Source: {source}")

        # Basic information
        embed.add_field(
            name="Error Type",
            value=f"`{data.get('type', 'N/A')}`",
            inline=True
        )

        embed.add_field(
            name="Source File",
            value=f"`{data.get('file', 'N/A')}:{data.get('line', '?')}`",
            inline=True
        )

        embed.add_field(
            name="Time",
            value=f"`{timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}`",
            inline=True
        )

        # Error message
        embed.add_field(
            name="Error Message",
            value=f"```{data.get('message', 'N/A')[:500]}```",
            inline=False
        )

        # Context if available
        if 'command' in data:
            context_value = (
                f"**Command:** `{data.get('command', 'N/A')}`\n"
                f"**User:** {data.get('user', 'N/A')}\n"
                f"**Server:** {data.get('guild', 'N/A')}\n"
                f"**Channel:** {data.get('channel', data.get('context', {}).get('channel', 'N/A'))}"
            )
            embed.add_field(
                name="Context",
                value=context_value,
                inline=False
            )

        if 'message' in data:
            embed.add_field(
                name="Original Message",
                value=f"```{data.get('message', 'N/A')[:300]}```",
                inline=False
            )

        # Traceback if available
        if 'traceback' in data and data['traceback']:
            tb = data['traceback']
            if len(tb) > 800:
                tb = tb[:800] + "\n... (truncated)"
            embed.add_field(
                name="Traceback",
                value=f"```py\n{tb}```",
                inline=False
            )

        await ctx.send(embed=embed)

        # Log the action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "error", {"code": error_code, "source": source})

    @commands.command(name="clearerrors", aliases=["cerr", "errorclear"])
    async def clear_errors(self, ctx, days: int = None):
        """Clears the error cache and/or cleans up old errors from the DB."""
        error_tracker = self.bot.get_cog("ErrorTracker")
        if not error_tracker:
            await ctx.send("<:undone:1398729502028333218> Error system not loaded.")
            return

        # Clear memory cache
        cache_count = len(error_tracker.error_cache)
        error_tracker.error_cache.clear()

        message = f"<:done:1398729525277229066> **Memory cache cleared:** `{cache_count}` errors removed."

        # If days are specified and we have a DB
        if days and self.bot.db:
            try:
                result = await self.bot.db.cleanup_old_errors(days)
                # Parse the result to get the count
                if result and hasattr(result, 'split'):
                    parts = result.split()
                    if len(parts) >= 2 and parts[0] == "DELETE":
                        db_count = parts[1]
                        message += f"\n<:done:1398729525277229066> **Database:** `{db_count}` errors older than {days} days deleted."
                else:
                    message += f"\n<:done:1398729525277229066> **Database:** Errors older than {days} days deleted."
            except Exception as e:
                message += f"\n<:undone:1398729502028333218> **DB Error:** {str(e)[:100]}"

        embed = discord.Embed(
            title="Error Cleanup",
            description=message,
            color=COLORS["success"]
        )
        await ctx.send(embed=embed)

        # Log the action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "clearerrors", {"cache": cache_count, "days": days})

    @commands.command(name="errortest", aliases=["testerror", "testerr"])
    async def test_error(self, ctx, error_type: str = "basic"):
        """Generates a test error to check the system."""
        embed = discord.Embed(
            title="<:bug:1401614189482475551> Error Test",
            description=f"Generating an error of type: `{error_type}`",
            color=COLORS["warning"]
        )
        await ctx.send(embed=embed)

        # Generate different types of errors based on the parameter
        if error_type == "basic":
            raise Exception("This is a basic test error.")
        elif error_type == "zerodiv":
            result = 1 / 0
        elif error_type == "keyerror":
            test_dict = {"a": 1}
            value = test_dict["b"]
        elif error_type == "attribute":
            None.undefined_method()
        elif error_type == "import":
            import a_module_that_does_not_exist
        elif error_type == "runtime":
            raise RuntimeError("Test runtime error (fatal).")
        else:
            raise ValueError(f"Unknown error type: {error_type}")

    @commands.command(name="errorstats", aliases=["errstats"])
    async def error_stats(self, ctx):
        """Displays statistics about errors."""
        error_tracker = self.bot.get_cog("ErrorTracker")
        if not error_tracker:
            await ctx.send("<:undone:1398729502028333218> Error system not loaded.")
            return

        errors = list(error_tracker.error_cache)

        embed = discord.Embed(
            title="<:info:1401614681440784477> Error Statistics",
            color=COLORS["info"],
            timestamp=datetime.utcnow()
        )

        # Memory cache stats
        if not errors:
            embed.add_field(
                name="Memory Cache",
                value="No errors in cache.",
                inline=False
            )
        else:
            # Calculate stats
            error_types = {}
            error_files = {}
            error_users = {}

            for error in errors:
                data = error['data']

                # By type
                error_type = data.get('type', 'Unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1

                # By file
                error_file = data.get('file', 'Unknown')
                error_files[error_file] = error_files.get(error_file, 0) + 1

                # By user (if available)
                if 'user' in data:
                    user_str = data['user'].split('(')[0].strip()
                    error_users[user_str] = error_users.get(user_str, 0) + 1

            # Sort and limit
            top_types = sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]
            top_files = sorted(error_files.items(), key=lambda x: x[1], reverse=True)[:5]
            top_users = sorted(error_users.items(), key=lambda x: x[1], reverse=True)[:5]

            # Memory cache
            cache_text = f"**Total:** `{len(errors)}` errors\n"

            if errors:
                oldest = errors[0]['timestamp']
                newest = errors[-1]['timestamp']
                cache_text += f"**Period:** {oldest.strftime('%H:%M')} - {newest.strftime('%H:%M')}"

            embed.add_field(
                name="Memory Cache",
                value=cache_text,
                inline=False
            )

            # Top error types
            types_text = "\n".join([f"`{t[0]}`: **{t[1]}**" for t in top_types])
            embed.add_field(
                name="Error Types",
                value=types_text or "None",
                inline=True
            )

            # Top files
            files_text = "\n".join([f"`{f[0]}`: **{f[1]}**" for f in top_files])
            embed.add_field(
                name="Affected Files",
                value=files_text or "None",
                inline=True
            )

            # Top users (if applicable)
            if top_users:
                users_text = "\n".join([f"{u[0]}: **{u[1]}**" for u in top_users])
                embed.add_field(
                    name="Users",
                    value=users_text,
                    inline=True
                )

        # DB stats if available
        if self.bot.db:
            try:
                stats = await self.bot.db.get_stats()
                embed.add_field(
                    name="Database",
                    value=f"**Total historical:** `{stats.get('errors', 0)}` errors",
                    inline=False
                )
            except:
                embed.add_field(
                    name="Database",
                    value="⚠️ Could not retrieve stats.",
                    inline=False
                )
        else:
            embed.add_field(
                name="Database",
                value="<:undone:1398729502028333218> Not connected",
                inline=False
            )

        await ctx.send(embed=embed)

        # Log the action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "errorstats")

    @commands.command(name="errordb", aliases=["errdb"])
    async def error_database(self, ctx, action: str = "info"):
        """Manages the error database."""
        if not self.bot.db:
            embed = ModdyResponse.error(
                "Database Not Connected",
                "The database is not available."
            )
            await ctx.send(embed=embed)
            return

        if action == "info":
            # Display info about the DB
            try:
                stats = await self.bot.db.get_stats()

                embed = discord.Embed(
                    title="<:data_object:1401600908323852318> Error Database",
                    color=COLORS["info"]
                )

                embed.add_field(
                    name="Statistics",
                    value=(
                        f"**Stored errors:** `{stats.get('errors', 0)}`\n"
                        f"**Tracked users:** `{stats.get('users', 0)}`\n"
                        f"**Tracked guilds:** `{stats.get('guilds', 0)}`"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="Configuration",
                    value=(
                        f"**Pool min:** `{self.bot.db.pool._minsize}`\n"
                        f"**Pool max:** `{self.bot.db.pool._maxsize}`\n"
                        f"**Current pool:** `{self.bot.db.pool._holders.__len__()}`"
                    ),
                    inline=False
                )

                await ctx.send(embed=embed)

            except Exception as e:
                embed = ModdyResponse.error(
                    "DB Error",
                    f"Could not retrieve stats: {str(e)[:200]}"
                )
                await ctx.send(embed=embed)

        elif action == "test":
            # Test connection
            try:
                async with self.bot.db.pool.acquire() as conn:
                    result = await conn.fetchval("SELECT 1")

                embed = ModdyResponse.success(
                    "Test Successful",
                    "The connection to the database is working correctly."
                )
                await ctx.send(embed=embed)

            except Exception as e:
                embed = ModdyResponse.error(
                    "Test Failed",
                    f"Connection error: {str(e)[:200]}"
                )
                await ctx.send(embed=embed)

        else:
            embed = discord.Embed(
                title="Available Actions",
                description=(
                    "`errordb info` - Displays statistics\n"
                    "`errordb test` - Tests the connection"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ErrorManagement(bot))