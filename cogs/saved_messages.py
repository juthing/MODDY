"""
Saved Messages Library for Moddy
Allows users to save messages to a personal library via context menu
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.ui import LayoutView, Container, TextDisplay, Separator
from discord import SeparatorSpacing
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from utils.i18n import t
from utils.incognito import get_incognito_setting

logger = logging.getLogger('moddy.saved_messages')


class AddNoteModal(ui.Modal):
    """Modal for adding a note to a saved message"""

    def __init__(self, locale: str, bot, message: discord.Message):
        super().__init__(title=t("commands.saved_messages.modals.add_note_title", locale=locale))
        self.locale = locale
        self.bot = bot
        self.message = message

        self.note_input = ui.TextInput(
            label=t("commands.saved_messages.modals.note_label", locale=locale),
            placeholder=t("commands.saved_messages.modals.note_placeholder", locale=locale),
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.note_input)

    async def on_submit(self, interaction: discord.Interaction):
        note = self.note_input.value if self.note_input.value else None

        # Préparer les données du message
        attachments = []
        for attachment in self.message.attachments:
            attachments.append({
                'url': attachment.url,
                'filename': attachment.filename,
                'size': attachment.size,
                'content_type': attachment.content_type
            })

        embeds = []
        for embed in self.message.embeds:
            embeds.append(embed.to_dict())

        # Sauvegarder le message
        try:
            saved_id = await self.bot.db.save_message(
                user_id=interaction.user.id,
                message_id=self.message.id,
                channel_id=self.message.channel.id,
                guild_id=self.message.guild.id if self.message.guild else None,
                author_id=self.message.author.id,
                content=self.message.content or "",
                attachments=attachments,
                embeds=embeds,
                created_at=self.message.created_at,
                message_url=self.message.jump_url,
                note=note
            )

            success_msg = t("commands.saved_messages.success.saved", interaction, id=saved_id)
            await interaction.response.send_message(success_msg, ephemeral=True)
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            error_msg = t("common.error", interaction)
            await interaction.response.send_message(error_msg, ephemeral=True)


class EditNoteModal(ui.Modal):
    """Modal for editing a note on a saved message"""

    def __init__(self, locale: str, bot, saved_msg: Dict, parent_view=None):
        super().__init__(title=t("commands.saved_messages.modals.edit_note_title", locale=locale))
        self.locale = locale
        self.bot = bot
        self.saved_msg = saved_msg
        self.parent_view = parent_view

        self.note_input = ui.TextInput(
            label=t("commands.saved_messages.modals.note_label", locale=locale),
            default=saved_msg.get('note', '') or '',
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.note_input)

    async def on_submit(self, interaction: discord.Interaction):
        note = self.note_input.value if self.note_input.value else None

        try:
            await self.bot.db.update_saved_message_note(
                self.saved_msg['id'],
                interaction.user.id,
                note
            )

            success_msg = t("commands.saved_messages.success.note_updated", interaction)
            await interaction.response.send_message(success_msg, ephemeral=True)

            # Refresh parent view if it exists
            if self.parent_view:
                await self.parent_view.refresh(interaction)
        except Exception as e:
            logger.error(f"Error updating note: {e}")
            error_msg = t("common.error", interaction)
            await interaction.response.send_message(error_msg, ephemeral=True)


class MessageDetailView(LayoutView):
    """View to display a single saved message in detail"""

    def __init__(self, bot, saved_msg: Dict, locale: str, user_id: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.saved_msg = saved_msg
        self.locale = locale
        self.user_id = user_id
        self._build_view()

    def _build_view(self):
        self.clear_items()

        container = Container()

        # Titre
        container.add_item(TextDisplay(t("commands.saved_messages.detail.title", locale=self.locale)))

        # Auteur du message
        author_line = t("commands.saved_messages.detail.author", locale=self.locale,
                       author_id=self.saved_msg['author_id'])
        container.add_item(TextDisplay(author_line))

        # Date du message
        created_ts = f"<t:{int(self.saved_msg['created_at'].timestamp())}:F>"
        saved_ts = f"<t:{int(self.saved_msg['saved_at'].timestamp())}:R>"
        date_line = t("commands.saved_messages.detail.dates", locale=self.locale,
                     created=created_ts, saved=saved_ts)
        container.add_item(TextDisplay(date_line))

        container.add_item(Separator(spacing=SeparatorSpacing.small))

        # Contenu du message
        if self.saved_msg['content']:
            content_preview = self.saved_msg['content'][:500]
            if len(self.saved_msg['content']) > 500:
                content_preview += "..."
            container.add_item(TextDisplay(f">>> {content_preview}"))
        else:
            container.add_item(TextDisplay(t("commands.saved_messages.detail.no_content", locale=self.locale)))

        # Note si présente
        if self.saved_msg.get('note'):
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            note_text = t("commands.saved_messages.detail.note", locale=self.locale,
                         note=self.saved_msg['note'])
            container.add_item(TextDisplay(note_text))

        # Attachments
        if self.saved_msg['attachments']:
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            attach_text = t("commands.saved_messages.detail.attachments", locale=self.locale,
                           count=len(self.saved_msg['attachments']))
            container.add_item(TextDisplay(attach_text))

        # Lien vers le message original
        if self.saved_msg.get('message_url'):
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            link_text = t("commands.saved_messages.detail.link", locale=self.locale,
                         url=self.saved_msg['message_url'])
            container.add_item(TextDisplay(link_text))

        self.add_item(container)

        # Boutons d'action
        btn_row = ui.ActionRow()

        # Bouton Edit Note
        edit_btn = ui.Button(
            emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
            label=t("commands.saved_messages.buttons.edit_note", locale=self.locale),
            style=discord.ButtonStyle.primary,
            custom_id="edit_note_btn"
        )
        edit_btn.callback = self.edit_note_callback
        btn_row.add_item(edit_btn)

        # Bouton Delete
        delete_btn = ui.Button(
            emoji=discord.PartialEmoji.from_str("<:delete:1401600770431909939>"),
            label=t("commands.saved_messages.buttons.delete", locale=self.locale),
            style=discord.ButtonStyle.danger,
            custom_id="delete_btn"
        )
        delete_btn.callback = self.delete_callback
        btn_row.add_item(delete_btn)

        container.add_item(btn_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t("commands.saved_messages.errors.author_only", interaction),
                ephemeral=True
            )
            return False
        return True

    async def edit_note_callback(self, interaction: discord.Interaction):
        modal = EditNoteModal(self.locale, self.bot, self.saved_msg, parent_view=self)
        await interaction.response.send_modal(modal)

    async def delete_callback(self, interaction: discord.Interaction):
        success = await self.bot.db.delete_saved_message(self.saved_msg['id'], interaction.user.id)
        if success:
            await interaction.response.edit_message(
                content=t("commands.saved_messages.success.deleted", interaction),
                view=None
            )
        else:
            await interaction.response.send_message(
                t("common.error", interaction),
                ephemeral=True
            )

    async def refresh(self, interaction: discord.Interaction):
        """Refresh the view with updated data"""
        self.saved_msg = await self.bot.db.get_saved_message(self.saved_msg['id'], self.user_id)
        if self.saved_msg:
            self._build_view()
            try:
                await interaction.edit_original_response(view=self)
            except Exception:
                pass


class SavedMessagesSelectMenu(ui.Select):
    """Select menu for choosing a saved message to view"""

    def __init__(self, messages: List[Dict], locale: str, bot, user_id: int):
        self.messages_map = {str(m['id']): m for m in messages}
        self.locale = locale
        self.bot = bot
        self.user_id = user_id

        options = []
        for msg in messages[:25]:  # Discord limit
            # Créer un label à partir du contenu ou d'une note
            if msg['content']:
                label = msg['content'][:50]
            elif msg.get('note'):
                label = f"📝 {msg['note'][:50]}"
            else:
                label = t("commands.saved_messages.select.no_preview", locale=locale)

            if len(msg['content']) > 50 or (msg.get('note') and len(msg['note']) > 50):
                label += "..."

            # Description avec la date
            saved_ts = f"<t:{int(msg['saved_at'].timestamp())}:R>"
            description = f"#{msg['id']} • {saved_ts}"

            options.append(discord.SelectOption(
                label=label,
                value=str(msg['id']),
                description=description[:100]
            ))

        super().__init__(
            placeholder=t("commands.saved_messages.select.placeholder", locale=locale),
            options=options if options else [discord.SelectOption(label="None", value="none")]
        )

    async def callback(self, interaction: discord.Interaction):
        msg_id = self.values[0]
        saved_msg = self.messages_map.get(msg_id)
        if saved_msg:
            view = MessageDetailView(self.bot, saved_msg, self.locale, self.user_id)
            await interaction.response.send_message(view=view, ephemeral=True)


class SavedMessagesLibraryView(LayoutView):
    """Main view for browsing the saved messages library"""

    def __init__(self, bot, user_id: int, messages: List[Dict], locale: str,
                 page: int = 0, total_count: int = 0):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.messages = messages
        self.locale = locale
        self.page = page
        self.total_count = total_count
        self._build_view()

    def _build_view(self):
        self.clear_items()

        container = Container()

        # Titre avec compte
        title = t("commands.saved_messages.library.title", locale=self.locale, count=self.total_count)
        container.add_item(TextDisplay(title))

        if not self.messages:
            container.add_item(TextDisplay(t("commands.saved_messages.library.empty", locale=self.locale)))
        else:
            # Afficher les messages
            for msg in self.messages[:10]:  # Limit to 10 per page
                saved_ts = f"<t:{int(msg['saved_at'].timestamp())}:R>"

                preview = msg['content'][:100] if msg['content'] else ""
                if len(msg['content']) > 100:
                    preview += "..."

                if msg.get('note'):
                    note_preview = f"📝 {msg['note'][:50]}"
                    if len(msg['note']) > 50:
                        note_preview += "..."
                    msg_line = f"**#{msg['id']}** {saved_ts}\n{preview}\n-# {note_preview}"
                else:
                    msg_line = f"**#{msg['id']}** {saved_ts}\n{preview}"

                container.add_item(TextDisplay(msg_line))

            container.add_item(Separator(spacing=SeparatorSpacing.small))

            # Page info
            total_pages = (self.total_count + 9) // 10
            page_info = t("commands.saved_messages.library.page_info", locale=self.locale,
                         page=self.page + 1, total=total_pages)
            container.add_item(TextDisplay(page_info))

            # Select menu pour voir les détails
            select_row = ui.ActionRow()
            select = SavedMessagesSelectMenu(self.messages, self.locale, self.bot, self.user_id)
            select_row.add_item(select)
            container.add_item(select_row)

            # Navigation buttons
            nav_row = ui.ActionRow()

            prev_btn = ui.Button(
                emoji=discord.PartialEmoji.from_str("<:back:1401600847733067806>"),
                label=t("commands.saved_messages.buttons.previous", locale=self.locale),
                style=discord.ButtonStyle.secondary,
                disabled=self.page == 0,
                custom_id="prev_btn"
            )
            prev_btn.callback = self.prev_callback
            nav_row.add_item(prev_btn)

            next_btn = ui.Button(
                emoji="▶️",
                label=t("commands.saved_messages.buttons.next", locale=self.locale),
                style=discord.ButtonStyle.secondary,
                disabled=(self.page + 1) * 10 >= self.total_count,
                custom_id="next_btn"
            )
            next_btn.callback = self.next_callback
            nav_row.add_item(next_btn)

            container.add_item(nav_row)

        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t("commands.saved_messages.errors.author_only", interaction),
                ephemeral=True
            )
            return False
        return True

    async def prev_callback(self, interaction: discord.Interaction):
        if self.page > 0:
            self.page -= 1
            await self.refresh(interaction)

    async def next_callback(self, interaction: discord.Interaction):
        if (self.page + 1) * 10 < self.total_count:
            self.page += 1
            await self.refresh(interaction)

    async def refresh(self, interaction: discord.Interaction):
        """Refresh the view with updated data"""
        offset = self.page * 10
        self.messages = await self.bot.db.get_saved_messages(self.user_id, limit=10, offset=offset)
        self.total_count = await self.bot.db.count_saved_messages(self.user_id)
        self._build_view()
        await interaction.response.edit_message(view=self)


class SavedMessages(commands.Cog):
    """Saved messages library system"""

    def __init__(self, bot):
        self.bot = bot

        # Create context menu command
        self.save_message_menu = app_commands.ContextMenu(
            name="Save Message",
            callback=self.save_message_context_menu
        )
        self.bot.tree.add_command(self.save_message_menu)

    async def save_message_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        """Context menu to save a message"""
        locale = str(interaction.locale)

        # Check if user already has too many saved messages
        count = await self.bot.db.count_saved_messages(interaction.user.id)
        if count >= 500:  # Max 500 saved messages per user
            error_msg = t("commands.saved_messages.errors.max_messages", interaction)
            await interaction.response.send_message(error_msg, ephemeral=True)
            return

        # Show modal to add optional note
        modal = AddNoteModal(locale, self.bot, message)
        await interaction.response.send_modal(modal)

    @app_commands.command(
        name="library",
        description="View your saved messages library"
    )
    @app_commands.describe(
        incognito="Make response visible only to you"
    )
    async def library_command(
        self,
        interaction: discord.Interaction,
        incognito: Optional[bool] = None
    ):
        """View saved messages library"""
        # Handle incognito setting
        if incognito is None and self.bot.db:
            try:
                user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                ephemeral = True if user_pref is None else user_pref
            except:
                ephemeral = True
        else:
            ephemeral = incognito if incognito is not None else True

        # Get saved messages
        messages = await self.bot.db.get_saved_messages(interaction.user.id, limit=10, offset=0)
        total_count = await self.bot.db.count_saved_messages(interaction.user.id)

        # Create view
        view = SavedMessagesLibraryView(
            self.bot,
            interaction.user.id,
            messages,
            str(interaction.locale),
            page=0,
            total_count=total_count
        )

        await interaction.response.send_message(view=view, ephemeral=ephemeral)

    async def cog_unload(self):
        """Remove context menu when cog is unloaded"""
        self.bot.tree.remove_command(self.save_message_menu.name, type=self.save_message_menu.type)


async def setup(bot):
    await bot.add_cog(SavedMessages(bot))
