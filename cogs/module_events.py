"""
Module Events Handler
Gère tous les événements Discord pour les modules de serveur
"""

import discord
from discord.ext import commands
import logging

logger = logging.getLogger('moddy.cogs.module_events')


class ModuleEvents(commands.Cog):
    """
    Cog qui écoute les événements Discord et les transmet aux modules concernés
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """
        Événement déclenché quand un membre rejoint un serveur
        Transmet l'événement aux modules concernés (Welcome, etc.)
        """
        if not self.bot.module_manager:
            return

        try:
            # Récupère l'instance du module Welcome pour ce serveur
            welcome_module = await self.bot.module_manager.get_module_instance(
                member.guild.id,
                'welcome'
            )

            # Si le module est actif, appelle sa méthode
            if welcome_module and welcome_module.enabled:
                await welcome_module.on_member_join(member)

        except Exception as e:
            logger.error(f"Error in on_member_join for guild {member.guild.id}: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """
        Événement déclenché quand un membre quitte un serveur
        Peut être utilisé pour les modules de leave messages, etc.
        """
        # À implémenter si besoin pour d'autres modules
        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Événement déclenché pour chaque message
        Peut être utilisé pour les modules de modération, inter-serveur, etc.
        """
        # Ignore les messages du bot
        if message.author.bot:
            return

        # Ignore les DMs
        if not message.guild:
            return

        if not self.bot.module_manager:
            return

        try:
            # Récupère l'instance du module Inter-Server pour ce serveur
            interserver_module = await self.bot.module_manager.get_module_instance(
                message.guild.id,
                'interserver'
            )

            # Si le module est actif, appelle sa méthode
            if interserver_module and interserver_module.enabled:
                await interserver_module.on_message(message)

        except Exception as e:
            logger.error(f"Error in on_message for guild {message.guild.id}: {e}", exc_info=True)


async def setup(bot):
    """Charge le cog"""
    await bot.add_cog(ModuleEvents(bot))
