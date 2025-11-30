"""
Module Inter-Server - Système de communication inter-serveurs
Permet de connecter plusieurs serveurs Discord via des salons dédiés
"""

import discord
from typing import Dict, Any, Optional, List
import logging
import random
import string
import re
from datetime import datetime, timedelta, timezone
import asyncio

from modules.module_manager import ModuleBase

logger = logging.getLogger('moddy.modules.interserver')

# Regex pour détecter les liens d'invitation Discord
INVITE_REGEX = re.compile(r'(?:https?://)?(?:www\.)?(?:discord\.gg|discord\.com/invite)/([a-zA-Z0-9-]+)', re.IGNORECASE)


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

        # Cooldown tracking (user_id -> timestamp)
        self.cooldowns: Dict[int, datetime] = {}

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

            # Configure le slowmode si le module est activé
            if self.enabled:
                await self._setup_slowmode()

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

                if not perms.add_reactions:
                    return False, f"Je n'ai pas la permission d'ajouter des réactions dans {channel.mention}"

                if not perms.manage_messages:
                    return False, f"Je n'ai pas la permission de gérer les messages dans {channel.mention}"

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

    async def _setup_slowmode(self):
        """Configure le slowmode de 3 secondes sur le salon inter-serveur"""
        try:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                return

            channel = guild.get_channel(self.channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                return

            # Configure le slowmode à 3 secondes
            if channel.slowmode_delay != 3:
                await channel.edit(slowmode_delay=3, reason="Inter-server slowmode")
                logger.info(f"Set slowmode to 3 seconds for inter-server channel in guild {self.guild_id}")
        except Exception as e:
            logger.error(f"Error setting up slowmode: {e}")

    def _generate_moddy_id(self) -> str:
        """Génère un ID Moddy unique (8 caractères alphanumériques)"""
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=8))

    def _check_cooldown(self, user_id: int) -> bool:
        """
        Vérifie si l'utilisateur est en cooldown
        Returns: True si OK, False si en cooldown
        """
        now = datetime.now(timezone.utc)

        if user_id in self.cooldowns:
            last_message = self.cooldowns[user_id]
            if (now - last_message).total_seconds() < 3:
                return False

        # Met à jour le timestamp
        self.cooldowns[user_id] = now
        return True

    def _contains_invite(self, text: str) -> bool:
        """Détecte si le texte contient un lien d'invitation Discord"""
        return bool(INVITE_REGEX.search(text))

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
            # Vérifie si l'utilisateur est blacklisté de l'inter-serveur
            if await self.bot.db.has_attribute('user', message.author.id, 'INTERSERVER_BLACKLISTED'):
                await message.add_reaction("<:undone:1398729502028333218>")
                await message.channel.send(
                    f"{message.author.mention} You are blacklisted from using the inter-server system.",
                    delete_after=10
                )
                return

            # Vérifie le cooldown (sauf pour l'équipe Moddy)
            is_team = await self.bot.db.has_attribute('user', message.author.id, 'TEAM')
            if not is_team:
                if not self._check_cooldown(message.author.id):
                    await message.add_reaction("<:undone:1398729502028333218>")
                    await message.channel.send(
                        f"{message.author.mention} Slow down! You can send a message every 3 seconds.",
                        delete_after=5
                    )
                    return

            # Vérifie les liens d'invitation
            if self._contains_invite(message.content):
                await message.delete()
                await message.channel.send(
                    f"{message.author.mention} Discord invite links are not allowed in inter-server chat.",
                    delete_after=10
                )
                return

            # Ajoute la réaction loading
            await message.add_reaction("<a:loading:1395047662092550194>")

            # Détecte les messages Moddy Team
            is_moddy_team_message = False
            content = message.content
            if is_team and content.startswith("$MT$ "):
                is_moddy_team_message = True
                content = content[5:]  # Retire le préfixe $MT$

            # Génère l'ID Moddy
            moddy_id = self._generate_moddy_id()

            # Enregistre le message en DB
            await self.bot.db.create_interserver_message(
                moddy_id=moddy_id,
                original_message_id=message.id,
                original_guild_id=message.guild.id,
                original_channel_id=message.channel.id,
                author_id=message.author.id,
                author_username=str(message.author),
                content=content,
                is_moddy_team=is_moddy_team_message
            )

            # Récupère tous les autres salons inter-serveur actifs
            target_channels = await self._get_all_interserver_channels()

            # Retire le salon actuel de la liste
            target_channels = [ch for ch in target_channels if ch.id != message.channel.id]

            if not target_channels:
                logger.debug(f"No target channels found for interserver relay from guild {self.guild_id}")
                # Retire la réaction loading et ajoute done quand même
                await message.remove_reaction("<a:loading:1395047662092550194>", self.bot.user)
                await message.add_reaction("<:done:1398729525277229066>")
                return

            # Prépare et envoie le message
            success_count = await self._relay_message(message, target_channels, moddy_id, content, is_moddy_team_message)

            # Ajoute la réaction verified pour les messages Moddy Team
            if is_moddy_team_message:
                await message.add_reaction("<:verified:1398729677601902635>")

            # Retire loading et ajoute done si majorité de succès
            await message.remove_reaction("<a:loading:1395047662092550194>", self.bot.user)
            if success_count >= len(target_channels) // 2:  # Au moins 50% de succès
                await message.add_reaction("<:done:1398729525277229066>")
            else:
                await message.add_reaction("<:undone:1398729502028333218>")

            logger.info(f"✅ Relayed message {moddy_id} from {message.guild.name} to {success_count}/{len(target_channels)} servers")

        except Exception as e:
            logger.error(f"Error relaying interserver message: {e}", exc_info=True)
            # Retire loading et ajoute error
            try:
                await message.remove_reaction("<a:loading:1395047662092550194>", self.bot.user)
                await message.add_reaction("<:undone:1398729502028333218>")
            except:
                pass

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

    async def _relay_message(self, message: discord.Message, target_channels: List[discord.TextChannel],
                            moddy_id: str, content: str, is_moddy_team: bool) -> int:
        """
        Relaie un message vers les salons cibles en utilisant des webhooks
        Returns: Nombre de messages envoyés avec succès
        """
        success_count = 0

        # Prépare le nom d'affichage pour le webhook
        if is_moddy_team:
            username = "Moddy Team"
            avatar_url = self.bot.user.display_avatar.url
        else:
            if self.show_server_name:
                username = f"{message.author.display_name} — {message.guild.name}"
            else:
                username = message.author.display_name

            # Limite la longueur du nom (max 80 caractères pour Discord)
            if len(username) > 80:
                username = username[:77] + "..."

            # Prépare l'avatar
            avatar_url = message.author.display_avatar.url if self.show_avatar else None

        # Prépare le contenu avec l'ID Moddy
        final_content = content

        # Ajoute la réponse si c'est une réponse à un message
        if message.reference and message.reference.message_id:
            try:
                replied_message = await message.channel.fetch_message(message.reference.message_id)
                # Cherche l'ID Moddy du message référencé
                replied_moddy_msg = await self.bot.db.get_interserver_message_by_original(replied_message.id)
                if replied_moddy_msg:
                    reply_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{replied_message.id}"
                    final_content = f"-# <:reply:1444821779444138146> [Reply to message]({reply_link})\n{final_content}"
            except:
                pass

        # Ajoute l'ID Moddy en bas
        final_content += f"\n-# ID: `{moddy_id}`"

        # Gère les mentions si désactivées
        if not self.allowed_mentions:
            allowed_mentions = discord.AllowedMentions.none()
        else:
            allowed_mentions = discord.AllowedMentions.all()

        # Prépare les fichiers (pièces jointes)
        # On ne peut pas réutiliser les mêmes fichiers, on va stocker les URLs
        attachment_links = []
        if message.attachments:
            for attachment in message.attachments[:10]:  # Limite à 10 fichiers
                attachment_links.append(f"[{attachment.filename}]({attachment.url})")

        # Ajoute les liens de fichiers au contenu si présents
        if attachment_links:
            final_content += "\n\n**Attachments:** " + " • ".join(attachment_links)

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
                    'wait': True  # On attend la réponse pour avoir l'ID du message
                }

                # Ajoute le contenu s'il existe
                if final_content:
                    webhook_kwargs['content'] = final_content

                # Ajoute l'avatar s'il existe
                if avatar_url:
                    webhook_kwargs['avatar_url'] = avatar_url

                # Ajoute les embeds s'il y en a
                if embeds:
                    webhook_kwargs['embeds'] = embeds

                # Envoie le message via le webhook
                sent_message = await webhook.send(**webhook_kwargs)

                # Enregistre le message relayé en DB
                await self.bot.db.add_relayed_message(moddy_id, channel.guild.id, channel.id, sent_message.id)

                # Ajoute la réaction verified pour les messages Moddy Team
                if is_moddy_team:
                    await sent_message.add_reaction("<:verified:1398729677601902635>")

                success_count += 1

            except discord.Forbidden:
                logger.warning(f"Missing permissions to send webhook in channel {channel.id}")
            except discord.HTTPException as e:
                logger.error(f"HTTP error sending webhook to channel {channel.id}: {e}")
            except Exception as e:
                logger.error(f"Error sending webhook to channel {channel.id}: {e}", exc_info=True)

        return success_count

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
