"""
Configuration UI pour le module Welcome
Utilise les Composants V2 pour une interface moderne
"""

import discord
from discord import ui
from typing import Optional, Dict, Any
import logging

from utils.i18n import t

logger = logging.getLogger('moddy.modules.welcome_config')


class MessageEditModal(ui.Modal, title="Modifier le message"):
    """Modal pour éditer le message de bienvenue"""

    def __init__(self, locale: str, current_value: str, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        # Champ de texte pour le message
        self.message_input = ui.TextInput(
            label=t('modules.welcome.config.message.modal.label', locale=locale),
            placeholder=t('modules.welcome.config.message.modal.placeholder', locale=locale),
            default=current_value,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.message_input.value)


class EmbedTitleModal(ui.Modal, title="Modifier le titre de l'embed"):
    """Modal pour éditer le titre de l'embed"""

    def __init__(self, locale: str, current_value: str, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.title_input = ui.TextInput(
            label=t('modules.welcome.config.embed.title_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.embed.title_modal.placeholder', locale=locale),
            default=current_value,
            style=discord.TextStyle.short,
            max_length=256,
            required=True
        )
        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.title_input.value)


class EmbedDescriptionModal(ui.Modal, title="Modifier la description de l'embed"):
    """Modal pour éditer la description de l'embed"""

    def __init__(self, locale: str, current_value: Optional[str], callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.desc_input = ui.TextInput(
            label=t('modules.welcome.config.embed.description_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.embed.description_modal.placeholder', locale=locale),
            default=current_value or "",
            style=discord.TextStyle.paragraph,
            max_length=4096,
            required=False
        )
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.desc_input.value if self.desc_input.value else None)


class EmbedColorModal(ui.Modal, title="Modifier la couleur de l'embed"):
    """Modal pour éditer la couleur de l'embed"""

    def __init__(self, locale: str, current_value: int, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        # Convertir int en hex string
        hex_color = f"#{current_value:06X}"

        self.color_input = ui.TextInput(
            label=t('modules.welcome.config.embed.color_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.embed.color_modal.placeholder', locale=locale),
            default=hex_color,
            style=discord.TextStyle.short,
            max_length=7,
            required=True
        )
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Convertir hex string en int
        color_str = self.color_input.value.strip()
        if not color_str.startswith('#'):
            color_str = '#' + color_str

        try:
            color_int = int(color_str[1:], 16)
            await self.callback_func(interaction, color_int)
        except ValueError:
            await interaction.response.send_message(
                t('modules.welcome.config.embed.color_modal.error', locale=self.locale),
                ephemeral=True
            )


class EmbedFooterModal(ui.Modal, title="Modifier le footer de l'embed"):
    """Modal pour éditer le footer de l'embed"""

    def __init__(self, locale: str, current_value: Optional[str], callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.footer_input = ui.TextInput(
            label=t('modules.welcome.config.embed.footer_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.embed.footer_modal.placeholder', locale=locale),
            default=current_value or "",
            style=discord.TextStyle.short,
            max_length=2048,
            required=False
        )
        self.add_item(self.footer_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.footer_input.value if self.footer_input.value else None)


class EmbedImageModal(ui.Modal, title="Modifier l'image de l'embed"):
    """Modal pour éditer l'URL de l'image de l'embed"""

    def __init__(self, locale: str, current_value: Optional[str], callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.image_input = ui.TextInput(
            label=t('modules.welcome.config.embed.image_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.embed.image_modal.placeholder', locale=locale),
            default=current_value or "",
            style=discord.TextStyle.short,
            max_length=512,
            required=False
        )
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        url = self.image_input.value.strip() if self.image_input.value else None
        if url and not url.startswith(('http://', 'https://')):
            await interaction.response.send_message(
                t('modules.welcome.config.embed.image_modal.error', locale=self.locale),
                ephemeral=True
            )
            return
        await self.callback_func(interaction, url)


class WelcomeConfigView(ui.LayoutView):
    """
    Interface de configuration du module Welcome
    Utilise les Composants V2 pour une UI moderne et interactive
    """

    def __init__(self, bot, guild_id: int, user_id: int, locale: str, current_config: Optional[Dict[str, Any]] = None):
        """
        Initialise la vue de configuration

        Args:
            bot: Instance du bot
            guild_id: ID du serveur
            user_id: ID de l'utilisateur qui configure
            locale: Langue de l'utilisateur
            current_config: Configuration actuelle du module (None si première config)
        """
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.locale = locale

        # Configuration actuelle (ou par défaut)
        from modules.welcome import WelcomeModule
        default_config = WelcomeModule(bot, guild_id).get_default_config()

        # Check if we have a real saved config by looking for channel_id or send_dm
        if current_config and (current_config.get('channel_id') is not None or current_config.get('send_dm') is True):
            # Merge current config with defaults to ensure all keys exist
            self.current_config = default_config.copy()
            self.current_config.update(current_config)
            self.has_existing_config = True
        else:
            # Utilise la config par défaut du module
            self.current_config = default_config
            self.has_existing_config = False

        # Configuration en cours de modification (copie de travail)
        self.working_config = self.current_config.copy()

        # État de modification
        self.has_changes = False

        self._build_view()

    def _build_view(self):
        """Construit l'interface de configuration"""
        self.clear_items()

        container = ui.Container()

        # Titre et description
        container.add_item(ui.TextDisplay(
            f"### <:waving_hand:1446127491004760184> {t('modules.welcome.config.title', locale=self.locale)}"
        ))
        container.add_item(ui.TextDisplay(
            t('modules.welcome.config.description', locale=self.locale)
        ))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # === SECTION: MODE D'ENVOI ===
        container.add_item(ui.TextDisplay(
            f"**{t('modules.welcome.config.send_mode.section_title', locale=self.locale)}**"
        ))

        # Toggle Send DM
        send_dm_row = ui.ActionRow()
        send_dm_btn = ui.Button(
            label=t('modules.welcome.config.send_mode.send_dm', locale=self.locale),
            style=discord.ButtonStyle.success if self.working_config['send_dm'] else discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['send_dm'] else "<:undone:1398729502028333218>"),
            custom_id="toggle_send_dm"
        )
        send_dm_btn.callback = self.on_toggle_send_dm
        send_dm_row.add_item(send_dm_btn)
        container.add_item(send_dm_row)

        container.add_item(ui.TextDisplay(
            f"-# {t('modules.welcome.config.send_mode.send_dm_desc', locale=self.locale)}"
        ))

        # Sélecteur de salon (uniquement si send_dm est désactivé)
        if not self.working_config['send_dm']:
            container.add_item(ui.TextDisplay(
                f"**{t('modules.welcome.config.channel.section_title', locale=self.locale)}**"
            ))
            container.add_item(ui.TextDisplay(
                f"-# {t('modules.welcome.config.channel.section_description', locale=self.locale)}"
            ))

            channel_row = ui.ActionRow()
            channel_select = ui.ChannelSelect(
                placeholder=t('modules.welcome.config.channel.placeholder', locale=self.locale),
                channel_types=[discord.ChannelType.text],
                min_values=0,
                max_values=1
            )

            # Pré-sélectionne le salon actuel si configuré
            if self.working_config.get('channel_id'):
                channel = self.bot.get_channel(self.working_config['channel_id'])
                if channel:
                    channel_select.default_values = [channel]

            channel_select.callback = self.on_channel_select
            channel_row.add_item(channel_select)
            container.add_item(channel_row)

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # === SECTION: MESSAGE ===
        container.add_item(ui.TextDisplay(
            f"**{t('modules.welcome.config.message.section_title', locale=self.locale)}**"
        ))
        container.add_item(ui.TextDisplay(
            f"-# {t('modules.welcome.config.message.section_description', locale=self.locale)}"
        ))

        # Affichage du message actuel
        container.add_item(ui.TextDisplay(
            f"-# {t('modules.config.current_value', locale=self.locale)} `{self.working_config['message_template'][:100]}{'...' if len(self.working_config['message_template']) > 100 else ''}`"
        ))

        # Boutons pour éditer le message et toggle mention
        message_row = ui.ActionRow()

        edit_message_btn = ui.Button(
            label=t('modules.welcome.config.message.edit_button', locale=self.locale),
            style=discord.ButtonStyle.primary,
            emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
            custom_id="edit_message"
        )
        edit_message_btn.callback = self.on_edit_message
        message_row.add_item(edit_message_btn)

        mention_btn = ui.Button(
            label=t('modules.welcome.config.message.mention_user', locale=self.locale),
            style=discord.ButtonStyle.success if self.working_config['mention_user'] else discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['mention_user'] else "<:undone:1398729502028333218>"),
            custom_id="toggle_mention"
        )
        mention_btn.callback = self.on_toggle_mention
        message_row.add_item(mention_btn)

        container.add_item(message_row)

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # === SECTION: EMBED ===
        container.add_item(ui.TextDisplay(
            f"**{t('modules.welcome.config.embed.section_title', locale=self.locale)}**"
        ))

        # Toggle Embed
        embed_toggle_row = ui.ActionRow()
        embed_btn = ui.Button(
            label=t('modules.welcome.config.embed.toggle', locale=self.locale),
            style=discord.ButtonStyle.success if self.working_config['embed_enabled'] else discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['embed_enabled'] else "<:undone:1398729502028333218>"),
            custom_id="toggle_embed"
        )
        embed_btn.callback = self.on_toggle_embed
        embed_toggle_row.add_item(embed_btn)
        container.add_item(embed_toggle_row)

        # Options d'embed (uniquement si embed activé)
        if self.working_config['embed_enabled']:
            container.add_item(ui.TextDisplay(
                f"-# {t('modules.welcome.config.embed.section_description', locale=self.locale)}"
            ))

            # Boutons pour éditer le titre et la couleur
            embed_row1 = ui.ActionRow()

            edit_title_btn = ui.Button(
                label=t('modules.welcome.config.embed.edit_title', locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                custom_id="edit_embed_title"
            )
            edit_title_btn.callback = self.on_edit_embed_title
            embed_row1.add_item(edit_title_btn)

            edit_color_btn = ui.Button(
                label=t('modules.welcome.config.embed.edit_color', locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji=discord.PartialEmoji.from_str("<:color:1398729435565396008>"),
                custom_id="edit_embed_color"
            )
            edit_color_btn.callback = self.on_edit_embed_color
            embed_row1.add_item(edit_color_btn)

            container.add_item(embed_row1)

            # Bouton pour éditer la description
            embed_row2 = ui.ActionRow()

            edit_desc_btn = ui.Button(
                label=t('modules.welcome.config.embed.edit_description', locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                custom_id="edit_embed_description"
            )
            edit_desc_btn.callback = self.on_edit_embed_description
            embed_row2.add_item(edit_desc_btn)

            container.add_item(embed_row2)

            # Boutons pour footer et image
            embed_row3 = ui.ActionRow()

            edit_footer_btn = ui.Button(
                label=t('modules.welcome.config.embed.edit_footer', locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                custom_id="edit_embed_footer"
            )
            edit_footer_btn.callback = self.on_edit_embed_footer
            embed_row3.add_item(edit_footer_btn)

            edit_image_btn = ui.Button(
                label=t('modules.welcome.config.embed.edit_image', locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                custom_id="edit_embed_image"
            )
            edit_image_btn.callback = self.on_edit_embed_image
            embed_row3.add_item(edit_image_btn)

            container.add_item(embed_row3)

            # Toggles pour thumbnail et author
            embed_row4 = ui.ActionRow()

            thumbnail_btn = ui.Button(
                label=t('modules.welcome.config.embed.thumbnail', locale=self.locale),
                style=discord.ButtonStyle.success if self.working_config['embed_thumbnail_enabled'] else discord.ButtonStyle.secondary,
                emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['embed_thumbnail_enabled'] else "<:undone:1398729502028333218>"),
                custom_id="toggle_thumbnail"
            )
            thumbnail_btn.callback = self.on_toggle_thumbnail
            embed_row4.add_item(thumbnail_btn)

            author_btn = ui.Button(
                label=t('modules.welcome.config.embed.author', locale=self.locale),
                style=discord.ButtonStyle.success if self.working_config['embed_author_enabled'] else discord.ButtonStyle.secondary,
                emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['embed_author_enabled'] else "<:undone:1398729502028333218>"),
                custom_id="toggle_author"
            )
            author_btn.callback = self.on_toggle_author
            embed_row4.add_item(author_btn)

            container.add_item(embed_row4)

        self.add_item(container)

        # Boutons d'action en bas
        self._add_action_buttons()

    def _add_action_buttons(self):
        """Ajoute les boutons d'action en bas de la vue"""
        button_row = ui.ActionRow()

        # Bouton Back (toujours présent, désactivé si modifications en cours)
        back_btn = ui.Button(
            emoji=discord.PartialEmoji.from_str("<:back:1401600847733067806>"),
            label=t('modules.config.buttons.back', locale=self.locale),
            style=discord.ButtonStyle.secondary,
            custom_id="back_btn",
            disabled=self.has_changes  # Désactivé si modifications en cours
        )
        back_btn.callback = self.on_back
        button_row.add_item(back_btn)

        # Bouton Save (visible uniquement si modifications)
        if self.has_changes:
            save_btn = ui.Button(
                emoji=discord.PartialEmoji.from_str("<:save:1444101502154182778>"),
                label=t('modules.config.buttons.save', locale=self.locale),
                style=discord.ButtonStyle.success,
                custom_id="save_btn"
            )
            save_btn.callback = self.on_save
            button_row.add_item(save_btn)

            # Bouton Annuler
            cancel_btn = ui.Button(
                emoji=discord.PartialEmoji.from_str("<:undone:1398729502028333218>"),
                label=t('modules.config.buttons.cancel', locale=self.locale),
                style=discord.ButtonStyle.danger,
                custom_id="cancel_btn"
            )
            cancel_btn.callback = self.on_cancel
            button_row.add_item(cancel_btn)
        else:
            # Bouton Supprimer la configuration (si config existe)
            if self.has_existing_config:
                delete_btn = ui.Button(
                    emoji=discord.PartialEmoji.from_str("<:delete:1401600770431909939>"),
                    label=t('modules.config.buttons.delete', locale=self.locale),
                    style=discord.ButtonStyle.danger,
                    custom_id="delete_btn"
                )
                delete_btn.callback = self.on_delete
                button_row.add_item(delete_btn)

        self.add_item(button_row)

    # === CALLBACKS ===

    async def on_toggle_send_dm(self, interaction: discord.Interaction):
        """Toggle pour envoyer en DM"""
        if not await self.check_user(interaction):
            return

        self.working_config['send_dm'] = not self.working_config['send_dm']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_channel_select(self, interaction: discord.Interaction):
        """Callback quand un salon est sélectionné"""
        if not await self.check_user(interaction):
            return

        # Récupère le salon sélectionné (ou None si désélectionné)
        if interaction.data['values']:
            channel_id = int(interaction.data['values'][0])
            self.working_config['channel_id'] = channel_id
        else:
            self.working_config['channel_id'] = None

        # Marque comme modifié
        self.has_changes = True

        # Reconstruit la vue
        self._build_view()

        # Met à jour le message
        await interaction.response.edit_message(view=self)

    async def on_edit_message(self, interaction: discord.Interaction):
        """Ouvre le modal pour éditer le message"""
        if not await self.check_user(interaction):
            return

        modal = MessageEditModal(
            self.locale,
            self.working_config['message_template'],
            self._on_message_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_message_edited(self, interaction: discord.Interaction, new_message: str):
        """Callback après édition du message"""
        self.working_config['message_template'] = new_message
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_mention(self, interaction: discord.Interaction):
        """Toggle pour mentionner l'utilisateur"""
        if not await self.check_user(interaction):
            return

        self.working_config['mention_user'] = not self.working_config['mention_user']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_embed(self, interaction: discord.Interaction):
        """Toggle pour activer l'embed"""
        if not await self.check_user(interaction):
            return

        self.working_config['embed_enabled'] = not self.working_config['embed_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_embed_title(self, interaction: discord.Interaction):
        """Ouvre le modal pour éditer le titre de l'embed"""
        if not await self.check_user(interaction):
            return

        modal = EmbedTitleModal(
            self.locale,
            self.working_config['embed_title'],
            self._on_embed_title_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_embed_title_edited(self, interaction: discord.Interaction, new_title: str):
        """Callback après édition du titre"""
        self.working_config['embed_title'] = new_title
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_embed_description(self, interaction: discord.Interaction):
        """Ouvre le modal pour éditer la description de l'embed"""
        if not await self.check_user(interaction):
            return

        modal = EmbedDescriptionModal(
            self.locale,
            self.working_config.get('embed_description'),
            self._on_embed_description_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_embed_description_edited(self, interaction: discord.Interaction, new_desc: Optional[str]):
        """Callback après édition de la description"""
        self.working_config['embed_description'] = new_desc
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_embed_color(self, interaction: discord.Interaction):
        """Ouvre le modal pour éditer la couleur de l'embed"""
        if not await self.check_user(interaction):
            return

        modal = EmbedColorModal(
            self.locale,
            self.working_config['embed_color'],
            self._on_embed_color_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_embed_color_edited(self, interaction: discord.Interaction, new_color: int):
        """Callback après édition de la couleur"""
        self.working_config['embed_color'] = new_color
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_embed_footer(self, interaction: discord.Interaction):
        """Ouvre le modal pour éditer le footer de l'embed"""
        if not await self.check_user(interaction):
            return

        modal = EmbedFooterModal(
            self.locale,
            self.working_config.get('embed_footer'),
            self._on_embed_footer_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_embed_footer_edited(self, interaction: discord.Interaction, new_footer: Optional[str]):
        """Callback après édition du footer"""
        self.working_config['embed_footer'] = new_footer
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_embed_image(self, interaction: discord.Interaction):
        """Ouvre le modal pour éditer l'URL de l'image"""
        if not await self.check_user(interaction):
            return

        modal = EmbedImageModal(
            self.locale,
            self.working_config.get('embed_image_url'),
            self._on_embed_image_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_embed_image_edited(self, interaction: discord.Interaction, new_url: Optional[str]):
        """Callback après édition de l'URL de l'image"""
        self.working_config['embed_image_url'] = new_url
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_thumbnail(self, interaction: discord.Interaction):
        """Toggle pour afficher la thumbnail"""
        if not await self.check_user(interaction):
            return

        self.working_config['embed_thumbnail_enabled'] = not self.working_config['embed_thumbnail_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_author(self, interaction: discord.Interaction):
        """Toggle pour afficher l'auteur"""
        if not await self.check_user(interaction):
            return

        self.working_config['embed_author_enabled'] = not self.working_config['embed_author_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_back(self, interaction: discord.Interaction):
        """Retour au menu principal"""
        if not await self.check_user(interaction):
            return

        # Importe et affiche le menu principal
        from cogs.config import ConfigMainView
        main_view = ConfigMainView(self.bot, self.guild_id, self.user_id, self.locale)
        await interaction.response.edit_message(view=main_view)

    async def on_save(self, interaction: discord.Interaction):
        """Sauvegarde la configuration"""
        if not await self.check_user(interaction):
            return

        # Désactive temporairement les boutons
        await interaction.response.defer()

        # Récupère le gestionnaire de modules
        module_manager = self.bot.module_manager

        # Sauvegarde la configuration
        success, error_msg = await module_manager.save_module_config(
            self.guild_id,
            'welcome',
            self.working_config
        )

        if success:
            # Met à jour l'état
            self.current_config = self.working_config.copy()
            self.has_changes = False
            self.has_existing_config = True

            # Reconstruit la vue
            self._build_view()

            # Met à jour le message avec un feedback
            await interaction.followup.send(
                t('modules.config.save.success', locale=self.locale),
                ephemeral=True
            )
            await interaction.edit_original_response(view=self)
        else:
            # Affiche l'erreur
            await interaction.followup.send(
                t('modules.config.save.error', locale=self.locale, error=error_msg),
                ephemeral=True
            )

    async def on_cancel(self, interaction: discord.Interaction):
        """Annule les modifications"""
        if not await self.check_user(interaction):
            return

        # Restaure la configuration originale
        self.working_config = self.current_config.copy()
        self.has_changes = False

        # Reconstruit la vue
        self._build_view()

        # Met à jour le message
        await interaction.response.edit_message(view=self)

    async def on_delete(self, interaction: discord.Interaction):
        """Supprime la configuration"""
        if not await self.check_user(interaction):
            return

        # Désactive temporairement les boutons
        await interaction.response.defer()

        # Récupère le gestionnaire de modules
        module_manager = self.bot.module_manager

        # Supprime la configuration
        success = await module_manager.delete_module_config(self.guild_id, 'welcome')

        if success:
            # Met à jour l'état
            from modules.welcome import WelcomeModule
            self.current_config = WelcomeModule(self.bot, self.guild_id).get_default_config()
            self.working_config = self.current_config.copy()
            self.has_changes = False
            self.has_existing_config = False

            # Reconstruit la vue
            self._build_view()

            # Met à jour le message avec un feedback
            await interaction.followup.send(
                t('modules.config.delete.success', locale=self.locale),
                ephemeral=True
            )
            await interaction.edit_original_response(view=self)
        else:
            # Affiche l'erreur
            await interaction.followup.send(
                t('modules.config.delete.error', locale=self.locale),
                ephemeral=True
            )

    async def check_user(self, interaction: discord.Interaction) -> bool:
        """Vérifie que c'est le bon utilisateur"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t('modules.config.errors.wrong_user', locale=self.locale),
                ephemeral=True
            )
            return False
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie les permissions pour chaque interaction"""
        return await self.check_user(interaction)
