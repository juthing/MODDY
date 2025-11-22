"""
Reminder system for Moddy
Uses APScheduler for task scheduling and PostgreSQL for persistence
"""
import asyncio
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
from discord.ui import LayoutView, Container, TextDisplay, Separator
from discord import SeparatorSpacing

from utils.i18n import t

logger = logging.getLogger('moddy.reminder')

# Common timezones grouped by region
TIMEZONE_GROUPS = {
    "Europe": [
        ("Europe/London", "London (GMT/BST)"),
        ("Europe/Paris", "Paris, Berlin, Rome (CET)"),
        ("Europe/Athens", "Athens, Helsinki (EET)"),
        ("Europe/Moscow", "Moscow (MSK)"),
    ],
    "Americas": [
        ("America/New_York", "New York (EST/EDT)"),
        ("America/Chicago", "Chicago (CST/CDT)"),
        ("America/Denver", "Denver (MST/MDT)"),
        ("America/Los_Angeles", "Los Angeles (PST/PDT)"),
        ("America/Sao_Paulo", "Sao Paulo (BRT)"),
        ("America/Mexico_City", "Mexico City (CST)"),
    ],
    "Asia/Pacific": [
        ("Asia/Tokyo", "Tokyo (JST)"),
        ("Asia/Shanghai", "Shanghai, Beijing (CST)"),
        ("Asia/Seoul", "Seoul (KST)"),
        ("Asia/Singapore", "Singapore (SGT)"),
        ("Asia/Dubai", "Dubai (GST)"),
        ("Asia/Kolkata", "Mumbai, Delhi (IST)"),
        ("Australia/Sydney", "Sydney (AEST/AEDT)"),
        ("Pacific/Auckland", "Auckland (NZST/NZDT)"),
    ],
    "Other": [
        ("UTC", "UTC (Coordinated Universal Time)"),
        ("Africa/Cairo", "Cairo (EET)"),
        ("Africa/Johannesburg", "Johannesburg (SAST)"),
    ]
}

# Flatten for quick lookup
ALL_TIMEZONES = {}
for group, tzs in TIMEZONE_GROUPS.items():
    for tz_id, tz_name in tzs:
        ALL_TIMEZONES[tz_id] = tz_name


def parse_time_string(time_str: str, user_tz: ZoneInfo) -> Optional[datetime]:
    """Parse a time string into a datetime object in UTC

    Supports formats:
    - Relative: 1h, 30m, 2d, 1h30m, 2d3h
    - Absolute: 15:30, 3pm, 15h30
    - Date + time: 25/12 15:30, 25/12/2024 15:30
    - Natural: tomorrow 3pm, demain 15h
    """
    time_str = time_str.strip().lower()
    now = datetime.now(user_tz)

    # Try relative time first (1h, 30m, 2d, 1h30m, etc.)
    relative_pattern = r'^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?$'
    match = re.match(relative_pattern, time_str.replace(' ', ''))
    if match and any(match.groups()):
        days = int(match.group(1) or 0)
        hours = int(match.group(2) or 0)
        minutes = int(match.group(3) or 0)

        if days == 0 and hours == 0 and minutes == 0:
            return None

        result = now + timedelta(days=days, hours=hours, minutes=minutes)
        return result.astimezone(ZoneInfo('UTC'))

    # Try "tomorrow" or "demain"
    tomorrow_match = re.match(r'^(tomorrow|demain)\s*(.*)$', time_str)
    if tomorrow_match:
        time_part = tomorrow_match.group(2).strip()
        target_date = now.date() + timedelta(days=1)

        if time_part:
            parsed_time = parse_time_only(time_part)
            if parsed_time:
                result = datetime.combine(target_date, parsed_time, tzinfo=user_tz)
                return result.astimezone(ZoneInfo('UTC'))
        else:
            # Default to 9:00 AM
            result = datetime.combine(target_date, datetime.strptime("09:00", "%H:%M").time(), tzinfo=user_tz)
            return result.astimezone(ZoneInfo('UTC'))

    # Try date + time: DD/MM HH:MM or DD/MM/YYYY HH:MM
    date_time_pattern = r'^(\d{1,2})/(\d{1,2})(?:/(\d{4}))?\s+(.+)$'
    match = re.match(date_time_pattern, time_str)
    if match:
        day = int(match.group(1))
        month = int(match.group(2))
        year = int(match.group(3)) if match.group(3) else now.year
        time_part = match.group(4)

        parsed_time = parse_time_only(time_part)
        if parsed_time:
            try:
                target_date = datetime(year, month, day, tzinfo=user_tz)
                result = datetime.combine(target_date.date(), parsed_time, tzinfo=user_tz)
                # If the date is in the past this year, try next year
                if result < now and not match.group(3):
                    result = result.replace(year=year + 1)
                return result.astimezone(ZoneInfo('UTC'))
            except ValueError:
                return None

    # Try time only (today or tomorrow if past)
    parsed_time = parse_time_only(time_str)
    if parsed_time:
        result = datetime.combine(now.date(), parsed_time, tzinfo=user_tz)
        # If the time is in the past, assume tomorrow
        if result <= now:
            result = result + timedelta(days=1)
        return result.astimezone(ZoneInfo('UTC'))

    return None


def parse_time_only(time_str: str) -> Optional[datetime]:
    """Parse time-only strings like 15:30, 3pm, 15h30"""
    time_str = time_str.strip().lower()

    # Try HH:MM format
    match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()

    # Try HHhMM format (French)
    match = re.match(r'^(\d{1,2})h(\d{2})?$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()

    # Try 12-hour format (3pm, 3:30pm)
    match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        period = match.group(3)

        if hour == 12:
            hour = 0 if period == 'am' else 12
        elif period == 'pm':
            hour += 12

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()

    return None


def format_relative_time(target: datetime, locale: str = "en") -> str:
    """Format a relative time string"""
    now = datetime.now(ZoneInfo('UTC'))
    if target.tzinfo is None:
        target = target.replace(tzinfo=ZoneInfo('UTC'))

    diff = target - now
    total_seconds = int(diff.total_seconds())

    if total_seconds < 0:
        # Past
        total_seconds = abs(total_seconds)
        is_past = True
    else:
        is_past = False

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []
    if locale.startswith("fr"):
        if days > 0:
            parts.append(f"{days}j")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")
    else:
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or not parts:
            parts.append(f"{minutes}m")

    result = " ".join(parts)
    if is_past:
        if locale.startswith("fr"):
            return f"il y a {result}"
        return f"{result} ago"
    return result


def format_datetime_for_user(dt: datetime, user_tz: ZoneInfo, locale: str = "en") -> str:
    """Format a datetime for display to user in their timezone"""
    local_dt = dt.astimezone(user_tz)
    if locale.startswith("fr"):
        return local_dt.strftime("%d/%m/%Y %H:%M")
    return local_dt.strftime("%m/%d/%Y %I:%M %p")


class TimezoneSelect(ui.Select):
    """Select menu for timezone selection"""

    def __init__(self, group: str, timezones: List[tuple], locale: str, pending_reminder: Dict = None):
        self.locale = locale
        self.pending_reminder = pending_reminder

        options = [
            discord.SelectOption(label=name[:100], value=tz_id, description=tz_id)
            for tz_id, name in timezones
        ]

        super().__init__(
            placeholder=t("commands.reminder.timezone_setup.placeholder", locale=locale),
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

        # If there's a pending reminder, create it now
        if self.pending_reminder:
            pr = self.pending_reminder
            user_tz = ZoneInfo(selected_tz)
            remind_at = parse_time_string(pr['time_str'], user_tz)

            if remind_at and remind_at > datetime.now(ZoneInfo('UTC')):
                reminder_id = await interaction.client.db.create_reminder(
                    user_id=interaction.user.id,
                    message=pr['message'],
                    remind_at=remind_at,
                    guild_id=pr.get('guild_id'),
                    channel_id=pr.get('channel_id'),
                    send_in_channel=pr.get('send_in_channel', False)
                )

                # Show success
                view = LayoutView()
                container = Container()
                container.add_item(TextDisplay(t("commands.reminder.add.title", interaction)))
                container.add_item(Separator(spacing=SeparatorSpacing.small))
                container.add_item(TextDisplay(t("commands.reminder.add.description", interaction, message=pr['message'])))
                container.add_item(TextDisplay(t("commands.reminder.add.time_field", interaction,
                    time=format_datetime_for_user(remind_at, user_tz, str(interaction.locale)))))
                container.add_item(TextDisplay(t("commands.reminder.add.relative_field", interaction,
                    relative=format_relative_time(remind_at, str(interaction.locale)))))

                if pr.get('send_in_channel') and pr.get('channel_id'):
                    container.add_item(TextDisplay(t("commands.reminder.add.location_channel", interaction,
                        channel_id=pr['channel_id'])))
                else:
                    container.add_item(TextDisplay(t("commands.reminder.add.location_dm", interaction)))

                container.add_item(Separator(spacing=SeparatorSpacing.small))
                container.add_item(TextDisplay(f"-# Reminder #{reminder_id}"))
                view.add_item(container)

                await interaction.response.edit_message(view=view)
            else:
                await interaction.response.edit_message(
                    content=t("commands.reminder.errors.invalid_time", interaction),
                    view=None
                )
        else:
            # Just timezone change confirmation
            await interaction.response.edit_message(
                content=t("commands.reminder.timezone_setup.success", interaction, timezone=selected_tz),
                view=None
            )


class TimezoneSetupView(LayoutView):
    """View for initial timezone setup"""

    def __init__(self, user_id: int, locale: str, pending_reminder: Dict = None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.locale = locale
        self.pending_reminder = pending_reminder

        container = Container()
        container.add_item(TextDisplay(t("commands.reminder.timezone_setup.title", locale=locale)))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(t("commands.reminder.timezone_setup.description", locale=locale)))
        container.add_item(Separator(spacing=SeparatorSpacing.small))

        # Add select menus for each timezone group
        for group_name, timezones in TIMEZONE_GROUPS.items():
            row = discord.ui.ActionRow()
            select = TimezoneSelect(group_name, timezones, locale, pending_reminder)
            row.add_item(select)
            container.add_item(row)

        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t("commands.reminder.errors.author_only", interaction),
                ephemeral=True
            )
            return False
        return True


class ReminderAddModal(ui.Modal):
    """Modal for adding a new reminder"""

    def __init__(self, locale: str, bot, channel_id: int = None, guild_id: int = None):
        super().__init__(title=t("commands.reminder.modals.add_title", locale=locale))
        self.locale = locale
        self.bot = bot
        self.channel_id = channel_id
        self.guild_id = guild_id

        self.message_input = ui.TextInput(
            label=t("commands.reminder.modals.add_message_label", locale=locale),
            placeholder=t("commands.reminder.modals.add_message_placeholder", locale=locale),
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.message_input)

        self.time_input = ui.TextInput(
            label=t("commands.reminder.modals.add_time_label", locale=locale),
            placeholder=t("commands.reminder.modals.add_time_placeholder", locale=locale),
            style=discord.TextStyle.short,
            max_length=50,
            required=True
        )
        self.add_item(self.time_input)

    async def on_submit(self, interaction: discord.Interaction):
        message = self.message_input.value
        time_str = self.time_input.value

        # Get user timezone
        user_data = await self.bot.db.get_user(interaction.user.id)
        user_tz_str = user_data.get('data', {}).get('reminder_timezone')

        if not user_tz_str:
            # Need to set timezone first
            view = TimezoneSetupView(
                interaction.user.id,
                str(interaction.locale),
                pending_reminder={
                    'message': message,
                    'time_str': time_str,
                    'channel_id': self.channel_id,
                    'guild_id': self.guild_id,
                    'send_in_channel': self.channel_id is not None
                }
            )
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        user_tz = ZoneInfo(user_tz_str)
        remind_at = parse_time_string(time_str, user_tz)

        if not remind_at:
            await interaction.response.send_message(
                t("commands.reminder.errors.invalid_time", interaction),
                ephemeral=True
            )
            return

        if remind_at <= datetime.now(ZoneInfo('UTC')):
            await interaction.response.send_message(
                t("commands.reminder.errors.past_time", interaction),
                ephemeral=True
            )
            return

        # Check max reminders
        existing = await self.bot.db.get_user_reminders(interaction.user.id)
        if len(existing) >= 50:
            await interaction.response.send_message(
                t("commands.reminder.errors.max_reminders", interaction),
                ephemeral=True
            )
            return

        # Create reminder
        reminder_id = await self.bot.db.create_reminder(
            user_id=interaction.user.id,
            message=message,
            remind_at=remind_at,
            guild_id=self.guild_id,
            channel_id=self.channel_id,
            send_in_channel=self.channel_id is not None
        )

        # Show success
        view = LayoutView()
        container = Container()
        container.add_item(TextDisplay(t("commands.reminder.add.title", interaction)))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(t("commands.reminder.add.description", interaction, message=message)))
        container.add_item(TextDisplay(t("commands.reminder.add.time_field", interaction,
            time=format_datetime_for_user(remind_at, user_tz, str(interaction.locale)))))
        container.add_item(TextDisplay(t("commands.reminder.add.relative_field", interaction,
            relative=format_relative_time(remind_at, str(interaction.locale)))))

        if self.channel_id:
            container.add_item(TextDisplay(t("commands.reminder.add.location_channel", interaction,
                channel_id=self.channel_id)))
        else:
            container.add_item(TextDisplay(t("commands.reminder.add.location_dm", interaction)))

        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(f"-# Reminder #{reminder_id}"))
        view.add_item(container)

        await interaction.response.send_message(view=view, ephemeral=True)


class ReminderEditModal(ui.Modal):
    """Modal for editing a reminder"""

    def __init__(self, locale: str, bot, reminder: Dict):
        super().__init__(title=t("commands.reminder.modals.edit_title", locale=locale))
        self.locale = locale
        self.bot = bot
        self.reminder = reminder

        self.message_input = ui.TextInput(
            label=t("commands.reminder.modals.edit_message_label", locale=locale),
            default=reminder['message'],
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.message_input)

        self.time_input = ui.TextInput(
            label=t("commands.reminder.modals.edit_time_label", locale=locale),
            placeholder=t("commands.reminder.modals.add_time_placeholder", locale=locale),
            style=discord.TextStyle.short,
            max_length=50,
            required=False
        )
        self.add_item(self.time_input)

    async def on_submit(self, interaction: discord.Interaction):
        message = self.message_input.value
        time_str = self.time_input.value.strip() if self.time_input.value else None

        new_remind_at = None
        if time_str:
            user_data = await self.bot.db.get_user(interaction.user.id)
            user_tz_str = user_data.get('data', {}).get('reminder_timezone', 'UTC')
            user_tz = ZoneInfo(user_tz_str)

            new_remind_at = parse_time_string(time_str, user_tz)
            if not new_remind_at:
                await interaction.response.send_message(
                    t("commands.reminder.errors.invalid_time", interaction),
                    ephemeral=True
                )
                return

            if new_remind_at <= datetime.now(ZoneInfo('UTC')):
                await interaction.response.send_message(
                    t("commands.reminder.errors.past_time", interaction),
                    ephemeral=True
                )
                return

        # Update reminder
        await self.bot.db.update_reminder(
            self.reminder['id'],
            interaction.user.id,
            message=message,
            remind_at=new_remind_at
        )

        await interaction.response.send_message(
            t("commands.reminder.success.edited", interaction, id=self.reminder['id']),
            ephemeral=True
        )


class ReminderSelectForEdit(ui.Select):
    """Select menu for choosing a reminder to edit"""

    def __init__(self, reminders: List[Dict], locale: str, bot):
        self.reminders_map = {str(r['id']): r for r in reminders}
        self.locale = locale
        self.bot = bot

        options = []
        for i, reminder in enumerate(reminders[:25], 1):
            label = f"{i}. {reminder['message'][:50]}"
            if len(reminder['message']) > 50:
                label += "..."
            options.append(discord.SelectOption(
                label=label,
                value=str(reminder['id'])
            ))

        super().__init__(
            placeholder=t("commands.reminder.modals.select_reminder_edit", locale=locale),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        reminder = self.reminders_map.get(self.values[0])
        if reminder:
            modal = ReminderEditModal(self.locale, self.bot, reminder)
            await interaction.response.send_modal(modal)


class ReminderSelectForDelete(ui.Select):
    """Select menu for choosing a reminder to delete"""

    def __init__(self, reminders: List[Dict], locale: str, bot):
        self.reminders_map = {str(r['id']): r for r in reminders}
        self.locale = locale
        self.bot = bot

        options = []
        for i, reminder in enumerate(reminders[:25], 1):
            label = f"{i}. {reminder['message'][:50]}"
            if len(reminder['message']) > 50:
                label += "..."
            options.append(discord.SelectOption(
                label=label,
                value=str(reminder['id'])
            ))

        super().__init__(
            placeholder=t("commands.reminder.modals.select_reminder_delete", locale=locale),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        reminder_id = int(self.values[0])
        await self.bot.db.delete_reminder(reminder_id, interaction.user.id)
        await interaction.response.send_message(
            t("commands.reminder.success.deleted", interaction, id=reminder_id),
            ephemeral=True
        )


class TimezoneChangeSelect(ui.Select):
    """Select menu for changing timezone"""

    def __init__(self, group: str, timezones: List[tuple], locale: str):
        self.locale = locale

        options = [
            discord.SelectOption(label=name[:100], value=tz_id, description=tz_id)
            for tz_id, name in timezones
        ]

        super().__init__(
            placeholder=t("commands.reminder.timezone_setup.placeholder", locale=locale),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_tz = self.values[0]

        await interaction.client.db.update_user_data(
            interaction.user.id,
            "reminder_timezone",
            selected_tz
        )

        await interaction.response.send_message(
            t("commands.reminder.success.timezone_changed", interaction, timezone=selected_tz),
            ephemeral=True
        )


class RemindersManageView(LayoutView):
    """Main view for managing reminders"""

    def __init__(self, bot, user_id: int, reminders: List[Dict], locale: str,
                 user_tz: ZoneInfo, show_history: bool = False, past_reminders: List[Dict] = None):
        super().__init__(timeout=300)
        self.bot = bot
        self.user_id = user_id
        self.locale = locale
        self.user_tz = user_tz
        self.show_history = show_history
        self.reminders = reminders
        self.past_reminders = past_reminders or []

        self._build_view()

    def _build_view(self):
        container = Container()

        if self.show_history:
            # History view
            container.add_item(TextDisplay(t("commands.reminder.manage.history_title", locale=self.locale)))
            container.add_item(Separator(spacing=SeparatorSpacing.small))

            if not self.past_reminders:
                container.add_item(TextDisplay(t("commands.reminder.manage.history_empty", locale=self.locale)))
            else:
                for i, reminder in enumerate(self.past_reminders[:15], 1):
                    sent_at = reminder.get('sent_at')
                    if sent_at:
                        time_str = format_relative_time(sent_at, self.locale)
                    else:
                        time_str = "N/A"

                    if reminder.get('failed'):
                        item_text = t("commands.reminder.manage.history_item_failed", locale=self.locale,
                            index=i, message=reminder['message'][:100], time=time_str)
                    else:
                        item_text = t("commands.reminder.manage.history_item", locale=self.locale,
                            index=i, message=reminder['message'][:100], time=time_str)
                    container.add_item(TextDisplay(item_text))

                container.add_item(Separator(spacing=SeparatorSpacing.small))
                container.add_item(TextDisplay(t("commands.reminder.manage.history_footer", locale=self.locale,
                    count=len(self.past_reminders))))

            # Back button
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            back_row = discord.ui.ActionRow()
            back_btn = discord.ui.Button(
                emoji=discord.PartialEmoji.from_str("<:back:1401600847733067806>"),
                label=t("commands.reminder.buttons.back", locale=self.locale),
                style=discord.ButtonStyle.secondary,
                custom_id="back_btn"
            )
            back_btn.callback = self.back_callback
            back_row.add_item(back_btn)
            container.add_item(back_row)
        else:
            # Main reminders view
            container.add_item(TextDisplay(t("commands.reminder.manage.title", locale=self.locale)))
            container.add_item(Separator(spacing=SeparatorSpacing.small))

            if not self.reminders:
                container.add_item(TextDisplay(t("commands.reminder.manage.no_reminders", locale=self.locale)))
            else:
                for i, reminder in enumerate(self.reminders[:15], 1):
                    remind_at = reminder['remind_at']
                    if remind_at.tzinfo is None:
                        remind_at = remind_at.replace(tzinfo=ZoneInfo('UTC'))

                    relative = format_relative_time(remind_at, self.locale)
                    time_str = format_datetime_for_user(remind_at, self.user_tz, self.locale)

                    if reminder.get('send_in_channel') and reminder.get('channel_id'):
                        item_text = t("commands.reminder.manage.reminder_item_channel", locale=self.locale,
                            index=i, message=reminder['message'][:100], relative=relative,
                            time=time_str, channel_id=reminder['channel_id'])
                    else:
                        item_text = t("commands.reminder.manage.reminder_item", locale=self.locale,
                            index=i, message=reminder['message'][:100], relative=relative, time=time_str)
                    container.add_item(TextDisplay(item_text))

            # Get user timezone for footer
            tz_name = ALL_TIMEZONES.get(str(self.user_tz), str(self.user_tz))
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            container.add_item(TextDisplay(t("commands.reminder.manage.footer", locale=self.locale,
                count=len(self.reminders), timezone=tz_name)))

            # Action buttons row 1
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            btn_row1 = discord.ui.ActionRow()

            # Add button
            add_btn = discord.ui.Button(
                emoji=discord.PartialEmoji.from_str("<:add:1439697866049323090>"),
                label=t("commands.reminder.buttons.add", locale=self.locale),
                style=discord.ButtonStyle.success,
                custom_id="add_btn"
            )
            add_btn.callback = self.add_callback
            btn_row1.add_item(add_btn)

            # Edit button (disabled if no reminders)
            edit_btn = discord.ui.Button(
                emoji=discord.PartialEmoji.from_str("<:edit:1401600709824086169>"),
                label=t("commands.reminder.buttons.edit", locale=self.locale),
                style=discord.ButtonStyle.primary,
                custom_id="edit_btn",
                disabled=len(self.reminders) == 0
            )
            edit_btn.callback = self.edit_callback
            btn_row1.add_item(edit_btn)

            # Delete button (disabled if no reminders)
            delete_btn = discord.ui.Button(
                emoji=discord.PartialEmoji.from_str("<:delete:1401600770431909939>"),
                label=t("commands.reminder.buttons.delete", locale=self.locale),
                style=discord.ButtonStyle.danger,
                custom_id="delete_btn",
                disabled=len(self.reminders) == 0
            )
            delete_btn.callback = self.delete_callback
            btn_row1.add_item(delete_btn)

            container.add_item(btn_row1)

            # Action buttons row 2
            btn_row2 = discord.ui.ActionRow()

            # Timezone button
            tz_btn = discord.ui.Button(
                emoji=discord.PartialEmoji.from_str("<:time:1398729780723060736>"),
                label=t("commands.reminder.buttons.timezone", locale=self.locale),
                style=discord.ButtonStyle.secondary,
                custom_id="tz_btn"
            )
            tz_btn.callback = self.timezone_callback
            btn_row2.add_item(tz_btn)

            # History button
            history_btn = discord.ui.Button(
                emoji=discord.PartialEmoji.from_str("<:history:1401600464587456512>"),
                label=t("commands.reminder.buttons.history", locale=self.locale),
                style=discord.ButtonStyle.secondary,
                custom_id="history_btn"
            )
            history_btn.callback = self.history_callback
            btn_row2.add_item(history_btn)

            container.add_item(btn_row2)

        self.add_item(container)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                t("commands.reminder.errors.author_only", interaction),
                ephemeral=True
            )
            return False
        return True

    async def add_callback(self, interaction: discord.Interaction):
        modal = ReminderAddModal(self.locale, self.bot)
        await interaction.response.send_modal(modal)

    async def edit_callback(self, interaction: discord.Interaction):
        if not self.reminders:
            return

        view = LayoutView()
        container = Container()
        container.add_item(TextDisplay(t("commands.reminder.modals.select_reminder_edit", locale=self.locale)))

        row = discord.ui.ActionRow()
        select = ReminderSelectForEdit(self.reminders, self.locale, self.bot)
        row.add_item(select)
        container.add_item(row)

        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def delete_callback(self, interaction: discord.Interaction):
        if not self.reminders:
            return

        view = LayoutView()
        container = Container()
        container.add_item(TextDisplay(t("commands.reminder.modals.select_reminder_delete", locale=self.locale)))

        row = discord.ui.ActionRow()
        select = ReminderSelectForDelete(self.reminders, self.locale, self.bot)
        row.add_item(select)
        container.add_item(row)

        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def timezone_callback(self, interaction: discord.Interaction):
        view = LayoutView()
        container = Container()
        container.add_item(TextDisplay(t("commands.reminder.timezone_setup.title", locale=self.locale)))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(t("commands.reminder.timezone_setup.current", locale=self.locale,
            timezone=ALL_TIMEZONES.get(str(self.user_tz), str(self.user_tz)))))
        container.add_item(Separator(spacing=SeparatorSpacing.small))

        for group_name, timezones in TIMEZONE_GROUPS.items():
            row = discord.ui.ActionRow()
            select = TimezoneChangeSelect(group_name, timezones, self.locale)
            row.add_item(select)
            container.add_item(row)

        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def history_callback(self, interaction: discord.Interaction):
        past = await self.bot.db.get_user_past_reminders(self.user_id)

        # Create new view with history
        new_view = RemindersManageView(
            self.bot, self.user_id, self.reminders, self.locale,
            self.user_tz, show_history=True, past_reminders=past
        )
        await interaction.response.edit_message(view=new_view)

    async def back_callback(self, interaction: discord.Interaction):
        # Return to main view
        new_view = RemindersManageView(
            self.bot, self.user_id, self.reminders, self.locale,
            self.user_tz, show_history=False
        )
        await interaction.response.edit_message(view=new_view)


class Reminder(commands.Cog):
    """Reminder system for Moddy"""

    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @tasks.loop(seconds=30)
    async def check_reminders(self):
        """Check for due reminders and send them"""
        if not self.bot.db or not self.bot.db.pool:
            return

        try:
            pending = await self.bot.db.get_pending_reminders()

            for reminder in pending:
                await self.send_reminder(reminder)
        except Exception as e:
            logger.error(f"Error checking reminders: {e}")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        """Wait for bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()

        # On startup, send any missed reminders
        logger.info("Checking for missed reminders...")
        await asyncio.sleep(5)  # Give DB time to initialize

        if self.bot.db and self.bot.db.pool:
            try:
                pending = await self.bot.db.get_pending_reminders()
                logger.info(f"Found {len(pending)} missed reminders to send")

                for reminder in pending:
                    await self.send_reminder(reminder, is_late=True)
            except Exception as e:
                logger.error(f"Error sending missed reminders: {e}")

    async def send_reminder(self, reminder: Dict, is_late: bool = False):
        """Send a reminder to the user"""
        user_id = reminder['user_id']
        channel_id = reminder.get('channel_id')
        guild_id = reminder.get('guild_id')
        send_in_channel = reminder.get('send_in_channel', False)

        # Get user
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            await self.bot.db.mark_reminder_sent(reminder['id'], failed=True)
            return

        # Build the reminder message
        view = LayoutView()
        container = Container()
        container.add_item(TextDisplay(t("commands.reminder.notification.title", locale="en")))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(f"> {reminder['message']}"))

        if is_late:
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            container.add_item(TextDisplay(t("commands.reminder.notification.late_notice", locale="en")))

        created_at = reminder.get('created_at')
        if created_at:
            container.add_item(Separator(spacing=SeparatorSpacing.small))
            container.add_item(TextDisplay(f"-# Created {format_relative_time(created_at, 'en')} ago"))

        view.add_item(container)

        sent = False

        # Try to send in channel if requested
        if send_in_channel and channel_id and guild_id:
            try:
                guild = self.bot.get_guild(guild_id)
                if guild:
                    # Check if user is still in the guild
                    member = guild.get_member(user_id)
                    if member:
                        channel = guild.get_channel(channel_id)
                        if channel and channel.permissions_for(guild.me).send_messages:
                            await channel.send(f"<@{user_id}>", view=view)
                            sent = True
            except Exception as e:
                logger.warning(f"Could not send reminder to channel: {e}")

        # Fallback to DM
        if not sent:
            try:
                await user.send(view=view)
                sent = True
            except discord.Forbidden:
                logger.warning(f"Could not DM user {user_id}")
                sent = False

        # Mark as sent
        await self.bot.db.mark_reminder_sent(reminder['id'], failed=not sent)

    @app_commands.command(
        name="reminder-add",
        description="Add a new reminder"
    )
    @app_commands.describe(
        message="What should I remind you?",
        time="When to remind (e.g. 1h30m, 2d, tomorrow 3pm)",
        send_here="Send reminder in this channel instead of DM"
    )
    async def reminder_add(
        self,
        interaction: discord.Interaction,
        message: str,
        time: str,
        send_here: Optional[bool] = False
    ):
        """Add a new reminder"""
        # Validate message length
        if len(message) > 1000:
            await interaction.response.send_message(
                t("commands.reminder.errors.too_long", interaction),
                ephemeral=True
            )
            return

        # Get user timezone
        user_data = await self.bot.db.get_user(interaction.user.id)
        user_tz_str = user_data.get('data', {}).get('reminder_timezone')

        # Channel info for "send here" option
        channel_id = interaction.channel_id if send_here else None
        guild_id = interaction.guild_id if send_here else None

        if not user_tz_str:
            # First time user - show timezone setup
            view = TimezoneSetupView(
                interaction.user.id,
                str(interaction.locale),
                pending_reminder={
                    'message': message,
                    'time_str': time,
                    'channel_id': channel_id,
                    'guild_id': guild_id,
                    'send_in_channel': send_here
                }
            )
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        user_tz = ZoneInfo(user_tz_str)
        remind_at = parse_time_string(time, user_tz)

        if not remind_at:
            await interaction.response.send_message(
                t("commands.reminder.errors.invalid_time", interaction),
                ephemeral=True
            )
            return

        if remind_at <= datetime.now(ZoneInfo('UTC')):
            await interaction.response.send_message(
                t("commands.reminder.errors.past_time", interaction),
                ephemeral=True
            )
            return

        # Check max reminders
        existing = await self.bot.db.get_user_reminders(interaction.user.id)
        if len(existing) >= 50:
            await interaction.response.send_message(
                t("commands.reminder.errors.max_reminders", interaction),
                ephemeral=True
            )
            return

        # Create reminder
        reminder_id = await self.bot.db.create_reminder(
            user_id=interaction.user.id,
            message=message,
            remind_at=remind_at,
            guild_id=guild_id,
            channel_id=channel_id,
            send_in_channel=send_here
        )

        # Show success
        view = LayoutView()
        container = Container()
        container.add_item(TextDisplay(t("commands.reminder.add.title", interaction)))
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(t("commands.reminder.add.description", interaction, message=message)))
        container.add_item(TextDisplay(t("commands.reminder.add.time_field", interaction,
            time=format_datetime_for_user(remind_at, user_tz, str(interaction.locale)))))
        container.add_item(TextDisplay(t("commands.reminder.add.relative_field", interaction,
            relative=format_relative_time(remind_at, str(interaction.locale)))))

        if send_here and channel_id:
            container.add_item(TextDisplay(t("commands.reminder.add.location_channel", interaction,
                channel_id=channel_id)))
        else:
            container.add_item(TextDisplay(t("commands.reminder.add.location_dm", interaction)))

        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(f"-# Reminder #{reminder_id}"))
        view.add_item(container)

        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(
        name="reminders",
        description="Manage your reminders"
    )
    async def reminders(self, interaction: discord.Interaction):
        """Manage reminders"""
        # Get user timezone
        user_data = await self.bot.db.get_user(interaction.user.id)
        user_tz_str = user_data.get('data', {}).get('reminder_timezone')

        if not user_tz_str:
            # First time - need to set timezone
            view = TimezoneSetupView(interaction.user.id, str(interaction.locale))
            await interaction.response.send_message(view=view, ephemeral=True)
            return

        user_tz = ZoneInfo(user_tz_str)

        # Get user's reminders
        reminders = await self.bot.db.get_user_reminders(interaction.user.id)

        # Create management view
        view = RemindersManageView(
            self.bot,
            interaction.user.id,
            reminders,
            str(interaction.locale),
            user_tz
        )

        await interaction.response.send_message(view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Reminder(bot))
