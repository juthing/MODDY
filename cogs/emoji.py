"""
Emoji command for Moddy
Displays information about a Discord emoji with Components V2
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import aiohttp
import re
from datetime import datetime

from utils.incognito import add_incognito_option, get_incognito_setting
from utils.i18n import i18n


class EmojiView(ui.LayoutView):
    """View to display emoji information using Components V2"""

    def __init__(self, emoji_data: dict, locale: str):
        super().__init__(timeout=180)
        self.emoji_data = emoji_data
        self.locale = locale

        # Build the view
        self.build_view()

    def build_view(self):
        """Builds the Components V2 view"""
        # Clear existing items
        self.clear_items()

        # Create main container
        container = ui.Container()

        # Get emoji info
        emoji_id = self.emoji_data.get("id")
        emoji_name = self.emoji_data.get("name", "Unknown")
        is_animated = self.emoji_data.get("animated", False)
        created_at = self.emoji_data.get("created_at")

        # Build emoji URL with proper extension
        extension = "gif" if is_animated else "png"
        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{extension}"
        emoji_url_display = f"{emoji_url}?size=256"

        # Add title with emoji icon
        container.add_item(ui.TextDisplay(f"### <:emoji:1398729407065100359> {i18n.get('commands.emoji.view.title', locale=self.locale, name=emoji_name)}"))

        # Add MediaGallery with emoji image (256px)
        container.add_item(
            ui.MediaGallery(
                discord.MediaGalleryItem(media=emoji_url_display)
            )
        )

        # Add emoji information
        name_label = i18n.get("commands.emoji.view.name", locale=self.locale)
        id_label = i18n.get("commands.emoji.view.id", locale=self.locale)
        created_label = i18n.get("commands.emoji.view.created", locale=self.locale)
        animated_label = i18n.get("commands.emoji.view.animated", locale=self.locale)

        # Format animated status with emojis
        animated_status = "<:done:1398729525277229066>" if is_animated else "<:undone:1398729502028333218>"

        # Build info text
        info_text = f"**{name_label}:** `{emoji_name}`\n"
        info_text += f"**{id_label}:** `{emoji_id}`\n"
        info_text += f"**{created_label}:** <t:{created_at}:R>\n"
        info_text += f"**{animated_label}:** {animated_status}"

        container.add_item(ui.TextDisplay(info_text))

        # Add download links with different sizes
        container.add_item(
            ui.TextDisplay(f"**Download:** [128]({emoji_url}?size=128) • [256]({emoji_url}?size=256) • [512]({emoji_url}?size=512) • [1024]({emoji_url}?size=1024)")
        )

        # Add container to view
        self.add_item(container)


class Emoji(commands.Cog):
    """Emoji command system"""

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def extract_emoji_info(emoji_str: str) -> Optional[tuple[str, str, bool]]:
        """
        Extracts emoji ID, name, and whether it's animated from emoji string

        Returns:
            tuple[emoji_id, emoji_name, is_animated_format] or None if invalid
        """
        # Match custom Discord emoji format: <:name:id> or <a:name:id>
        pattern = r'<(a)?:([^:]+):(\d+)>'
        match = re.match(pattern, emoji_str)

        if match:
            is_animated_format = bool(match.group(1))  # 'a' prefix for animated
            emoji_name = match.group(2)
            emoji_id = match.group(3)
            return emoji_id, emoji_name, is_animated_format

        return None

    @staticmethod
    def snowflake_to_timestamp(snowflake_id: str) -> int:
        """
        Converts a Discord snowflake ID to Unix timestamp

        Returns:
            Unix timestamp in seconds
        """
        # Discord epoch (first second of 2015)
        DISCORD_EPOCH = 1420070400000

        # Extract timestamp from snowflake
        timestamp_ms = (int(snowflake_id) >> 22) + DISCORD_EPOCH

        # Convert to seconds
        return int(timestamp_ms / 1000)

    @staticmethod
    async def check_if_animated(emoji_id: str) -> bool:
        """
        Checks if an emoji is animated by attempting to fetch the GIF version

        Returns:
            True if animated, False otherwise
        """
        gif_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"

        async with aiohttp.ClientSession() as session:
            async with session.get(gif_url) as resp:
                # If we get a 200, it's animated
                # If we get an error response with JSON, it's not animated
                if resp.status == 200:
                    return True

                try:
                    data = await resp.json()
                    # Discord returns {"message": "Invalid resource..."} for non-animated emojis
                    if "message" in data and "Invalid resource" in data["message"]:
                        return False
                except:
                    pass

                return False

    @app_commands.command(
        name="emoji",
        description="Display information about a Discord emoji"
    )
    @app_commands.describe(
        emoji="The emoji to lookup",
        incognito="Make response visible only to you"
    )
    @add_incognito_option()
    async def emoji_command(
        self,
        interaction: discord.Interaction,
        emoji: str,
        incognito: Optional[bool] = None
    ):
        """Display information about a Discord emoji"""
        # Get the ephemeral mode
        ephemeral = get_incognito_setting(interaction)

        # Get the user's locale
        locale = i18n.get_user_locale(interaction)

        # Send loading message
        loading_msg = i18n.get("commands.emoji.loading", locale=locale)
        await interaction.response.send_message(loading_msg, ephemeral=ephemeral)

        # Try to extract emoji info
        emoji_info = self.extract_emoji_info(emoji)

        if not emoji_info:
            # Check if it's a default Unicode emoji (no custom format)
            # Unicode emojis don't have the <:name:id> format
            error_msg = i18n.get("commands.emoji.errors.default_emoji", locale=locale, emoji=emoji)
            await interaction.edit_original_response(content=error_msg)
            return

        emoji_id, emoji_name, is_animated_format = emoji_info

        # Check if emoji is actually animated by trying to fetch the GIF
        is_animated = await self.check_if_animated(emoji_id)

        # Get creation timestamp from snowflake
        created_timestamp = self.snowflake_to_timestamp(emoji_id)

        # Build emoji data
        emoji_data = {
            "id": emoji_id,
            "name": emoji_name,
            "animated": is_animated,
            "created_at": created_timestamp
        }

        # Create the view with emoji data
        view = EmojiView(emoji_data, locale)

        # Send response with Components V2
        await interaction.edit_original_response(
            content=None,
            view=view
        )


async def setup(bot):
    await bot.add_cog(Emoji(bot))
