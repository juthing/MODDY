"""
User command for Moddy
Display detailed information about a Discord user
"""

import discord
from discord import app_commands, ui
from discord.ext import commands
from typing import Optional
import aiohttp
from datetime import datetime
from config import COLORS, EMOJIS
from utils.i18n import i18n


# Discord badge emojis mapping
# TODO: Add correct emoji IDs from https://github.com/mezotv/discord-badges
# For now, using text representation
DISCORD_BADGES = {
    "staff": "Discord Staff",
    "partner": "Partner",
    "hypesquad": "HypeSquad Events",
    "bug_hunter_level_1": "Bug Hunter",
    "bug_hunter_level_2": "Bug Hunter Gold",
    "hypesquad_bravery": "HypeSquad Bravery",
    "hypesquad_brilliance": "HypeSquad Brilliance",
    "hypesquad_balance": "HypeSquad Balance",
    "early_supporter": "Early Supporter",
    "verified_bot_developer": "Early Verified Bot Developer",
    "active_developer": "Active Developer",
}

# Moddy badge emojis from AGENTS.MD
MODDY_BADGES = {
    "PREMIUM": "<:premium_badge:1437514360758075514>",
    "PARTNER": "<:partener_badge:1437514359294263388>",
    "CONTRIBUTOR": "<:contributor_badge:1437514354802036940>",
    "CERTIF": "<:Certif_badge:1437514351774011392>",
    "BUGHUNTER": "<:BugHunter_badge:1437514350406668318>",
    "BLACKLISTED": "<:Blacklisted_badge:1437514349152571452>",
    "DEVELOPER": "<:dev_badge:1437514335009247274>",
    "MODDYTEAM": "<:moddyteam_badge:1437514344467398837>",
    "MANAGER": "<:manager_badge:1437514336355483749>",
    "SUPERVISOR": "<:supervisor_badge:1437514346476470405>",
    "SUPPORT_SUPERVISOR": "<:support_supervisor_badge:1437514347923636435>",
    "COMMUNICATION_SUPERVISOR": "<:communication_supervisor_badge:1437514333763535068>",
    "MOD_SUPERVISOR": "<:mod_supervisor_badge:1437514356135821322>",
    "MODERATOR": "<:moderator_badge:1437514357230796891>",
    "COMMUNICATION": "<:comunication_badge:1437514353304670268>",
    "SUPPORTAGENT": "<:supportagent_badge:1437514361861177350>",
}


class UserInfoView(ui.LayoutView):
    """View for displaying user information using Components V2"""

    def __init__(self, user_data: dict, bot_data: Optional[dict], moddy_attributes: dict, locale: str, author_id: int, bot):
        super().__init__(timeout=180)
        self.user_data = user_data
        self.bot_data = bot_data
        self.moddy_attributes = moddy_attributes
        self.locale = locale
        self.author_id = author_id
        self.bot = bot

        # Build the view
        self.build_view()

    def build_view(self):
        """Builds the Components V2 view with user information"""
        # Clear existing items
        self.clear_items()

        # Create main container
        container = ui.Container()

        # Title
        title = i18n.get("commands.user.view.title", locale=self.locale, username=self.user_data.get("username", "Unknown"))
        container.add_item(ui.TextDisplay(title))

        # Add separator
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Basic info
        user_id = self.user_data.get("id", "Unknown")
        username = self.user_data.get("username", "Unknown")
        discriminator = self.user_data.get("discriminator", "0")
        global_name = self.user_data.get("global_name", username)

        # Display name
        if discriminator != "0":
            display = f"**{global_name}** (`{username}#{discriminator}`)"
        else:
            display = f"**{global_name}** (`@{username}`)"

        container.add_item(ui.TextDisplay(display))

        # User ID
        id_text = i18n.get("commands.user.view.id", locale=self.locale, id=user_id)
        container.add_item(ui.TextDisplay(id_text))

        # User mention
        mention_text = i18n.get("commands.user.view.mention", locale=self.locale, mention=f"<@{user_id}>")
        container.add_item(ui.TextDisplay(mention_text))

        # Account creation date
        try:
            snowflake_id = int(user_id)
            timestamp = ((snowflake_id >> 22) + 1420070400000) // 1000
            created_at = f"<t:{timestamp}:D> (<t:{timestamp}:R>)"
        except:
            created_at = i18n.get("common.unknown", locale=self.locale)

        creation_text = i18n.get("commands.user.view.created_at", locale=self.locale, date=created_at)
        container.add_item(ui.TextDisplay(creation_text))

        # Add separator before badges
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Discord badges
        discord_badges = self._get_discord_badges()
        if discord_badges:
            badges_title = i18n.get("commands.user.view.discord_badges", locale=self.locale)
            container.add_item(ui.TextDisplay(f"**{badges_title}**"))
            container.add_item(ui.TextDisplay(" ".join(discord_badges)))

        # Moddy badges
        moddy_badges = self._get_moddy_badges()
        if moddy_badges:
            badges_title = i18n.get("commands.user.view.moddy_badges", locale=self.locale)
            container.add_item(ui.TextDisplay(f"**{badges_title}**"))
            container.add_item(ui.TextDisplay(" ".join(moddy_badges)))

        # Profile decorations
        avatar_decoration = self.user_data.get("avatar_decoration_data")
        collectibles = self.user_data.get("collectibles", {})

        if avatar_decoration or collectibles.get("nameplate"):
            container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
            deco_title = i18n.get("commands.user.view.decorations", locale=self.locale)
            container.add_item(ui.TextDisplay(f"**{deco_title}**"))

            if avatar_decoration:
                sku_id = avatar_decoration.get("sku_id")
                if sku_id:
                    deco_link = f"[{i18n.get('commands.user.view.avatar_decoration', locale=self.locale)}](https://discord.com/shop#itemSkuId={sku_id})"
                    container.add_item(ui.TextDisplay(deco_link))

            if collectibles.get("nameplate"):
                nameplate_sku = collectibles["nameplate"].get("sku_id")
                if nameplate_sku:
                    nameplate_link = f"[{i18n.get('commands.user.view.profile_decoration', locale=self.locale)}](https://discord.com/shop#itemSkuId={nameplate_sku})"
                    container.add_item(ui.TextDisplay(nameplate_link))

        # Add container to view
        self.add_item(container)

        # Add action buttons
        self._add_buttons()

    def _get_discord_badges(self) -> list:
        """Get Discord badges for the user"""
        badges = []
        flags = self.user_data.get("public_flags", 0)

        # Check each flag
        if flags & (1 << 0):  # Staff
            badges.append(DISCORD_BADGES.get("staff", ""))
        if flags & (1 << 1):  # Partner
            badges.append(DISCORD_BADGES.get("partner", ""))
        if flags & (1 << 2):  # HypeSquad Events
            badges.append(DISCORD_BADGES.get("hypesquad", ""))
        if flags & (1 << 3):  # Bug Hunter Level 1
            badges.append(DISCORD_BADGES.get("bug_hunter_level_1", ""))
        if flags & (1 << 6):  # House Bravery
            badges.append(DISCORD_BADGES.get("hypesquad_bravery", ""))
        if flags & (1 << 7):  # House Brilliance
            badges.append(DISCORD_BADGES.get("hypesquad_brilliance", ""))
        if flags & (1 << 8):  # House Balance
            badges.append(DISCORD_BADGES.get("hypesquad_balance", ""))
        if flags & (1 << 9):  # Early Supporter
            badges.append(DISCORD_BADGES.get("early_supporter", ""))
        if flags & (1 << 14):  # Bug Hunter Level 2
            badges.append(DISCORD_BADGES.get("bug_hunter_level_2", ""))
        if flags & (1 << 17):  # Verified Bot Developer
            badges.append(DISCORD_BADGES.get("verified_bot_developer", ""))
        if flags & (1 << 22):  # Active Developer
            badges.append(DISCORD_BADGES.get("active_developer", ""))

        return [b for b in badges if b]

    def _get_moddy_badges(self) -> list:
        """Get Moddy badges based on user attributes"""
        badges = []

        for attr_name, badge_emoji in MODDY_BADGES.items():
            if self.moddy_attributes.get(attr_name):
                badges.append(badge_emoji)

        return badges

    def _add_buttons(self):
        """Add action buttons to the view"""
        button_row = ui.ActionRow()

        # Bot Info button (only if user is a bot)
        if self.bot_data:
            bot_info_btn = ui.Button(
                label=i18n.get("commands.user.buttons.bot_info", locale=self.locale),
                style=discord.ButtonStyle.primary,
                emoji="<:code:1401610523803652196>",
                custom_id="bot_info"
            )
            bot_info_btn.callback = self.on_bot_info_click
            button_row.add_item(bot_info_btn)

        # Avatar button
        avatar_btn = ui.Button(
            label=i18n.get("commands.user.buttons.avatar", locale=self.locale),
            style=discord.ButtonStyle.secondary,
            custom_id="avatar"
        )
        avatar_btn.callback = self.on_avatar_click
        button_row.add_item(avatar_btn)

        # Banner button
        if self.user_data.get("banner"):
            banner_btn = ui.Button(
                label=i18n.get("commands.user.buttons.banner", locale=self.locale),
                style=discord.ButtonStyle.secondary,
                custom_id="banner"
            )
            banner_btn.callback = self.on_banner_click
            button_row.add_item(banner_btn)

        self.add_item(button_row)

    async def on_bot_info_click(self, interaction: discord.Interaction):
        """Handle Bot Info button click"""
        # Check if the user is the author
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                i18n.get("commands.user.errors.author_only", locale=self.locale),
                ephemeral=True
            )
            return

        # Create bot info embed
        embed = discord.Embed(
            title=i18n.get("commands.user.bot_info.title", locale=self.locale, name=self.bot_data.get("name", "Unknown")),
            color=COLORS["primary"]
        )

        # Server count
        server_count = i18n.get("common.unknown", locale=self.locale)
        if "approximate_guild_count" in self.bot_data:
            server_count = f"{self.bot_data['approximate_guild_count']:,}"

        # Is public
        is_public = self.bot_data.get("bot_public", False)
        public_text = i18n.get("common.yes" if is_public else "common.no", locale=self.locale)

        # Is verified
        is_verified = self.bot_data.get("is_verified", False)
        verified_text = i18n.get("common.yes" if is_verified else "common.no", locale=self.locale)

        # Support server
        guild_id = self.bot_data.get("guild_id")
        support_server = f"https://discord.gg/{guild_id}" if guild_id else i18n.get("common.none", locale=self.locale)

        # HTTP interactions
        hook = self.bot_data.get("hook", False)
        http_text = i18n.get("common.yes" if hook else "common.no", locale=self.locale)

        # Global commands (check integration types)
        integration_config = self.bot_data.get("integration_types_config", {})
        has_global = "1" in integration_config  # User install
        global_text = i18n.get("common.yes" if has_global else "common.no", locale=self.locale)

        # Intents (based on flags)
        flags = self.bot_data.get("flags", 0)
        intents = []
        if flags & (1 << 12):  # GATEWAY_PRESENCE
            intents.append(i18n.get("commands.user.bot_info.intents.presence", locale=self.locale))
        if flags & (1 << 14):  # GATEWAY_GUILD_MEMBERS
            intents.append(i18n.get("commands.user.bot_info.intents.guild_members", locale=self.locale))
        if flags & (1 << 18):  # GATEWAY_MESSAGE_CONTENT
            intents.append(i18n.get("commands.user.bot_info.intents.message_content", locale=self.locale))

        intents_text = ", ".join(intents) if intents else i18n.get("common.none", locale=self.locale)

        # Add fields
        embed.add_field(
            name=i18n.get("commands.user.bot_info.fields.server_count", locale=self.locale),
            value=server_count,
            inline=True
        )
        embed.add_field(
            name=i18n.get("commands.user.bot_info.fields.public", locale=self.locale),
            value=public_text,
            inline=True
        )
        embed.add_field(
            name=i18n.get("commands.user.bot_info.fields.verified", locale=self.locale),
            value=verified_text,
            inline=True
        )
        embed.add_field(
            name=i18n.get("commands.user.bot_info.fields.support_server", locale=self.locale),
            value=support_server,
            inline=False
        )
        embed.add_field(
            name=i18n.get("commands.user.bot_info.fields.http_interactions", locale=self.locale),
            value=http_text,
            inline=True
        )
        embed.add_field(
            name=i18n.get("commands.user.bot_info.fields.global_commands", locale=self.locale),
            value=global_text,
            inline=True
        )
        embed.add_field(
            name=i18n.get("commands.user.bot_info.fields.intents", locale=self.locale),
            value=intents_text,
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_avatar_click(self, interaction: discord.Interaction):
        """Handle Avatar button click"""
        # Check if the user is the author
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                i18n.get("commands.user.errors.author_only", locale=self.locale),
                ephemeral=True
            )
            return

        user_id = self.user_data.get("id")
        avatar_hash = self.user_data.get("avatar")

        if not avatar_hash:
            await interaction.response.send_message(
                i18n.get("commands.user.errors.no_avatar", locale=self.locale),
                ephemeral=True
            )
            return

        # Build avatar URL
        extension = "gif" if avatar_hash.startswith("a_") else "png"
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{extension}?size=1024"

        # Create embed
        embed = discord.Embed(
            title=i18n.get("commands.user.avatar.title", locale=self.locale, username=self.user_data.get("username", "Unknown")),
            color=COLORS["primary"]
        )
        embed.set_image(url=avatar_url)
        embed.add_field(
            name=i18n.get("commands.user.avatar.download", locale=self.locale),
            value=f"[256]({avatar_url}?size=256) • [512]({avatar_url}?size=512) • [1024]({avatar_url}?size=1024) • [2048]({avatar_url}?size=2048)",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_banner_click(self, interaction: discord.Interaction):
        """Handle Banner button click"""
        # Check if the user is the author
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                i18n.get("commands.user.errors.author_only", locale=self.locale),
                ephemeral=True
            )
            return

        user_id = self.user_data.get("id")
        banner_hash = self.user_data.get("banner")

        if not banner_hash:
            await interaction.response.send_message(
                i18n.get("commands.user.errors.no_banner", locale=self.locale),
                ephemeral=True
            )
            return

        # Build banner URL
        extension = "gif" if banner_hash.startswith("a_") else "png"
        banner_url = f"https://cdn.discordapp.com/banners/{user_id}/{banner_hash}.{extension}?size=1024"

        # Create embed
        embed = discord.Embed(
            title=i18n.get("commands.user.banner.title", locale=self.locale, username=self.user_data.get("username", "Unknown")),
            color=COLORS["primary"]
        )
        embed.set_image(url=banner_url)
        embed.add_field(
            name=i18n.get("commands.user.banner.download", locale=self.locale),
            value=f"[256]({banner_url}?size=256) • [512]({banner_url}?size=512) • [1024]({banner_url}?size=1024) • [2048]({banner_url}?size=2048)",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class User(commands.Cog):
    """User information command"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="user",
        description="Display detailed information about a Discord user"
    )
    @app_commands.describe(
        user="The user to lookup (defaults to yourself)",
        incognito="Make response visible only to you"
    )
    async def user_command(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        incognito: Optional[bool] = None
    ):
        """Display user information"""

        # === BLOC INCOGNITO ===
        if incognito is None and self.bot.db:
            try:
                user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                ephemeral = True if user_pref is None else user_pref
            except:
                ephemeral = True
        else:
            ephemeral = incognito if incognito is not None else True

        # Get locale
        locale = i18n.get_user_locale(interaction)

        # If no user specified, use the command author
        target_user = user if user else interaction.user
        user_id = str(target_user.id)

        # Send loading message
        loading_msg = i18n.get("commands.user.loading", locale=locale)
        await interaction.response.send_message(loading_msg, ephemeral=ephemeral)

        try:
            # Fetch user data from Discord API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bot {self.bot.http.token}",
                    "User-Agent": "DiscordBot (Moddy, 1.0)"
                }

                # Get user data
                async with session.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers) as resp:
                    if resp.status != 200:
                        error_msg = i18n.get("commands.user.errors.not_found", locale=locale)
                        await interaction.edit_original_response(content=error_msg)
                        return

                    user_data = await resp.json()

                # Check if user is a bot
                bot_data = None
                if user_data.get("bot"):
                    # Get bot/application data
                    async with session.get(f"https://discord.com/api/v10/applications/{user_id}/rpc", headers=headers) as resp:
                        if resp.status == 200:
                            bot_data = await resp.json()

            # Get Moddy attributes for the user
            moddy_attributes = {}
            if self.bot.db:
                try:
                    user_db_data = await self.bot.db.get_user(int(user_id))
                    if user_db_data:
                        moddy_attributes = user_db_data.get("attributes", {})
                except Exception as e:
                    # If user not in DB, that's okay
                    pass

            # Create the view
            view = UserInfoView(
                user_data=user_data,
                bot_data=bot_data,
                moddy_attributes=moddy_attributes,
                locale=locale,
                author_id=interaction.user.id,
                bot=self.bot
            )

            # Update the message with the view
            await interaction.edit_original_response(content=None, view=view)

        except Exception as e:
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Error in user command: {e}", exc_info=True)

            error_msg = i18n.get("commands.user.errors.generic", locale=locale, error=str(e))
            await interaction.edit_original_response(content=error_msg)


async def setup(bot):
    await bot.add_cog(User(bot))
