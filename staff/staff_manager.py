"""
Staff Management Commands
Commands for managing staff members, roles, and permissions
"""

import discord
from discord.ext import commands
from discord import ui
from discord.ui import LayoutView, Container, TextDisplay, Separator, ActionRow, Select, Button
from discord import SeparatorSpacing, SelectOption, ButtonStyle
from typing import Optional, List
import logging
from datetime import datetime, timezone

from utils.staff_permissions import staff_permissions, StaffRole, CommandType
from database import db
from config import COLORS
from utils.components_v2 import (
    create_error_message,
    create_success_message,
    create_info_message,
    create_warning_message,
    create_staff_info_message,
    create_simple_message,
    EMOJIS
)

logger = logging.getLogger('moddy.staff_manager')


class RoleSelectView(ui.View):
    """View for selecting staff roles - Uses ui.View to handle interactions"""

    def __init__(self, target_user: discord.User, modifier: discord.User, perm_manager):
        super().__init__(timeout=300)
        self.target_user = target_user
        self.modifier = modifier
        self.perm_manager = perm_manager
        self.selected_roles: List[StaffRole] = []

        # Add select menu
        select = ui.Select(
            placeholder="Select roles for this staff member",
            min_values=0,
            max_values=7,
            custom_id="role_select_menu",
            options=[
                discord.SelectOption(
                    label="Manager",
                    value=StaffRole.MANAGER.value,
                    description="Can manage all staff and assign roles",
                    emoji="👑"
                ),
                discord.SelectOption(
                    label="Moderator Supervisor",
                    value=StaffRole.SUPERVISOR_MOD.value,
                    description="Supervises moderators",
                    emoji="🛡️"
                ),
                discord.SelectOption(
                    label="Communication Supervisor",
                    value=StaffRole.SUPERVISOR_COM.value,
                    description="Supervises communication team",
                    emoji="📢"
                ),
                discord.SelectOption(
                    label="Support Supervisor",
                    value=StaffRole.SUPERVISOR_SUP.value,
                    description="Supervises support team",
                    emoji="🎫"
                ),
                discord.SelectOption(
                    label="Moderator",
                    value=StaffRole.MODERATOR.value,
                    description="Moderation staff member",
                    emoji="🔨"
                ),
                discord.SelectOption(
                    label="Communication",
                    value=StaffRole.COMMUNICATION.value,
                    description="Communication staff member",
                    emoji="💬"
                ),
                discord.SelectOption(
                    label="Support",
                    value=StaffRole.SUPPORT.value,
                    description="Support staff member",
                    emoji="🎧"
                )
            ]
        )
        select.callback = self.role_select
        self.add_item(select)

        # Add confirm button
        confirm_btn = ui.Button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅", custom_id="confirm_roles")
        confirm_btn.callback = self.confirm_button
        self.add_item(confirm_btn)

        # Add cancel button
        cancel_btn = ui.Button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌", custom_id="cancel_roles")
        cancel_btn.callback = self.cancel_button
        self.add_item(cancel_btn)

    async def role_select(self, interaction: discord.Interaction):
        """Handle role selection"""
        # Verify it's the modifier
        if interaction.user.id != self.modifier.id:
            await interaction.response.send_message(
                "❌ Only the command initiator can use this menu.",
                ephemeral=True
            )
            return

        # Get the select component
        select_component = [item for item in self.children if isinstance(item, ui.Select)][0]

        # Convert values to StaffRole enums
        self.selected_roles = [StaffRole(v) for v in select_component.values]

        # Check if modifier can assign all selected roles
        invalid_roles = []
        for role in self.selected_roles:
            if not await self.perm_manager.can_assign_role(self.modifier.id, role):
                invalid_roles.append(role)

        if invalid_roles:
            await interaction.response.send_message(
                f"❌ You cannot assign the following roles: {', '.join([r.value for r in invalid_roles])}",
                ephemeral=True
            )
            return

        await interaction.response.defer()

    async def confirm_button(self, interaction: discord.Interaction):
        """Confirm role assignment"""
        if interaction.user.id != self.modifier.id:
            await interaction.response.send_message(
                "❌ Only the command initiator can use this button.",
                ephemeral=True
            )
            return

        if not self.selected_roles:
            await interaction.response.send_message(
                "❌ Please select at least one role.",
                ephemeral=True
            )
            return

        # Save roles to database
        try:
            role_values = [role.value for role in self.selected_roles]
            await db.set_staff_roles(self.target_user.id, role_values, self.modifier.id)

            # Create success view
            fields = [{
                'name': 'Roles Assigned',
                'value': "\n".join([f"• {role.value}" for role in self.selected_roles])
            }]

            view = create_success_message(
                "Staff Roles Updated",
                f"Roles for {self.target_user.mention} have been updated.",
                fields=fields,
                footer=f"Modified by {self.modifier}"
            )

            await interaction.response.edit_message(view=view, content=None)

        except Exception as e:
            logger.error(f"Error assigning roles: {e}")
            await interaction.response.send_message(
                f"❌ Error assigning roles: {str(e)}",
                ephemeral=True
            )

    async def cancel_button(self, interaction: discord.Interaction):
        """Cancel role assignment"""
        if interaction.user.id != self.modifier.id:
            await interaction.response.send_message(
                f"{EMOJIS['undone']} Only the command initiator can use this button.",
                ephemeral=True
            )
            return

        view = create_error_message("Cancelled", "Role assignment cancelled.")

        await interaction.response.edit_message(view=view, content=None)


class DenyCommandModal(ui.Modal, title="Deny Specific Commands"):
    """Modal for denying specific commands"""

    command_input = ui.TextInput(
        label="Commands to deny (one per line)",
        style=discord.TextStyle.paragraph,
        placeholder="mod.ban\nmod.kick\nsup.ticket",
        required=False
    )

    def __init__(self, target_user: discord.User, modifier: discord.User):
        super().__init__()
        self.target_user = target_user
        self.modifier = modifier

    async def on_submit(self, interaction: discord.Interaction):
        """Handle command denial submission"""
        commands = [cmd.strip() for cmd in self.command_input.value.split('\n') if cmd.strip()]

        try:
            await db.set_denied_commands(self.target_user.id, commands, self.modifier.id)

            denied_value = "\n".join([f"• `{cmd}`" for cmd in commands]) if commands else "None - All restrictions removed"

            fields = [{
                'name': 'Denied Commands',
                'value': denied_value
            }]

            view = create_success_message(
                "Command Restrictions Updated",
                f"Command restrictions for {self.target_user.mention} have been updated.",
                fields=fields,
                footer=f"Modified by {self.modifier}"
            )

            await interaction.response.send_message(view=view, ephemeral=True)

        except Exception as e:
            logger.error(f"Error setting denied commands: {e}")
            await interaction.response.send_message(
                f"❌ Error updating command restrictions: {str(e)}",
                ephemeral=True
            )


class StaffManagement(commands.Cog):
    """Staff management commands (m. prefix)"""

    def __init__(self, bot):
        self.bot = bot
        # Store pending interactions context
        self.interaction_contexts = {}

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions from Components V2"""
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get('custom_id', '')

        # Handle edit roles button
        if custom_id.startswith('edit_roles_'):
            # Extract session_id (everything after 'edit_roles_')
            session_id = custom_id[len('edit_roles_'):]

            # Get context if stored
            context = self.interaction_contexts.get(session_id)
            if not context:
                await interaction.response.send_message("❌ Session expired. Please run the command again.", ephemeral=True)
                return

            if interaction.user.id != context['modifier_id']:
                await interaction.response.send_message(f"{EMOJIS['undone']} Only the command initiator can use this.", ephemeral=True)
                return

            target_user = await self.bot.fetch_user(context['target_id'])
            modifier = await self.bot.fetch_user(context['modifier_id'])

            role_view = RoleSelectView(target_user, modifier, staff_permissions)

            # Create Components V2 layout for role selection
            class RoleSelectLayout(discord.ui.LayoutView):
                container1 = discord.ui.Container(
                    discord.ui.TextDisplay(content=f"{EMOJIS['settings']} **Edit Roles**\nEditing roles for {target_user.mention}\n\nSelect the new roles below:"),
                )

            layout = RoleSelectLayout()
            await interaction.response.send_message(view=layout, ephemeral=True)
            # Also send the interactive view
            await interaction.followup.send(view=role_view, ephemeral=True)

        # Handle manage restrictions button
        elif custom_id.startswith('manage_restrictions_'):
            # Extract session_id (everything after 'manage_restrictions_')
            session_id = custom_id[len('manage_restrictions_'):]

            # Get context if stored
            context = self.interaction_contexts.get(session_id)
            if not context:
                await interaction.response.send_message("❌ Session expired. Please run the command again.", ephemeral=True)
                return

            if interaction.user.id != context['modifier_id']:
                await interaction.response.send_message("❌ Only the command initiator can use this.", ephemeral=True)
                return

            target_user = await self.bot.fetch_user(context['target_id'])
            modifier = await self.bot.fetch_user(context['modifier_id'])

            modal = DenyCommandModal(target_user, modifier)
            await interaction.response.send_modal(modal)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for staff commands with new syntax"""
        # Ignore bots
        if message.author.bot:
            return

        # Check if staff permissions system is ready
        if not staff_permissions or not db:
            return

        # Parse command
        parsed = staff_permissions.parse_staff_command(message.content)
        if not parsed:
            return

        command_type, command_name, args = parsed

        # Only handle management commands in this cog
        if command_type != CommandType.MANAGEMENT:
            return

        # Log the command attempt
        logger.info(f"👑 Management command '{command_name}' attempted by {message.author} ({message.author.id})")

        # Check if user is in dev team
        is_dev = self.bot.is_developer(message.author.id)
        logger.info(f"   Developer status: {is_dev}")

        # Check permissions
        allowed, reason = await staff_permissions.check_command_permission(
            message.author.id, command_type, command_name
        )

        if not allowed:
            logger.warning(f"   ❌ Permission denied: {reason}")
            view = create_error_message("Permission Denied", reason)
            await message.reply(view=view, mention_author=False)
            return

        logger.info(f"   ✅ Permission granted")

        # Route to appropriate command
        if command_name == "rank":
            await self.handle_rank_command(message, args)
        elif command_name == "unrank":
            await self.handle_unrank_command(message, args)
        elif command_name == "setstaff":
            await self.handle_setstaff_command(message, args)
        elif command_name == "stafflist":
            await self.handle_stafflist_command(message, args)
        elif command_name == "staffinfo":
            await self.handle_staffinfo_command(message, args)
        else:
            view = create_error_message("Unknown Command", f"Management command `{command_name}` not found.")
            await message.reply(view=view, mention_author=False)

    async def handle_rank_command(self, message: discord.Message, args: str):
        """
        Handle m.rank command - Add user to staff team
        Usage: <@1373916203814490194> m.rank @user
        """
        # Parse user mention or ID
        target_user = None

        # Try to get user from mentions (exclude bot mention)
        for mention in message.mentions:
            if mention.id != self.bot.user.id:
                target_user = mention
                break

        # If no mention found, try to parse as ID
        if not target_user and args:
            try:
                user_id = int(args.strip().split()[0])
                target_user = await self.bot.fetch_user(user_id)
            except (ValueError, discord.NotFound, discord.HTTPException):
                pass

        if not target_user:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> m.rank @user` or `<@1373916203814490194> m.rank [user_id]`\n\nMention a user or provide their ID to add them to the staff team."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Can't rank bots
        if target_user.bot:
            view = create_error_message("Invalid Target", "You cannot add bots to the staff team.")
            await message.reply(view=view, mention_author=False)
            return

        # Check if user is already staff
        user_data = await db.get_user(target_user.id)
        if user_data['attributes'].get('TEAM'):
            view = create_warning_message("Already Staff", f"{target_user.mention} is already a staff member.")
            await message.reply(view=view, mention_author=False)
            return

        # Open role selection with Components V2
        button_view = RoleSelectView(target_user, message.author, staff_permissions)

        # Create Components V2 layout
        class RankLayout(discord.ui.LayoutView):
            container1 = discord.ui.Container(
                discord.ui.TextDisplay(content=f"{EMOJIS['user']} **Add Staff Member**\nAdding {target_user.mention} to the staff team.\n\nSelect the roles for this staff member:"),
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(content=f"*Requested by {message.author}*"),
            )

        layout = RankLayout()

        # Send Components V2 layout
        await message.reply(view=layout, mention_author=False)
        # Send interactive view as followup
        await message.channel.send(view=button_view)

    async def handle_unrank_command(self, message: discord.Message, args: str):
        """
        Handle m.unrank command - Remove user from staff team
        Usage: <@1373916203814490194> m.unrank @user
        """
        # Parse user mention or ID
        target_user = None

        # Try to get user from mentions (exclude bot mention)
        for mention in message.mentions:
            if mention.id != self.bot.user.id:
                target_user = mention
                break

        # If no mention found, try to parse as ID
        if not target_user and args:
            try:
                user_id = int(args.strip().split()[0])
                target_user = await self.bot.fetch_user(user_id)
            except (ValueError, discord.NotFound, discord.HTTPException):
                pass

        if not target_user:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> m.unrank @user` or `<@1373916203814490194> m.unrank [user_id]`\n\nMention a user or provide their ID to remove them from the staff team."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Check if target is staff
        user_data = await db.get_user(target_user.id)
        if not user_data['attributes'].get('TEAM'):
            view = create_error_message(
                "Not Staff",
                f"{target_user.mention} is not a staff member."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Check if modifier can modify target
        can_modify = await staff_permissions.can_modify_user(message.author.id, target_user.id)
        if not can_modify:
            view = create_error_message(
                "Permission Denied",
                "You cannot remove this user from the staff team.\n\nYou can only modify staff members below your hierarchy level."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Remove all roles and TEAM attribute
        try:
            # Remove staff permissions (clears roles and denied commands)
            await db.remove_staff_permissions(target_user.id)

            # Remove TEAM attribute
            await db.set_attribute('user', target_user.id, 'TEAM', False, message.author.id, "Removed from staff via m.unrank")

            # Create success message
            view = create_success_message(
                f"{EMOJIS['done']} Staff Member Removed",
                f"{target_user.mention} has been removed from the staff team.",
                footer=f"Removed by {message.author}"
            )

            await message.reply(view=view, mention_author=False)

            # Log the action
            logger.info(f"Staff {message.author} ({message.author.id}) removed {target_user} ({target_user.id}) from staff")

        except Exception as e:
            logger.error(f"Error removing staff member: {e}")
            view = create_error_message(
                "Error",
                f"Failed to remove staff member: {str(e)}"
            )
            await message.reply(view=view, mention_author=False)

    async def handle_setstaff_command(self, message: discord.Message, args: str):
        """
        Handle m.setstaff command - Manage staff permissions
        Usage: <@1373916203814490194> m.setstaff @user
        """
        # Parse user mention or ID
        target_user = None

        # Try to get user from mentions (exclude bot mention)
        for mention in message.mentions:
            if mention.id != self.bot.user.id:
                target_user = mention
                break

        # If no mention found, try to parse as ID
        if not target_user and args:
            try:
                user_id = int(args.strip().split()[0])
                target_user = await self.bot.fetch_user(user_id)
            except (ValueError, discord.NotFound, discord.HTTPException):
                pass

        if not target_user:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> m.setstaff @user` or `<@1373916203814490194> m.setstaff [user_id]`\n\nMention a user or provide their ID to manage their permissions."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Check if target is staff
        user_data = await db.get_user(target_user.id)
        if not user_data['attributes'].get('TEAM') and not self.bot.is_developer(target_user.id):
            view = create_error_message(
                "Not Staff",
                f"{target_user.mention} is not a staff member.\n\nUse `m.rank @user` to add them first."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Check if modifier can modify target
        can_modify = await staff_permissions.can_modify_user(message.author.id, target_user.id)
        if not can_modify:
            view = create_error_message(
                "Permission Denied",
                "You cannot modify this user's permissions.\n\nYou can only modify staff members below your hierarchy level."
            )
            await message.reply(view=view, mention_author=False)
            return

        # Get current permissions
        perms = await db.get_staff_permissions(target_user.id)
        current_roles = [StaffRole(r) for r in perms['roles']] if perms['roles'] else []
        denied_commands = perms['denied_commands']

        # Build role display with badges
        role_display_lines = []
        if current_roles:
            for role in current_roles:
                badge = ""
                if role == StaffRole.DEV:
                    badge = EMOJIS['dev_badge']
                elif role == StaffRole.MANAGER:
                    badge = EMOJIS['manager_badge']
                elif role == StaffRole.SUPERVISOR_MOD:
                    badge = EMOJIS['mod_supervisor_badge']
                elif role == StaffRole.SUPERVISOR_COM:
                    badge = EMOJIS['communication_supervisor_badge']
                elif role == StaffRole.SUPERVISOR_SUP:
                    badge = EMOJIS['support_supervisor_badge']
                elif role == StaffRole.MODERATOR:
                    badge = EMOJIS['moderator_badge']
                elif role == StaffRole.COMMUNICATION:
                    badge = EMOJIS['comunication_badge']
                elif role == StaffRole.SUPPORT:
                    badge = EMOJIS['supportagent_badge']

                role_display_lines.append(f"{badge} {role.value}")
        else:
            role_display_lines.append("*No roles assigned*")

        # Build denied commands display
        denied_display = ""
        if denied_commands:
            denied_display = "\n".join([f"• `{cmd}`" for cmd in denied_commands])

        # Build the container components list dynamically
        container_components = [
            discord.ui.TextDisplay(content=f"{EMOJIS['user']} **Staff Member Management**\nManaging permissions for {target_user.mention}"),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"**Current Roles**\n" + "\n".join(role_display_lines)),
        ]

        # Add denied commands section if exists
        if denied_commands:
            container_components.extend([
                discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
                discord.ui.TextDisplay(content=f"**Denied Commands**\n{denied_display}")
            ])

        # Generate unique session ID for this interaction
        import time
        session_id = f"{int(time.time())}_{message.author.id}_{target_user.id}"

        # Add action buttons
        container_components.extend([
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.ActionRow(
                discord.ui.Button(
                    style=discord.ButtonStyle.primary,
                    label="Edit Roles",
                    custom_id=f"edit_roles_{session_id}",
                    emoji="✏️"
                ),
                discord.ui.Button(
                    style=discord.ButtonStyle.secondary,
                    label="Manage Command Restrictions",
                    custom_id=f"manage_restrictions_{session_id}",
                    emoji="🚫"
                ),
            ),
            discord.ui.Separator(spacing=discord.SeparatorSpacing.small),
            discord.ui.TextDisplay(content=f"*Requested by {message.author}*"),
        ])

        # Create Components V2 LayoutView
        class StaffManagementView(discord.ui.LayoutView):
            container1 = discord.ui.Container(*container_components)

        # Create the layout view
        layout_view = StaffManagementView()

        # Store interaction context for button handling
        self.interaction_contexts[session_id] = {
            'modifier_id': message.author.id,
            'target_id': target_user.id
        }

        # Send the message
        await message.reply(view=layout_view, mention_author=False)

    async def handle_stafflist_command(self, message: discord.Message, args: str):
        """
        Handle m.stafflist command - List all staff members
        Usage: <@1373916203814490194> m.stafflist
        """
        staff_members = await db.get_all_staff_members()

        if not staff_members:
            view = create_info_message("📋 Staff List", "No staff members found.")
            await message.reply(view=view, mention_author=False)
            return

        # Group by roles
        by_role = {}
        for member in staff_members:
            for role_str in member['roles']:
                if role_str not in by_role:
                    by_role[role_str] = []
                by_role[role_str].append(member['user_id'])

        fields = []

        # Add fields for each role
        role_order = [
            StaffRole.MANAGER.value,
            StaffRole.SUPERVISOR_MOD.value,
            StaffRole.SUPERVISOR_COM.value,
            StaffRole.SUPERVISOR_SUP.value,
            StaffRole.MODERATOR.value,
            StaffRole.COMMUNICATION.value,
            StaffRole.SUPPORT.value
        ]

        for role_str in role_order:
            if role_str in by_role:
                members = by_role[role_str]
                member_mentions = [f"<@{uid}>" for uid in members]
                fields.append({
                    'name': f"{role_str} ({len(members)})",
                    'value': ", ".join(member_mentions)
                })

        view = create_info_message(
            "📋 MODDY Staff Team",
            f"Total staff members: **{len(staff_members)}**",
            fields=fields,
            footer=f"Requested by {message.author}"
        )

        await message.reply(view=view, mention_author=False)

    async def handle_staffinfo_command(self, message: discord.Message, args: str):
        """
        Handle m.staffinfo command - Show info about a staff member
        Usage: <@1373916203814490194> m.staffinfo @user
        """
        # Parse user mention or ID or use self
        target_user = None

        # Try to get user from mentions (exclude bot mention)
        for mention in message.mentions:
            if mention.id != self.bot.user.id:
                target_user = mention
                break

        # If no mention found, try to parse as ID
        if not target_user and args:
            try:
                user_id = int(args.strip().split()[0])
                target_user = await self.bot.fetch_user(user_id)
            except (ValueError, discord.NotFound, discord.HTTPException):
                pass

        # If still no target, use command author
        if not target_user:
            target_user = message.author

        # Get permissions
        perms = await db.get_staff_permissions(target_user.id)

        if not perms['roles'] and not self.bot.is_developer(target_user.id):
            view = create_error_message("Not Staff", f"{target_user.mention} is not a staff member.")
            await message.reply(view=view, mention_author=False)
            return

        fields = []

        # Add roles with badges
        role_display = []
        staff_roles = [StaffRole(r) for r in perms['roles']] if perms['roles'] else []

        # Add auto-assigned roles for developers
        if self.bot.is_developer(target_user.id):
            if StaffRole.DEV not in staff_roles:
                role_display.append(f"{EMOJIS['dev_badge']} Dev (Auto)")
            if StaffRole.MANAGER not in staff_roles:
                role_display.append(f"{EMOJIS['manager_badge']} Manager (Auto)")

        # Add regular roles
        for role in staff_roles:
            badge = ""
            if role == StaffRole.DEV:
                badge = EMOJIS['dev_badge']
            elif role == StaffRole.MANAGER:
                badge = EMOJIS['manager_badge']
            elif role == StaffRole.SUPERVISOR_MOD:
                badge = EMOJIS['mod_supervisor_badge']
            elif role == StaffRole.SUPERVISOR_COM:
                badge = EMOJIS['communication_supervisor_badge']
            elif role == StaffRole.SUPERVISOR_SUP:
                badge = EMOJIS['support_supervisor_badge']
            elif role == StaffRole.MODERATOR:
                badge = EMOJIS['moderator_badge']
            elif role == StaffRole.COMMUNICATION:
                badge = EMOJIS['comunication_badge']
            elif role == StaffRole.SUPPORT:
                badge = EMOJIS['supportagent_badge']

            role_display.append(f"{badge} {role.value}")

        fields.append({
            'name': 'Roles',
            'value': "\n".join(role_display) if role_display else "*No roles*"
        })

        # Add denied commands
        if perms['denied_commands']:
            fields.append({
                'name': 'Command Restrictions',
                'value': "\n".join([f"• `{cmd}`" for cmd in perms['denied_commands']])
            })

        # Add timestamps
        if perms['created_at']:
            fields.append({
                'name': f"{EMOJIS['time']} Joined Staff",
                'value': f"<t:{int(perms['created_at'].timestamp())}:R>"
            })

        if perms['updated_at']:
            fields.append({
                'name': f"{EMOJIS['time']} Last Updated",
                'value': f"<t:{int(perms['updated_at'].timestamp())}:R>"
            })

        view = create_info_message(
            f"{EMOJIS['user']} Staff Member Information - {str(target_user)}",
            f"Information about staff member {target_user.mention}",
            fields=fields,
            footer=f"Requested by {message.author}"
        )

        await message.reply(view=view, mention_author=False)


async def setup(bot):
    await bot.add_cog(StaffManagement(bot))
