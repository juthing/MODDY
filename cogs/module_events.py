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

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """
        Événement déclenché quand un message est supprimé
        Supprime tous les messages relayés si c'est un message inter-serveur
        """
        # Ignore les messages des bots
        if message.author.bot:
            return

        # Ignore les DMs
        if not message.guild:
            return

        if not self.bot.module_manager or not self.bot.db:
            return

        try:
            # Vérifie si c'est un message inter-serveur
            interserver_msg = await self.bot.db.get_interserver_message_by_original(message.id)
            if not interserver_msg:
                return

            # Supprime tous les messages relayés
            relayed_messages = interserver_msg.get('relayed_messages', [])
            for relayed in relayed_messages:
                try:
                    guild = self.bot.get_guild(relayed['guild_id'])
                    if not guild:
                        continue

                    channel = guild.get_channel(relayed['channel_id'])
                    if not channel:
                        continue

                    # Supprime le message
                    msg = await channel.fetch_message(relayed['message_id'])
                    await msg.delete()
                except discord.NotFound:
                    # Message déjà supprimé
                    pass
                except Exception as e:
                    logger.error(f"Error deleting relayed message {relayed['message_id']}: {e}")

            # Marque le message comme supprimé en DB
            await self.bot.db.delete_interserver_message(interserver_msg['moddy_id'])
            logger.info(f"Deleted inter-server message {interserver_msg['moddy_id']} and all relayed copies")

        except Exception as e:
            logger.error(f"Error in on_message_delete for inter-server: {e}", exc_info=True)


async def setup(bot):
    """Charge le cog"""
    await bot.add_cog(ModuleEvents(bot))
