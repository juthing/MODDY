"""
Avatar command for Moddy
Displays a user's avatar with Components V2
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional

from utils.incognito import add_incognito_option, get_incognito_setting
from utils.i18n import i18n


class AvatarView(ui.LayoutView):
    """View to display user avatar using Components V2"""

    def __init__(self, user: discord.User, locale: str):
        super().__init__(timeout=180)
        self.user = user
        self.locale = locale

        # Build the view
        self.build_view()

    def build_view(self):
        """Builds the Components V2 view"""
        # Clear existing items
        self.clear_items()

        # Create main container
        container = ui.Container()

        # Add title
        title = i18n.get("commands.avatar.view.title", locale=self.locale, user=self.user.display_name)
        container.add_item(ui.TextDisplay(title))

        # Add separator
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # User information
        user_info = f"**{i18n.get('commands.avatar.view.username', locale=self.locale)}** `{self.user.name}`\n"
        user_info += f"**{i18n.get('commands.avatar.view.user_id', locale=self.locale)}** `{self.user.id}`"

        if self.user.bot:
            user_info += f"\n**{i18n.get('commands.avatar.view.bot', locale=self.locale)}** {i18n.get('common.yes', locale=self.locale)}"

        container.add_item(ui.TextDisplay(user_info))

        # Add separator
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Avatar links
        links_text = i18n.get("commands.avatar.view.links", locale=self.locale)
        avatar_url = self.user.display_avatar.url
        avatar_url_512 = self.user.display_avatar.replace(size=512).url
        avatar_url_1024 = self.user.display_avatar.replace(size=1024).url
        avatar_url_2048 = self.user.display_avatar.replace(size=2048).url

        links = f"**{links_text}**\n"
        links += f"• [512x512]({avatar_url_512})\n"
        links += f"• [1024x1024]({avatar_url_1024})\n"
        links += f"• [2048x2048]({avatar_url_2048})"

        container.add_item(ui.TextDisplay(links))

        # Add container to view
        self.add_item(container)


class Avatar(commands.Cog):
    """Avatar command system"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="avatar",
        description="Affiche l'avatar d'un utilisateur / Display a user's avatar"
    )
    @app_commands.describe(
        user="L'utilisateur dont vous voulez voir l'avatar / The user whose avatar you want to see",
        incognito="Rendre la réponse visible uniquement pour vous / Make response visible only to you"
    )
    @add_incognito_option()
    async def avatar_command(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        incognito: Optional[bool] = None
    ):
        """Display a user's avatar"""
        # Get the ephemeral mode
        ephemeral = get_incognito_setting(interaction)

        # Get the user's locale
        locale = i18n.get_user_locale(interaction)

        # Create the view
        view = AvatarView(user, locale)

        # Send response with Components V2
        # Note: Components V2 cannot be used with embeds
        await interaction.response.send_message(
            view=view,
            ephemeral=ephemeral
        )


async def setup(bot):
    await bot.add_cog(Avatar(bot))
