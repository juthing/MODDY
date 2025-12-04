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
    """

    MODULE_ID = "welcome"
    MODULE_NAME = "Welcome"
    MODULE_DESCRIPTION = "Envoie un message de bienvenue aux nouveaux membres"
    MODULE_EMOJI = "<:waving_hand:1446127491004760184>"

    def __init__(self, bot, guild_id: int):
        super().__init__(bot, guild_id)
        # Channel configuration
        self.channel_id: Optional[int] = None
        self.send_dm: bool = False  # Send welcome message as DM instead of channel

        # Message configuration
        self.message_template: str = "Bienvenue {user} sur le serveur !"
        self.mention_user: bool = True

        # Embed configuration
        self.embed_enabled: bool = False
        self.embed_title: str = "Bienvenue !"
        self.embed_description: Optional[str] = None  # Separate description for embed (uses message_template if None)
        self.embed_color: int = 0x5865F2
        self.embed_footer: Optional[str] = None
        self.embed_image_url: Optional[str] = None
        self.embed_thumbnail_enabled: bool = True  # Show user's avatar as thumbnail
        self.embed_author_enabled: bool = False  # Show user as embed author

    async def load_config(self, config_data: Dict[str, Any]) -> bool:
        """Charge la configuration depuis la DB"""
        try:
            self.config = config_data

            # Channel configuration
            self.channel_id = config_data.get('channel_id')
            self.send_dm = config_data.get('send_dm', False)

            # Message configuration
            self.message_template = config_data.get('message_template', "Bienvenue {user} sur le serveur !")
            self.mention_user = config_data.get('mention_user', True)

            # Embed configuration
            self.embed_enabled = config_data.get('embed_enabled', False)
            self.embed_title = config_data.get('embed_title', "Bienvenue !")
            self.embed_description = config_data.get('embed_description')
            self.embed_color = config_data.get('embed_color', 0x5865F2)
            self.embed_footer = config_data.get('embed_footer')
            self.embed_image_url = config_data.get('embed_image_url')
            self.embed_thumbnail_enabled = config_data.get('embed_thumbnail_enabled', True)
            self.embed_author_enabled = config_data.get('embed_author_enabled', False)

            # Le module est activé si la config est valide (channel_id présent OU send_dm activé)
            self.enabled = self.channel_id is not None or self.send_dm

            return True
        except Exception as e:
            logger.error(f"Error loading welcome config: {e}")
            return False

    async def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valide la configuration"""
        send_dm = config_data.get('send_dm', False)

        # Si send_dm est désactivé, le channel_id est requis
        if not send_dm:
            if not config_data.get('channel_id'):
                return False, "Un salon de bienvenue est requis si l'envoi en DM est désactivé"

        # Vérifie que le salon existe si spécifié (et send_dm désactivé)
        if 'channel_id' in config_data and config_data['channel_id'] and not send_dm:
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

                if config_data.get('embed_enabled', False) and not perms.embed_links:
                    return False, f"Je n'ai pas la permission d'envoyer des embeds dans {channel.mention}"

            except Exception as e:
                return False, f"Erreur de validation : {str(e)}"

        # Vérifie que le message template est valide
        if 'message_template' in config_data:
            template = config_data['message_template']
            if not template or len(template.strip()) == 0:
                return False, "Le message de bienvenue ne peut pas être vide"

            if len(template) > 2000:
                return False, "Le message de bienvenue ne peut pas dépasser 2000 caractères"

        # Vérifie la couleur de l'embed
        if 'embed_color' in config_data:
            color = config_data['embed_color']
            if not isinstance(color, int) or color < 0 or color > 0xFFFFFF:
                return False, "La couleur de l'embed doit être un nombre hexadécimal valide (0x000000 - 0xFFFFFF)"

        # Vérifie l'URL de l'image si fournie
        if 'embed_image_url' in config_data and config_data['embed_image_url']:
            url = config_data['embed_image_url']
            if not url.startswith(('http://', 'https://')):
                return False, "L'URL de l'image doit commencer par http:// ou https://"

        # Vérifie les longueurs des champs d'embed
        if 'embed_title' in config_data and len(config_data['embed_title']) > 256:
            return False, "Le titre de l'embed ne peut pas dépasser 256 caractères"

        if 'embed_description' in config_data and config_data['embed_description']:
            if len(config_data['embed_description']) > 4096:
                return False, "La description de l'embed ne peut pas dépasser 4096 caractères"

        if 'embed_footer' in config_data and config_data['embed_footer']:
            if len(config_data['embed_footer']) > 2048:
                return False, "Le footer de l'embed ne peut pas dépasser 2048 caractères"

        return True, None

    def get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        return {
            # Channel configuration
            'channel_id': None,
            'send_dm': False,

            # Message configuration
            'message_template': "Bienvenue {user} sur le serveur !",
            'mention_user': True,

            # Embed configuration
            'embed_enabled': False,
            'embed_title': "Bienvenue !",
            'embed_description': None,
            'embed_color': 0x5865F2,
            'embed_footer': None,
            'embed_image_url': None,
            'embed_thumbnail_enabled': True,
            'embed_author_enabled': False
        }

    async def on_member_join(self, member: discord.Member):
        """
        Appelé quand un membre rejoint le serveur
        Cette méthode sera appelée par un event listener dans le cog
        """
        if not self.enabled:
            return

        try:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                return

            # Determine where to send the message
            if self.send_dm:
                destination = member
            else:
                if not self.channel_id:
                    logger.warning(f"Welcome module enabled but no channel_id set for guild {self.guild_id}")
                    return

                channel = guild.get_channel(self.channel_id)
                if not channel or not isinstance(channel, discord.TextChannel):
                    logger.warning(f"Welcome channel {self.channel_id} not found or not a text channel")
                    return
                destination = channel

            # Prepare message variables
            user_mention = member.mention if self.mention_user else member.name
            message_content = self.message_template.format(
                user=user_mention,
                username=member.name,
                server=guild.name,
                member_count=guild.member_count
            )

            # Send the message
            if self.embed_enabled:
                # Use embed_description if set, otherwise use message_content
                embed_desc = self.embed_description if self.embed_description else message_content
                embed_desc = embed_desc.format(
                    user=user_mention,
                    username=member.name,
                    server=guild.name,
                    member_count=guild.member_count
                )

                embed = discord.Embed(
                    title=self.embed_title,
                    description=embed_desc,
                    color=self.embed_color
                )

                # Add author if enabled
                if self.embed_author_enabled:
                    embed.set_author(
                        name=member.display_name,
                        icon_url=member.display_avatar.url
                    )

                # Add thumbnail if enabled
                if self.embed_thumbnail_enabled:
                    embed.set_thumbnail(url=member.display_avatar.url)

                # Add image if URL provided
                if self.embed_image_url:
                    embed.set_image(url=self.embed_image_url)

                # Add footer if provided
                if self.embed_footer:
                    footer_text = self.embed_footer.format(
                        user=user_mention,
                        username=member.name,
                        server=guild.name,
                        member_count=guild.member_count
                    )
                    embed.set_footer(text=footer_text)

                # Send embed (if not using embed_description, send message_content as regular text)
                if self.embed_description:
                    await destination.send(embed=embed)
                else:
                    await destination.send(content=message_content if not self.send_dm else None, embed=embed)
            else:
                await destination.send(message_content)

            logger.info(f"✅ Welcome message sent for {member.name} in guild {self.guild_id} ({'DM' if self.send_dm else f'channel {self.channel_id}'})")

        except discord.Forbidden:
            logger.warning(f"Missing permissions to send welcome message in guild {self.guild_id}")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}", exc_info=True)
