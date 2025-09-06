"""
Commande Jishaku pour Moddy
Exécution de code Python pour debug avancé
OWNER ONLY - Même les développeurs n'ont pas accès
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
    """Commande Jishaku pour l'owner uniquement"""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = {}  # Stockage des sessions par utilisateur

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est l'owner du bot"""
        return ctx.author.id == 1164597199594852395

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Gestionnaire d'erreur local pour les commandes Jishaku."""
        if isinstance(error, commands.CheckFailure):
            embed = ModdyResponse.error(
                "Accès Refusé",
                "Cette commande est strictement réservée au propriétaire du bot pour des raisons de sécurité."
            )
            await ctx.send(embed=embed)

    def cleanup_code(self, content: str) -> str:
        """Nettoie le code des balises markdown"""
        # Enlève les ```py\n``` et ```
        if content.startswith('```') and content.endswith('```'):
            content = '\n'.join(content.split('\n')[1:-1])

        # Enlève les `py` au début si présent
        content = content.strip('` \n')
        if content.startswith('py\n'):
            content = content[3:]
        elif content.startswith('python\n'):
            content = content[7:]

        return content

    def get_syntax_error(self, e: SyntaxError) -> str:
        """Formate une erreur de syntaxe"""
        if e.text is None:
            return f'```py\n{e.__class__.__name__}: {e}\n```'
        return f'```py\n{e.text}{"^":>{e.offset}}\n{e.__class__.__name__}: {e}```'

    async def run_code(self, ctx, code: str, *, add_return: bool = True) -> Optional[Any]:
        """Exécute du code Python dans un environnement contrôlé"""

        # Variables d'environnement pour le code
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

        # Ajoute les imports courants
        env.update(globals())

        # Nettoie le code
        code = self.cleanup_code(code)
        stdout = io.StringIO()

        # Prépare le code pour l'exécution
        to_compile = f'async def func():\n{textwrap.indent(code, "  ")}'

        # Essaye d'ajouter un return automatique si nécessaire
        if add_return:
            # Trouve la dernière ligne non vide
            lines = code.split('\n')
            last_line_idx = -1
            for i in range(len(lines) - 1, -1, -1):
                if lines[i].strip():
                    last_line_idx = i
                    break

            if last_line_idx >= 0:
                last_line = lines[last_line_idx].strip()
                # Vérifie si c'est une expression qui peut être retournée
                if not any(last_line.startswith(kw) for kw in
                           ['return', 'raise', 'pass', 'break', 'continue',
                            'if ', 'for ', 'while ', 'with ', 'def ', 'class ',
                            'try:', 'except:', 'finally:', 'elif ', 'else:']):
                    # Ajoute return devant la dernière ligne
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

            # Stocke le résultat pour la prochaine exécution
            if ret is not None:
                self._last_result = ret

            # Prépare la sortie
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
        Commande Jishaku - Exécute du code Python
        Owner only, même les développeurs n'ont pas accès

        Variables disponibles:
        - ctx, bot, channel, author, guild, message
        - discord, commands, asyncio
        - _ (dernier résultat)

        Exemples:
        jsk print("Hello")
        jsk return len(bot.guilds)
        jsk await ctx.send("Test")
        """
        if not code:
            embed = discord.Embed(
                title="<:terminal:1398729532193853592> Jishaku",
                description=(
                    "**Commande d'exécution Python - Owner Only**\n\n"
                    "```\n"
                    "jsk <code>\n"
                    "```\n"
                    "**Variables disponibles:**\n"
                    "• `ctx` - Contexte de la commande\n"
                    "• `bot` - Instance du bot\n"
                    "• `channel` - Salon actuel\n"
                    "• `author` - Auteur de la commande\n"
                    "• `guild` - Serveur actuel\n"
                    "• `message` - Message de la commande\n"
                    "• `_` - Dernier résultat retourné\n"
                    "• Modules: `discord`, `commands`, `asyncio`"
                ),
                color=COLORS["primary"]
            )
            embed.set_footer(text="⚠️ Cette commande est réservée à l'owner du bot")
            await ctx.send(embed=embed)
            return

        # Indicateur de traitement
        async with ctx.typing():
            # Exécute le code
            result = await self.run_code(ctx, code)

        # Si pas de résultat ou résultat vide
        if result is None or (isinstance(result, str) and result == '```py\n\n```'):
            # Réaction de succès
            try:
                await ctx.message.add_reaction("<:done:1398729525277229066>")
            except:
                pass
        # Si erreur
        elif result and '```py\n' in result and 'Traceback' in result:
            # Réaction d'erreur
            try:
                await ctx.message.add_reaction("<:undone:1398729502028333218>")
            except:
                pass

            # Envoie l'erreur si elle est courte
            if len(result) <= 2000:
                await ctx.send(result)
            else:
                # Si l'erreur est trop longue, l'envoie en fichier
                file = discord.File(
                    io.BytesIO(result.encode('utf-8')),
                    filename='error.py'
                )
                await ctx.send("Erreur trop longue, envoyée en fichier:", file=file)
        # Si résultat normal
        else:
            # Envoie le résultat
            if result and len(result) <= 2000:
                await ctx.send(result)
            elif result:
                # Si le résultat est trop long, l'envoie en fichier
                # Enlève les ``` pour le fichier
                clean_result = result.replace('```py\n', '').replace('\n```', '')
                file = discord.File(
                    io.BytesIO(clean_result.encode('utf-8')),
                    filename='output.py'
                )
                await ctx.send("Résultat trop long, envoyé en fichier:", file=file)
            else:
                # Réaction de succès si pas de sortie
                try:
                    await ctx.message.add_reaction("<:done:1398729525277229066>")
                except:
                    pass

    @commands.command(name="shell", aliases=["sh", "bash", "cmd"])
    async def shell(self, ctx, *, command: str = None):
        """
        Exécute une commande shell/système
        Owner only
        """
        if not command:
            embed = discord.Embed(
                title="<:terminal:1398729532193853592> Shell",
                description=(
                    "**Exécution de commandes système - Owner Only**\n\n"
                    "```\n"
                    "shell <commande>\n"
                    "```\n"
                    "**Exemples:**\n"
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
                # Exécute la commande
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await process.communicate()

                # Décode les résultats
                result = ''
                if stdout:
                    result += f'[stdout]\n{stdout.decode("utf-8", errors="ignore")}\n'
                if stderr:
                    result += f'[stderr]\n{stderr.decode("utf-8", errors="ignore")}\n'
                if process.returncode != 0:
                    result += f'\n[Return code: {process.returncode}]'

                # Limite la taille
                if len(result) > 1900:
                    # Envoie en fichier si trop long
                    file = discord.File(
                        io.BytesIO(result.encode('utf-8')),
                        filename='output.txt'
                    )
                    await ctx.send(f"```\n$ {command}\n```", file=file)
                else:
                    await ctx.send(f'```\n$ {command}\n{result}\n```')

                # Réaction selon le code de retour
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
                await ctx.send(f'```\nErreur: {str(e)}\n```')
                try:
                    await ctx.message.add_reaction("<:undone:1398729502028333218>")
                except:
                    pass

    @commands.command(name="load", aliases=["reload"])
    async def load_module(self, ctx, *, module: str = None):
        """
        Charge ou recharge un module Python
        Owner only
        """
        if not module:
            # Liste les modules chargés
            modules_list = [m for m in sys.modules.keys() if 'moddy' in m.lower() or 'cogs' in m or 'staff' in m]
            modules_list.sort()

            embed = discord.Embed(
                title="<:settings:1398729549323440208> Modules",
                description=f"**{len(modules_list)} modules chargés:**\n```\n" + '\n'.join(modules_list[:20]) + "\n```",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        try:
            # Recharge le module
            if module in sys.modules:
                importlib.reload(sys.modules[module])
                await ctx.send(f"<:done:1398729525277229066> Module `{module}` rechargé")
            else:
                importlib.import_module(module)
                await ctx.send(f"<:done:1398729525277229066> Module `{module}` chargé")
        except Exception as e:
            await ctx.send(f"<:undone:1398729502028333218> Erreur: {str(e)}")

    @commands.command(name="sql")
    async def sql_query(self, ctx, *, query: str = None):
        """
        Exécute une requête SQL directe
        Owner only - DANGEREUX
        """
        if not self.bot.db:
            await ctx.send("<:undone:1398729502028333218> Base de données non connectée")
            return

        if not query:
            embed = discord.Embed(
                title="<:data_object:1401600908323852318> SQL",
                description=(
                    "Exécution SQL directe - Owner Only\n\n"
                    "```sql\n"
                    "sql <requête>\n"
                    "```\n"
                    "<:undone:1398729502028333218> Commande dangereuse\n"
                    "Peut modifier/supprimer des données"
                ),
                color=COLORS["warning"]
            )
            await ctx.send(embed=embed)
            return

        # Nettoie la requête
        query = self.cleanup_code(query)

        try:
            async with ctx.typing():
                # Exécute la requête
                async with self.bot.db.pool.acquire() as conn:
                    # Si c'est un SELECT ou EXPLAIN
                    if query.upper().startswith(('SELECT', 'EXPLAIN', 'SHOW', 'DESCRIBE')):
                        rows = await conn.fetch(query)

                        if not rows:
                            await ctx.send("<:done:1398729525277229066> Aucun résultat")
                            return

                        # Formate les résultats
                        headers = list(rows[0].keys())
                        table_data = []

                        for row in rows[:10]:  # Limite à 10 lignes
                            table_data.append([str(row[h])[:20] for h in headers])

                        # Crée un tableau simple
                        result = f"```\n{' | '.join(headers)}\n"
                        result += '-' * len(' | '.join(headers)) + '\n'
                        for row in table_data:
                            result += ' | '.join(row) + '\n'

                        if len(rows) > 10:
                            result += f"\n... et {len(rows) - 10} lignes de plus"

                        result += "```"

                        await ctx.send(f"<:done:1398729525277229066> {len(rows)} résultats\n{result}")

                    else:
                        # Pour INSERT, UPDATE, DELETE, etc.
                        result = await conn.execute(query)

                        # Parse le résultat pour obtenir le nombre de lignes affectées
                        affected = 0
                        if ' ' in result:
                            parts = result.split(' ')
                            for part in parts:
                                if part.isdigit():
                                    affected = int(part)
                                    break

                        await ctx.send(f"<:done:1398729525277229066> Requête exécutée\nRésultat: `{result}`")

        except Exception as e:
            await ctx.send(f"<:undone:1398729502028333218> Erreur SQL:\n```sql\n{str(e)}\n```")


async def setup(bot):
    await bot.add_cog(JishakuCommand(bot))