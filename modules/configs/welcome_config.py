"""
Configuration UI pour le module Welcome
Interface séparée pour les messages de bienvenue en DM et dans un salon
"""

import discord
from discord import ui
from typing import Optional, Dict, Any
import logging

from utils.i18n import t

logger = logging.getLogger('moddy.modules.welcome_config')


# === MODALS FOR CHANNEL WELCOME ===

class ChannelMessageEditModal(ui.Modal, title="Message de bienvenue public"):
    """Modal pour éditer le message de bienvenue dans le salon"""

    def __init__(self, locale: str, current_value: str, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.message_input = ui.TextInput(
            label=t('modules.welcome.config.channel.message_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.channel.message_modal.placeholder', locale=locale),
            default=current_value,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.message_input.value)


class ChannelEmbedTitleModal(ui.Modal, title="Titre embed public"):
    """Modal pour éditer le titre de l'embed du salon"""

    def __init__(self, locale: str, current_value: str, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.title_input = ui.TextInput(
            label=t('modules.welcome.config.channel.embed_title_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.channel.embed_title_modal.placeholder', locale=locale),
            default=current_value,
            style=discord.TextStyle.short,
            max_length=256,
            required=True
        )
        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.title_input.value)


class ChannelEmbedDescriptionModal(ui.Modal, title="Description embed public"):
    """Modal pour éditer la description de l'embed du salon"""

    def __init__(self, locale: str, current_value: Optional[str], callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.desc_input = ui.TextInput(
            label=t('modules.welcome.config.channel.embed_description_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.channel.embed_description_modal.placeholder', locale=locale),
            default=current_value or "",
            style=discord.TextStyle.paragraph,
            max_length=4096,
            required=False
        )
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.desc_input.value if self.desc_input.value else None)


class ChannelEmbedColorModal(ui.Modal, title="Couleur embed public"):
    """Modal pour éditer la couleur de l'embed du salon"""

    def __init__(self, locale: str, current_value: int, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        hex_color = f"#{current_value:06X}"

        self.color_input = ui.TextInput(
            label=t('modules.welcome.config.channel.embed_color_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.channel.embed_color_modal.placeholder', locale=locale),
            default=hex_color,
            style=discord.TextStyle.short,
            max_length=7,
            required=True
        )
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        color_str = self.color_input.value.strip()
        if not color_str.startswith('#'):
            color_str = '#' + color_str

        try:
            color_int = int(color_str[1:], 16)
            await self.callback_func(interaction, color_int)
        except ValueError:
            await interaction.response.send_message(
                t('modules.welcome.config.channel.embed_color_modal.error', locale=self.locale),
                ephemeral=True
            )


# === MODALS FOR DM WELCOME ===

class DmMessageEditModal(ui.Modal, title="Message de bienvenue privé"):
    """Modal pour éditer le message de bienvenue en DM"""

    def __init__(self, locale: str, current_value: str, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.message_input = ui.TextInput(
            label=t('modules.welcome.config.dm.message_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.dm.message_modal.placeholder', locale=locale),
            default=current_value,
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.message_input.value)


class DmEmbedTitleModal(ui.Modal, title="Titre embed privé"):
    """Modal pour éditer le titre de l'embed DM"""

    def __init__(self, locale: str, current_value: str, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.title_input = ui.TextInput(
            label=t('modules.welcome.config.dm.embed_title_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.dm.embed_title_modal.placeholder', locale=locale),
            default=current_value,
            style=discord.TextStyle.short,
            max_length=256,
            required=True
        )
        self.add_item(self.title_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.title_input.value)


class DmEmbedDescriptionModal(ui.Modal, title="Description embed privé"):
    """Modal pour éditer la description de l'embed DM"""

    def __init__(self, locale: str, current_value: Optional[str], callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        self.desc_input = ui.TextInput(
            label=t('modules.welcome.config.dm.embed_description_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.dm.embed_description_modal.placeholder', locale=locale),
            default=current_value or "",
            style=discord.TextStyle.paragraph,
            max_length=4096,
            required=False
        )
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.desc_input.value if self.desc_input.value else None)


class DmEmbedColorModal(ui.Modal, title="Couleur embed privé"):
    """Modal pour éditer la couleur de l'embed DM"""

    def __init__(self, locale: str, current_value: int, callback_func):
        super().__init__(timeout=300)
        self.locale = locale
        self.callback_func = callback_func

        hex_color = f"#{current_value:06X}"

        self.color_input = ui.TextInput(
            label=t('modules.welcome.config.dm.embed_color_modal.label', locale=locale),
            placeholder=t('modules.welcome.config.dm.embed_color_modal.placeholder', locale=locale),
            default=hex_color,
            style=discord.TextStyle.short,
            max_length=7,
            required=True
        )
        self.add_item(self.color_input)

    async def on_submit(self, interaction: discord.Interaction):
        color_str = self.color_input.value.strip()
        if not color_str.startswith('#'):
            color_str = '#' + color_str

        try:
            color_int = int(color_str[1:], 16)
            await self.callback_func(interaction, color_int)
        except ValueError:
            await interaction.response.send_message(
                t('modules.welcome.config.dm.embed_color_modal.error', locale=self.locale),
                ephemeral=True
            )


class WelcomeConfigView(ui.LayoutView):
    """
    Interface de configuration du module Welcome avec sections séparées pour DM et salon
    """

    def __init__(self, bot, guild_id: int, user_id: int, locale: str, current_config: Optional[Dict[str, Any]] = None):
        """
        Initialise la vue de configuration

        Args:
            bot: Instance du bot
            guild_id: ID du serveur
            user_id: ID de l'utilisateur qui configure
            locale: Langue de l'utilisateur
            current_config: Configuration actuelle du module
        """
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.locale = locale

        # Load default config
        from modules.welcome import WelcomeModule
        default_config = WelcomeModule(bot, guild_id).get_default_config()

        # Check if we have a real saved config
        if current_config and (
            current_config.get('channel_enabled') is True or
            current_config.get('dm_enabled') is True
        ):
            # Merge with defaults to ensure all keys exist
            self.current_config = default_config.copy()
            self.current_config.update(current_config)
            self.has_existing_config = True
        else:
            # Use default config
            self.current_config = default_config
            self.has_existing_config = False

        # Working copy
        self.working_config = self.current_config.copy()
        self.has_changes = False

        self._build_view()

    def _build_view(self):
        """Construit l'interface de configuration avec deux sections distinctes"""
        self.clear_items()

        container = ui.Container()

        # === HEADER ===
        container.add_item(ui.TextDisplay(
            f"### <:waving_hand:1446127491004760184> {t('modules.welcome.config.title', locale=self.locale)}"
        ))
        container.add_item(ui.TextDisplay(
            t('modules.welcome.config.description', locale=self.locale)
        ))

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        # === SECTION 1: CHANNEL WELCOME (Public) ===
        container.add_item(ui.TextDisplay(
            f"## {t('modules.welcome.config.channel.section_title', locale=self.locale)}"
        ))
        container.add_item(ui.TextDisplay(
            f"-# {t('modules.welcome.config.channel.section_description', locale=self.locale)}"
        ))

        # Toggle Channel Welcome
        channel_enabled_row = ui.ActionRow()
        channel_enabled_btn = ui.Button(
            label=t('modules.welcome.config.channel.enable', locale=self.locale),
            style=discord.ButtonStyle.success if self.working_config['channel_enabled'] else discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['channel_enabled'] else "<:undone:1398729502028333218>"),
            custom_id="toggle_channel_enabled"
        )
        channel_enabled_btn.callback = self.on_toggle_channel_enabled
        channel_enabled_row.add_item(channel_enabled_btn)
        container.add_item(channel_enabled_row)

        # Channel configuration (only if enabled)
        if self.working_config['channel_enabled']:
            # Channel selector
            channel_row = ui.ActionRow()
            channel_select = ui.ChannelSelect(
                placeholder=t('modules.welcome.config.channel.channel_placeholder', locale=self.locale),
                channel_types=[discord.ChannelType.text],
                min_values=0,
                max_values=1
            )

            # Pre-select current channel if set
            if self.working_config.get('channel_id'):
                channel = self.bot.get_channel(self.working_config['channel_id'])
                if channel:
                    channel_select.default_values = [channel]

            channel_select.callback = self.on_channel_select
            channel_row.add_item(channel_select)
            container.add_item(channel_row)

            # Message configuration
            container.add_item(ui.TextDisplay(
                f"-# **{t('modules.welcome.config.channel.message_label', locale=self.locale)}:** `{self.working_config['channel_message_template'][:80]}{'...' if len(self.working_config['channel_message_template']) > 80 else ''}`"
            ))

            # Buttons for message and mention
            channel_msg_row = ui.ActionRow()

            edit_channel_msg_btn = ui.Button(
                label=t('modules.welcome.config.channel.edit_message', locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                custom_id="edit_channel_message"
            )
            edit_channel_msg_btn.callback = self.on_edit_channel_message
            channel_msg_row.add_item(edit_channel_msg_btn)

            mention_channel_btn = ui.Button(
                label=t('modules.welcome.config.channel.mention_user', locale=self.locale),
                style=discord.ButtonStyle.success if self.working_config['channel_mention_user'] else discord.ButtonStyle.secondary,
                emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['channel_mention_user'] else "<:undone:1398729502028333218>"),
                custom_id="toggle_channel_mention"
            )
            mention_channel_btn.callback = self.on_toggle_channel_mention
            channel_msg_row.add_item(mention_channel_btn)

            container.add_item(channel_msg_row)

            # Embed toggle
            channel_embed_row = ui.ActionRow()
            channel_embed_btn = ui.Button(
                label=t('modules.welcome.config.channel.embed_toggle', locale=self.locale),
                style=discord.ButtonStyle.success if self.working_config['channel_embed_enabled'] else discord.ButtonStyle.secondary,
                emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['channel_embed_enabled'] else "<:undone:1398729502028333218>"),
                custom_id="toggle_channel_embed"
            )
            channel_embed_btn.callback = self.on_toggle_channel_embed
            channel_embed_row.add_item(channel_embed_btn)
            container.add_item(channel_embed_row)

            # Embed options (only if embed enabled)
            if self.working_config['channel_embed_enabled']:
                channel_embed_opts_row1 = ui.ActionRow()

                edit_channel_embed_title_btn = ui.Button(
                    label=t('modules.welcome.config.channel.edit_embed_title', locale=self.locale),
                    style=discord.ButtonStyle.primary,
                    emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                    custom_id="edit_channel_embed_title"
                )
                edit_channel_embed_title_btn.callback = self.on_edit_channel_embed_title
                channel_embed_opts_row1.add_item(edit_channel_embed_title_btn)

                edit_channel_embed_color_btn = ui.Button(
                    label=t('modules.welcome.config.channel.edit_embed_color', locale=self.locale),
                    style=discord.ButtonStyle.primary,
                    emoji=discord.PartialEmoji.from_str("<:color:1398729435565396008>"),
                    custom_id="edit_channel_embed_color"
                )
                edit_channel_embed_color_btn.callback = self.on_edit_channel_embed_color
                channel_embed_opts_row1.add_item(edit_channel_embed_color_btn)

                container.add_item(channel_embed_opts_row1)

                # Edit description button
                channel_embed_opts_row2 = ui.ActionRow()

                edit_channel_embed_desc_btn = ui.Button(
                    label=t('modules.welcome.config.channel.edit_embed_description', locale=self.locale),
                    style=discord.ButtonStyle.primary,
                    emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                    custom_id="edit_channel_embed_description"
                )
                edit_channel_embed_desc_btn.callback = self.on_edit_channel_embed_description
                channel_embed_opts_row2.add_item(edit_channel_embed_desc_btn)

                container.add_item(channel_embed_opts_row2)

                # Thumbnail and author toggles
                channel_embed_opts_row3 = ui.ActionRow()

                channel_thumbnail_btn = ui.Button(
                    label=t('modules.welcome.config.channel.embed_thumbnail', locale=self.locale),
                    style=discord.ButtonStyle.success if self.working_config['channel_embed_thumbnail_enabled'] else discord.ButtonStyle.secondary,
                    emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['channel_embed_thumbnail_enabled'] else "<:undone:1398729502028333218>"),
                    custom_id="toggle_channel_thumbnail"
                )
                channel_thumbnail_btn.callback = self.on_toggle_channel_thumbnail
                channel_embed_opts_row3.add_item(channel_thumbnail_btn)

                channel_author_btn = ui.Button(
                    label=t('modules.welcome.config.channel.embed_author', locale=self.locale),
                    style=discord.ButtonStyle.success if self.working_config['channel_embed_author_enabled'] else discord.ButtonStyle.secondary,
                    emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['channel_embed_author_enabled'] else "<:undone:1398729502028333218>"),
                    custom_id="toggle_channel_author"
                )
                channel_author_btn.callback = self.on_toggle_channel_author
                channel_embed_opts_row3.add_item(channel_author_btn)

                container.add_item(channel_embed_opts_row3)

        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.large))

        # === SECTION 2: DM WELCOME (Private) ===
        container.add_item(ui.TextDisplay(
            f"## {t('modules.welcome.config.dm.section_title', locale=self.locale)}"
        ))
        container.add_item(ui.TextDisplay(
            f"-# {t('modules.welcome.config.dm.section_description', locale=self.locale)}"
        ))

        # Toggle DM Welcome
        dm_enabled_row = ui.ActionRow()
        dm_enabled_btn = ui.Button(
            label=t('modules.welcome.config.dm.enable', locale=self.locale),
            style=discord.ButtonStyle.success if self.working_config['dm_enabled'] else discord.ButtonStyle.secondary,
            emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['dm_enabled'] else "<:undone:1398729502028333218>"),
            custom_id="toggle_dm_enabled"
        )
        dm_enabled_btn.callback = self.on_toggle_dm_enabled
        dm_enabled_row.add_item(dm_enabled_btn)
        container.add_item(dm_enabled_row)

        # DM configuration (only if enabled)
        if self.working_config['dm_enabled']:
            # Message configuration
            container.add_item(ui.TextDisplay(
                f"-# **{t('modules.welcome.config.dm.message_label', locale=self.locale)}:** `{self.working_config['dm_message_template'][:80]}{'...' if len(self.working_config['dm_message_template']) > 80 else ''}`"
            ))

            # Button for message
            dm_msg_row = ui.ActionRow()

            edit_dm_msg_btn = ui.Button(
                label=t('modules.welcome.config.dm.edit_message', locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                custom_id="edit_dm_message"
            )
            edit_dm_msg_btn.callback = self.on_edit_dm_message
            dm_msg_row.add_item(edit_dm_msg_btn)

            container.add_item(dm_msg_row)

            # Embed toggle
            dm_embed_row = ui.ActionRow()
            dm_embed_btn = ui.Button(
                label=t('modules.welcome.config.dm.embed_toggle', locale=self.locale),
                style=discord.ButtonStyle.success if self.working_config['dm_embed_enabled'] else discord.ButtonStyle.secondary,
                emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['dm_embed_enabled'] else "<:undone:1398729502028333218>"),
                custom_id="toggle_dm_embed"
            )
            dm_embed_btn.callback = self.on_toggle_dm_embed
            dm_embed_row.add_item(dm_embed_btn)
            container.add_item(dm_embed_row)

            # Embed options (only if embed enabled)
            if self.working_config['dm_embed_enabled']:
                dm_embed_opts_row1 = ui.ActionRow()

                edit_dm_embed_title_btn = ui.Button(
                    label=t('modules.welcome.config.dm.edit_embed_title', locale=self.locale),
                    style=discord.ButtonStyle.primary,
                    emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                    custom_id="edit_dm_embed_title"
                )
                edit_dm_embed_title_btn.callback = self.on_edit_dm_embed_title
                dm_embed_opts_row1.add_item(edit_dm_embed_title_btn)

                edit_dm_embed_color_btn = ui.Button(
                    label=t('modules.welcome.config.dm.edit_embed_color', locale=self.locale),
                    style=discord.ButtonStyle.primary,
                    emoji=discord.PartialEmoji.from_str("<:color:1398729435565396008>"),
                    custom_id="edit_dm_embed_color"
                )
                edit_dm_embed_color_btn.callback = self.on_edit_dm_embed_color
                dm_embed_opts_row1.add_item(edit_dm_embed_color_btn)

                container.add_item(dm_embed_opts_row1)

                # Edit description button
                dm_embed_opts_row2 = ui.ActionRow()

                edit_dm_embed_desc_btn = ui.Button(
                    label=t('modules.welcome.config.dm.edit_embed_description', locale=self.locale),
                    style=discord.ButtonStyle.primary,
                    emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                    custom_id="edit_dm_embed_description"
                )
                edit_dm_embed_desc_btn.callback = self.on_edit_dm_embed_description
                dm_embed_opts_row2.add_item(edit_dm_embed_desc_btn)

                container.add_item(dm_embed_opts_row2)

                # Thumbnail and author toggles
                dm_embed_opts_row3 = ui.ActionRow()

                dm_thumbnail_btn = ui.Button(
                    label=t('modules.welcome.config.dm.embed_thumbnail', locale=self.locale),
                    style=discord.ButtonStyle.success if self.working_config['dm_embed_thumbnail_enabled'] else discord.ButtonStyle.secondary,
                    emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['dm_embed_thumbnail_enabled'] else "<:undone:1398729502028333218>"),
                    custom_id="toggle_dm_thumbnail"
                )
                dm_thumbnail_btn.callback = self.on_toggle_dm_thumbnail
                dm_embed_opts_row3.add_item(dm_thumbnail_btn)

                dm_author_btn = ui.Button(
                    label=t('modules.welcome.config.dm.embed_author', locale=self.locale),
                    style=discord.ButtonStyle.success if self.working_config['dm_embed_author_enabled'] else discord.ButtonStyle.secondary,
                    emoji=discord.PartialEmoji.from_str("<:done:1398729525277229066>" if self.working_config['dm_embed_author_enabled'] else "<:undone:1398729502028333218>"),
                    custom_id="toggle_dm_author"
                )
                dm_author_btn.callback = self.on_toggle_dm_author
                dm_embed_opts_row3.add_item(dm_author_btn)

                container.add_item(dm_embed_opts_row3)

        self.add_item(container)

        # Add action buttons at the bottom
        self._add_action_buttons()

    def _add_action_buttons(self):
        """Ajoute les boutons d'action en bas de la vue"""
        button_row = ui.ActionRow()

        # Back button (disabled if changes pending)
        back_btn = ui.Button(
            emoji=discord.PartialEmoji.from_str("<:back:1401600847733067806>"),
            label=t('modules.config.buttons.back', locale=self.locale),
            style=discord.ButtonStyle.secondary,
            custom_id="back_btn",
            disabled=self.has_changes
        )
        back_btn.callback = self.on_back
        button_row.add_item(back_btn)

        # Save button (only if changes)
        if self.has_changes:
            save_btn = ui.Button(
                emoji=discord.PartialEmoji.from_str("<:save:1444101502154182778>"),
                label=t('modules.config.buttons.save', locale=self.locale),
                style=discord.ButtonStyle.success,
                custom_id="save_btn"
            )
            save_btn.callback = self.on_save
            button_row.add_item(save_btn)

            # Cancel button
            cancel_btn = ui.Button(
                emoji=discord.PartialEmoji.from_str("<:undone:1398729502028333218>"),
                label=t('modules.config.buttons.cancel', locale=self.locale),
                style=discord.ButtonStyle.danger,
                custom_id="cancel_btn"
            )
            cancel_btn.callback = self.on_cancel
            button_row.add_item(cancel_btn)
        else:
            # Delete button (if config exists)
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

    # === CHANNEL WELCOME CALLBACKS ===

    async def on_toggle_channel_enabled(self, interaction: discord.Interaction):
        """Toggle channel welcome"""
        if not await self.check_user(interaction):
            return

        self.working_config['channel_enabled'] = not self.working_config['channel_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_channel_select(self, interaction: discord.Interaction):
        """Channel selector callback"""
        if not await self.check_user(interaction):
            return

        if interaction.data['values']:
            channel_id = int(interaction.data['values'][0])
            self.working_config['channel_id'] = channel_id
        else:
            self.working_config['channel_id'] = None

        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_channel_message(self, interaction: discord.Interaction):
        """Edit channel message"""
        if not await self.check_user(interaction):
            return

        modal = ChannelMessageEditModal(
            self.locale,
            self.working_config['channel_message_template'],
            self._on_channel_message_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_channel_message_edited(self, interaction: discord.Interaction, new_message: str):
        """Callback after channel message edit"""
        self.working_config['channel_message_template'] = new_message
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_channel_mention(self, interaction: discord.Interaction):
        """Toggle channel mention"""
        if not await self.check_user(interaction):
            return

        self.working_config['channel_mention_user'] = not self.working_config['channel_mention_user']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_channel_embed(self, interaction: discord.Interaction):
        """Toggle channel embed"""
        if not await self.check_user(interaction):
            return

        self.working_config['channel_embed_enabled'] = not self.working_config['channel_embed_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_channel_embed_title(self, interaction: discord.Interaction):
        """Edit channel embed title"""
        if not await self.check_user(interaction):
            return

        modal = ChannelEmbedTitleModal(
            self.locale,
            self.working_config['channel_embed_title'],
            self._on_channel_embed_title_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_channel_embed_title_edited(self, interaction: discord.Interaction, new_title: str):
        """Callback after channel embed title edit"""
        self.working_config['channel_embed_title'] = new_title
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_channel_embed_description(self, interaction: discord.Interaction):
        """Edit channel embed description"""
        if not await self.check_user(interaction):
            return

        modal = ChannelEmbedDescriptionModal(
            self.locale,
            self.working_config.get('channel_embed_description'),
            self._on_channel_embed_description_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_channel_embed_description_edited(self, interaction: discord.Interaction, new_desc: Optional[str]):
        """Callback after channel embed description edit"""
        self.working_config['channel_embed_description'] = new_desc
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_channel_embed_color(self, interaction: discord.Interaction):
        """Edit channel embed color"""
        if not await self.check_user(interaction):
            return

        modal = ChannelEmbedColorModal(
            self.locale,
            self.working_config['channel_embed_color'],
            self._on_channel_embed_color_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_channel_embed_color_edited(self, interaction: discord.Interaction, new_color: int):
        """Callback after channel embed color edit"""
        self.working_config['channel_embed_color'] = new_color
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_channel_thumbnail(self, interaction: discord.Interaction):
        """Toggle channel thumbnail"""
        if not await self.check_user(interaction):
            return

        self.working_config['channel_embed_thumbnail_enabled'] = not self.working_config['channel_embed_thumbnail_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_channel_author(self, interaction: discord.Interaction):
        """Toggle channel author"""
        if not await self.check_user(interaction):
            return

        self.working_config['channel_embed_author_enabled'] = not self.working_config['channel_embed_author_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    # === DM WELCOME CALLBACKS ===

    async def on_toggle_dm_enabled(self, interaction: discord.Interaction):
        """Toggle DM welcome"""
        if not await self.check_user(interaction):
            return

        self.working_config['dm_enabled'] = not self.working_config['dm_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_dm_message(self, interaction: discord.Interaction):
        """Edit DM message"""
        if not await self.check_user(interaction):
            return

        modal = DmMessageEditModal(
            self.locale,
            self.working_config['dm_message_template'],
            self._on_dm_message_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_dm_message_edited(self, interaction: discord.Interaction, new_message: str):
        """Callback after DM message edit"""
        self.working_config['dm_message_template'] = new_message
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_dm_embed(self, interaction: discord.Interaction):
        """Toggle DM embed"""
        if not await self.check_user(interaction):
            return

        self.working_config['dm_embed_enabled'] = not self.working_config['dm_embed_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_dm_embed_title(self, interaction: discord.Interaction):
        """Edit DM embed title"""
        if not await self.check_user(interaction):
            return

        modal = DmEmbedTitleModal(
            self.locale,
            self.working_config['dm_embed_title'],
            self._on_dm_embed_title_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_dm_embed_title_edited(self, interaction: discord.Interaction, new_title: str):
        """Callback after DM embed title edit"""
        self.working_config['dm_embed_title'] = new_title
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_dm_embed_description(self, interaction: discord.Interaction):
        """Edit DM embed description"""
        if not await self.check_user(interaction):
            return

        modal = DmEmbedDescriptionModal(
            self.locale,
            self.working_config.get('dm_embed_description'),
            self._on_dm_embed_description_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_dm_embed_description_edited(self, interaction: discord.Interaction, new_desc: Optional[str]):
        """Callback after DM embed description edit"""
        self.working_config['dm_embed_description'] = new_desc
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_edit_dm_embed_color(self, interaction: discord.Interaction):
        """Edit DM embed color"""
        if not await self.check_user(interaction):
            return

        modal = DmEmbedColorModal(
            self.locale,
            self.working_config['dm_embed_color'],
            self._on_dm_embed_color_edited
        )
        await interaction.response.send_modal(modal)

    async def _on_dm_embed_color_edited(self, interaction: discord.Interaction, new_color: int):
        """Callback after DM embed color edit"""
        self.working_config['dm_embed_color'] = new_color
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_dm_thumbnail(self, interaction: discord.Interaction):
        """Toggle DM thumbnail"""
        if not await self.check_user(interaction):
            return

        self.working_config['dm_embed_thumbnail_enabled'] = not self.working_config['dm_embed_thumbnail_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_toggle_dm_author(self, interaction: discord.Interaction):
        """Toggle DM author"""
        if not await self.check_user(interaction):
            return

        self.working_config['dm_embed_author_enabled'] = not self.working_config['dm_embed_author_enabled']
        self.has_changes = True
        self._build_view()
        await interaction.response.edit_message(view=self)

    # === ACTION BUTTON CALLBACKS ===

    async def on_back(self, interaction: discord.Interaction):
        """Return to main menu"""
        if not await self.check_user(interaction):
            return

        from cogs.config import ConfigMainView
        main_view = ConfigMainView(self.bot, self.guild_id, self.user_id, self.locale)
        await interaction.response.edit_message(view=main_view)

    async def on_save(self, interaction: discord.Interaction):
        """Save configuration"""
        if not await self.check_user(interaction):
            return

        await interaction.response.defer()

        module_manager = self.bot.module_manager

        success, error_msg = await module_manager.save_module_config(
            self.guild_id,
            'welcome',
            self.working_config
        )

        if success:
            self.current_config = self.working_config.copy()
            self.has_changes = False
            self.has_existing_config = True

            self._build_view()

            await interaction.followup.send(
                t('modules.config.save.success', locale=self.locale),
                ephemeral=True
            )
            await interaction.edit_original_response(view=self)
        else:
            await interaction.followup.send(
                t('modules.config.save.error', locale=self.locale, error=error_msg),
                ephemeral=True
            )

    async def on_cancel(self, interaction: discord.Interaction):
        """Cancel changes"""
        if not await self.check_user(interaction):
            return

        self.working_config = self.current_config.copy()
        self.has_changes = False

        self._build_view()
        await interaction.response.edit_message(view=self)

    async def on_delete(self, interaction: discord.Interaction):
        """Delete configuration"""
        if not await self.check_user(interaction):
            return

        await interaction.response.defer()

        module_manager = self.bot.module_manager

        success = await module_manager.delete_module_config(self.guild_id, 'welcome')

        if success:
            from modules.welcome import WelcomeModule
            self.current_config = WelcomeModule(self.bot, self.guild_id).get_default_config()
            self.working_config = self.current_config.copy()
            self.has_changes = False
            self.has_existing_config = False

            self._build_view()

            await interaction.followup.send(
                t('modules.config.delete.success', locale=self.locale),
                ephemeral=True
            )
            await interaction.edit_original_response(view=self)
        else:
            await interaction.followup.send(
                t('modules.config.delete.error', locale=self.locale),
                ephemeral=True
            )

    async def check_user(self, interaction: discord.Interaction) -> bool:
        """Check if the user is the one who started the config"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t('modules.config.errors.wrong_user', locale=self.locale),
                ephemeral=True
            )
            return False
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check permissions for each interaction"""
        return await self.check_user(interaction)
