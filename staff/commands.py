"""
Commande pour lister toutes les commandes disponibles
Utile pour le debug et la gestion
Utilise les composants V2
"""

import discord
from discord.ext import commands
from typing import List

# Import du système d'embeds V2
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse


class CommandsList(commands.Cog):
    """Liste les commandes du bot"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="commands", aliases=["cmds", "list"])
    async def list_commands(self, ctx):
        """Liste toutes les commandes disponibles avec composants V2"""

        components = [
            ModdyEmbed.heading("Commandes disponibles", 1),
            ModdyEmbed.separator()
        ]

        # Commandes par cog
        for cog_name, cog in self.bot.cogs.items():
            commands_list = []

            # Commandes texte
            for cmd in cog.get_commands():
                if not cmd.hidden:
                    aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                    commands_list.append(f"`{cmd.name}{aliases}`")

            # Commandes slash
            for cmd in cog.get_app_commands():
                commands_list.append(f"`/{cmd.name}` (slash)")

            if commands_list:
                components.append(ModdyEmbed.heading(cog_name, 3))
                components.append(ModdyEmbed.text("\n".join(commands_list)))
                components.append(ModdyEmbed.separator())

        # Commandes sans cog
        no_cog_commands = []
        for cmd in self.bot.commands:
            if not cmd.cog and not cmd.hidden:
                aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
                no_cog_commands.append(f"`{cmd.name}{aliases}`")

        if no_cog_commands:
            components.append(ModdyEmbed.heading("Sans catégorie", 3))
            components.append(ModdyEmbed.text("\n".join(no_cog_commands)))
            components.append(ModdyEmbed.separator())

        # Stats
        total_commands = len([c for c in self.bot.commands if not c.hidden])
        total_slash = len(self.bot.tree.get_commands())

        components.append(ModdyEmbed.text(f"_Total : `{total_commands}` commandes texte, `{total_slash}` commandes slash_"))

        await ctx.send(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components
        })

    @commands.command(name="cogs", aliases=["modules"])
    async def list_cogs(self, ctx):
        """Liste tous les cogs chargés avec composants V2"""

        components = [
            ModdyEmbed.heading("Modules chargés", 1),
            ModdyEmbed.separator()
        ]

        for cog_name, cog in self.bot.cogs.items():
            # Compte les commandes
            text_cmds = len([c for c in cog.get_commands() if not c.hidden])
            app_cmds = len(cog.get_app_commands())

            # Détermine le type
            cog_type = "Staff" if "staff" in cog.__module__ else "Public"

            components.extend([
                ModdyEmbed.text(f"**{cog_name}** ({cog_type})"),
                ModdyEmbed.text(f"→ `{text_cmds}` cmd(s) texte, `{app_cmds}` cmd(s) slash"),
                ModdyEmbed.text("")  # Ligne vide
            ])

        components.append(ModdyEmbed.separator())
        components.append(ModdyEmbed.text(f"_Total : `{len(self.bot.cogs)}` cogs_"))

        await ctx.send(**{
            "flags": ModdyEmbed.V2_FLAGS,
            "components": components
        })


async def setup(bot):
    await bot.add_cog(CommandsList(bot))