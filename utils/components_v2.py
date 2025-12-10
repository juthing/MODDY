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
    # Core emojis
    'done': '<:done:1398729525277229066>',
    'undone': '<:undone:1398729502028333218>',
    'error': '<error:1444049460924776478>',
    'info': '<:info:1401614681440784477>',
    'warning': '<:warning:1446108410092195902>',
    'sync': '<:sync:1398729150885269546>',
    'user': '<:user:1398729712204779571>',
    'dev': '<:dev:1398729645557285066>',
    'settings': '<:settings:1398729549323440208>',
    'blacklist': '<:blacklist:1401596866478477363>',
    'time': '<:time:1398729780723060736>',
    'snowflake': '<:snowflake:1398729841938792458>',
    'web': '<:web:1398729801061240883>',
    'moddy': '<:moddy:1396880909117947924>',
    'loading': '<:loading:1395047662092550194>',
    'history': '<:history:1401600464587456512>',
    'delete': '<:delete:1401600770431909939>',
    'commands': '<:commands:1401610449136648283>',
    'book': '<:book:1446557736350388364>',
    'code': '<:code:1401610523803652196>',
    'bug': '<:bug:1401614189482475551>',
    'logout': '<:logout:1401603690858676224>',
    'verified': '<:verified:1398729677601902635>',
    'next': '<next:1443745574972031067>',
    'back': '<:back:1401600847733067806>',
    'note': '<note:1443749708857085982>',
    'message': '<message:1443749710073696286>',
    'search': '<search:1443752796460552232>',
    'save': '<save:1444101502154182778>',
    'reply': '<reply:1444821779444138146>',
    'groups': '<:groups:1446127489842806967>',
    'waving_hand': '<:waving_hand:1446127491004760184>',
    'flag': '<:flag:1446197210198048778>',
    'toggle_off': '<:toggle_off:1446267399786594514>',
    'toggle_on': '<:toogle_on:1446267419034386473>',
    'at': '<:at:1446199071013470319>',
    'star': '<:star:1446267438671859832>',
    'required_fields': '<:required_fields:1446549185385074769>',
    # Staff badges
    'supportagent_badge': '<:supportagent_badge:1437514361861177350>',
    'moderator_badge': '<:moderator_badge:1437514357230796891>',
    'mod_supervisor_badge': '<:mod_supervisor_badge:1437514356135821322>',
    'comunication_badge': '<:comunication_badge:1437514353304670268>',
    'support_supervisor_badge': '<:support_supervisor_badge:1437514347923636435>',
    'supervisor_badge': '<:supervisor_badge:1437514346476470405>',
    'moddyteam_badge': '<:moddyteam_badge:1437514344467398837>',
    'manager_badge': '<:manager_badge:1437514336355483749>',
    'dev_badge': '<:dev_badge:1437514335009247274>',
    'communication_supervisor_badge': '<:communication_supervisor_badge:1437514333763535068>',
    # Other badges
    'premium_badge': '<:premium_badge:1437514360758075514>',
    'partner_badge': '<:partener_badge:1437514359294263388>',
    'contributor_badge': '<:contributor_badge:1437514354802036940>',
    'certif_badge': '<:Certif_badge:1437514351774011392>',
    'bughunter_badge': '<:BugHunter_badge:1437514350406668318>',
    'blacklisted_badge': '<:Blacklisted_badge:1437514349152571452>',
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

    error_text = f"{EMOJIS['error']} **{title}**\n{description}"
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


def create_blacklist_message() -> LayoutView:
    """
    Create the blacklist error message using Components V2

    Returns:
        LayoutView with blacklist message and unblacklist request button
    """
    view = LayoutView()
    container = Container()

    # Message de blacklist avec emoji
    blacklist_text = (
        f"{EMOJIS['undone']} **Account Blacklisted**\n"
        "You cannot interact with Moddy because your account has been blacklisted by our team.\n"
        "-# If you believe this is a mistake, you can submit an unblacklist request."
    )
    container.add_item(TextDisplay(blacklist_text))

    # Ajouter le container à la vue
    view.add_item(container)

    # Ajouter le bouton dans un ActionRow
    button_row = discord.ui.ActionRow()
    button = discord.ui.Button(
        label="Unblacklist Request",
        url="https://moddy.app/unbl_request",
        style=discord.ButtonStyle.link
    )
    button_row.add_item(button)
    view.add_item(button_row)

    return view
