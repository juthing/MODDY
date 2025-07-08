"""
Système centralisé pour les embeds V2
Utilise les nouveaux composants Discord sans bordure colorée
"""

import discord
from typing import List, Optional, Dict, Any
import json


class ModdyEmbed:
    """Classe pour créer des embeds V2 standardisés"""

    # Flag pour les composants V2
    V2_FLAGS = 32768  # 1 << 15

    # Forcer l'utilisation des composants V2 partout
    USE_V2_EVERYWHERE = True

    @staticmethod
    def create_v2_message(components: List[Dict[str, Any]], flags: int = V2_FLAGS) -> Dict[str, Any]:
        """
        Crée un message avec les composants V2

        Args:
            components: Liste des composants à inclure
            flags: Flags du message (par défaut V2)

        Returns:
            Dict prêt à être envoyé
        """
        return {
            "flags": flags,
            "components": components
        }

    @staticmethod
    def text(content: str, markdown: bool = True) -> Dict[str, Any]:
        """
        Crée un composant Text Display

        Args:
            content: Texte à afficher
            markdown: Si True, supporte le markdown
        """
        return {
            "type": 10,
            "content": content
        }

    @staticmethod
    def heading(text: str, level: int = 1) -> Dict[str, Any]:
        """
        Crée un titre avec markdown

        Args:
            text: Texte du titre
            level: Niveau du titre (1-3)
        """
        prefix = "#" * min(level, 3)
        return ModdyEmbed.text(f"{prefix} {text}")

    @staticmethod
    def code_block(content: str, language: str = "") -> Dict[str, Any]:
        """
        Crée un bloc de code

        Args:
            content: Code à afficher
            language: Langage pour la coloration syntaxique
        """
        return ModdyEmbed.text(f"```{language}\n{content}\n```")

    @staticmethod
    def field(name: str, value: str, inline: bool = False) -> Dict[str, Any]:
        """
        Crée un champ formaté

        Args:
            name: Nom du champ
            value: Valeur du champ
            inline: Si les champs doivent être inline (non supporté en V2)
        """
        return ModdyEmbed.text(f"**{name}**\n{value}")

    @staticmethod
    def separator() -> Dict[str, Any]:
        """Crée un séparateur horizontal"""
        return ModdyEmbed.text("───────────────────────")

    @staticmethod
    def action_row(components: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Crée une ligne d'action avec des boutons

        Args:
            components: Liste des composants (boutons, etc.)
        """
        return {
            "type": 1,
            "components": components
        }

    @staticmethod
    def button(
            label: str,
            custom_id: str,
            style: int = 2,
            disabled: bool = False,
            emoji: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Crée un bouton

        Args:
            label: Texte du bouton
            custom_id: ID personnalisé pour les interactions
            style: 1=Primary, 2=Secondary, 3=Success, 4=Danger, 5=Link
            disabled: Si le bouton est désactivé
            emoji: Emoji optionnel
        """
        button = {
            "type": 2,
            "style": style,
            "label": label,
            "custom_id": custom_id,
            "disabled": disabled
        }

        if emoji:
            button["emoji"] = emoji

        return button

    @staticmethod
    def link_button(label: str, url: str, emoji: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Crée un bouton lien"""
        button = {
            "type": 2,
            "style": 5,
            "label": label,
            "url": url
        }

        if emoji:
            button["emoji"] = emoji

        return button


class ModdyResponse:
    """Templates de réponses standardisées"""

    @staticmethod
    def success(title: str, description: str, footer: Optional[str] = None) -> List[Dict[str, Any]]:
        """Message de succès"""
        components = [
            ModdyEmbed.heading(f"✓ {title}", 2),
            ModdyEmbed.text(description)
        ]

        if footer:
            components.extend([
                ModdyEmbed.separator(),
                ModdyEmbed.text(f"_{footer}_")
            ])

        return components

    @staticmethod
    def error(title: str, description: str, details: Optional[str] = None) -> List[Dict[str, Any]]:
        """Message d'erreur"""
        components = [
            ModdyEmbed.heading(f"✗ {title}", 2),
            ModdyEmbed.text(description)
        ]

        if details:
            components.append(ModdyEmbed.code_block(details))

        return components

    @staticmethod
    def info(title: str, fields: Dict[str, str], footer: Optional[str] = None) -> List[Dict[str, Any]]:
        """Message d'information avec champs"""
        components = [ModdyEmbed.heading(title, 2)]

        for name, value in fields.items():
            components.append(ModdyEmbed.field(name, f"`{value}`"))

        if footer:
            components.extend([
                ModdyEmbed.separator(),
                ModdyEmbed.text(f"_{footer}_")
            ])

        return components

    @staticmethod
    def loading(message: str = "Chargement en cours...") -> List[Dict[str, Any]]:
        """Message de chargement"""
        return [
            ModdyEmbed.text(f"⏳ {message}")
        ]

    @staticmethod
    def confirm(
            title: str,
            description: str,
            confirm_id: str = "confirm",
            cancel_id: str = "cancel"
    ) -> Dict[str, Any]:
        """Message de confirmation avec boutons"""
        return {
            "flags": ModdyEmbed.V2_FLAGS,
            "components": [
                ModdyEmbed.heading(title, 2),
                ModdyEmbed.text(description),
                ModdyEmbed.separator(),
                ModdyEmbed.action_row([
                    ModdyEmbed.button("Confirmer", confirm_id, style=3),  # Success
                    ModdyEmbed.button("Annuler", cancel_id, style=4)  # Danger
                ])
            ]
        }


# Pour la compatibilité avec l'ancien système
async def send_v2_response(ctx, components: List[Dict[str, Any]], ephemeral: bool = False):
    """
    Envoie une réponse V2 dans un contexte

    Args:
        ctx: Contexte de la commande ou interaction
        components: Liste des composants
        ephemeral: Si le message doit être éphémère
    """
    data = ModdyEmbed.create_v2_message(components)

    # Force l'utilisation des composants V2
    if ModdyEmbed.USE_V2_EVERYWHERE:
        if hasattr(ctx, 'response'):  # Interaction
            if ephemeral:
                await ctx.response.send_message(**data, ephemeral=True)
            else:
                await ctx.response.send_message(**data)
        else:  # Command context
            await ctx.send(**data)
    else:
        # Fallback pour la compatibilité
        if hasattr(ctx, 'response'):  # Interaction
            if ephemeral:
                await ctx.response.send_message(**data, ephemeral=True)
            else:
                await ctx.response.send_message(**data)
        else:  # Command context
            # Pour les commandes classiques, on doit convertir en embed standard
            # car les composants V2 ne sont pas encore supportés partout
            embed = discord.Embed(description="", color=None)

            for component in components:
                if component.get("type") == 10:  # Text Display
                    embed.description += component.get("content", "") + "\n"

            await ctx.send(embed=embed)