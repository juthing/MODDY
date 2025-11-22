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

    def __init__(self, locale: str, current_tz: str = None):
        self.locale = locale

        options = []
        for tz_id, name in TIMEZONE_OPTIONS:
            option = discord.SelectOption(
                label=name[:100],
                value=tz_id,
                description=tz_id,
                default=(tz_id == current_tz)
            )
            options.append(option)

        super().__init__(
            placeholder=t("commands.preferences.timezone.placeholder", locale=locale),
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        selected_tz = self.values[0]

        # Save timezone to user data
        await interaction.client.db.update_user_data(
            interaction.user.id,
            "reminder_timezone",
            selected_tz
        )

        await interaction.response.send_message(
            t("commands.preferences.timezone.success", interaction, timezone=TIMEZONE_NAMES.get(selected_tz, selected_tz)),
            ephemeral=True
        )


class PreferencesView(LayoutView):
    """Main preferences view"""

    def __init__(self, bot, user_id: int, locale: str, user_data: dict):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.locale = locale
        self.user_data = user_data

        self._build_view()

    def _build_view(self):
        container = Container()

        # Title
        container.add_item(TextDisplay(t("commands.preferences.title", locale=self.locale)))
        container.add_item(Separator(spacing=SeparatorSpacing.small))

        # Description
        container.add_item(TextDisplay(t("commands.preferences.description", locale=self.locale)))
        container.add_item(Separator(spacing=SeparatorSpacing.small))

        # Current timezone
        current_tz = self.user_data.get('data', {}).get('reminder_timezone')
        if current_tz:
            tz_display = TIMEZONE_NAMES.get(current_tz, current_tz)
        else:
            # Show auto-detected timezone
            default_tz = get_default_timezone(self.locale)
            tz_display = f"{TIMEZONE_NAMES.get(default_tz, default_tz)} ({t('commands.preferences.timezone.auto_detected', locale=self.locale)})"

        container.add_item(TextDisplay(t("commands.preferences.timezone.current", locale=self.locale, timezone=tz_display)))

        # Timezone select
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(t("commands.preferences.timezone.label", locale=self.locale)))

        tz_row = discord.ui.ActionRow()
        tz_select = TimezoneSelect(self.locale, current_tz)
        tz_row.add_item(tz_select)
        container.add_item(tz_row)

        # Footer with tip
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(t("commands.preferences.footer", locale=self.locale)))

        self.add_item(container)

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
    async def preferences(self, interaction: discord.Interaction):
        """Open preferences menu"""
        # Get user data
        user_data = await self.bot.db.get_user(interaction.user.id)

        # Create preferences view
        view = PreferencesView(
            self.bot,
            interaction.user.id,
            str(interaction.locale),
            user_data
        )

        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Preferences(bot))
