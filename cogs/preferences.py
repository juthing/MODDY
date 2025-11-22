"""
User preferences command for Moddy
Allows users to customize their experience
"""
import discord
from discord import app_commands, ui
from discord.ext import commands
from discord.ui import LayoutView, Container, TextDisplay
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

    def __init__(self, locale: str, current_tz: str, bot):
        self.locale = locale
        self.bot = bot

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
            options=options,
            min_values=1,
            max_values=1
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


class TimezoneSettingsView(ui.View):
    """View for timezone settings - uses standard View for reliability"""

    def __init__(self, bot, user_id: int, locale: str, current_tz: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.locale = locale

        # Add timezone select
        self.add_item(TimezoneSelect(locale, current_tz, bot))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t("commands.preferences.errors.author_only", interaction),
                ephemeral=True
            )
            return False
        return True


class PreferencesView(ui.View):
    """Main preferences view - uses standard View for reliability"""

    def __init__(self, bot, user_id: int, locale: str, user_data: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.locale = locale
        self.user_data = user_data

    @ui.button(label="Manage timezone", style=discord.ButtonStyle.primary, emoji="<:time:1398729780723060736>")
    async def timezone_button(self, interaction: discord.Interaction, button: ui.Button):
        """Show timezone settings"""
        current_tz = self.user_data.get('data', {}).get('reminder_timezone')

        # Get display for current timezone
        if current_tz:
            tz_display = TIMEZONE_NAMES.get(current_tz, current_tz)
        else:
            default_tz = get_default_timezone(self.locale)
            tz_display = f"{TIMEZONE_NAMES.get(default_tz, default_tz)} ({t('commands.preferences.timezone.auto_detected', locale=self.locale)})"

        # Create timezone settings view
        view = TimezoneSettingsView(self.bot, self.user_id, self.locale, current_tz)

        await interaction.response.send_message(
            f"{t('commands.preferences.timezone.title', locale=self.locale)}\n\n"
            f"{t('commands.preferences.timezone.current', locale=self.locale, timezone=tz_display)}\n\n"
            f"{t('commands.preferences.timezone.label', locale=self.locale)}",
            view=view,
            ephemeral=True
        )

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

        # Create preferences view (standard View, not LayoutView)
        view = PreferencesView(
            self.bot,
            interaction.user.id,
            str(interaction.locale),
            user_data
        )

        # Build message content
        content = (
            f"{t('commands.preferences.title', locale=str(interaction.locale))}\n\n"
            f"{t('commands.preferences.main_description', locale=str(interaction.locale))}\n\n"
            f"{t('commands.preferences.footer', locale=str(interaction.locale))}"
        )

        await interaction.response.send_message(content=content, view=view, ephemeral=ephemeral)


async def setup(bot):
    await bot.add_cog(Preferences(bot))
