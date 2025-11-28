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
    MODULE_EMOJI = "👋"

    def __init__(self, bot, guild_id: int):
        super().__init__(bot, guild_id)
        self.channel_id: Optional[int] = None
        self.message_template: str = "Bienvenue {user} sur le serveur !"
        self.embed_enabled: bool = False
        self.embed_color: int = 0x5865F2
        self.embed_title: str = "Bienvenue !"
        self.mention_user: bool = True

    async def load_config(self, config_data: Dict[str, Any]) -> bool:
        """Charge la configuration depuis la DB"""
        try:
            self.config = config_data
            self.enabled = config_data.get('enabled', False)
            self.channel_id = config_data.get('channel_id')
            self.message_template = config_data.get('message_template', "Bienvenue {user} sur le serveur !")
            self.embed_enabled = config_data.get('embed_enabled', False)
            self.embed_color = config_data.get('embed_color', 0x5865F2)
            self.embed_title = config_data.get('embed_title', "Bienvenue !")
            self.mention_user = config_data.get('mention_user', True)

            return True
        except Exception as e:
            logger.error(f"Error loading welcome config: {e}")
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

        return True, None

    def get_default_config(self) -> Dict[str, Any]:
        """Retourne la configuration par défaut"""
        return {
            'enabled': False,
            'channel_id': None,
            'message_template': "Bienvenue {user} sur le serveur !",
            'embed_enabled': False,
            'embed_color': 0x5865F2,
            'embed_title': "Bienvenue !",
            'mention_user': True
        }

    async def on_member_join(self, member: discord.Member):
        """
        Appelé quand un membre rejoint le serveur
        Cette méthode sera appelée par un event listener dans le cog
        """
        if not self.enabled or not self.channel_id:
            return

        try:
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                return

            channel = guild.get_channel(self.channel_id)
            if not channel or not isinstance(channel, discord.TextChannel):
                logger.warning(f"Welcome channel {self.channel_id} not found or not a text channel")
                return

            # Prépare le message
            user_mention = member.mention if self.mention_user else member.name
            message_content = self.message_template.format(
                user=user_mention,
                username=member.name,
                server=guild.name,
                member_count=guild.member_count
            )

            # Envoie le message
            if self.embed_enabled:
                embed = discord.Embed(
                    title=self.embed_title,
                    description=message_content,
                    color=self.embed_color
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)
            else:
                await channel.send(message_content)

            logger.info(f"✅ Welcome message sent for {member.name} in guild {self.guild_id}")

        except discord.Forbidden:
            logger.warning(f"Missing permissions to send welcome message in guild {self.guild_id}")
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}", exc_info=True)
