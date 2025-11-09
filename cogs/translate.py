"""
Translate command for Moddy
Uses the DeepL API to translate text with automatic detection
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import aiohttp
import re
from datetime import datetime, timedelta
import asyncio

from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from utils.incognito import add_incognito_option, get_incognito_setting
from config import COLORS, DEEPL_API_KEY
from utils.i18n import i18n


class TranslateView(discord.ui.View):
    """View to re-translate into another language"""

    def __init__(self, bot, original_text: str, from_lang: str, current_to_lang: str, locale: str, author: discord.User):
        super().__init__(timeout=120)
        self.bot = bot
        self.original_text = original_text
        self.from_lang = from_lang
        self.current_to_lang = current_to_lang
        self.locale = locale
        self.author = author

        # Add the select menu
        self.add_item(self.create_select())

    def create_select(self):
        """Creates the language selection menu"""
        options = []

        # Available DeepL languages (most common)
        languages = {
            "EN-US": ("🇺🇸", "English (US)", "Anglais (US)"),
            "EN-GB": ("🇬🇧", "English (UK)", "Anglais (UK)"),
            "FR": ("🇫🇷", "Français", "Français"),
            "DE": ("🇩🇪", "Deutsch", "Allemand"),
            "ES": ("🇪🇸", "Español", "Espagnol"),
            "IT": ("🇮🇹", "Italiano", "Italien"),
            "PT-PT": ("🇵🇹", "Português", "Portugais"),
            "PT-BR": ("🇧🇷", "Português (BR)", "Portugais (BR)"),
            "NL": ("🇳🇱", "Nederlands", "Néerlandais"),
            "PL": ("🇵🇱", "Polski", "Polonais"),
            "RU": ("🇷🇺", "Русский", "Russe"),
            "JA": ("🇯🇵", "日本語", "Japonais"),
            "ZH": ("🇨🇳", "中文", "Chinois"),
            "KO": ("🇰🇷", "한국어", "Coréen"),
            "TR": ("🇹🇷", "Türkçe", "Turc"),
            "SV": ("🇸🇪", "Svenska", "Suédois"),
            "DA": ("🇩🇰", "Dansk", "Danois"),
            "NO": ("🇳🇴", "Norsk", "Norvégien"),
            "FI": ("🇫🇮", "Suomi", "Finnois"),
            "EL": ("🇬🇷", "Ελληνικά", "Grec"),
            "CS": ("🇨🇿", "Čeština", "Tchèque"),
            "RO": ("🇷🇴", "Română", "Roumain"),
            "HU": ("🇭🇺", "Magyar", "Hongrois"),
            "UK": ("🇺🇦", "Українська", "Ukrainien"),
            "BG": ("🇧🇬", "Български", "Bulgare")
        }

        for code, (emoji, name, name_fr) in languages.items():
            # Do not include the current language
            if code != self.current_to_lang:
                # Use French names for French locale, English names for others
                label = name_fr if self.locale == "fr" else name
                options.append(discord.SelectOption(
                    label=label,
                    value=code,
                    emoji=emoji
                ))

        # Limit to 25 options (Discord limit)
        options = options[:25]

        placeholder = i18n.get("commands.translate.view.placeholder", locale=self.locale)

        select = discord.ui.Select(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1
        )
        select.callback = self.translate_callback

        return select

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Checks that it's the author using the menu"""
        if interaction.user != self.author:
            locale = i18n.get_user_locale(interaction)
            if locale == "fr":
                msg = "Seul l'auteur de la commande peut utiliser ce menu."
            else:
                msg = "Only the command author can use this menu."
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    async def translate_callback(self, interaction: discord.Interaction):
        """Callback to re-translate the text"""
        new_lang = self.children[0].values[0]

        await interaction.response.defer()

        # Use the translation function of the cog
        translator = self.bot.get_cog("Translate")
        if translator:
            translated = await translator.translate_text(self.original_text, new_lang)

            if translated:
                # Create the new embed
                embed = translator.create_translation_embed(
                    self.original_text,
                    translated,
                    self.from_lang,
                    new_lang,
                    self.locale
                )

                # Update the view with the new language
                self.current_to_lang = new_lang
                self.clear_items()
                self.add_item(self.create_select())

                await interaction.edit_original_response(embed=embed, view=self)
            else:
                error_msg = i18n.get("common.error", locale=self.locale)
                await interaction.followup.send(error_msg, ephemeral=True)


class Translate(commands.Cog):
    """Translation system using DeepL"""

    def __init__(self, bot):
        self.bot = bot
        self.deepl_api_key = DEEPL_API_KEY  # Retrieved from config.py
        self.user_usage = {}  # Dict to track usage per user
        self.max_uses_per_minute = 20  # Maximum 20 uses per minute per user

    def get_language_name(self, code: str, locale: str) -> str:
        """Gets the name of a language using i18n"""
        # Convert DeepL code (uppercase) to i18n code (lowercase with proper format)
        # DeepL: EN-US, EN-GB, FR, DE -> i18n: en-US, en-GB, fr, de
        normalized_code = code.lower()

        # Special cases for codes without region
        if normalized_code in ['en', 'fr', 'de', 'es', 'it', 'pt', 'nl', 'pl', 'ru', 'ja', 'zh', 'ko', 'tr', 'sv', 'da', 'no', 'fi', 'el', 'cs', 'ro', 'hu', 'uk', 'bg']:
            # Map to standard codes
            code_mapping = {
                'en': 'en-US',
                'es': 'es-ES',
                'pt': 'pt-PT',
                'zh': 'zh-CN',
                'sv': 'sv-SE'
            }
            normalized_code = code_mapping.get(normalized_code, normalized_code)

        # Try to get the language name from i18n
        lang_name = i18n.get(f"languages.{normalized_code}", locale=locale)

        # If not found (returns [languages.xxx]), return the code itself
        if lang_name.startswith('['):
            return code

        return lang_name

    def sanitize_mentions(self, text: str, guild: Optional[discord.Guild]) -> str:
        """Replaces mentions with non-pinging text"""
        # Replace @everyone and @here
        text = text.replace('@everyone', '@\u200beveryone')
        text = text.replace('@here', '@\u200bhere')

        # Replace user mentions
        user_mention_pattern = r'<@!?(\d+)>'

        def replace_user_mention(match):
            user_id = int(match.group(1))
            if guild:
                member = guild.get_member(user_id)
                if member:
                    return f"@{member.display_name}"
            user = self.bot.get_user(user_id)
            if user:
                return f"@{user.name}"
            return f"@User"

        text = re.sub(user_mention_pattern, replace_user_mention, text)

        # Replace role mentions
        role_mention_pattern = r'<@&(\d+)>'

        def replace_role_mention(match):
            if guild:
                role_id = int(match.group(1))
                role = guild.get_role(role_id)
                if role:
                    return f"@{role.name}"
            return f"@Role"

        text = re.sub(role_mention_pattern, replace_role_mention, text)

        return text

    async def check_rate_limit(self, user_id: int) -> tuple[bool, int]:
        """Checks the 20 uses per minute limit for a user"""
        now = datetime.now()

        # Initialize the list for this user if it doesn't exist
        if user_id not in self.user_usage:
            self.user_usage[user_id] = []

        # Clean uses older than one minute for this user
        cutoff = now - timedelta(minutes=1)
        self.user_usage[user_id] = [timestamp for timestamp in self.user_usage[user_id] if timestamp > cutoff]

        # Clean users who haven't used the command for more than 2 minutes
        users_to_clean = []
        for uid, timestamps in self.user_usage.items():
            if uid != user_id and (not timestamps or max(timestamps) < now - timedelta(minutes=2)):
                users_to_clean.append(uid)
        for uid in users_to_clean:
            del self.user_usage[uid]

        # Check if the user can use the command
        if len(self.user_usage[user_id]) >= self.max_uses_per_minute:
            # Calculate the time until the next possible use
            oldest_use = min(self.user_usage[user_id])
            wait_time = 60 - (now - oldest_use).total_seconds()
            return False, int(wait_time)

        # Add this use for this user
        self.user_usage[user_id].append(now)
        return True, 0

    async def translate_text(self, text: str, target_lang: str) -> Optional[str]:
        """Calls the DeepL API to translate the text"""
        try:
            # DeepL API URL (free)
            url = "https://api-free.deepl.com/v2/translate"

            headers = {
                "Authorization": f"DeepL-Auth-Key {self.deepl_api_key}"
            }

            data = {
                "text": text,
                "target_lang": target_lang
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["translations"][0]["text"]
                    else:
                        return None

        except Exception as e:
            import logging
            logger = logging.getLogger('moddy')
            logger.error(f"DeepL translation error: {e}")
            return None

    async def detect_language(self, text: str) -> Optional[str]:
        """Detects the language of the text with DeepL"""
        try:
            # DeepL automatically detects the source language
            # We make a translation request to EN to get the source language
            url = "https://api-free.deepl.com/v2/translate"

            headers = {
                "Authorization": f"DeepL-Auth-Key {self.deepl_api_key}"
            }

            data = {
                "text": text,
                "target_lang": "EN-US"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["translations"][0]["detected_source_language"]
                    else:
                        return None

        except Exception:
            return None

    def create_translation_embed(self, original: str, translated: str, from_lang: str, to_lang: str, locale: str) -> discord.Embed:
        """Creates the translation embed"""
        title = i18n.get("commands.translate.response.title", locale=locale)
        embed = discord.Embed(
            title=title,
            color=COLORS["primary"]
        )

        # Original text
        original_display = original[:1000] + "..." if len(original) > 1000 else original
        from_field = i18n.get("commands.translate.response.from_field", locale=locale, language=self.get_language_name(from_lang, locale))
        embed.add_field(
            name=from_field,
            value=f"```\n{original_display}\n```",
            inline=False
        )

        # Translated text
        translated_display = translated[:1000] + "..." if len(translated) > 1000 else translated
        to_field = i18n.get("commands.translate.response.to_field", locale=locale, language=self.get_language_name(to_lang, locale))
        embed.add_field(
            name=to_field,
            value=f"```\n{translated_display}\n```",
            inline=False
        )

        # Footer with character count
        footer = i18n.get("commands.translate.response.footer", locale=locale, char_count=len(original))
        embed.set_footer(
            text=footer,
            icon_url="https://www.deepl.com/img/logo/DeepL_Logo_darkBlue_v2.svg"
        )

        embed.timestamp = datetime.utcnow()

        return embed

    @app_commands.command(
        name="translate",
        description="Traduit du texte dans une autre langue / Translate text to another language"
    )
    @app_commands.describe(
        text="Le texte à traduire / The text to translate",
        to="Langue de destination / Target language",
        incognito="Rendre la réponse visible uniquement pour vous / Make response visible only to you"
    )
    @app_commands.choices(to=[
        app_commands.Choice(name="🇺🇸 English (US)", value="EN-US"),
        app_commands.Choice(name="🇬🇧 English (UK)", value="EN-GB"),
        app_commands.Choice(name="🇫🇷 Français", value="FR"),
        app_commands.Choice(name="🇩🇪 Deutsch", value="DE"),
        app_commands.Choice(name="🇪🇸 Español", value="ES"),
        app_commands.Choice(name="🇮🇹 Italiano", value="IT"),
        app_commands.Choice(name="🇵🇹 Português", value="PT-PT"),
        app_commands.Choice(name="🇧🇷 Português (BR)", value="PT-BR"),
        app_commands.Choice(name="🇳🇱 Nederlands", value="NL"),
        app_commands.Choice(name="🇵🇱 Polski", value="PL"),
        app_commands.Choice(name="🇷🇺 Русский", value="RU"),
        app_commands.Choice(name="🇯🇵 日本語", value="JA"),
        app_commands.Choice(name="🇨🇳 中文", value="ZH"),
        app_commands.Choice(name="🇰🇷 한국어", value="KO"),
        app_commands.Choice(name="🇹🇷 Türkçe", value="TR"),
        app_commands.Choice(name="🇸🇪 Svenska", value="SV"),
        app_commands.Choice(name="🇩🇰 Dansk", value="DA"),
        app_commands.Choice(name="🇳🇴 Norsk", value="NO"),
        app_commands.Choice(name="🇫🇮 Suomi", value="FI"),
        app_commands.Choice(name="🇬🇷 Ελληνικά", value="EL"),
        app_commands.Choice(name="🇨🇿 Čeština", value="CS"),
        app_commands.Choice(name="🇷🇴 Română", value="RO"),
        app_commands.Choice(name="🇭🇺 Magyar", value="HU"),
        app_commands.Choice(name="🇺🇦 Українська", value="UK"),
        app_commands.Choice(name="🇧🇬 Български", value="BG")
    ])
    @add_incognito_option()
    async def translate_command(
        self,
        interaction: discord.Interaction,
        text: str,
        to: app_commands.Choice[str],
        incognito: Optional[bool] = None
    ):
        """Main translation command"""

        # Get the user's locale from Discord
        locale = i18n.get_user_locale(interaction)

        # Get the ephemeral mode
        ephemeral = get_incognito_setting(interaction)

        # Check the rate limit (20 per minute per user)
        can_use, remaining = await self.check_rate_limit(interaction.user.id)
        if not can_use:
            error_msg = i18n.get("commands.translate.errors.rate_limit", locale=locale, seconds=remaining)
            error_embed = ModdyResponse.error(i18n.get("common.error", locale=locale), error_msg)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Check the length of the text
        if len(text) > 3000:
            error_msg = i18n.get("commands.translate.errors.too_long", locale=locale)
            error_embed = ModdyResponse.error(i18n.get("common.error", locale=locale), error_msg)
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Sanitize mentions
        sanitized_text = self.sanitize_mentions(text, interaction.guild)

        # Loading message
        loading_msg = i18n.get("commands.translate.translating", locale=locale)
        loading_embed = ModdyResponse.loading(loading_msg)
        await interaction.response.send_message(embed=loading_embed, ephemeral=ephemeral)

        # Detect the source language
        source_lang = await self.detect_language(sanitized_text)

        # Translate the text
        translated = await self.translate_text(sanitized_text, to.value)

        if translated and source_lang:
            # Create the result embed
            embed = self.create_translation_embed(
                sanitized_text,
                translated,
                source_lang,
                to.value,
                locale
            )

            # Create the view with the re-translation menu
            view = TranslateView(
                self.bot,
                sanitized_text,
                source_lang,
                to.value,
                locale,
                interaction.user
            )

            await interaction.edit_original_response(embed=embed, view=view)

        else:
            # Translation error
            error_msg = i18n.get("commands.translate.errors.api_error", locale=locale)
            error_embed = ModdyResponse.error(i18n.get("common.error", locale=locale), error_msg)
            await interaction.edit_original_response(embed=error_embed)


async def setup(bot):
    await bot.add_cog(Translate(bot))