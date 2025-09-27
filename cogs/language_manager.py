"""
Language management system for Moddy
Intercepts interactions and checks/sets the user's language
"""

import discord
from discord.ext import commands
from typing import Optional, Dict
import asyncio

from config import COLORS


class LanguageSelectView(discord.ui.View):
    """View to select the preferred language"""

    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.selected_lang = None

    @discord.ui.button(label="Français", emoji="🇫🇷", style=discord.ButtonStyle.primary)
    async def french_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Selects French"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Cette sélection n'est pas pour vous.",
                ephemeral=True
            )
            return

        self.selected_lang = "FR"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="English", emoji="🇬🇧", style=discord.ButtonStyle.primary)
    async def english_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Selects English"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This selection is not for you.",
                ephemeral=True
            )
            return

        self.selected_lang = "EN"
        await interaction.response.defer()
        self.stop()


class LanguageManager(commands.Cog):
    """Manages user language for all interactions"""

    def __init__(self, bot):
        self.bot = bot
        self.lang_cache = {}  # Cache to avoid too many DB requests
        self.pending_interactions = {}  # Stores pending interactions
        # Dictionary to store the languages of ongoing interactions
        self.interaction_languages = {}

        # Multilingual texts
        self.texts = {
            "FR": {
                "welcome": "Bienvenue sur Moddy !",
                "language_prompt": "Quelle langue préférez-vous utiliser ?",
                "language_set": "Votre langue a été définie sur **Français** <:done:1398729525277229066>",
                "processing": "Traitement de votre demande...",
                "error": "Une erreur est survenue",
                "timeout": "Temps écoulé. Veuillez réessayer."
            },
            "EN": {
                "welcome": "Welcome to Moddy!",
                "language_prompt": "Which language do you prefer to use?",
                "language_set": "Your language has been set to **English** <:done:1398729525277229066>",
                "processing": "Processing your request...",
                "error": "An error occurred",
                "timeout": "Time expired. Please try again."
            }
        }

    def get_text(self, lang: str, key: str) -> str:
        """Gets a text in the appropriate language"""
        return self.texts.get(lang, self.texts["EN"]).get(key, key)

    async def get_user_language(self, user_id: int) -> Optional[str]:
        """Gets a user's language (with cache)"""
        # Check the cache first
        if user_id in self.lang_cache:
            return self.lang_cache[user_id]

        # Otherwise, check the DB
        if self.bot.db:
            try:
                lang = await self.bot.db.get_attribute('user', user_id, 'LANG')
                self.lang_cache[user_id] = lang
                return lang
            except:
                return None
        return None

    def get_interaction_language(self, interaction: discord.Interaction) -> Optional[str]:
        """Gets the stored language for an interaction"""
        return self.interaction_languages.get(interaction.id)

    def set_interaction_language(self, interaction: discord.Interaction, lang: str):
        """Stores the language for an interaction"""
        self.interaction_languages[interaction.id] = lang
        # Clean up old entries after 5 minutes
        asyncio.create_task(self._cleanup_interaction_language(interaction.id))

    async def _cleanup_interaction_language(self, interaction_id: str):
        """Cleans up an interaction's language after 5 minutes"""
        await asyncio.sleep(300)  # 5 minutes
        self.interaction_languages.pop(interaction_id, None)

    async def set_user_language(self, user_id: int, lang: str, set_by: int = None):
        """Sets a user's language"""
        if self.bot.db:
            try:
                await self.bot.db.set_attribute(
                    'user', user_id, 'LANG', lang,
                    set_by or user_id, "User-selected language"
                )
                # Update the cache
                self.lang_cache[user_id] = lang
                return True
            except Exception as e:
                import logging
                logger = logging.getLogger('moddy')
                logger.error(f"Error setting language: {e}")
                return False
        return False

    async def prompt_language_selection(self, interaction: discord.Interaction) -> Optional[str]:
        """Asks the user to choose their language"""
        # Create the bilingual embed
        embed = discord.Embed(
            title="Language Selection / Sélection de la langue",
            description=(
                "🇫🇷 **Français**\n"
                "Quelle langue préférez-vous utiliser ?\n\n"
                "🇬🇧 **English**\n"
                "Which language do you prefer to use?"
            ),
            color=COLORS["info"]
        )

        # Create the view with the buttons
        view = LanguageSelectView(interaction.user.id)

        # Send the message
        try:
            if interaction.response.is_done():
                msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                msg = await interaction.original_response()

            # Wait for the selection
            await view.wait()

            if view.selected_lang:
                # Save the language
                success = await self.set_user_language(interaction.user.id, view.selected_lang)

                if success:
                    # Confirmation message
                    confirm_embed = discord.Embed(
                        description=self.get_text(view.selected_lang, "language_set"),
                        color=COLORS["success"]
                    )

                    try:
                        await msg.edit(embed=confirm_embed, view=None)
                    except:
                        pass

                    return view.selected_lang
                else:
                    # Error while saving
                    error_embed = discord.Embed(
                        description="Error saving language preference / Erreur lors de la sauvegarde",
                        color=COLORS["error"]
                    )
                    try:
                        await msg.edit(embed=error_embed, view=None)
                    except:
                        pass
                    return None
            else:
                # Timeout
                timeout_embed = discord.Embed(
                    description="Time expired / Temps écoulé",
                    color=COLORS["warning"]
                )
                try:
                    await msg.edit(embed=timeout_embed, view=None)
                except:
                    pass
                return None

        except Exception as e:
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"Error during language selection: {e}")
            return None

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Intercepts all interactions to check the language"""
        # Ignore interactions from the bot itself
        if interaction.user.bot:
            return

        # Ignore interactions that are not commands
        if interaction.type != discord.InteractionType.application_command:
            return

        # Ignore developer commands (they remain in English)
        if hasattr(interaction.command, 'module') and 'staff' in str(interaction.command.module):
            return

        # Check if the user has a defined language
        user_lang = await self.get_user_language(interaction.user.id)

        if not user_lang:
            # The user does not have a defined language, we ask them
            # Store the original interaction
            self.pending_interactions[interaction.user.id] = interaction

            # Ask for the language
            selected_lang = await self.prompt_language_selection(interaction)

            if selected_lang:
                # The language has been selected, we can continue
                # Store the language in our dictionary
                self.set_interaction_language(interaction, selected_lang)

                # Log the action
                if log_cog := self.bot.get_cog("LoggingSystem"):
                    await log_cog.log_command(
                        type('obj', (object,), {
                            'author': interaction.user,
                            'guild': interaction.guild,
                            'channel': interaction.channel
                        })(),
                        "language_set",
                        {"language": selected_lang, "first_interaction": True}
                    )
            else:
                # Error or timeout, we stop the interaction
                if interaction.user.id in self.pending_interactions:
                    del self.pending_interactions[interaction.user.id]
                return

            # Clean up
            if interaction.user.id in self.pending_interactions:
                del self.pending_interactions[interaction.user.id]
        else:
            # The user already has a language, we store it
            self.set_interaction_language(interaction, user_lang)

    @commands.command(name="changelang", aliases=["cl", "lang"])
    async def change_language(self, ctx, lang: str = None):
        """Changes the user's language (text command)"""
        if not lang:
            current_lang = await self.get_user_language(ctx.author.id)

            embed = discord.Embed(
                title="Language / Langue",
                description=(
                    f"**Current / Actuelle:** `{current_lang or 'Not set / Non définie'}`\n\n"
                    "**Available / Disponibles:**\n"
                    "`FR` - Français\n"
                    "`EN` - English\n\n"
                    "**Usage:** `!changelang FR` or `!changelang EN`"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        # Validate the language
        lang = lang.upper()
        if lang not in ["FR", "EN"]:
            await ctx.send("<:undone:1398729502028333218> Invalid language / Langue invalide. Use `FR` or `EN`.")
            return

        # Change the language
        success = await self.set_user_language(ctx.author.id, lang, ctx.author.id)

        if success:
            if lang == "FR":
                await ctx.send("<:done:1398729525277229066> Votre langue a été changée en **Français**")
            else:
                await ctx.send("<:done:1398729525277229066> Your language has been changed to **English**")
        else:
            await ctx.send("<:undone:1398729502028333218> Error changing language / Erreur lors du changement")

    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command):
        """Cleans the cache periodically after commands"""
        # Clean the cache if it's too large
        if len(self.lang_cache) > 1000:
            # Keep only the last 500
            import itertools
            self.lang_cache = dict(itertools.islice(self.lang_cache.items(), 500))

        # Also clean the interaction's language
        self.interaction_languages.pop(interaction.id, None)


# Helper function to get the language of an interaction
def get_user_lang(interaction: discord.Interaction, bot) -> str:
    """Gets the user's language for an interaction"""
    # Try to get from the manager
    if lang_manager := bot.get_cog("LanguageManager"):
        lang = lang_manager.get_interaction_language(interaction)
        if lang:
            return lang

        # If not found in the interaction, search the cache
        if interaction.user.id in lang_manager.lang_cache:
            return lang_manager.lang_cache[interaction.user.id]

    # By default, return EN
    return "EN"


async def setup(bot):
    await bot.add_cog(LanguageManager(bot))