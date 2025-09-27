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


class TranslateView(discord.ui.View):
    """View to re-translate into another language"""

    def __init__(self, bot, original_text: str, from_lang: str, current_to_lang: str, lang: str, author: discord.User):
        super().__init__(timeout=120)
        self.bot = bot
        self.original_text = original_text
        self.from_lang = from_lang
        self.current_to_lang = current_to_lang
        self.lang = lang
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
                options.append(discord.SelectOption(
                    label=name_fr if self.lang == "FR" else name,
                    value=code,
                    emoji=emoji
                ))

        # Limit to 25 options (Discord limit)
        options = options[:25]

        placeholder = "Traduire dans une autre langue" if self.lang == "FR" else "Translate to another language"

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
            if self.lang == "FR":
                msg = "Seul l'auteur de la commande peut utiliser ce menu."
            else:
                msg = "Only the command author can use this menu."
            await interaction.response.send_message(msg, ephemeral=True)
            return False
        return True

    async def translate_callback(self, interaction: discord.Interaction):
        """Callback to re-translate the text"""
        new_lang = self.children[0].values[0]

        # Loading message
        if self.lang == "FR":
            loading_text = f"<:loading:1395047662092550194> Traduction en cours..."
        else:
            loading_text = f"<:loading:1395047662092550194> Translating..."

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
                    self.lang
                )

                # Update the view with the new language
                self.current_to_lang = new_lang
                self.clear_items()
                self.add_item(self.create_select())

                await interaction.edit_original_response(embed=embed, view=self)
            else:
                if self.lang == "FR":
                    error_msg = "<:undone:1398729502028333218> Erreur lors de la traduction"
                else:
                    error_msg = "<:undone:1398729502028333218> Translation error"

                await interaction.followup.send(error_msg, ephemeral=True)


class Translate(commands.Cog):
    """Translation system using DeepL"""

    def __init__(self, bot):
        self.bot = bot
        self.deepl_api_key = DEEPL_API_KEY  # Retrieved from config.py
        self.user_usage = {}  # Dict to track usage per user
        self.max_uses_per_minute = 20  # Maximum 20 uses per minute per user

        # Multilingual texts
        self.texts = {
            "FR": {
                "description": "Traduit du texte dans une autre langue",
                "text_desc": "Le texte à traduire",
                "to_desc": "Langue de destination",
                "incognito_desc": "Rendre la réponse visible uniquement pour vous",
                "translating": "Traduction en cours...",
                "from_lang": "Langue détectée",
                "to_lang": "Traduit en",
                "translation_title": "Traduction",
                "error_title": "Erreur de traduction",
                "error_api": "Impossible de contacter l'API de traduction",
                "error_rate_limit": "Limite atteinte ! Maximum 20 traductions par minute. Réessayez dans {} secondes",
                "error_too_long": "Le texte est trop long (maximum 3000 caractères)",
                "error_no_text": "Aucun texte fourni à traduire",
                "characters": "caractères"
            },
            "EN": {
                "description": "Translate text to another language",
                "text_desc": "The text to translate",
                "to_desc": "Target language",
                "incognito_desc": "Make response visible only to you",
                "translating": "Translating...",
                "from_lang": "Detected language",
                "to_lang": "Translated to",
                "translation_title": "Translation",
                "error_title": "Translation error",
                "error_api": "Unable to contact translation API",
                "error_rate_limit": "Rate limit reached! Maximum 20 translations per minute. Try again in {} seconds",
                "error_too_long": "Text is too long (maximum 3000 characters)",
                "error_no_text": "No text provided to translate",
                "characters": "characters"
            }
        }

        # Map of DeepL language codes to names
        self.language_names = {
            "EN": {"FR": "Anglais", "EN": "English"},
            "EN-US": {"FR": "Anglais (US)", "EN": "English (US)"},
            "EN-GB": {"FR": "Anglais (UK)", "EN": "English (UK)"},
            "FR": {"FR": "Français", "EN": "French"},
            "DE": {"FR": "Allemand", "EN": "German"},
            "ES": {"FR": "Espagnol", "EN": "Spanish"},
            "IT": {"FR": "Italien", "EN": "Italian"},
            "PT": {"FR": "Portugais", "EN": "Portuguese"},
            "PT-PT": {"FR": "Portugais", "EN": "Portuguese"},
            "PT-BR": {"FR": "Portugais (BR)", "EN": "Portuguese (BR)"},
            "NL": {"FR": "Néerlandais", "EN": "Dutch"},
            "PL": {"FR": "Polonais", "EN": "Polish"},
            "RU": {"FR": "Russe", "EN": "Russian"},
            "JA": {"FR": "Japonais", "EN": "Japanese"},
            "ZH": {"FR": "Chinois", "EN": "Chinese"},
            "KO": {"FR": "Coréen", "EN": "Korean"},
            "TR": {"FR": "Turc", "EN": "Turkish"},
            "SV": {"FR": "Suédois", "EN": "Swedish"},
            "DA": {"FR": "Danois", "EN": "Danish"},
            "NO": {"FR": "Norvégien", "EN": "Norwegian"},
            "FI": {"FR": "Finnois", "EN": "Finnish"},
            "EL": {"FR": "Grec", "EN": "Greek"},
            "CS": {"FR": "Tchèque", "EN": "Czech"},
            "RO": {"FR": "Roumain", "EN": "Romanian"},
            "HU": {"FR": "Hongrois", "EN": "Hungarian"},
            "UK": {"FR": "Ukrainien", "EN": "Ukrainian"},
            "BG": {"FR": "Bulgare", "EN": "Bulgarian"},
            "AR": {"FR": "Arabe", "EN": "Arabic"},
            "ID": {"FR": "Indonésien", "EN": "Indonesian"},
            "SK": {"FR": "Slovaque", "EN": "Slovak"},
            "SL": {"FR": "Slovène", "EN": "Slovenian"},
            "ET": {"FR": "Estonien", "EN": "Estonian"},
            "LV": {"FR": "Letton", "EN": "Latvian"},
            "LT": {"FR": "Lituanien", "EN": "Lithuanian"}
        }

    def get_text(self, lang: str, key: str) -> str:
        """Gets a translated text"""
        return self.texts.get(lang, self.texts["EN"]).get(key, key)

    def get_language_name(self, code: str, lang: str) -> str:
        """Gets the name of a language in the correct translation"""
        # Clean the code (EN-US -> EN-US, EN -> EN)
        base_code = code.split('-')[0] if '-' not in code or code in self.language_names else code

        if code in self.language_names:
            return self.language_names[code].get(lang, code)
        elif base_code in self.language_names:
            return self.language_names[base_code].get(lang, code)
        else:
            return code

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

    def create_translation_embed(self, original: str, translated: str, from_lang: str, to_lang: str, user_lang: str) -> discord.Embed:
        """Creates the translation embed"""
        embed = discord.Embed(
            title=f"<:translate:1398720130950627600> {self.get_text(user_lang, 'translation_title')}",
            color=COLORS["primary"]
        )

        # Original text
        original_display = original[:1000] + "..." if len(original) > 1000 else original
        embed.add_field(
            name=f"{self.get_text(user_lang, 'from_lang')}: {self.get_language_name(from_lang, user_lang)}",
            value=f"```\n{original_display}\n```",
            inline=False
        )

        # Translated text
        translated_display = translated[:1000] + "..." if len(translated) > 1000 else translated
        embed.add_field(
            name=f"{self.get_text(user_lang, 'to_lang')}: {self.get_language_name(to_lang, user_lang)}",
            value=f"```\n{translated_display}\n```",
            inline=False
        )

        # Footer with character count
        embed.set_footer(
            text=f"{len(original)} {self.get_text(user_lang, 'characters')} • DeepL API",
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

        # IMPORTANT: Wait a bit to let the language system do its work
        await asyncio.sleep(0.1)

        # Check if the interaction has already been responded to (by the language system)
        if interaction.response.is_done():
            # The language system has requested the selection, we wait for it to finish
            # and execute the translation afterwards
            await asyncio.sleep(2)  # Wait for the user to choose their language

            # Get the updated language
            lang = 'EN'  # Default fallback
            if self.bot.db:
                try:
                    user_lang = await self.bot.db.get_attribute('user', interaction.user.id, 'LANG')
                    if user_lang:
                        lang = user_lang
                except:
                    pass

            # Get the ephemeral mode
            if incognito is None and self.bot.db:
                try:
                    user_pref = await self.bot.db.get_attribute('user', interaction.user.id, 'DEFAULT_INCOGNITO')
                    ephemeral = True if user_pref is None else user_pref
                except:
                    ephemeral = True
            else:
                ephemeral = incognito if incognito is not None else True

            # Check the rate limit
            can_use, remaining = await self.check_rate_limit(interaction.user.id)
            if not can_use:
                error_embed = ModdyResponse.error(
                    self.get_text(lang, "error_title"),
                    self.get_text(lang, "error_rate_limit").format(remaining)
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
                return

            # Continue with the translation via followup
            loading_embed = ModdyResponse.loading(self.get_text(lang, "translating"))
            msg = await interaction.followup.send(embed=loading_embed, ephemeral=ephemeral)

            # Execute the translation
            sanitized_text = self.sanitize_mentions(text, interaction.guild)
            source_lang = await self.detect_language(sanitized_text)
            translated = await self.translate_text(sanitized_text, to.value)

            if translated and source_lang:
                embed = self.create_translation_embed(
                    sanitized_text,
                    translated,
                    source_lang,
                    to.value,
                    lang
                )
                view = TranslateView(
                    self.bot,
                    sanitized_text,
                    source_lang,
                    to.value,
                    lang,
                    interaction.user
                )
                await msg.edit(embed=embed, view=view)
            else:
                error_embed = ModdyResponse.error(
                    self.get_text(lang, "error_title"),
                    self.get_text(lang, "error_api")
                )
                await msg.edit(embed=error_embed)

            return

        # If the interaction has not yet been responded to, we continue normally
        # Get the user's language
        lang = getattr(interaction, 'user_lang', 'EN')

        # Get the ephemeral mode
        ephemeral = get_incognito_setting(interaction)

        # Check the rate limit (20 per minute per user)
        can_use, remaining = await self.check_rate_limit(interaction.user.id)
        if not can_use:
            error_embed = ModdyResponse.error(
                self.get_text(lang, "error_title"),
                self.get_text(lang, "error_rate_limit").format(remaining)
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Check the length of the text
        if len(text) > 3000:
            error_embed = ModdyResponse.error(
                self.get_text(lang, "error_title"),
                self.get_text(lang, "error_too_long")
            )
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

        # Sanitize mentions
        sanitized_text = self.sanitize_mentions(text, interaction.guild)

        # Loading message
        loading_embed = ModdyResponse.loading(self.get_text(lang, "translating"))
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
                lang
            )

            # Create the view with the re-translation menu
            view = TranslateView(
                self.bot,
                sanitized_text,
                source_lang,
                to.value,
                lang,
                interaction.user
            )

            await interaction.edit_original_response(embed=embed, view=view)

        else:
            # Translation error
            error_embed = ModdyResponse.error(
                self.get_text(lang, "error_title"),
                self.get_text(lang, "error_api")
            )
            await interaction.edit_original_response(embed=error_embed)


async def setup(bot):
    await bot.add_cog(Translate(bot))