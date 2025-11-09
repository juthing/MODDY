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
from utils.components_v2 import create_error_message, create_success_message, create_info_message, create_warning_message, EMOJIS

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
            view = create_error_message("Permission Denied", reason)
            await message.reply(view=view, mention_author=False)
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
            view = create_error_message("Unknown Command", f"Developer command `{command_name}` not found.")
            await message.reply(view=view, mention_author=False)

    async def handle_reload_command(self, message: discord.Message, args: str):
        """
        Handle d.reload command - Reload bot extensions
        Usage: <@1373916203814490194> d.reload [extension]
        """
        if not args or args == "all":
            # Reload all extensions
            view = create_info_message(f"{EMOJIS['sync']} Reloading All Extensions", "Reloading all cogs and staff commands...")
            msg = await message.reply(view=view, mention_author=False)

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

            # Create result view
            title = f"{EMOJIS['done']} Reload Complete" if not failed else "⚠️ Reload Complete with Errors"
            description = "Extensions reloaded successfully." if not failed else "Some extensions failed to reload."

            fields = []
            if success:
                fields.append({
                    'name': f"{EMOJIS['done']} Reloaded ({len(success)})",
                    'value': "\n".join([f"• `{ext}`" for ext in success[:10]]) + (f"\n*...and {len(success) - 10} more*" if len(success) > 10 else "")
                })

            if failed:
                fields.append({
                    'name': f"{EMOJIS['undone']} Failed ({len(failed)})",
                    'value': "\n".join([f"• {f}" for f in failed[:5]]) + (f"\n*...and {len(failed) - 5} more*" if len(failed) > 5 else "")
                })

            footer = f"Executed by {message.author}"

            if failed:
                result_view = create_warning_message(title, description, fields)
            else:
                result_view = create_success_message(title, description, fields, footer)

            await msg.edit(view=result_view)

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

                view = create_success_message(
                    "Extension Reloaded",
                    f"Successfully reloaded `{ext_name}`",
                    footer=f"Executed by {message.author}"
                )

                await message.reply(view=view, mention_author=False)

            except Exception as e:
                view = create_error_message(
                    "Reload Failed",
                    f"Failed to reload `{ext_name}`",
                    fields=[{'name': 'Error', 'value': f"```{str(e)[:500]}```"}]
                )

                await message.reply(view=view, mention_author=False)

    async def handle_shutdown_command(self, message: discord.Message, args: str):
        """
        Handle d.shutdown command - Shutdown the bot
        Usage: <@1373916203814490194> d.shutdown
        """
        view = create_error_message(
            f"{EMOJIS['logout']} Shutting Down" if 'logout' in EMOJIS else "🔴 Shutting Down",
            "MODDY is shutting down..."
        )

        await message.reply(view=view, mention_author=False)

        logger.info(f"Bot shutdown requested by {message.author} ({message.author.id})")
        await self.bot.close()

    async def handle_stats_command(self, message: discord.Message, args: str):
        """
        Handle d.stats command - Show bot statistics
        Usage: <@1373916203814490194> d.stats
        """
        # Bot info
        uptime = datetime.now(timezone.utc) - self.bot.launch_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        fields = []

        fields.append({
            'name': f"{EMOJIS['moddy']} Bot Information",
            'value': f"**Uptime:** {days}d {hours}h {minutes}m {seconds}s\n**Latency:** {round(self.bot.latency * 1000)}ms"
        })

        # Server stats
        fields.append({
            'name': f"{EMOJIS['web']} Discord Statistics",
            'value': f"**Guilds:** {len(self.bot.guilds):,}\n**Users:** {len(self.bot.users):,}\n**Commands:** {len(self.bot.tree.get_commands())}"
        })

        # Database stats
        if db:
            try:
                stats = await db.get_stats()
                fields.append({
                    'name': "Database Statistics",
                    'value': f"**Users:** {stats.get('users', 0):,}\n**Guilds:** {stats.get('guilds', 0):,}\n**Errors:** {stats.get('errors', 0):,}"
                })
            except:
                pass

        # System info
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()

        fields.append({
            'name': "System Resources",
            'value': f"**RAM:** {memory_info.rss / 1024 / 1024:.2f} MB\n**CPU:** {process.cpu_percent()}%\n**Threads:** {process.num_threads()}"
        })

        # Extensions
        fields.append({
            'name': "Extensions",
            'value': f"**Loaded:** {len(self.bot.extensions)}\n**Cogs:** {len(self.bot.cogs)}"
        })

        view = create_info_message(
            f"{EMOJIS['info']} MODDY Statistics",
            "Statistiques actuelles du bot",
            fields=fields,
            footer=f"Requested by {message.author}"
        )

        await message.reply(view=view, mention_author=False)

    async def handle_sql_command(self, message: discord.Message, args: str):
        """
        Handle d.sql command - Execute SQL query
        Usage: <@1373916203814490194> d.sql [query]
        """
        if not args:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> d.sql [query]`\n\nProvide a SQL query to execute."
            )
            await message.reply(view=view, mention_author=False)
            return

        if not db:
            view = create_error_message(
                "Database Not Available",
                "Database is not connected."
            )
            await message.reply(view=view, mention_author=False)
            return

        query = args.strip()

        # Warning for dangerous queries
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER"]
        if any(keyword in query.upper() for keyword in dangerous_keywords):
            view = create_warning_message(
                "Dangerous Query",
                f"This query contains potentially dangerous operations:\n```sql\n{query[:500]}\n```\n\nReact with ✅ to confirm execution."
            )
            msg = await message.reply(view=view, mention_author=False)
            await msg.add_reaction("✅")
            await msg.add_reaction("❌")

            def check(reaction, user):
                return user == message.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)

                if str(reaction.emoji) == "❌":
                    cancel_view = create_error_message("Cancelled", "Query execution cancelled.")
                    await msg.edit(view=cancel_view)
                    return
            except:
                timeout_view = create_error_message(f"{EMOJIS['time']} Timeout", "Query confirmation timed out.")
                await msg.edit(view=timeout_view)
                return

        try:
            async with db.pool.acquire() as conn:
                # Check if it's a SELECT query
                if query.upper().strip().startswith("SELECT"):
                    rows = await conn.fetch(query)

                    if not rows:
                        view = create_success_message("Query Executed", "No results returned.")
                        await message.reply(view=view, mention_author=False)
                        return

                    # Format results
                    result_text = "```\n"
                    for row in rows[:10]:  # Limit to 10 rows
                        result_text += " | ".join([str(v) for v in row.values()]) + "\n"
                    result_text += "```"

                    if len(rows) > 10:
                        result_text += f"\n*...and {len(rows) - 10} more rows*"

                    view = create_success_message(
                        "Query Executed",
                        f"**Rows:** {len(rows)}\n\n{result_text}",
                        footer=f"Executed by {message.author}"
                    )
                else:
                    # Execute non-SELECT query
                    result = await conn.execute(query)

                    view = create_success_message(
                        "Query Executed",
                        f"```sql\n{query[:500]}\n```\n\n**Result:** {result}",
                        footer=f"Executed by {message.author}"
                    )

                await message.reply(view=view, mention_author=False)

        except Exception as e:
            view = create_error_message(
                "Query Failed",
                f"```sql\n{query[:500]}\n```",
                fields=[{'name': 'Error', 'value': f"```{str(e)[:500]}```"}]
            )

            await message.reply(view=view, mention_author=False)

    async def handle_jsk_command(self, message: discord.Message, args: str):
        """
        Handle d.jsk command - Execute Python code
        Usage: <@1373916203814490194> d.jsk [code]
        """
        if not args:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> d.jsk [code]`\n\nProvide Python code to execute."
            )
            await message.reply(view=view, mention_author=False)
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
                output = f"{EMOJIS['done']} Code executed successfully (no output)"

            # Limit output length
            if len(output) > 1900:
                output = output[:1900] + "\n... (output truncated)"

            view = create_success_message(
                f"{EMOJIS['code']} Code Executed",
                f"```python\n{code[:500]}\n```",
                fields=[{'name': 'Output', 'value': f"```python\n{output}\n```"}],
                footer=f"Executed by {message.author}"
            )

            await message.reply(view=view, mention_author=False)

        except Exception as e:
            # Format error
            error_traceback = traceback.format_exc()

            if len(error_traceback) > 1900:
                error_traceback = error_traceback[-1900:]

            view = create_error_message(
                "Execution Failed",
                f"```python\n{code[:500]}\n```",
                fields=[{'name': 'Error', 'value': f"```python\n{error_traceback}\n```"}]
            )

            await message.reply(view=view, mention_author=False)


async def setup(bot):
    await bot.add_cog(DeveloperCommands(bot))
