"""
User preferences command for Moddy
Allows users to customize their experience
"""
import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.ui import LayoutView, Container, TextDisplay, Separator
from discord import SeparatorSpacing
from typing import Optional

from utils.i18n import t

# Common timezones for selection
TIMEZONE_OPTIONS = [
    ("Europe/London", "London (GMT/BST)"),
    ("Europe/Paris", "Paris, Berlin, Rome (CET)"),
    ("Europe/Athens", "Athens, Helsinki (EET)"),
    ("Europe/Moscow", "Moscow (MSK)"),
    ("America/New_York", "New York (EST/EDT)"),
    ("America/Chicago", "Chicago (CST/CDT)"),
    ("America/Denver", "Denver (MST/MDT)"),
    ("America/Los_Angeles", "Los Angeles (PST/PDT)"),
    ("America/Sao_Paulo", "Sao Paulo (BRT)"),
    ("America/Mexico_City", "Mexico City (CST)"),
    ("Asia/Tokyo", "Tokyo (JST)"),
    ("Asia/Shanghai", "Shanghai, Beijing (CST)"),
    ("Asia/Seoul", "Seoul (KST)"),
    ("Asia/Singapore", "Singapore (SGT)"),
    ("Asia/Dubai", "Dubai (GST)"),
    ("Asia/Kolkata", "Mumbai, Delhi (IST)"),
    ("Australia/Sydney", "Sydney (AEST/AEDT)"),
    ("Pacific/Auckland", "Auckland (NZST/NZDT)"),
    ("UTC", "UTC"),
]

TIMEZONE_NAMES = {tz_id: name for tz_id, name in TIMEZONE_OPTIONS}

# Mapping of Discord locales to default timezones
LOCALE_TO_TIMEZONE = {
    "en-US": "America/New_York",
    "en-GB": "Europe/London",
    "fr": "Europe/Paris",
    "de": "Europe/Berlin",
    "es-ES": "Europe/Madrid",
    "es-419": "America/Mexico_City",
    "pt-BR": "America/Sao_Paulo",
    "it": "Europe/Rome",
    "nl": "Europe/Amsterdam",
    "pl": "Europe/Warsaw",
    "ru": "Europe/Moscow",
    "ja": "Asia/Tokyo",
    "zh-CN": "Asia/Shanghai",
    "zh-TW": "Asia/Taipei",
    "ko": "Asia/Seoul",
}


def get_default_timezone(locale: str) -> str:
    """Get default timezone based on Discord locale"""
    locale_str = str(locale)
    if locale_str in LOCALE_TO_TIMEZONE:
        return LOCALE_TO_TIMEZONE[locale_str]
    base_lang = locale_str.split("-")[0]
    if base_lang in LOCALE_TO_TIMEZONE:
        return LOCALE_TO_TIMEZONE[base_lang]
    return "UTC"


class TimezoneSelect(ui.Select):
    """Select menu for timezone selection"""

    def __init__(self, locale: str, current_tz: Optional[str], bot, parent_view=None):
        self.locale = locale
        self.bot = bot
        self.parent_view = parent_view

        # Build options
        options = []
        for tz_id, name in TIMEZONE_OPTIONS:
            options.append(discord.SelectOption(
                label=name[:100],
                value=tz_id,
                description=tz_id,
                default=(tz_id == current_tz)
            ))

        super().__init__(
            placeholder=t("commands.preferences.timezone.placeholder", locale=locale),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle timezone selection"""
        selected_tz = self.values[0]

        # Save timezone to user data
        await self.bot.db.update_user_data(
            interaction.user.id,
            "reminder_timezone",
            selected_tz
        )

        # Send confirmation
        await interaction.response.send_message(
            t("commands.preferences.timezone.success", interaction, timezone=TIMEZONE_NAMES.get(selected_tz, selected_tz)),
            ephemeral=True
        )

        # Refresh the parent view if it exists
        if self.parent_view:
            await self.parent_view.refresh(interaction)


class PreferencesView(LayoutView):
    """Main preferences view"""

    def __init__(self, bot, user_id: int, locale: str, user_data: dict, original_interaction: discord.Interaction = None):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.locale = locale
        self.user_data = user_data
        self.original_interaction = original_interaction

        self._build_view()

    def _build_view(self):
        # Clear existing items
        self.clear_items()

        container = Container()

        # Title and description
        container.add_item(TextDisplay(t("commands.preferences.title", locale=self.locale)))
        container.add_item(TextDisplay(t("commands.preferences.main_description", locale=self.locale)))

        # Current timezone display
        current_tz = self.user_data.get('data', {}).get('reminder_timezone')
        if current_tz:
            tz_display = TIMEZONE_NAMES.get(current_tz, current_tz)
        else:
            default_tz = get_default_timezone(self.locale)
            tz_display = f"{TIMEZONE_NAMES.get(default_tz, default_tz)} ({t('commands.preferences.timezone.auto_detected', locale=self.locale)})"

        container.add_item(TextDisplay(t("commands.preferences.timezone.current", locale=self.locale, timezone=tz_display)))

        container.add_item(Separator(spacing=SeparatorSpacing.small))

        # Manage timezone button
        btn_row = discord.ui.ActionRow()
        tz_btn = discord.ui.Button(
            emoji=discord.PartialEmoji.from_str("<:time:1398729780723060736>"),
            label=t("commands.preferences.buttons.manage_timezone", locale=self.locale),
            style=discord.ButtonStyle.primary,
            custom_id="timezone_btn"
        )
        tz_btn.callback = self.timezone_callback
        btn_row.add_item(tz_btn)
        container.add_item(btn_row)

        # Footer
        container.add_item(TextDisplay(t("commands.preferences.footer", locale=self.locale)))

        self.add_item(container)

    async def refresh(self, interaction: discord.Interaction):
        """Refresh the view with updated data"""
        # Fetch fresh data
        self.user_data = await self.bot.db.get_user(self.user_id)

        # Rebuild the view
        self._build_view()

        # Update the original message
        if self.original_interaction:
            try:
                await self.original_interaction.edit_original_response(view=self)
            except Exception:
                pass

    async def timezone_callback(self, interaction: discord.Interaction):
        """Show timezone settings - sends NEW view like reminder.py does"""
        current_tz = self.user_data.get('data', {}).get('reminder_timezone')

        # Create NEW LayoutView - same pattern as reminder.py edit_callback
        view = LayoutView()
        container = Container()
        container.add_item(TextDisplay(t("commands.preferences.timezone.title", locale=self.locale)))
        container.add_item(TextDisplay(t("commands.preferences.timezone.label", locale=self.locale)))

        # Add select in ActionRow - same pattern as reminder.py
        row = discord.ui.ActionRow()
        select = TimezoneSelect(self.locale, current_tz, self.bot, parent_view=self)
        row.add_item(select)
        container.add_item(row)

        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t("commands.preferences.errors.author_only", interaction),
                ephemeral=True
            )
            return False
        return True


class Preferences(commands.Cog):
    """User preferences management"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="preferences",
        description="Manage your personal preferences"
    )
    @app_commands.describe(
        incognito="Make response visible only to you"
    )
    async def preferences(
        self,
        interaction: discord.Interaction,
        incognito: Optional[bool] = None
    ):
        """Open preferences menu"""
        # Handle incognito setting
        if incognito is None and self.bot.db:
            try:
                user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                ephemeral = True if user_pref is None else user_pref
            except:
                ephemeral = True
        else:
            ephemeral = incognito if incognito is not None else True

        # Get user data
        user_data = await self.bot.db.get_user(interaction.user.id)

        # Create preferences view
        view = PreferencesView(
            self.bot,
            interaction.user.id,
            str(interaction.locale),
            user_data,
            original_interaction=interaction
        )

        await interaction.response.send_message(view=view, ephemeral=ephemeral)


async def setup(bot):
    await bot.add_cog(Preferences(bot))
