"""
Module Inter-Server - Système de communication inter-serveurs
Permet de connecter plusieurs serveurs Discord via des salons dédiés
"""

import discord
from typing import Dict, Any, Optional, List
import logging

from modules.module_manager import ModuleBase

logger = logging.getLogger('moddy.modules.interserver')


class InterServerModule(ModuleBase):
    """
    Module de communication inter-serveurs
    Connecte des salons de différents serveurs pour créer un portail de communication
    """

    MODULE_ID = "interserver"
    MODULE_NAME = "Inter-Server"
    MODULE_DESCRIPTION = "Connecte plusieurs serveurs via des salons dédiés"
    MODULE_EMOJI = "🌐"

    def __init__(self, bot, guild_id: int):
        super().__init__(bot, guild_id)
        self.channel_id: Optional[int] = None
        self.show_server_name: bool = True
        self.show_avatar: bool = True
        self.allowed_mentions: bool = False

    async def load_config(self, config_data: Dict[str, Any]) -> bool:
        """Charge la configuration depuis la DB"""
        try:
            self.config = config_data
            self.channel_id = config_data.get('channel_id')
            self.show_server_name = config_data.get('show_server_name', True)
            self.show_avatar = config_data.get('show_avatar', True)
            self.allowed_mentions = config_data.get('allowed_mentions', False)

            # Le module est activé si un salon est configuré
            self.enabled = self.channel_id is not None

            return True
        except Exception as e:
            logger.error(f"Error loading interserver config: {e}")
            return False

    async def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valide la configuration"""
        # Vérifie que le salon existe si spécifié
        if 'channel_id' in config_data and config_data['channel_id']:
            try:
                guild = self.bot.get_guild(self.guild_id)
                if not guild:
                    return False, "Serveur introuvable"

                channel = guild.get_channel(config_data['channel_id'])
                if not channel:
                    return False, "Salon introuvable"

                if not isinstance(channel, discord.TextChannel):
                    return False, "Le salon doit être un salon textuel"

                # Vérifie les permissions
                perms = channel.permissions_for(guild.me)
                if not perms.send_messages:
                    return False, f"Je n'ai pas la permission d'envoyer des messages dans {channel.mention}"

                if not perms.manage_webhooks:
                    return False, f"Je n'ai pas la permission de gérer les webhooks dans {channel.mention}"

            except Exception as e:
                return False, f"Erreur de validation : {str(e)}"

        return True, None

    def get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        return {
            'channel_id': None,
            'show_server_name': True,
            'show_avatar': True,
            'allowed_mentions': False
        }

    async def on_message(self, message: discord.Message):
        """
        Appelé quand un message est envoyé dans un salon inter-serveur
        Relaie le message vers tous les autres salons inter-serveur
        """
        if not self.enabled or not self.channel_id:
            return

        # Ignore les messages qui ne sont pas dans le salon configuré
        if message.channel.id != self.channel_id:
            return

        # Ignore les messages des bots (évite les boucles infinies)
        if message.author.bot:
            return

        # Ignore les messages vides sans pièces jointes
        if not message.content and not message.attachments and not message.embeds:
            return

        try:
            # Récupère tous les autres salons inter-serveur actifs
            target_channels = await self._get_all_interserver_channels()

            # Retire le salon actuel de la liste
            target_channels = [ch for ch in target_channels if ch.id != message.channel.id]

            if not target_channels:
                logger.debug(f"No target channels found for interserver relay from guild {self.guild_id}")
                return

            # Prépare le contenu du message
            await self._relay_message(message, target_channels)

            logger.info(f"✅ Relayed message from {message.guild.name} to {len(target_channels)} servers")

        except Exception as e:
            logger.error(f"Error relaying interserver message: {e}", exc_info=True)

    async def _get_all_interserver_channels(self) -> List[discord.TextChannel]:
        """
        Récupère tous les salons inter-serveur actifs
        """
        channels = []

        # Parcourt tous les serveurs où le bot est présent
        for guild in self.bot.guilds:
            # Récupère le module inter-serveur pour ce serveur
            module = await self.bot.module_manager.get_module_instance(
                guild.id,
                'interserver'
            )

            # Si le module est actif et configuré
            if module and module.enabled and module.channel_id:
                channel = guild.get_channel(module.channel_id)
                if channel and isinstance(channel, discord.TextChannel):
                    # Vérifie les permissions
                    perms = channel.permissions_for(guild.me)
                    if perms.send_messages and perms.manage_webhooks:
                        channels.append(channel)

        return channels

    async def _relay_message(self, message: discord.Message, target_channels: List[discord.TextChannel]):
        """
        Relaie un message vers les salons cibles en utilisant des webhooks
        """
        # Prépare le nom d'affichage
        if self.show_server_name:
            username = f"{message.author.display_name} ({message.guild.name})"
        else:
            username = message.author.display_name

        # Limite la longueur du nom (max 80 caractères pour Discord)
        if len(username) > 80:
            username = username[:77] + "..."

        # Prépare l'avatar
        avatar_url = message.author.display_avatar.url if self.show_avatar else None

        # Prépare le contenu
        content = message.content

        # Gère les mentions si désactivées
        if not self.allowed_mentions:
            allowed_mentions = discord.AllowedMentions.none()
        else:
            allowed_mentions = discord.AllowedMentions.all()

        # Prépare les fichiers (pièces jointes)
        files = []
        if message.attachments:
            for attachment in message.attachments[:10]:  # Limite à 10 fichiers
                try:
                    # Télécharge le fichier
                    file_data = await attachment.read()
                    files.append(discord.File(
                        fp=discord.utils.BytesIO(file_data),
                        filename=attachment.filename,
                        spoiler=attachment.is_spoiler()
                    ))
                except Exception as e:
                    logger.warning(f"Failed to download attachment {attachment.filename}: {e}")

        # Prépare les embeds
        embeds = []
        if message.embeds:
            # Limite à 10 embeds (limite Discord)
            embeds = message.embeds[:10]

        # Envoie le message via webhook dans chaque salon cible
        for channel in target_channels:
            try:
                # Récupère ou crée un webhook pour ce salon
                webhook = await self._get_or_create_webhook(channel)

                if not webhook:
                    logger.warning(f"Could not get webhook for channel {channel.id} in guild {channel.guild.id}")
                    continue

                # Prépare les kwargs pour le webhook
                webhook_kwargs = {
                    'username': username,
                    'allowed_mentions': allowed_mentions,
                    'wait': False
                }

                # Ajoute le contenu s'il existe
                if content:
                    webhook_kwargs['content'] = content

                # Ajoute l'avatar s'il existe
                if avatar_url:
                    webhook_kwargs['avatar_url'] = avatar_url

                # Ajoute les embeds s'il y en a
                if embeds:
                    webhook_kwargs['embeds'] = embeds

                # Ajoute les fichiers s'il y en a
                if files:
                    webhook_kwargs['files'] = files

                # Envoie le message via le webhook
                await webhook.send(**webhook_kwargs)

            except discord.Forbidden:
                logger.warning(f"Missing permissions to send webhook in channel {channel.id}")
            except discord.HTTPException as e:
                logger.error(f"HTTP error sending webhook to channel {channel.id}: {e}")
            except Exception as e:
                logger.error(f"Error sending webhook to channel {channel.id}: {e}", exc_info=True)

    async def _get_or_create_webhook(self, channel: discord.TextChannel) -> Optional[discord.Webhook]:
        """
        Récupère ou crée un webhook pour le salon inter-serveur
        """
        try:
            # Récupère les webhooks existants
            webhooks = await channel.webhooks()

            # Cherche un webhook créé par Moddy pour l'inter-serveur
            moddy_webhook = None
            for webhook in webhooks:
                if webhook.user and webhook.user.id == self.bot.user.id:
                    if webhook.name == "Moddy Inter-Server":
                        moddy_webhook = webhook
                        break

            # Si aucun webhook trouvé, en créer un
            if not moddy_webhook:
                moddy_webhook = await channel.create_webhook(
                    name="Moddy Inter-Server",
                    reason="Webhook for inter-server communication"
                )
                logger.info(f"Created webhook for inter-server in channel {channel.id}")

            return moddy_webhook

        except discord.Forbidden:
            logger.error(f"Missing permissions to manage webhooks in channel {channel.id}")
            return None
        except Exception as e:
            logger.error(f"Error getting/creating webhook: {e}", exc_info=True)
            return None
