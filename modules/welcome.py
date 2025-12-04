"""
Module Welcome - Message de bienvenue pour les nouveaux membres
"""

import discord
from typing import Dict, Any, Optional
import logging

from modules.module_manager import ModuleBase

logger = logging.getLogger('moddy.modules.welcome')


class WelcomeModule(ModuleBase):
    """
    Module de messages de bienvenue
    Envoie un message personnalisé quand un nouveau membre rejoint le serveur
    Supporte l'envoi simultané de messages en DM et dans un salon
    """

    MODULE_ID = "welcome"
    MODULE_NAME = "Welcome"
    MODULE_DESCRIPTION = "Envoie un message de bienvenue aux nouveaux membres"
    MODULE_EMOJI = "<:waving_hand:1446127491004760184>"

    def __init__(self, bot, guild_id: int):
        super().__init__(bot, guild_id)

        # === CHANNEL WELCOME (Public message in a channel) ===
        self.channel_enabled: bool = False
        self.channel_id: Optional[int] = None
        self.channel_message_template: str = "Bienvenue {user} sur le serveur !"
        self.channel_mention_user: bool = True
        self.channel_embed_enabled: bool = False
        self.channel_embed_title: str = "Bienvenue !"
        self.channel_embed_description: Optional[str] = None
        self.channel_embed_color: int = 0x5865F2
        self.channel_embed_footer: Optional[str] = None
        self.channel_embed_image_url: Optional[str] = None
        self.channel_embed_thumbnail_enabled: bool = True
        self.channel_embed_author_enabled: bool = False

        # === DM WELCOME (Private message) ===
        self.dm_enabled: bool = False
        self.dm_message_template: str = "Bienvenue sur le serveur {server} !"
        self.dm_mention_user: bool = False  # Mentions don't work in DMs
        self.dm_embed_enabled: bool = False
        self.dm_embed_title: str = "Bienvenue !"
        self.dm_embed_description: Optional[str] = None
        self.dm_embed_color: int = 0x5865F2
        self.dm_embed_footer: Optional[str] = None
        self.dm_embed_image_url: Optional[str] = None
        self.dm_embed_thumbnail_enabled: bool = True
        self.dm_embed_author_enabled: bool = False

    async def load_config(self, config_data: Dict[str, Any]) -> bool:
        """Charge la configuration depuis la DB"""
        try:
            self.config = config_data

            # === CHANNEL WELCOME CONFIGURATION ===
            self.channel_enabled = config_data.get('channel_enabled', False)
            self.channel_id = config_data.get('channel_id')
            self.channel_message_template = config_data.get('channel_message_template', "Bienvenue {user} sur le serveur !")
            self.channel_mention_user = config_data.get('channel_mention_user', True)
            self.channel_embed_enabled = config_data.get('channel_embed_enabled', False)
            self.channel_embed_title = config_data.get('channel_embed_title', "Bienvenue !")
            self.channel_embed_description = config_data.get('channel_embed_description')
            self.channel_embed_color = config_data.get('channel_embed_color', 0x5865F2)
            self.channel_embed_footer = config_data.get('channel_embed_footer')
            self.channel_embed_image_url = config_data.get('channel_embed_image_url')
            self.channel_embed_thumbnail_enabled = config_data.get('channel_embed_thumbnail_enabled', True)
            self.channel_embed_author_enabled = config_data.get('channel_embed_author_enabled', False)

            # === DM WELCOME CONFIGURATION ===
            self.dm_enabled = config_data.get('dm_enabled', False)
            self.dm_message_template = config_data.get('dm_message_template', "Bienvenue sur le serveur {server} !")
            self.dm_mention_user = config_data.get('dm_mention_user', False)
            self.dm_embed_enabled = config_data.get('dm_embed_enabled', False)
            self.dm_embed_title = config_data.get('dm_embed_title', "Bienvenue !")
            self.dm_embed_description = config_data.get('dm_embed_description')
            self.dm_embed_color = config_data.get('dm_embed_color', 0x5865F2)
            self.dm_embed_footer = config_data.get('dm_embed_footer')
            self.dm_embed_image_url = config_data.get('dm_embed_image_url')
            self.dm_embed_thumbnail_enabled = config_data.get('dm_embed_thumbnail_enabled', True)
            self.dm_embed_author_enabled = config_data.get('dm_embed_author_enabled', False)

            # Module is enabled if at least one of the welcome types is enabled
            self.enabled = self.channel_enabled or self.dm_enabled

            return True
        except Exception as e:
            logger.error(f"Error loading welcome config: {e}")
            return False

    async def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valide la configuration"""
        channel_enabled = config_data.get('channel_enabled', False)
        dm_enabled = config_data.get('dm_enabled', False)

        # At least one welcome type must be enabled
        if not channel_enabled and not dm_enabled:
            return False, "Au moins un type de message de bienvenue doit être activé (salon ou DM)"

        # === VALIDATE CHANNEL WELCOME ===
        if channel_enabled:
            # Channel ID is required if channel welcome is enabled
            if not config_data.get('channel_id'):
                return False, "Un salon est requis pour le message de bienvenue public"

            # Verify channel exists and bot has permissions
            try:
                guild = self.bot.get_guild(self.guild_id)
                if not guild:
                    return False, "Serveur introuvable"

                channel = guild.get_channel(config_data['channel_id'])
                if not channel:
                    return False, "Salon introuvable"

                if not isinstance(channel, discord.TextChannel):
                    return False, "Le salon doit être un salon textuel"

                # Check permissions
                perms = channel.permissions_for(guild.me)
                if not perms.send_messages:
                    return False, f"Je n'ai pas la permission d'envoyer des messages dans {channel.mention}"

                if config_data.get('channel_embed_enabled', False) and not perms.embed_links:
                    return False, f"Je n'ai pas la permission d'envoyer des embeds dans {channel.mention}"

            except Exception as e:
                return False, f"Erreur de validation du salon : {str(e)}"

            # Validate channel message template
            channel_template = config_data.get('channel_message_template', '')
            if not channel_template or len(channel_template.strip()) == 0:
                return False, "Le message de bienvenue public ne peut pas être vide"
            if len(channel_template) > 2000:
                return False, "Le message de bienvenue public ne peut pas dépasser 2000 caractères"

            # Validate channel embed settings
            if config_data.get('channel_embed_enabled'):
                if 'channel_embed_title' in config_data and len(config_data['channel_embed_title']) > 256:
                    return False, "Le titre de l'embed public ne peut pas dépasser 256 caractères"
                if 'channel_embed_description' in config_data and config_data['channel_embed_description']:
                    if len(config_data['channel_embed_description']) > 4096:
                        return False, "La description de l'embed public ne peut pas dépasser 4096 caractères"
                if 'channel_embed_footer' in config_data and config_data['channel_embed_footer']:
                    if len(config_data['channel_embed_footer']) > 2048:
                        return False, "Le footer de l'embed public ne peut pas dépasser 2048 caractères"
                if 'channel_embed_image_url' in config_data and config_data['channel_embed_image_url']:
                    url = config_data['channel_embed_image_url']
                    if not url.startswith(('http://', 'https://')):
                        return False, "L'URL de l'image publique doit commencer par http:// ou https://"
                if 'channel_embed_color' in config_data:
                    color = config_data['channel_embed_color']
                    if not isinstance(color, int) or color < 0 or color > 0xFFFFFF:
                        return False, "La couleur de l'embed public est invalide"

        # === VALIDATE DM WELCOME ===
        if dm_enabled:
            # Validate DM message template
            dm_template = config_data.get('dm_message_template', '')
            if not dm_template or len(dm_template.strip()) == 0:
                return False, "Le message de bienvenue privé ne peut pas être vide"
            if len(dm_template) > 2000:
                return False, "Le message de bienvenue privé ne peut pas dépasser 2000 caractères"

            # Validate DM embed settings
            if config_data.get('dm_embed_enabled'):
                if 'dm_embed_title' in config_data and len(config_data['dm_embed_title']) > 256:
                    return False, "Le titre de l'embed privé ne peut pas dépasser 256 caractères"
                if 'dm_embed_description' in config_data and config_data['dm_embed_description']:
                    if len(config_data['dm_embed_description']) > 4096:
                        return False, "La description de l'embed privé ne peut pas dépasser 4096 caractères"
                if 'dm_embed_footer' in config_data and config_data['dm_embed_footer']:
                    if len(config_data['dm_embed_footer']) > 2048:
                        return False, "Le footer de l'embed privé ne peut pas dépasser 2048 caractères"
                if 'dm_embed_image_url' in config_data and config_data['dm_embed_image_url']:
                    url = config_data['dm_embed_image_url']
                    if not url.startswith(('http://', 'https://')):
                        return False, "L'URL de l'image privée doit commencer par http:// ou https://"
                if 'dm_embed_color' in config_data:
                    color = config_data['dm_embed_color']
                    if not isinstance(color, int) or color < 0 or color > 0xFFFFFF:
                        return False, "La couleur de l'embed privé est invalide"

        return True, None

    def get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        return {
            # === CHANNEL WELCOME (Public message in a channel) ===
            'channel_enabled': False,
            'channel_id': None,
            'channel_message_template': "Bienvenue {user} sur le serveur !",
            'channel_mention_user': True,
            'channel_embed_enabled': False,
            'channel_embed_title': "Bienvenue !",
            'channel_embed_description': None,
            'channel_embed_color': 0x5865F2,
            'channel_embed_footer': None,
            'channel_embed_image_url': None,
            'channel_embed_thumbnail_enabled': True,
            'channel_embed_author_enabled': False,

            # === DM WELCOME (Private message) ===
            'dm_enabled': False,
            'dm_message_template': "Bienvenue sur le serveur {server} !",
            'dm_mention_user': False,
            'dm_embed_enabled': False,
            'dm_embed_title': "Bienvenue !",
            'dm_embed_description': None,
            'dm_embed_color': 0x5865F2,
            'dm_embed_footer': None,
            'dm_embed_image_url': None,
            'dm_embed_thumbnail_enabled': True,
            'dm_embed_author_enabled': False
        }

    async def on_member_join(self, member: discord.Member):
        """
        Appelé quand un membre rejoint le serveur
        Envoie les messages de bienvenue configurés (DM et/ou salon)
        """
        if not self.enabled:
            return

        try:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                return

            # Send channel welcome if enabled
            if self.channel_enabled and self.channel_id:
                await self._send_channel_welcome(member, guild)

            # Send DM welcome if enabled
            if self.dm_enabled:
                await self._send_dm_welcome(member, guild)

        except Exception as e:
            logger.error(f"Error in welcome module for guild {self.guild_id}: {e}", exc_info=True)

    async def _send_channel_welcome(self, member: discord.Member, guild: discord.Guild):
        """Send welcome message in the configured channel"""
        try:
            channel = guild.get_channel(self.channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                logger.warning(f"Welcome channel {self.channel_id} not found or not a text channel")
                return

            # Prepare message variables
            user_mention = member.mention if self.channel_mention_user else member.name
            message_content = self.channel_message_template.format(
                user=user_mention,
                username=member.name,
                server=guild.name,
                member_count=guild.member_count
            )

            # Send with or without embed
            if self.channel_embed_enabled:
                embed = self._create_embed(
                    member=member,
                    guild=guild,
                    title=self.channel_embed_title,
                    description=self.channel_embed_description,
                    color=self.channel_embed_color,
                    footer=self.channel_embed_footer,
                    image_url=self.channel_embed_image_url,
                    thumbnail_enabled=self.channel_embed_thumbnail_enabled,
                    author_enabled=self.channel_embed_author_enabled,
                    default_description=message_content,
                    mention_user=self.channel_mention_user
                )

                # Send with content if no custom embed description
                if self.channel_embed_description:
                    await channel.send(embed=embed)
                else:
                    await channel.send(content=message_content, embed=embed)
            else:
                await channel.send(message_content)

            logger.info(f"✅ Channel welcome sent for {member.name} in channel {self.channel_id} (guild {self.guild_id})")

        except discord.Forbidden:
            logger.warning(f"Missing permissions to send channel welcome in guild {self.guild_id}")
        except Exception as e:
            logger.error(f"Error sending channel welcome: {e}", exc_info=True)

    async def _send_dm_welcome(self, member: discord.Member, guild: discord.Guild):
        """Send welcome message as DM to the member"""
        try:
            # Prepare message variables (no mention in DMs)
            message_content = self.dm_message_template.format(
                user=member.name,
                username=member.name,
                server=guild.name,
                member_count=guild.member_count
            )

            # Send with or without embed
            if self.dm_embed_enabled:
                embed = self._create_embed(
                    member=member,
                    guild=guild,
                    title=self.dm_embed_title,
                    description=self.dm_embed_description,
                    color=self.dm_embed_color,
                    footer=self.dm_embed_footer,
                    image_url=self.dm_embed_image_url,
                    thumbnail_enabled=self.dm_embed_thumbnail_enabled,
                    author_enabled=self.dm_embed_author_enabled,
                    default_description=message_content,
                    mention_user=False  # Never mention in DMs
                )

                # Send with content if no custom embed description
                if self.dm_embed_description:
                    await member.send(embed=embed)
                else:
                    await member.send(content=message_content, embed=embed)
            else:
                await member.send(message_content)

            logger.info(f"✅ DM welcome sent to {member.name} (guild {self.guild_id})")

        except discord.Forbidden:
            logger.warning(f"Cannot send DM welcome to {member.name} - DMs disabled")
        except Exception as e:
            logger.error(f"Error sending DM welcome: {e}", exc_info=True)

    def _create_embed(
        self,
        member: discord.Member,
        guild: discord.Guild,
        title: str,
        description: Optional[str],
        color: int,
        footer: Optional[str],
        image_url: Optional[str],
        thumbnail_enabled: bool,
        author_enabled: bool,
        default_description: str,
        mention_user: bool
    ) -> discord.Embed:
        """Create an embed for welcome message"""
        # Use custom description or default message content
        user_ref = member.mention if mention_user else member.name
        embed_desc = description if description else default_description
        embed_desc = embed_desc.format(
            user=user_ref,
            username=member.name,
            server=guild.name,
            member_count=guild.member_count
        )

        embed = discord.Embed(
            title=title,
            description=embed_desc,
            color=color
        )

        # Add author if enabled
        if author_enabled:
            embed.set_author(
                name=member.display_name,
                icon_url=member.display_avatar.url
            )

        # Add thumbnail if enabled
        if thumbnail_enabled:
            embed.set_thumbnail(url=member.display_avatar.url)

        # Add image if URL provided
        if image_url:
            embed.set_image(url=image_url)

        # Add footer if provided
        if footer:
            footer_text = footer.format(
                user=user_ref,
                username=member.name,
                server=guild.name,
                member_count=guild.member_count
            )
            embed.set_footer(text=footer_text)

        return embed
