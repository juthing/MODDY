"""
Système i18n (internationalisation) pour Moddy
Gère automatiquement les traductions basées sur interaction.locale
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
import discord
from enum import Enum

logger = logging.getLogger('moddy.i18n')


class Locale(Enum):
    """Langues supportées par Discord et Moddy"""
    # Langues principales
    EN_US = "en-US"  # Anglais (US)
    EN_GB = "en-GB"  # Anglais (UK)
    FR = "fr"  # Français
    ES_ES = "es-ES"  # Espagnol (Espagne)
    ES_419 = "es-419"  # Espagnol (Amérique Latine)
    DE = "de"  # Allemand
    IT = "it"  # Italien
    PT_BR = "pt-BR"  # Portugais (Brésil)
    RU = "ru"  # Russe
    PL = "pl"  # Polonais
    NL = "nl"  # Néerlandais
    JA = "ja"  # Japonais
    ZH_CN = "zh-CN"  # Chinois simplifié
    ZH_TW = "zh-TW"  # Chinois traditionnel
    KO = "ko"  # Coréen
    TR = "tr"  # Turc
    SV_SE = "sv-SE"  # Suédois
    DA = "da"  # Danois
    NO = "no"  # Norvégien
    FI = "fi"  # Finnois
    CS = "cs"  # Tchèque
    EL = "el"  # Grec
    BG = "bg"  # Bulgare
    UK = "uk"  # Ukrainien
    HI = "hi"  # Hindi
    RO = "ro"  # Roumain
    HR = "hr"  # Croate
    HU = "hu"  # Hongrois
    TH = "th"  # Thaï
    VI = "vi"  # Vietnamien
    LT = "lt"  # Lituanien

    @classmethod
    def from_discord(cls, locale: str) -> 'Locale':
        """Convertit une locale Discord en enum Locale"""
        try:
            return cls(locale)
        except ValueError:
            # Si la locale exacte n'existe pas, essayer de matcher le code langue de base
            base_lang = locale.split('-')[0]
            for l in cls:
                if l.value.startswith(base_lang):
                    return l
            return cls.EN_US  # Fallback par défaut


class I18n:
    """Gestionnaire de traductions pour Moddy"""

    _instance = None
    _translations: Dict[str, Dict[str, Any]] = {}
    _default_locale = Locale.EN_US
    _supported_locales = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialise le système i18n"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.load_translations()

    def load_translations(self):
        """Charge toutes les traductions depuis les fichiers JSON"""
        translations_dir = Path(__file__).parent.parent / 'locales'

        if not translations_dir.exists():
            logger.warning(f"⚠️ Dossier de traductions non trouvé : {translations_dir}")
            translations_dir.mkdir(exist_ok=True)
            return

        # Charger chaque fichier de langue
        for locale_file in translations_dir.glob('*.json'):
            locale_code = locale_file.stem  # nom du fichier sans extension

            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    self._translations[locale_code] = json.load(f)
                    self._supported_locales.add(locale_code)
                    logger.info(f"✅ Langue chargée : {locale_code}")
            except Exception as e:
                logger.error(f"❌ Erreur chargement {locale_file}: {e}")

        if not self._translations:
            logger.warning("⚠️ Aucune traduction chargée, utilisation des valeurs par défaut")

    def reload_translations(self):
        """Recharge toutes les traductions (utile pour le développement)"""
        self._translations.clear()
        self._supported_locales.clear()
        self.load_translations()
        logger.info("🔄 Traductions rechargées")

    def get_user_locale(self, interaction: discord.Interaction) -> str:
        """
        Détermine la locale à utiliser pour l'utilisateur

        Args:
            interaction: L'interaction Discord

        Returns:
            Le code de locale à utiliser (ex: "fr", "en-US")
        """
        # Récupérer la locale de Discord
        discord_locale = str(interaction.locale)

        # Convertir en enum Locale pour normaliser
        locale_enum = Locale.from_discord(discord_locale)
        locale_code = locale_enum.value

        # Si on a cette langue, l'utiliser
        if locale_code in self._supported_locales:
            return locale_code

        # Sinon, essayer avec le code de base (fr au lieu de fr-FR)
        base_lang = locale_code.split('-')[0]
        if base_lang in self._supported_locales:
            return base_lang

        # Chercher une variante de cette langue
        for supported in self._supported_locales:
            if supported.startswith(base_lang):
                return supported

        # Fallback sur anglais
        return self._default_locale.value

    def get(self, key: str, interaction: Optional[discord.Interaction] = None,
            locale: Optional[str] = None, **kwargs) -> str:
        """
        Récupère une traduction

        Args:
            key: Clé de traduction (ex: "commands.ping.title")
            interaction: Interaction Discord (pour auto-détecter la langue)
            locale: Code de langue manuel (prioritaire sur interaction)
            **kwargs: Variables à remplacer dans le texte

        Returns:
            Le texte traduit
        """
        # Déterminer la locale à utiliser
        if locale:
            target_locale = locale
        elif interaction:
            target_locale = self.get_user_locale(interaction)
        else:
            target_locale = self._default_locale.value

        # Récupérer la traduction
        text = self._get_nested_key(self._translations.get(target_locale, {}), key)

        # Si pas trouvé, essayer en anglais
        if text is None and target_locale != self._default_locale.value:
            text = self._get_nested_key(
                self._translations.get(self._default_locale.value, {}),
                key
            )

        # Si toujours pas trouvé, retourner la clé
        if text is None:
            logger.warning(f"⚠️ Traduction manquante : {key} ({target_locale})")
            return f"[{key}]"

        # Remplacer les variables si nécessaires
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                logger.error(f"❌ Variable manquante dans la traduction {key}: {e}")

        return text

    def _get_nested_key(self, data: dict, key: str) -> Optional[str]:
        """
        Récupère une valeur dans un dictionnaire avec des clés imbriquées

        Args:
            data: Dictionnaire de données
            key: Clé avec notation pointée (ex: "commands.ping.title")

        Returns:
            La valeur ou None
        """
        keys = key.split('.')
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current

    def t(self, key: str, interaction: Optional[discord.Interaction] = None, **kwargs) -> str:
        """Alias court pour get()"""
        return self.get(key, interaction, **kwargs)

    def get_embed(self, key: str, interaction: discord.Interaction,
                  **kwargs) -> discord.Embed:
        """
        Crée un embed depuis les traductions

        Args:
            key: Clé de base pour l'embed (ex: "commands.ping.response")
            interaction: Interaction Discord
            **kwargs: Variables supplémentaires

        Returns:
            Un discord.Embed configuré
        """
        from config import COLORS

        # Récupérer les éléments de l'embed
        title = self.get(f"{key}.title", interaction, **kwargs)
        description = self.get(f"{key}.description", interaction, **kwargs)

        # Créer l'embed
        embed = discord.Embed(
            title=title if title != f"[{key}.title]" else None,
            description=description if description != f"[{key}.description]" else None,
            color=COLORS.get("primary", 0x5865F2)
        )

        # Ajouter les fields si ils existent
        fields_key = f"{key}.fields"
        locale = self.get_user_locale(interaction)
        fields_data = self._get_nested_key(
            self._translations.get(locale, {}),
            fields_key
        )

        if isinstance(fields_data, list):
            for field in fields_data:
                if isinstance(field, dict):
                    name = field.get('name', 'Unknown')
                    value = field.get('value', 'Unknown')
                    inline = field.get('inline', False)

                    # Remplacer les variables dans les fields
                    if kwargs:
                        try:
                            name = name.format(**kwargs)
                            value = value.format(**kwargs)
                        except:
                            pass

                    embed.add_field(name=name, value=value, inline=inline)

        # Footer si existe
        footer = self.get(f"{key}.footer", interaction, **kwargs)
        if footer and footer != f"[{key}.footer]":
            embed.set_footer(text=footer)

        return embed

    @property
    def supported_locales(self) -> set:
        """Retourne les langues supportées"""
        return self._supported_locales

    def is_supported(self, locale: str) -> bool:
        """Vérifie si une langue est supportée"""
        return locale in self._supported_locales


# Instance globale
i18n = I18n()


# Fonctions utilitaires pour faciliter l'usage
def t(key: str, interaction: Optional[discord.Interaction] = None, **kwargs) -> str:
    """Fonction raccourci pour obtenir une traduction"""
    return i18n.get(key, interaction, **kwargs)


def get_embed(key: str, interaction: discord.Interaction, **kwargs) -> discord.Embed:
    """Fonction raccourci pour créer un embed traduit"""
    return i18n.get_embed(key, interaction, **kwargs)


def get_locale(interaction: discord.Interaction) -> str:
    """Récupère la locale de l'utilisateur"""
    return i18n.get_user_locale(interaction)