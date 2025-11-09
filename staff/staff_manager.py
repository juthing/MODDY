"""
Staff Management Commands
Commands for managing staff members, roles, and permissions
"""

import discord
from discord.ext import commands
from discord import ui
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
    create_staff_info_message
)

logger = logging.getLogger('moddy.staff_manager')


class RoleSelectView(ui.View):
    """View for selecting staff roles"""

    def __init__(self, target_user: discord.User, modifier: discord.User, perm_manager):
        super().__init__(timeout=300)
        self.target_user = target_user
        self.modifier = modifier
        self.perm_manager = perm_manager
        self.selected_roles: List[StaffRole] = []
        self.denied_commands: List[str] = []

    @ui.select(
        placeholder="Select roles for this staff member",
        min_values=0,
        max_values=7,
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
    async def role_select(self, interaction: discord.Interaction, select: ui.Select):
        """Handle role selection"""
        # Verify it's the modifier
        if interaction.user.id != self.modifier.id:
            await interaction.response.send_message(
                "❌ Only the command initiator can use this menu.",
                ephemeral=True
            )
            return

        # Convert values to StaffRole enums
        self.selected_roles = [StaffRole(v) for v in select.values]

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

    @ui.button(label="Confirm", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
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

            # Create success embed
            embed = discord.Embed(
                title="✅ Staff Roles Updated",
                description=f"Roles for {self.target_user.mention} have been updated.",
                color=COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(
                name="Roles Assigned",
                value="\n".join([f"• {role.value}" for role in self.selected_roles]),
                inline=False
            )

            embed.set_footer(text=f"Modified by {self.modifier}")

            await interaction.response.edit_message(embed=embed, view=None)

        except Exception as e:
            logger.error(f"Error assigning roles: {e}")
            await interaction.response.send_message(
                f"❌ Error assigning roles: {str(e)}",
                ephemeral=True
            )

    @ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel role assignment"""
        if interaction.user.id != self.modifier.id:
            await interaction.response.send_message(
                "❌ Only the command initiator can use this button.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="❌ Cancelled",
            description="Role assignment cancelled.",
            color=COLORS["error"]
        )

        await interaction.response.edit_message(embed=embed, view=None)


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

            embed = discord.Embed(
                title="✅ Command Restrictions Updated",
                description=f"Command restrictions for {self.target_user.mention} have been updated.",
                color=COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )

            if commands:
                embed.add_field(
                    name="Denied Commands",
                    value="\n".join([f"• `{cmd}`" for cmd in commands]),
                    inline=False
                )
            else:
                embed.add_field(
                    name="Denied Commands",
                    value="None - All restrictions removed",
                    inline=False
                )

            embed.set_footer(text=f"Modified by {self.modifier}")

            await interaction.response.send_message(embed=embed, ephemeral=True)

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
        # Parse user mention
        if not message.mentions:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> m.rank @user`\n\nMention a user to add them to the staff team."
            )
            await message.reply(view=view, mention_author=False)
            return

        target_user = message.mentions[0]

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

        # Open role selection
        view = RoleSelectView(target_user, message.author, staff_permissions)

        embed = discord.Embed(
            title="👥 Add Staff Member",
            description=f"Adding {target_user.mention} to the staff team.\n\nSelect the roles for this staff member:",
            color=COLORS["primary"],
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.reply(embed=embed, view=view, mention_author=False)

    async def handle_setstaff_command(self, message: discord.Message, args: str):
        """
        Handle m.setstaff command - Manage staff permissions
        Usage: <@1373916203814490194> m.setstaff @user
        """
        # Parse user mention
        if not message.mentions:
            view = create_error_message(
                "Invalid Usage",
                "**Usage:** `<@1373916203814490194> m.setstaff @user`\n\nMention a user to manage their permissions."
            )
            await message.reply(view=view, mention_author=False)
            return

        target_user = message.mentions[0]

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

        # Create management view
        view = ui.View(timeout=300)

        # Add role management button
        async def edit_roles_callback(interaction: discord.Interaction):
            if interaction.user.id != message.author.id:
                await interaction.response.send_message("❌ Only the command initiator can use this.", ephemeral=True)
                return

            role_view = RoleSelectView(target_user, message.author, staff_permissions)
            embed = discord.Embed(
                title="✏️ Edit Roles",
                description=f"Editing roles for {target_user.mention}\n\nSelect the new roles:",
                color=COLORS["primary"]
            )
            await interaction.response.send_message(embed=embed, view=role_view, ephemeral=True)

        edit_roles_btn = ui.Button(label="Edit Roles", style=discord.ButtonStyle.primary, emoji="✏️")
        edit_roles_btn.callback = edit_roles_callback
        view.add_item(edit_roles_btn)

        # Add deny commands button
        async def deny_commands_callback(interaction: discord.Interaction):
            if interaction.user.id != message.author.id:
                await interaction.response.send_message("❌ Only the command initiator can use this.", ephemeral=True)
                return

            modal = DenyCommandModal(target_user, message.author)
            await interaction.response.send_modal(modal)

        deny_cmd_btn = ui.Button(label="Manage Command Restrictions", style=discord.ButtonStyle.secondary, emoji="🚫")
        deny_cmd_btn.callback = deny_commands_callback
        view.add_item(deny_cmd_btn)

        # Create info embed
        embed = discord.Embed(
            title="👤 Staff Member Management",
            description=f"Managing permissions for {target_user.mention}",
            color=COLORS["primary"],
            timestamp=datetime.now(timezone.utc)
        )

        # Add current roles
        if current_roles:
            embed.add_field(
                name="Current Roles",
                value="\n".join([f"• {role.value}" for role in current_roles]),
                inline=False
            )
        else:
            embed.add_field(
                name="Current Roles",
                value="*No roles assigned*",
                inline=False
            )

        # Add denied commands
        if denied_commands:
            embed.add_field(
                name="Denied Commands",
                value="\n".join([f"• `{cmd}`" for cmd in denied_commands]),
                inline=False
            )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.reply(embed=embed, view=view, mention_author=False)

    async def handle_stafflist_command(self, message: discord.Message, args: str):
        """
        Handle m.stafflist command - List all staff members
        Usage: <@1373916203814490194> m.stafflist
        """
        staff_members = await db.get_all_staff_members()

        if not staff_members:
            embed = discord.Embed(
                title="📋 Staff List",
                description="No staff members found.",
                color=COLORS["info"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Group by roles
        by_role = {}
        for member in staff_members:
            for role_str in member['roles']:
                if role_str not in by_role:
                    by_role[role_str] = []
                by_role[role_str].append(member['user_id'])

        embed = discord.Embed(
            title="📋 MODDY Staff Team",
            description=f"Total staff members: **{len(staff_members)}**",
            color=COLORS["primary"],
            timestamp=datetime.now(timezone.utc)
        )

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
                embed.add_field(
                    name=f"{role_str} ({len(members)})",
                    value=", ".join(member_mentions),
                    inline=False
                )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.reply(embed=embed, mention_author=False)

    async def handle_staffinfo_command(self, message: discord.Message, args: str):
        """
        Handle m.staffinfo command - Show info about a staff member
        Usage: <@1373916203814490194> m.staffinfo @user
        """
        # Parse user mention or use self
        target_user = message.mentions[0] if message.mentions else message.author

        # Get permissions
        perms = await db.get_staff_permissions(target_user.id)

        if not perms['roles'] and not self.bot.is_developer(target_user.id):
            embed = discord.Embed(
                title="❌ Not Staff",
                description=f"{target_user.mention} is not a staff member.",
                color=COLORS["error"]
            )
            await message.reply(embed=embed, mention_author=False)
            return

        # Create info embed
        embed = discord.Embed(
            title="👤 Staff Member Information",
            color=COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_author(name=str(target_user), icon_url=target_user.display_avatar.url)

        # Add roles
        roles = [StaffRole(r).value for r in perms['roles']] if perms['roles'] else []
        if self.bot.is_developer(target_user.id) and "Dev" not in roles:
            roles.insert(0, "Dev (Auto)")
        if self.bot.is_developer(target_user.id) and "Manager" not in roles:
            roles.insert(0, "Manager (Auto)")

        embed.add_field(
            name="Roles",
            value="\n".join([f"• {role}" for role in roles]) if roles else "*No roles*",
            inline=False
        )

        # Add denied commands
        if perms['denied_commands']:
            embed.add_field(
                name="Command Restrictions",
                value="\n".join([f"• `{cmd}`" for cmd in perms['denied_commands']]),
                inline=False
            )

        # Add timestamps
        if perms['created_at']:
            embed.add_field(
                name="Joined Staff",
                value=f"<t:{int(perms['created_at'].timestamp())}:R>",
                inline=True
            )

        if perms['updated_at']:
            embed.add_field(
                name="Last Updated",
                value=f"<t:{int(perms['updated_at'].timestamp())}:R>",
                inline=True
            )

        embed.set_footer(text=f"Requested by {message.author}")

        await message.reply(embed=embed, mention_author=False)


async def setup(bot):
    await bot.add_cog(StaffManagement(bot))
