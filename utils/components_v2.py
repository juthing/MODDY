"""
Components V2 Helper for Discord.py
Utilities for creating structured messages using Discord's Components V2
"""

import discord
from discord.ui import LayoutView, Container, TextDisplay, Separator
from discord import SeparatorSpacing
from typing import List, Optional, Dict

# Emojis personnalisés du bot
EMOJIS = {
    'done': '<:done:1398729525277229066>',
    'undone': '<:undone:1398729502028333218>',
    'info': '<:info:1401614681440784477>',
    'sync': '<:sync:1398729150885269546>',
    'user': '<:user:1398729712204779571>',
    'dev': '<:dev:1398729645557285066>',
    'settings': '<:settings:1398729549323440208>',
    'blacklist': '<:blacklist:1401596864784777363>',
    'time': '<:time:1398729780723060736>',
    'snowflake': '<:snowflake:1398729841938792458>',
    'web': '<:web:1398729801061240883>',
    'moddy': '<:moddy:1396880909117947924>',
    'loading': '<:loading:1395047662092550194>',
    'history': '<:history:1401600464587456512>',
    'delete': '<:delete:1401600770431909939>',
    'commands': '<:commands:1401610449136648283>',
    'code': '<:code:1401610523803652196>',
    'bug': '<:bug:1401614189482475551>',
    'logout': '<:logout:1401603690858676224>',
    'verified': '<:verified:1398729677601902635>',
}


def create_simple_message(
    title: str,
    description: str,
    fields: Optional[List[Dict[str, str]]] = None,
    color: Optional[int] = None,
    footer: Optional[str] = None
) -> LayoutView:
    """
    Create a simple message using Components V2

    Args:
        title: Message title
        description: Message description
        fields: List of dictionaries with 'name' and 'value' keys
        color: Not used in V2, kept for compatibility
        footer: Optional footer text

    Returns:
        LayoutView ready to send
    """
    view = LayoutView()
    container = Container()

    # Add title and description
    header = f"**{title}**\n{description}"
    container.add_item(TextDisplay(header))

    # Add fields if present
    if fields:
        # Add separator before fields
        container.add_item(Separator(spacing=SeparatorSpacing.small))

        for field in fields:
            field_text = f"**{field['name']}**\n{field['value']}"
            container.add_item(TextDisplay(field_text))

    # Add footer if present
    if footer:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(f"*{footer}*"))

    view.add_item(container)
    return view


def create_error_message(title: str, description: str, fields: Optional[List[Dict[str, str]]] = None) -> LayoutView:
    """
    Create an error message using Components V2

    Args:
        title: Error title
        description: Error description
        fields: Optional list of fields

    Returns:
        LayoutView ready to send
    """
    view = LayoutView()
    container = Container()

    error_text = f"{EMOJIS['undone']} **{title}**\n{description}"
    container.add_item(TextDisplay(error_text))

    if fields:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        for field in fields:
            field_text = f"**{field['name']}**\n{field['value']}"
            container.add_item(TextDisplay(field_text))

    view.add_item(container)
    return view


def create_success_message(title: str, description: str, fields: Optional[List[Dict[str, str]]] = None, footer: Optional[str] = None) -> LayoutView:
    """
    Create a success message using Components V2

    Args:
        title: Success title
        description: Success description
        fields: Optional list of fields
        footer: Optional footer text

    Returns:
        LayoutView ready to send
    """
    view = LayoutView()
    container = Container()

    success_text = f"{EMOJIS['done']} **{title}**\n{description}"
    container.add_item(TextDisplay(success_text))

    if fields:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        for field in fields:
            field_text = f"**{field['name']}**\n{field['value']}"
            container.add_item(TextDisplay(field_text))

    if footer:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(f"*{footer}*"))

    view.add_item(container)
    return view


def create_info_message(title: str, description: str, fields: Optional[List[Dict[str, str]]] = None, footer: Optional[str] = None) -> LayoutView:
    """
    Create an info message using Components V2

    Args:
        title: Info title
        description: Info description
        fields: Optional list of fields
        footer: Optional footer text

    Returns:
        LayoutView ready to send
    """
    view = LayoutView()
    container = Container()

    info_text = f"{EMOJIS['info']} **{title}**\n{description}"
    container.add_item(TextDisplay(info_text))

    if fields:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        for field in fields:
            field_text = f"**{field['name']}**\n{field['value']}"
            container.add_item(TextDisplay(field_text))

    if footer:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(f"*{footer}*"))

    view.add_item(container)
    return view


def create_warning_message(title: str, description: str, fields: Optional[List[Dict[str, str]]] = None) -> LayoutView:
    """
    Create a warning message using Components V2

    Args:
        title: Warning title
        description: Warning description
        fields: Optional list of fields

    Returns:
        LayoutView ready to send
    """
    view = LayoutView()
    container = Container()

    warning_text = f"⚠️ **{title}**\n{description}"
    container.add_item(TextDisplay(warning_text))

    if fields:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        for field in fields:
            field_text = f"**{field['name']}**\n{field['value']}"
            container.add_item(TextDisplay(field_text))

    view.add_item(container)
    return view


def create_staff_info_message(
    title: str,
    user_name: str,
    user_id: int,
    fields: List[Dict[str, str]],
    footer: Optional[str] = None
) -> LayoutView:
    """
    Create a staff information message using Components V2

    Args:
        title: Message title
        user_name: User's display name
        user_id: User's ID
        fields: List of information fields
        footer: Optional footer text

    Returns:
        LayoutView ready to send
    """
    view = LayoutView()
    container = Container()

    # Header with user info
    header = f"**{title}**\n*{user_name}* (`{user_id}`)"
    container.add_item(TextDisplay(header))

    # Add separator
    container.add_item(Separator(spacing=SeparatorSpacing.small))

    # Add fields
    for field in fields:
        field_text = f"**{field['name']}**\n{field['value']}"
        container.add_item(TextDisplay(field_text))

    # Add footer if present
    if footer:
        container.add_item(Separator(spacing=SeparatorSpacing.small))
        container.add_item(TextDisplay(f"*{footer}*"))

    view.add_item(container)
    return view
