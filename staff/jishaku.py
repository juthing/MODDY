"""
Jishaku command for Moddy
Advanced Python code execution for debugging
OWNER ONLY - Not even developers have access
"""

import discord
from discord.ext import commands
import sys
from pathlib import Path
import asyncio
import io
import contextlib
import textwrap
import traceback
import inspect
import importlib
import subprocess
import os
import re
from typing import Optional, Any

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from config import COLORS


class JishakuCommand(commands.Cog):
    """Jishaku command for the owner only"""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = {}  # Storage of sessions per user

    async def cog_check(self, ctx):
        """Checks if the user is the bot owner"""
        return ctx.author.id == 1164597199594852395

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Local error handler for Jishaku commands."""
        if isinstance(error, commands.CheckFailure):
            embed = ModdyResponse.error(
                "Access Denied",
                "This command is strictly reserved for the bot owner for security reasons."
            )
            await ctx.send(embed=embed)

    def cleanup_code(self, content: str) -> str:
        """Cleans the code of markdown tags"""
        # Removes ```py\n``` and ```
        if content.startswith('```') and content.endswith('```'):
            content = '\n'.join(content.split('\n')[1:-1])

        # Removes `py` at the beginning if present
        content = content.strip('` \n')
        if content.startswith('py\n'):
            content = content[3:]
        elif content.startswith('python\n'):
            content = content[7:]

        return content

    def get_syntax_error(self, e: SyntaxError) -> str:
        """Formats a syntax error"""
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    async def run_code(self, ctx, code: str, *, add_return: bool = True) -> Optional[Any]:
        """Executes Python code in a controlled environment"""

        # Environment variables for the code
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'discord': discord,
            'commands': commands,
            '_': self._last_result,
            '__import__': __import__,
            'asyncio': asyncio,
        }

        # Add common imports
        env.update(globals())

        # Clean the code
        code = self.cleanup_code(code)
        stdout = io.StringIO()

        # Prepare the code for execution
        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

        # Try to add an automatic return if necessary
        if add_return:
            # Find the last non-empty line
            lines = code.split('\n')
            last_line_idx = -1
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip():
                    last_line_idx = i
                    break

            if last_line_idx >= 0:
                last_line = lines[last_line_idx].strip()
                # Check if it is an expression that can be returned
                if not any(last_line.startswith(kw) for kw in
                           ['return', 'raise', 'pass', 'break', 'continue',
                            'if ', 'for ', 'while ', 'with ', 'def ', 'class ',
                            'try:', 'except:', 'finally:', 'elif ', 'else:']):
                    # Add return before the last line
                    indent = len(lines[last_line_idx]) - len(lines[last_line_idx].lstrip())
                    lines[last_line_idx] = ' ' * indent + 'return ' + last_line
                    code = '\n'.join(lines)
                    to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

        try:
            exec(to_compile, env)
        except SyntaxError as e:
            return self.get_syntax_error(e)

        func = env['func']

        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            error = f'{value}{traceback.format_exc()}'
            return f'```py\n{error}\n```'
        else:
            value = stdout.getvalue()

            # Store the result for the next execution
            if ret is not None:
                self._last_result = ret

            # Prepare the output
            if ret is None:
                if value:
                    return f'```py\n{value}\n```'
                else:
                    return None
            else:
                return f'```py\n{value}{ret}\n```'

    @commands.command(name="jsk", aliases=["py", "jishaku", "exec", "eval"])
    async def jishaku(self, ctx, *, code: str = None):
        """
        Jishaku command - Executes Python code
        Owner only, not even developers have access

        Available variables:
        - ctx, bot, channel, author, guild, message
        - discord, commands, asyncio
        - _ (last result)

        Examples:
        jsk print("Hello")
        jsk return len(bot.guilds)
        jsk await ctx.send("Test")
        """
        if not code:
            embed = discord.Embed(
                title="<:terminal:1398729532193853592> Jishaku",
                description=(
                    "**Python Execution Command - Owner Only**\n\n"
                    "```\n"
                    "jsk <code>\n"
                    "```\n"
                    "**Available variables:**\n"
                    "• `ctx` - Command context\n"
                    "• `bot` - Bot instance\n"
                    "• `channel` - Current channel\n"
                    "• `author` - Command author\n"
                    "• `guild` - Current server\n"
                    "• `message` - Command message\n"
                    "• `_` - Last returned result\n"
                    "• Modules: `discord`, `commands`, `asyncio`"
                ),
                color=COLORS["primary"]
            )
            embed.set_footer(text="⚠️ This command is reserved for the bot owner")
            await ctx.send(embed=embed)
            return

        # Processing indicator
        async with ctx.typing():
            # Execute the code
            result = await self.run_code(ctx, code)

        # If no result or empty result
        if result is None or (isinstance(result, str) and result == '```py\n\n```'):
            # Success reaction
            try:
                await ctx.message.add_reaction("<:done:1398729525277229066>")
            except:
                pass
        # If error
        elif result and '```py\n' in result and 'Traceback' in result:
            # Error reaction
            try:
                await ctx.message.add_reaction("<:undone:1398729502028333218>")
            except:
                pass

            # Send the error if it is short
            if len(result) <= 2000:
                await ctx.send(result)
            else:
                # If the error is too long, send it as a file
                file = discord.File(
                    io.BytesIO(result.encode('utf-8')),
                    filename='error.py'
                )
                await ctx.send("Error too long, sent as a file:", file=file)
        # If normal result
        else:
            # Send the result
            if result and len(result) <= 2000:
                await ctx.send(result)
            elif result:
                # If the result is too long, send it as a file
                # Remove ``` for the file
                clean_result = result.replace('```py\n', '').replace('\n```', '')
                file = discord.File(
                    io.BytesIO(clean_result.encode('utf-8')),
                    filename='output.py'
                )
                await ctx.send("Result too long, sent as a file:", file=file)
            else:
                # Success reaction if no output
                try:
                    await ctx.message.add_reaction("<:done:1398729525277229066>")
                except:
                    pass

    @commands.command(name="shell", aliases=["sh", "bash", "cmd"])
    async def shell(self, ctx, *, command: str = None):
        """
        Executes a shell/system command
        Owner only
        """
        if not command:
            embed = discord.Embed(
                title="<:terminal:1398729532193853592> Shell",
                description=(
                    "**System command execution - Owner Only**\n\n"
                    "```\n"
                    "shell <command>\n"
                    "```\n"
                    "**Examples:**\n"
                    "• `shell ls -la`\n"
                    "• `shell git status`\n"
                    "• `shell pip list`"
                ),
                color=COLORS["primary"]
            )
            await ctx.send(embed=embed)
            return

        async with ctx.typing():
            try:
                # Execute the command
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                # Decode the results
                result = ''
                if stdout:
                    result += f'[stdout]\n{stdout.decode("utf-8", errors="ignore")}\n'
                if stderr:
                    result += f'[stderr]\n{stderr.decode("utf-8", errors="ignore")}\n'
                if process.returncode != 0:
                    result += f'\n[Return code: {process.returncode}]'

                # Limit the size
                if len(result) > 1900:
                    # Send as a file if too long
                    file = discord.File(
                        io.BytesIO(result.encode('utf-8')),
                        filename='output.txt'
                    )
                    await ctx.send(f"```\n$ {command}\n```", file=file)
                else:
                    await ctx.send(f'```\n$ {command}\n{result}\n```')

                # Reaction according to the return code
                if process.returncode == 0:
                    try:
                        await ctx.message.add_reaction("<:done:1398729525277229066>")
                    except:
                        pass
                else:
                    try:
                        await ctx.message.add_reaction("<:undone:1398729502028333218>")
                    except:
                        pass

            except Exception as e:
                await ctx.send(f'```\nError: {str(e)}\n```')
                try:
                    await ctx.message.add_reaction("<:undone:1398729502028333218>")
                except:
                    pass

    @commands.command(name="load", aliases=["reload"])
    async def load_module(self, ctx, *, module: str = None):
        """
        Loads or reloads a Python module
        Owner only
        """
        if not module:
            # List loaded modules
            modules_list = [m for m in sys.modules.keys() if 'moddy' in m.lower() or 'cogs' in m or 'staff' in m]
            modules_list.sort()

            embed = discord.Embed(
                title="<:settings:1398729549323440208> Modules",
                description=f"**{len(modules_list)} modules loaded:**\n```\n" + '\n'.join(modules_list[:20]) + "\n```",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        try:
            # Reload the module
            if module in sys.modules:
                importlib.reload(sys.modules[module])
                await ctx.send(f"<:done:1398729525277229066> Module `{module}` reloaded")
            else:
                importlib.import_module(module)
                await ctx.send(f"<:done:1398729525277229066> Module `{module}` loaded")
        except Exception as e:
            await ctx.send(f"<:undone:1398729502028333218> Error: {str(e)}")

    @commands.command(name="sql")
    async def sql_query(self, ctx, *, query: str = None):
        """
        Executes a direct SQL query
        Owner only - DANGEROUS
        """
        if not self.bot.db:
            await ctx.send("<:undone:1398729502028333218> Database not connected")
            return

        if not query:
            embed = discord.Embed(
                title="<:data_object:1401600908323852318> SQL",
                description=(
                    "Direct SQL execution - Owner Only\n\n"
                    "```sql\n"
                    "sql <query>\n"
                    "```\n"
                    "<:undone:1398729502028333218> Dangerous command\n"
                    "Can modify/delete data"
                ),
                color=COLORS["warning"]
            )
            await ctx.send(embed=embed)
            return

        # Clean the query
        query = self.cleanup_code(query)

        try:
            async with ctx.typing():
                # Execute the query
                async with self.bot.db.pool.acquire() as conn:
                    # If it's a SELECT or EXPLAIN
                    if query.upper().startswith(('SELECT', 'EXPLAIN', 'SHOW', 'DESCRIBE')):
                        rows = await conn.fetch(query)

                        if not rows:
                            await ctx.send("<:done:1398729525277229066> No results")
                            return

                        # Format the results
                        headers = list(rows[0].keys())
                        table_data = []

                        for row in rows[:10]:  # Limit to 10 rows
                            table_data.append([str(row[h])[:20] for h in headers])

                        # Create a simple table
                        result = f"```\n{' | '.join(headers)}\n"
                        result += '-' * len(' | '.join(headers)) + '\n'
                        for row in table_data:
                            result += ' | '.join(row) + '\n'

                        if len(rows) > 10:
                            result += f"\n... and {len(rows) - 10} more rows"

                        result += "```"

                        await ctx.send(f"<:done:1398729525277229066> {len(rows)} results\n{result}")

                    else:
                        # For INSERT, UPDATE, DELETE, etc.
                        result = await conn.execute(query)

                        # Parse the result to get the number of affected rows
                        affected = 0
                        if ' ' in result:
                            parts = result.split(' ')
                            for part in parts:
                                if part.isdigit():
                                    affected = int(part)
                                    break

                        await ctx.send(f"<:done:1398729525277229066> Query executed\nResult: `{result}`")

        except Exception as e:
            await ctx.send(f"<:undone:1398729502028333218> SQL Error:\n```sql\n{str(e)}\n```")


async def setup(bot):
    await bot.add_cog(JishakuCommand(bot))