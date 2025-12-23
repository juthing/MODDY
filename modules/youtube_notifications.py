"""
Module Youtube Notifications - Notifications en temps réel pour les vidéos YouTube
Utilise WebSub (PubSubHubbub) pour recevoir des notifications instantanées
"""

import discord
from typing import Dict, Any, Optional, List
import logging
import aiohttp
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from modules.module_manager import ModuleBase

logger = logging.getLogger('moddy.modules.youtube_notifications')


class YoutubeNotificationsModule(ModuleBase):
    """
    Module de notifications YouTube via WebSub
    Permet de poster des alertes quand une chaîne YouTube publie une vidéo
    """

    MODULE_ID = "youtube_notifications"
    MODULE_NAME = "YouTube Notifications"
    MODULE_DESCRIPTION = "Notifications en temps réel pour les vidéos YouTube"
    MODULE_EMOJI = "<:moddy:1451280939412881508>"  # Using moddy emoji as YouTube icon

    # WebSub Hub URL for YouTube
    WEBSUB_HUB = "https://pubsubhubbub.appspot.com/"

    def __init__(self, bot, guild_id: int):
        super().__init__(bot, guild_id)

        # List of channel subscriptions
        # Format: [{"channel_id": "...", "channel_username": "...", "discord_channel_id": ..., "message": "...", "roles": [...]}]
        self.subscriptions: List[Dict[str, Any]] = []

    async def load_config(self, config_data: Dict[str, Any]) -> bool:
        """Charge la configuration depuis la DB"""
        try:
            self.config = config_data

            # Load subscriptions
            self.subscriptions = config_data.get('subscriptions', [])

            # Module is enabled if there are subscriptions
            self.enabled = len(self.subscriptions) > 0

            logger.info(f"✅ YouTube Notifications module loaded for guild {self.guild_id} with {len(self.subscriptions)} subscriptions")

            return True
        except Exception as e:
            logger.error(f"Error loading youtube_notifications config: {e}", exc_info=True)
            return False

    async def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valide la configuration"""
        # Validate subscriptions list
        subscriptions = config_data.get('subscriptions', [])

        if not isinstance(subscriptions, list):
            return False, "Les abonnements doivent être une liste"

        # Validate each subscription
        for sub in subscriptions:
            if not isinstance(sub, dict):
                return False, "Chaque abonnement doit être un dictionnaire"

            # Required fields
            if 'channel_id' not in sub or not sub['channel_id']:
                return False, "L'ID de chaîne YouTube est requis"

            if 'discord_channel_id' not in sub or not sub['discord_channel_id']:
                return False, "Le salon Discord est requis"

            if 'message' not in sub or not sub['message']:
                return False, "Le message est requis"

            # Verify Discord channel exists
            try:
                guild = self.bot.get_guild(self.guild_id)
                if not guild:
                    return False, "Serveur introuvable"

                channel = guild.get_channel(sub['discord_channel_id'])
                if not channel:
                    return False, f"Salon Discord {sub['discord_channel_id']} introuvable"

                if not isinstance(channel, discord.TextChannel):
                    return False, "Le salon doit être un salon textuel"

                # Check permissions
                perms = channel.permissions_for(guild.me)
                if not perms.send_messages:
                    return False, f"Je n'ai pas la permission d'envoyer des messages dans {channel.mention}"

            except Exception as e:
                return False, f"Erreur de validation du salon : {str(e)}"

            # Validate message length
            if len(sub['message']) > 2000:
                return False, "Le message ne peut pas dépasser 2000 caractères"

            # Validate roles
            if 'roles' in sub:
                if not isinstance(sub['roles'], list):
                    return False, "Les rôles doivent être une liste"

                for role_id in sub['roles']:
                    try:
                        guild = self.bot.get_guild(self.guild_id)
                        role = guild.get_role(role_id)
                        if not role:
                            return False, f"Rôle {role_id} introuvable"
                    except:
                        return False, f"Erreur de validation du rôle {role_id}"

        return True, None

    def get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        return {
            'subscriptions': []
        }

    async def subscribe_to_channel(self, channel_id: str, callback_url: str) -> bool:
        """
        S'abonne à une chaîne YouTube via WebSub

        Args:
            channel_id: ID de la chaîne YouTube
            callback_url: URL de callback pour les notifications

        Returns:
            bool: True si l'abonnement a réussi
        """
        topic = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"

        payload = {
            'hub.mode': 'subscribe',
            'hub.topic': topic,
            'hub.callback': callback_url,
            'hub.lease_seconds': '864000',  # 10 days
            'hub.verify': 'async'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.WEBSUB_HUB, data=payload) as response:
                    if response.status in [202, 204]:
                        logger.info(f"✅ Successfully subscribed to YouTube channel {channel_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed to subscribe to YouTube channel {channel_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error subscribing to YouTube channel {channel_id}: {e}", exc_info=True)
            return False

    async def unsubscribe_from_channel(self, channel_id: str, callback_url: str) -> bool:
        """
        Se désabonne d'une chaîne YouTube via WebSub

        Args:
            channel_id: ID de la chaîne YouTube
            callback_url: URL de callback pour les notifications

        Returns:
            bool: True si le désabonnement a réussi
        """
        topic = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"

        payload = {
            'hub.mode': 'unsubscribe',
            'hub.topic': topic,
            'hub.callback': callback_url,
            'hub.verify': 'async'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.WEBSUB_HUB, data=payload) as response:
                    if response.status in [202, 204]:
                        logger.info(f"✅ Successfully unsubscribed from YouTube channel {channel_id}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed to unsubscribe from YouTube channel {channel_id}: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error unsubscribing from YouTube channel {channel_id}: {e}", exc_info=True)
            return False

    async def handle_notification(self, feed_xml: str) -> bool:
        """
        Traite une notification WebSub reçue

        Args:
            feed_xml: Contenu XML du feed Atom YouTube

        Returns:
            bool: True si le traitement a réussi
        """
        try:
            # Parse XML
            root = ET.fromstring(feed_xml)

            # Namespaces YouTube
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'yt': 'http://www.youtube.com/xml/schemas/2015'
            }

            # Extract video info
            entry = root.find('atom:entry', ns)
            if entry is None:
                logger.warning("No entry found in YouTube notification")
                return False

            video_id_elem = entry.find('yt:videoId', ns)
            channel_id_elem = entry.find('yt:channelId', ns)
            title_elem = entry.find('atom:title', ns)
            published_elem = entry.find('atom:published', ns)

            if video_id_elem is None or channel_id_elem is None:
                logger.warning("Missing required elements in YouTube notification")
                return False

            video_id = video_id_elem.text
            channel_id = channel_id_elem.text
            title = title_elem.text if title_elem is not None else "Nouvelle vidéo"
            published = published_elem.text if published_elem is not None else None

            logger.info(f"📺 YouTube notification: {title} ({video_id}) from channel {channel_id}")

            # Find matching subscription
            subscription = None
            for sub in self.subscriptions:
                if sub['channel_id'] == channel_id:
                    subscription = sub
                    break

            if not subscription:
                logger.warning(f"No subscription found for YouTube channel {channel_id}")
                return False

            # Send notification to Discord
            await self._send_discord_notification(subscription, video_id, title)

            return True

        except Exception as e:
            logger.error(f"Error handling YouTube notification: {e}", exc_info=True)
            return False

    async def _send_discord_notification(self, subscription: Dict[str, Any], video_id: str, video_title: str):
        """
        Envoie la notification dans le salon Discord configuré

        Args:
            subscription: Configuration de l'abonnement
            video_id: ID de la vidéo YouTube
            video_title: Titre de la vidéo
        """
        try:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                logger.warning(f"Guild {self.guild_id} not found")
                return

            channel = guild.get_channel(subscription['discord_channel_id'])
            if not channel or not isinstance(channel, discord.TextChannel):
                logger.warning(f"Channel {subscription['discord_channel_id']} not found or not a text channel")
                return

            # Build message
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            message = subscription['message'].replace('[video_link]', video_url)

            # Add role mentions if configured
            role_mentions = []
            if subscription.get('roles'):
                for role_id in subscription['roles']:
                    role = guild.get_role(role_id)
                    if role:
                        role_mentions.append(role.mention)

            if role_mentions:
                message = f"{' '.join(role_mentions)} {message}"

            # Send message
            await channel.send(message)

            logger.info(f"✅ YouTube notification sent to channel {channel.name} (guild {self.guild_id})")

        except discord.Forbidden:
            logger.warning(f"Missing permissions to send YouTube notification in guild {self.guild_id}")
        except Exception as e:
            logger.error(f"Error sending YouTube notification: {e}", exc_info=True)

    def get_subscription_by_channel(self, youtube_channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un abonnement par ID de chaîne YouTube

        Args:
            youtube_channel_id: ID de la chaîne YouTube

        Returns:
            Optional[Dict]: L'abonnement trouvé ou None
        """
        for sub in self.subscriptions:
            if sub['channel_id'] == youtube_channel_id:
                return sub
        return None
