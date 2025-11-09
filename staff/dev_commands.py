"""
Developer Commands (d. prefix)
Commands exclusively for developers from Discord Dev Portal
"""

import discord
from discord.ext import commands
from typing import Optional
import logging
from datetime import datetime, timezone
import sys
import os

from utils.staff_permissions import staff_permissions, CommandType
from database import db
from config import COLORS
from utils.components_v2 import create_error_message, create_success_message, create_info_message, create_warning_message

logger = logging.getLogger('moddy.dev_commands')


class DeveloperCommands(commands.Cog):
    """Developer commands (d. prefix)"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for developer commands with new syntax"""
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

        # Only handle dev commands in this cog
        if command_type != CommandType.DEV:
            return

        # Log the command attempt
        logger.info(f"🔧 Dev command '{command_name}' attempted by {message.author} ({message.author.id})")

        # Check if user is in dev team
        is_dev = self.bot.is_developer(message.author.id)
        logger.info(f"   Developer status: {is_dev}")

        # Check permissions
        allowed, reason = await staff_permissions.check_command_permission(
            message.author.id, command_type, command_name
        )

        if not allowed:
            logger.warning(f"   ❌ Permission denied: {reason}")
            embed = discord.Embed(
                title="❌ Permission Denied",
                description=reason,
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        logger.info(f"   ✅ Permission granted")

        # Route to appropriate command
        if command_name == "reload":
            await self.handle_reload_command(message, args)
        elif command_name == "shutdown":
            await self.handle_shutdown_command(message, args)
        elif command_name == "stats":
            await self.handle_stats_command(message, args)
        elif command_name == "sql":
            await self.handle_sql_command(message, args)
        elif command_name == "jsk":
            await self.handle_jsk_command(message, args)
        else:
            embed = discord.Embed(
                title="❌ Unknown Command",
                description=f"Developer command `{command_name}` not found.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)

    async def handle_reload_command(self, message: discord.Message, args: str):
        """
        Handle d.reload command - Reload bot extensions
        Usage: <@1373916203814490194> d.reload [extension]
        """
        if not args or args == "all":
            # Reload all extensions
            embed = discord.Embed(
                title="🔄 Reloading All Extensions",
                description="Reloading all cogs and staff commands...",
                color=COLORS["info"]
            )
            msg = await message.reply(embed=embed, mention_author=False)

            success = []
            failed = []

            # Reload all loaded extensions
            extensions = list(self.bot.extensions.keys())
            for ext in extensions:
                try:
                    await self.bot.reload_extension(ext)
                    success.append(ext)
                except Exception as e:
                    failed.append(f"{ext}: {str(e)}")

            # Create result embed
            result_embed = discord.Embed(
                title="✅ Reload Complete" if not failed else "⚠️ Reload Complete with Errors",
                color=COLORS["success"] if not failed else COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )

            if success:
                result_embed.add_field(
                    name=f"✅ Reloaded ({len(success)})",
                    value="\n".join([f"• `{ext}`" for ext in success[:10]]) + (f"\n*...and {len(success) - 10} more*" if len(success) > 10 else ""),
                    inline=False
                )

            if failed:
                result_embed.add_field(
                    name=f"❌ Failed ({len(failed)})",
                    value="\n".join([f"• {f}" for f in failed[:5]]) + (f"\n*...and {len(failed) - 5} more*" if len(failed) > 5 else ""),
                    inline=False
                )

            result_embed.set_footer(text=f"Executed by {message.author}")

            await msg.edit(embed=result_embed)

        else:
            # Reload specific extension
            ext_name = args.strip()

            # Try to find the extension
            if not ext_name.startswith(("cogs.", "staff.")):
                # Try to guess the right path
                if ext_name in [e.split('.')[-1] for e in self.bot.extensions]:
                    # Find full name
                    for full_name in self.bot.extensions:
                        if full_name.endswith(ext_name):
                            ext_name = full_name
                            break

            try:
                await self.bot.reload_extension(ext_name)

                embed = discord.Embed(
                    title="✅ Extension Reloaded",
                    description=f"Successfully reloaded `{ext_name}`",
                    color=COLORS["success"],
                    timestamp=datetime.now(timezone.utc)
                )
                embed.set_footer(text=f"Executed by {message.author}")

                await message.reply(embed=embed, mention_author=False)

            except Exception as e:
                embed = discord.Embed(
                    title="❌ Reload Failed",
                    description=f"Failed to reload `{ext_name}`",
                    color=COLORS["error"]
                )
                embed.add_field(
                    name="Error",
                    value=f"```{str(e)[:500]}```",
                    inline=False
                )

                await message.reply(embed=embed, mention_author=False)

    async def handle_shutdown_command(self, message: discord.Message, args: str):
        """
        Handle d.shutdown command - Shutdown the bot
        Usage: <@1373916203814490194> d.shutdown
        """
        embed = discord.Embed(
            title="🔴 Shutting Down",
            description="MODDY is shutting down...",
            color=COLORS["error"],
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Executed by {message.author}")

        await message.reply(embed=embed, mention_author=False)

        logger.info(f"Bot shutdown requested by {message.author} ({message.author.id})")
        await self.bot.close()

    async def handle_stats_command(self, message: discord.Message, args: str):
        """
        Handle d.stats command - Show bot statistics
        Usage: <@1373916203814490194> d.stats
        """
        embed = discord.Embed(
            title="📊 MODDY Statistics",
            color=COLORS["developer"],
            timestamp=datetime.now(timezone.utc)
        )

        # Bot info
        uptime = datetime.now(timezone.utc) - self.bot.launch_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed.add_field(
            name="Bot Information",
            value=f"**Uptime:** {days}d {hours}h {minutes}m {seconds}s\n**Latency:** {round(self.bot.latency * 1000)}ms",
            inline=False
        )

        # Server stats
        embed.add_field(
            name="Discord Statistics",
            value=f"**Guilds:** {len(self.bot.guilds):,}\n**Users:** {len(self.bot.users):,}\n**Commands:** {len(self.bot.tree.get_commands())}",
            inline=True
        )

        # Database stats
        if db:
            try:
                stats = await db.get_stats()
                embed.add_field(
                    name="Database Statistics",
                    value=f"**Users:** {stats.get('users', 0):,}\n**Guilds:** {stats.get('guilds', 0):,}\n**Errors:** {stats.get('errors', 0):,}",
                    inline=True
                )
            except:
                pass

        # System info
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()

        embed.add_field(
            name="System Resources",
            value=f"**RAM:** {memory_info.rss / 1024 / 1024:.2f} MB\n**CPU:** {process.cpu_percent()}%\n**Threads:** {process.num_threads()}",
            inline=True
        )

        # Extensions
        embed.add_field(
            name="Extensions",
            value=f"**Loaded:** {len(self.bot.extensions)}\n**Cogs:** {len(self.bot.cogs)}",
            inline=True
        )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.reply(embed=embed, mention_author=False)

    async def handle_sql_command(self, message: discord.Message, args: str):
        """
        Handle d.sql command - Execute SQL query
        Usage: <@1373916203814490194> d.sql [query]
        """
        if not args:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@1373916203814490194> d.sql [query]`\n\nProvide a SQL query to execute.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        if not db:
            embed = discord.Embed(
                title="❌ Database Not Available",
                description="Database is not connected.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        query = args.strip()

        # Warning for dangerous queries
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER"]
        if any(keyword in query.upper() for keyword in dangerous_keywords):
            embed = discord.Embed(
                title="⚠️ Dangerous Query",
                description=f"This query contains potentially dangerous operations:\n```sql\n{query[:500]}\n```\n\nReact with ✅ to confirm execution.",
                color=COLORS["warning"]
            )
            msg = await message.reply(embed=embed, mention_author=False)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return user == message.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)

                if str(reaction.emoji) == "❌":
                    embed = discord.Embed(
                        title="❌ Cancelled",
                        description="Query execution cancelled.",
                        color=COLORS["error"]
                    )
                    await msg.edit(embed=embed)
                    return
            except:
                embed = discord.Embed(
                    title="⏱️ Timeout",
                    description="Query confirmation timed out.",
                    color=COLORS["error"]
                )
                await msg.edit(embed=embed)
                return

        try:
            async with db.pool.acquire() as conn:
                # Check if it's a SELECT query
                if query.upper().strip().startswith("SELECT"):
                    rows = await conn.fetch(query)

                    if not rows:
                        embed = discord.Embed(
                            title="✅ Query Executed",
                            description="No results returned.",
                            color=COLORS["success"]
                        )
                        await message.reply(embed=embed, mention_author=False)
                        return

                    # Format results
                    result_text = "```\n"
                    for row in rows[:10]:  # Limit to 10 rows
                        result_text += " | ".join([str(v) for v in row.values()]) + "\n"
                    result_text += "```"

                    if len(rows) > 10:
                        result_text += f"\n*...and {len(rows) - 10} more rows*"

                    embed = discord.Embed(
                        title="✅ Query Executed",
                        description=f"**Rows:** {len(rows)}\n\n{result_text}",
                        color=COLORS["success"],
                        timestamp=datetime.now(timezone.utc)
                    )
                else:
                    # Execute non-SELECT query
                    result = await conn.execute(query)

                    embed = discord.Embed(
                        title="✅ Query Executed",
                        description=f"```sql\n{query[:500]}\n```\n\n**Result:** {result}",
                        color=COLORS["success"],
                        timestamp=datetime.now(timezone.utc)
                    )

                embed.set_footer(text=f"Executed by {message.author}")
                await message.reply(embed=embed, mention_author=False)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Query Failed",
                description=f"```sql\n{query[:500]}\n```",
                color=COLORS["error"]
            )
            embed.add_field(
                name="Error",
                value=f"```{str(e)[:500]}```",
                inline=False
            )

            await message.reply(embed=embed, mention_author=False)

    async def handle_jsk_command(self, message: discord.Message, args: str):
        """
        Handle d.jsk command - Execute Python code
        Usage: <@1373916203814490194> d.jsk [code]
        """
        if not args:
            embed = discord.Embed(
                title="❌ Invalid Usage",
                description="**Usage:** `<@1373916203814490194> d.jsk [code]`\n\nProvide Python code to execute.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        code = args.strip()

        # Remove code blocks if present
        if code.startswith("```") and code.endswith("```"):
            code = code[3:-3]
            if code.startswith("python") or code.startswith("py"):
                code = code.split('\n', 1)[1] if '\n' in code else ""

        # Create execution environment
        env = {
            'bot': self.bot,
            'message': message,
            'channel': message.channel,
            'author': message.author,
            'guild': message.guild,
            'db': db,
            'discord': discord,
            'commands': commands,
            'asyncio': __import__('asyncio'),
            'datetime': datetime,
            'timezone': timezone,
        }

        # Add imports
        import io
        import contextlib
        import textwrap
        import traceback

        # Prepare code
        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

        try:
            # Compile the code
            exec(to_compile, env)

            # Execute and capture output
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                func = env['func']
                result = await func()

            # Get output
            output = stdout.getvalue()

            # Format result
            if result is not None:
                output += f"\n{repr(result)}"

            if not output:
                output = "✅ Code executed successfully (no output)"

            # Limit output length
            if len(output) > 1900:
                output = output[:1900] + "\n... (output truncated)"

            embed = discord.Embed(
                title="✅ Code Executed",
                description=f"```python\n{code[:500]}\n```",
                color=COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Output",
                value=f"```python\n{output}\n```",
                inline=False
            )

            embed.set_footer(text=f"Executed by {message.author}")

            await message.reply(embed=embed, mention_author=False)

        except Exception as e:
            # Format error
            error_traceback = traceback.format_exc()

            if len(error_traceback) > 1900:
                error_traceback = error_traceback[-1900:]

            embed = discord.Embed(
                title="❌ Execution Failed",
                description=f"```python\n{code[:500]}\n```",
                color=COLORS["error"]
            )

            embed.add_field(
                name="Error",
                value=f"```python\n{error_traceback}\n```",
                inline=False
            )

            await message.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(DeveloperCommands(bot))
