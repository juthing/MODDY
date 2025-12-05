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

# IDs des salons de logs staff
ENGLISH_LOG_CHANNEL_ID = 1446555149031047388
FRENCH_LOG_CHANNEL_ID = 1446555476044284045


class InterServerModule(ModuleBase):
    """
    Module de communication inter-serveurs
    Connecte des salons de différents serveurs pour créer un portail de communication
    """

    MODULE_ID = "interserver"
    MODULE_NAME = "Inter-Server"
    MODULE_DESCRIPTION = "Connecte plusieurs serveurs via des salons dédiés"
    MODULE_EMOJI = "<:groups:1446127489842806967>"

    def __init__(self, bot, guild_id: int):
        super().__init__(bot, guild_id)
        self.channel_id: Optional[int] = None
        self.interserver_type: str = "english"  # "english" or "french"
        self.show_server_name: bool = True
        self.show_avatar: bool = True
        self.allowed_mentions: bool = False

        # Cooldown tracking (user_id -> timestamp)
        self.cooldowns: Dict[int, datetime] = {}

        # Sticky message tracking (channel_id -> message_id)
        self.sticky_message_id: Optional[int] = None

    async def load_config(self, config_data: Dict[str, Any]) -> bool:
        """Charge la configuration depuis la DB"""
        try:
            self.config = config_data
            self.channel_id = config_data.get('channel_id')
            self.interserver_type = config_data.get('interserver_type', 'english')
            self.show_server_name = config_data.get('show_server_name', True)
            self.show_avatar = config_data.get('show_avatar', True)
            self.allowed_mentions = config_data.get('allowed_mentions', False)
            self.sticky_message_id = config_data.get('sticky_message_id')

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
            'interserver_type': 'english',
            'show_server_name': True,
            'show_avatar': True,
            'allowed_mentions': False,
            'sticky_message_id': None
        }

    def get_required_fields(self) -> List[str]:
        """Retourne la liste des champs obligatoires"""
        return ['channel_id', 'interserver_type']

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

    async def _get_all_interserver_channels(self) -> List[discord.TextChannel]:
        """
        Récupère tous les salons inter-serveur actifs du même type
        """
        channels = []

        # Parcourt tous les serveurs où le bot est présent
        for guild in self.bot.guilds:
            # Récupère le module inter-serveur pour ce serveur
            module = await self.bot.module_manager.get_module_instance(
                guild.id,
                'interserver'
            )

            # Si le module est actif et configuré, et du même type
            if module and module.enabled and module.channel_id:
                # Vérifie que c'est le même type d'inter-serveur
                if module.interserver_type == self.interserver_type:
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

        # Prépare le contenu de base avec l'ID Moddy
        base_content = content

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
                # Récupère le module inter-serveur du serveur cible pour utiliser ses options d'affichage
                target_module = await self.bot.module_manager.get_module_instance(
                    channel.guild.id,
                    'interserver'
                )

                if not target_module:
                    logger.warning(f"No interserver module for guild {channel.guild.id}")
                    continue

                # Vérifie si l'auteur est banni ou timeout sur ce serveur (sauf pour Moddy Team)
                if not is_moddy_team:
                    try:
                        # Vérifie si l'auteur est membre du serveur cible
                        target_member = channel.guild.get_member(message.author.id)

                        if target_member:
                            # Vérifie si le membre est en timeout
                            if target_member.timed_out_until and target_member.timed_out_until > discord.utils.utcnow():
                                logger.info(f"Skipping message relay to {channel.guild.name} - Author {message.author.id} is timed out")
                                continue

                        # Vérifie si l'auteur est banni (coûteux, donc on fait une vérification rapide)
                        try:
                            await channel.guild.fetch_ban(discord.Object(id=message.author.id))
                            # Si pas d'exception, l'utilisateur est banni
                            logger.info(f"Skipping message relay to {channel.guild.name} - Author {message.author.id} is banned")
                            continue
                        except discord.NotFound:
                            # L'utilisateur n'est pas banni, on continue
                            pass

                    except Exception as e:
                        logger.debug(f"Error checking ban/timeout status: {e}")

                # Prépare le nom d'affichage selon les préférences du serveur CIBLE
                if is_moddy_team:
                    username = "Moddy Team"
                    avatar_url = self.bot.user.display_avatar.url
                else:
                    if target_module.show_server_name:
                        username = f"{message.author.display_name} — {message.guild.name}"
                    else:
                        username = message.author.display_name

                    # Limite la longueur du nom (max 80 caractères pour Discord)
                    if len(username) > 80:
                        username = username[:77] + "..."

                    # Prépare l'avatar selon les préférences du serveur CIBLE
                    avatar_url = message.author.display_avatar.url if target_module.show_avatar else None

                # Prépare le contenu pour ce serveur spécifique
                final_content = base_content

                # Ajoute la réponse si c'est une réponse à un message
                if message.reference and message.reference.message_id:
                    try:
                        # Cherche l'ID Moddy du message référencé
                        replied_moddy_msg = await self.bot.db.get_interserver_message_by_original(message.reference.message_id)
                        if replied_moddy_msg:
                            # Cherche le message relayé dans le serveur cible
                            target_relayed = None
                            for relayed in replied_moddy_msg.get('relayed_messages', []):
                                if relayed['guild_id'] == channel.guild.id:
                                    target_relayed = relayed
                                    break

                            if target_relayed:
                                # Lien vers le message dans le serveur cible
                                reply_link = f"https://discord.com/channels/{target_relayed['guild_id']}/{target_relayed['channel_id']}/{target_relayed['message_id']}"
                            else:
                                # Fallback vers le message original si pas trouvé dans ce serveur
                                reply_link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.reference.message_id}"

                            final_content = f"-# <:reply:1444821779444138146> [Reply to message]({reply_link})\n{final_content}"
                    except Exception as e:
                        logger.debug(f"Could not add reply link: {e}")

                # Ajoute l'ID Moddy en bas
                final_content += f"\n-# ID: `{moddy_id}`"

                # Gère les mentions selon les préférences du serveur CIBLE
                if not target_module.allowed_mentions:
                    allowed_mentions = discord.AllowedMentions.none()
                else:
                    allowed_mentions = discord.AllowedMentions.all()

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

    async def _manage_sticky_message(self, channel: discord.TextChannel):
        """
        Gère le sticky message en bas du salon inter-serveur
        Supprime l'ancien et en crée un nouveau
        """
        try:
            from utils.i18n import t

            # Détermine la langue du sticky message selon le type d'inter-serveur
            if self.interserver_type == "french":
                sticky_title = t('modules.interserver.sticky_message.french_title', locale='fr')
                sticky_body = t('modules.interserver.sticky_message.french_body', locale='fr')
            else:
                sticky_title = t('modules.interserver.sticky_message.english_title', locale='en-US')
                sticky_body = t('modules.interserver.sticky_message.english_body', locale='en-US')

            # Crée le sticky message avec Components V2
            from discord.ui import LayoutView, Container, TextDisplay

            class StickyComponents(discord.ui.LayoutView):
                container1 = discord.ui.Container(
                    discord.ui.TextDisplay(content=sticky_title),
                    discord.ui.TextDisplay(content=sticky_body),
                )

            view = StickyComponents()

            # Supprime l'ancien sticky message s'il existe
            if self.sticky_message_id:
                try:
                    old_sticky = await channel.fetch_message(self.sticky_message_id)
                    await old_sticky.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

            # Envoie le nouveau sticky message
            sticky_msg = await channel.send(view=view)
            self.sticky_message_id = sticky_msg.id

            # Sauvegarde l'ID en DB pour persistence
            self.config['sticky_message_id'] = sticky_msg.id
            await self.bot.module_manager.save_module_config(
                self.guild_id,
                'interserver',
                self.config
            )

        except Exception as e:
            logger.error(f"Error managing sticky message: {e}", exc_info=True)

    async def _send_staff_log(self, message: discord.Message, moddy_id: str, is_moddy_team: bool, success_count: int, total_count: int):
        """
        Envoie un log du message au salon staff approprié
        """
        try:
            # Détermine le salon de log selon le type d'inter-serveur
            log_channel_id = FRENCH_LOG_CHANNEL_ID if self.interserver_type == "french" else ENGLISH_LOG_CHANNEL_ID
            log_channel = self.bot.get_channel(log_channel_id)

            if not log_channel:
                logger.warning(f"Could not find log channel {log_channel_id}")
                return

            # Prépare les informations (SANS mentions pour éviter les pings)
            author_info = f"{message.author.name} (`{message.author.id}`)"
            server_info = f"{message.guild.name} (`{message.guild.id}`)"
            content_preview = message.content[:500] if message.content else "*No content*"

            # Crée le message de log avec Components V2
            from discord import ui as discord_ui

            class StaffLogView(discord_ui.LayoutView):
                def __init__(self, bot, moddy_id: str, message: discord.Message, author_info: str, server_info: str, content_preview: str, success_count: int, total_count: int, is_moddy_team: bool):
                    super().__init__()
                    self.bot = bot
                    self.moddy_id = moddy_id
                    self.message = message
                    self.claimed_by = None
                    self.author_info = author_info
                    self.server_info = server_info
                    self.content_preview = content_preview
                    self.success_count = success_count
                    self.total_count = total_count
                    self.is_moddy_team = is_moddy_team

                    self._build_view()

                def _build_view(self):
                    """Construit la vue avec containers et boutons"""
                    self.clear_items()

                    # Container avec les informations
                    container = discord_ui.Container(
                        discord_ui.TextDisplay(content=f"### <:groups:1446127489842806967> New Inter-Server Message"),
                        discord_ui.TextDisplay(content=f"**Moddy ID:** `{self.moddy_id}`\n**Author:** {self.author_info}\n**Server:** {self.server_info}\n**Relayed:** {self.success_count}/{self.total_count} servers\n**Moddy Team:** {'✅ Yes' if self.is_moddy_team else '❌ No'}\n**Time:** <t:{int(datetime.now(timezone.utc).timestamp())}:R>\n{f'**Claimed by:** {self.claimed_by.name}' if self.claimed_by else ''}\n\n**Content:**\n{self.content_preview}"),
                    )
                    self.add_item(container)

                    # ActionRow avec les boutons
                    button_row = discord_ui.ActionRow()

                    # Delete button
                    delete_btn = discord_ui.Button(
                        label="Delete",
                        style=discord.ButtonStyle.danger,
                        emoji="🗑️",
                        custom_id="delete_btn"
                    )
                    delete_btn.callback = self.on_delete
                    button_row.add_item(delete_btn)

                    # Invite Link button
                    invite_btn = discord_ui.Button(
                        label="Invite Link",
                        style=discord.ButtonStyle.secondary,
                        emoji="🔗",
                        custom_id="invite_btn"
                    )
                    invite_btn.callback = self.on_invite
                    button_row.add_item(invite_btn)

                    # Claim button
                    claim_btn = discord_ui.Button(
                        label="Claim",
                        style=discord.ButtonStyle.primary,
                        emoji="👋",
                        custom_id="claim_btn",
                        disabled=self.claimed_by is not None
                    )
                    claim_btn.callback = self.on_claim
                    button_row.add_item(claim_btn)

                    # Processed button
                    processed_btn = discord_ui.Button(
                        label="Processed",
                        style=discord.ButtonStyle.success,
                        emoji="✅",
                        custom_id="processed_btn",
                        disabled=self.claimed_by is None
                    )
                    processed_btn.callback = self.on_processed
                    button_row.add_item(processed_btn)

                    self.add_item(button_row)

                async def on_delete(self, interaction: discord.Interaction):
                    """Supprime le message inter-serveur"""
                    # Vérifie les permissions
                    from utils.staff_permissions import staff_permissions, StaffRole
                    user_roles = await staff_permissions.get_user_roles(interaction.user.id)

                    allowed_roles = [StaffRole.Dev, StaffRole.Manager, StaffRole.Supervisor_Mod, StaffRole.Moderator]
                    if not any(role in allowed_roles for role in user_roles):
                        await interaction.response.send_message(
                            "You don't have permission to delete inter-server messages.",
                            ephemeral=True
                        )
                        return

                    # Supprime le message
                    msg_data = await self.bot.db.get_interserver_message(self.moddy_id)
                    if not msg_data:
                        await interaction.response.send_message(
                            "Message not found in database.",
                            ephemeral=True
                        )
                        return

                    # Supprime tous les messages relayés
                    deleted_count = 0
                    for relayed in msg_data.get('relayed_messages', []):
                        try:
                            guild = self.bot.get_guild(relayed['guild_id'])
                            if guild:
                                channel = guild.get_channel(relayed['channel_id'])
                                if channel:
                                    msg = await channel.fetch_message(relayed['message_id'])
                                    await msg.delete()
                                    deleted_count += 1
                        except:
                            pass

                    # Marque comme supprimé en DB
                    await self.bot.db.delete_interserver_message(self.moddy_id)

                    # Met à jour le log
                    self.clear_items()
                    container = discord_ui.Container(
                        discord_ui.TextDisplay(content=f"### <:delete:1401600770431909939> Message Deleted"),
                        discord_ui.TextDisplay(content=f"**Moddy ID:** `{self.moddy_id}`\n**Deleted by:** {interaction.user.name}\n**Messages deleted:** {deleted_count}"),
                    )
                    self.add_item(container)

                    await interaction.response.edit_message(view=self)

                async def on_invite(self, interaction: discord.Interaction):
                    """Crée un lien d'invitation vers le serveur"""
                    # Vérifie les permissions
                    from utils.staff_permissions import staff_permissions, StaffRole
                    user_roles = await staff_permissions.get_user_roles(interaction.user.id)

                    allowed_roles = [StaffRole.Dev, StaffRole.Manager, StaffRole.Supervisor_Mod, StaffRole.Moderator]
                    if not any(role in allowed_roles for role in user_roles):
                        await interaction.response.send_message(
                            "You don't have permission to get invite links.",
                            ephemeral=True
                        )
                        return

                    # Récupère le serveur
                    guild = self.message.guild
                    if not guild:
                        await interaction.response.send_message(
                            "Could not find the server.",
                            ephemeral=True
                        )
                        return

                    # Crée un lien d'invitation
                    try:
                        invite_channel = guild.system_channel or self.message.channel
                        invite = await invite_channel.create_invite(
                            max_age=604800,  # 7 jours
                            max_uses=5,
                            reason=f"Staff invite requested by {interaction.user}"
                        )

                        await interaction.response.send_message(
                            f"**Invite link for {guild.name}:**\n{invite.url}",
                            ephemeral=True
                        )
                    except Exception as e:
                        await interaction.response.send_message(
                            f"Failed to create invite: {str(e)}",
                            ephemeral=True
                        )

                async def on_claim(self, interaction: discord.Interaction):
                    """Claim le message pour investigation"""
                    # Vérifie les permissions
                    from utils.staff_permissions import staff_permissions, StaffRole
                    user_roles = await staff_permissions.get_user_roles(interaction.user.id)

                    allowed_roles = [StaffRole.Dev, StaffRole.Manager, StaffRole.Supervisor_Mod, StaffRole.Moderator]
                    if not any(role in allowed_roles for role in user_roles):
                        await interaction.response.send_message(
                            "You don't have permission to claim messages.",
                            ephemeral=True
                        )
                        return

                    self.claimed_by = interaction.user
                    self._build_view()
                    await interaction.response.edit_message(view=self)

                async def on_processed(self, interaction: discord.Interaction):
                    """Marque comme traité avec un formulaire"""
                    # Ouvre un modal pour les actions prises
                    from cogs.interserver_commands import ProcessedModal
                    modal = ProcessedModal(self.moddy_id)
                    await interaction.response.send_modal(modal)

            # Envoie le log
            log_view = StaffLogView(self.bot, moddy_id, message, author_info, server_info, content_preview, success_count, total_count, is_moddy_team)
            await log_channel.send(view=log_view, allowed_mentions=discord.AllowedMentions.none())

        except Exception as e:
            logger.error(f"Error sending staff log: {e}", exc_info=True)

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

                # Gère le sticky message pour ce salon
                await self._manage_sticky_message(message.channel)
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

            # Gère le sticky message pour ce salon et tous les salons cibles
            await self._manage_sticky_message(message.channel)

            # Gère le sticky message pour tous les salons qui ont reçu le message
            for channel in target_channels:
                try:
                    target_module = await self.bot.module_manager.get_module_instance(
                        channel.guild.id,
                        'interserver'
                    )
                    if target_module:
                        await target_module._manage_sticky_message(channel)
                except Exception as e:
                    logger.debug(f"Error managing sticky message for {channel.guild.name}: {e}")

            # Envoie le log au salon staff approprié
            await self._send_staff_log(message, moddy_id, is_moddy_team_message, success_count, len(target_channels))

            logger.info(f"✅ Relayed message {moddy_id} from {message.guild.name} to {success_count}/{len(target_channels)} servers")

        except Exception as e:
            logger.error(f"Error relaying interserver message: {e}", exc_info=True)
            # Retire loading et ajoute error
            try:
                await message.remove_reaction("<a:loading:1395047662092550194>", self.bot.user)
                await message.add_reaction("<:undone:1398729502028333218>")
            except:
                pass
