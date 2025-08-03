"""
Commande de gestion utilisateur pour développeurs
Panel complet avec boutons pour gérer les utilisateurs
"""

import discord
from discord.ext import commands
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import io  # Pour StringIO lors de l'export

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from config import COLORS


class UserManagement(commands.Cog):
    """Gestion complète des utilisateurs"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="user", aliases=["u", "manage"])
    async def user_management(self, ctx, user: discord.User = None):
        """Panel de gestion d'un utilisateur"""

        if not user:
            embed = discord.Embed(
                title="<:manageuser:1398729745293774919> Gestion Utilisateur",
                description=(
                    "**Usage :** `user @utilisateur` ou `user [ID]`\n\n"
                    "Affiche un panel complet pour gérer l'utilisateur :\n"
                    "• Voir et modifier les attributs\n"
                    "• Consulter la data stockée\n"
                    "• Gérer les permissions\n"
                    "• Voir l'historique"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        # Vérifie la BDD
        if not self.bot.db:
            await ctx.send("<:undone:1398729502028333218> Base de données non connectée")
            return

        # Récupère les données utilisateur
        try:
            user_data = await self.bot.db.get_user(user.id)
        except Exception as e:
            embed = ModdyResponse.error(
                "Erreur BDD",
                f"Impossible de récupérer les données : {str(e)}"
            )
            await ctx.send(embed=embed)
            return

        # Crée l'embed principal
        embed = UserManagement._create_user_embed(self.bot, user, user_data, ctx)

        # Crée la vue avec les boutons
        view = UserManagementView(self.bot, user, user_data, ctx.author)

        # Envoie le message
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg  # Stocke la référence du message

        # Log l'action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "user", {"target": str(user), "id": user.id})

    @staticmethod
    def _create_user_embed(bot, user: discord.User, user_data: Dict[str, Any], ctx: commands.Context) -> discord.Embed:
        """Crée l'embed principal avec les infos utilisateur"""

        # Récupère les infos Discord
        created_at = int(user.created_at.timestamp())

        # Badges
        badges = []
        if user_data['attributes'].get('DEVELOPER'):
            badges.append("<:dev:1398729645557285066>")
        if user_data['attributes'].get('PREMIUM'):
            badges.append("<:verified:1398729677601902635>")
        if user_data['attributes'].get('BETA'):
            badges.append("<:idea:1398729314597343313>")
        if user_data['attributes'].get('BLACKLISTED'):
            badges.append("<:undone:1398729502028333218>")

        badges_str = " ".join(badges) if badges else "Aucun"

        # Compte les serveurs mutuels
        mutual_guilds = []
        for guild in bot.guilds:
            if guild.get_member(user.id):
                mutual_guilds.append(guild)

        embed = discord.Embed(
            title=f"<:manageuser:1398729745293774919> Gestion de {user}",
            color=COLORS["primary"]
        )

        # Avatar
        embed.set_thumbnail(url=user.display_avatar.url)

        # Informations principales
        embed.add_field(
            name="<:user:1398729712204779571> Informations",
            value=(
                f"**ID :** `{user.id}`\n"
                f"**Mention :** {user.mention}\n"
                f"**Créé :** <t:{created_at}:R>\n"
                f"**Bot :** {'Oui' if user.bot else 'Non'}"
            ),
            inline=True
        )

        embed.add_field(
            name="<:settings:1398729549323440208> Statut",
            value=(
                f"**Badges :** {badges_str}\n"
                f"**Serveurs mutuels :** `{len(mutual_guilds)}`\n"
                f"**Attributs :** `{len(user_data['attributes'])}`\n"
                f"**Data stockée :** {'Oui' if user_data['data'] else 'Non'}"
            ),
            inline=True
        )

        # Attributs principaux
        if user_data['attributes']:
            attrs_preview = []
            for attr, value in list(user_data['attributes'].items())[:3]:
                if isinstance(value, bool):
                    val_str = "<:done:1398729525277229066>" if value else "<:undone:1398729502028333218>"
                else:
                    val_str = str(value)
                attrs_preview.append(f"`{attr}` : {val_str}")

            if len(user_data['attributes']) > 3:
                attrs_preview.append(f"*+{len(user_data['attributes']) - 3} autres...*")

            embed.add_field(
                name="<:label:1398729473649676440> Attributs",
                value="\n".join(attrs_preview),
                inline=False
            )

        # Footer avec timestamp
        embed.set_footer(
            text=f"Demandé par {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        embed.timestamp = datetime.now(timezone.utc)

        return embed


class UserManagementView(discord.ui.View):
    """Vue avec les boutons de gestion"""

    def __init__(self, bot, user: discord.User, user_data: Dict[str, Any], author: discord.User):
        super().__init__(timeout=300)  # 5 minutes
        self.bot = bot
        self.user = user
        self.user_data = user_data
        self.author = author
        self.current_page = "main"
        self.ctx = None  # Sera défini lors du rafraîchissement
        self.message = None  # Sera défini lors de l'envoi

    async def on_timeout(self):
        """Appelé quand la vue expire"""
        try:
            # Désactive tous les boutons
            for item in self.children:
                item.disabled = True

            if self.message:
                await self.message.edit(view=self)
        except:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Seul l'auteur peut utiliser les boutons"""
        if interaction.user != self.author:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Seul l'auteur de la commande peut utiliser ces boutons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Attributs", emoji="<:label:1398729473649676440>", style=discord.ButtonStyle.primary)
    async def show_attributes(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche et gère les attributs"""

        embed = discord.Embed(
            title=f"<:label:1398729473649676440> Attributs de {self.user}",
            color=COLORS["info"]
        )

        if self.user_data['attributes']:
            # Liste tous les attributs
            for attr, value in self.user_data['attributes'].items():
                if isinstance(value, bool):
                    val_str = "<:done:1398729525277229066> Activé" if value else "<:undone:1398729502028333218> Désactivé"
                else:
                    val_str = f"`{value}`"

                embed.add_field(
                    name=attr,
                    value=val_str,
                    inline=True
                )
        else:
            embed.description = "Aucun attribut défini pour cet utilisateur."

        # Ajoute les boutons d'action
        view = AttributeActionView(self.bot, self.user, self.user_data, self.author, self)

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Data", emoji="<:data_object:1401600908323852318>", style=discord.ButtonStyle.primary)
    async def show_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche la data stockée"""

        embed = discord.Embed(
            title=f"<:data_object:1401600908323852318> Data de {self.user}",
            color=COLORS["info"]
        )

        if self.user_data['data']:
            # Formate la data en JSON pretty
            data_str = json.dumps(self.user_data['data'], indent=2, ensure_ascii=False)

            # Tronque si trop long
            if len(data_str) > 1000:
                data_str = data_str[:997] + "..."

            embed.description = f"```json\n{data_str}\n```"

            # Stats sur la data
            embed.add_field(
                name="<:settings:1398729549323440208> Informations",
                value=(
                    f"**Taille :** `{len(json.dumps(self.user_data['data']))}` octets\n"
                    f"**Clés principales :** `{len(self.user_data['data'])}`"
                ),
                inline=False
            )
        else:
            embed.description = "Aucune data stockée pour cet utilisateur."

        # Bouton retour
        view = BackButtonView(self, interaction.message)

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Actions", emoji="<:settings:1398729549323440208>", style=discord.ButtonStyle.secondary)
    async def show_actions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche les actions disponibles"""

        embed = discord.Embed(
            title=f"<:settings:1398729549323440208> Actions pour {self.user}",
            description="Choisissez une action à effectuer :",
            color=COLORS["warning"]
        )

        # Crée la vue avec les actions
        view = UserActionsView(self.bot, self.user, self.user_data, self.author, self)

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Historique", emoji="<:history:1401600464587456512>", style=discord.ButtonStyle.secondary)
    async def show_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche l'historique des changements"""

        embed = discord.Embed(
            title=f"<:history:1401600464587456512> Historique de {self.user}",
            color=COLORS["info"]
        )

        try:
            # Récupère l'historique depuis la BDD
            async with self.bot.db.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM attribute_changes
                    WHERE entity_type = 'user' AND entity_id = $1
                    ORDER BY changed_at DESC
                    LIMIT 10
                """, self.user.id)

            if rows:
                for row in rows:
                    # Formate le changement
                    changed_by = self.bot.get_user(row['changed_by']) or f"ID: {row['changed_by']}"
                    timestamp = int(row['changed_at'].timestamp())

                    value_text = (
                        f"**Attribut :** `{row['attribute_name']}`\n"
                        f"**Avant :** `{row['old_value'] or 'Non défini'}`\n"
                        f"**Après :** `{row['new_value'] or 'Supprimé'}`\n"
                        f"**Par :** {changed_by}\n"
                        f"**Raison :** {row['reason'] or 'Aucune'}"
                    )

                    embed.add_field(
                        name=f"<t:{timestamp}:R>",
                        value=value_text,
                        inline=False
                    )
            else:
                embed.description = "Aucun historique trouvé pour cet utilisateur."

        except Exception as e:
            embed.description = f"<:undone:1398729502028333218> Erreur : {str(e)}"

        # Bouton retour
        view = BackButtonView(self, interaction.message)

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Rafraîchir", emoji="<:sync:1398729150885269546>", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rafraîchit les données"""

        await interaction.response.defer()

        # Recharge les données
        try:
            self.user_data = await self.bot.db.get_user(self.user.id)

            # Crée un contexte factice pour l'embed
            class FakeContext:
                def __init__(self, author):
                    self.author = author

            fake_ctx = FakeContext(self.author)

            # Recrée l'embed principal
            embed = UserManagement._create_user_embed(self.bot, self.user, self.user_data, fake_ctx)

            # Reset la vue
            new_view = UserManagementView(self.bot, self.user, self.user_data, self.author)

            await interaction.edit_original_response(embed=embed, view=new_view)

        except Exception as e:
            await interaction.followup.send(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ferme le panel"""
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class AttributeActionView(discord.ui.View):
    """Vue pour gérer les attributs"""

    def __init__(self, bot, user: discord.User, user_data: Dict[str, Any], author: discord.User, parent_view):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.user_data = user_data
        self.author = author
        self.parent_view = parent_view
        self.message = None

    async def on_timeout(self):
        """Désactive les boutons au timeout"""
        try:
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.edit(view=self)
        except:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author

    @discord.ui.button(label="Ajouter", emoji="<:done:1398729525277229066>", style=discord.ButtonStyle.success)
    async def add_attribute(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Modal pour ajouter un attribut"""
        modal = AddAttributeModal(self.bot, self.user, self.author)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Modifier", emoji="<:edit:1401600709824086169>", style=discord.ButtonStyle.primary)
    async def modify_attribute(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sélecteur pour modifier un attribut"""
        if not self.user_data['attributes']:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Aucun attribut à modifier",
                ephemeral=True
            )
            return

        # Crée le select menu
        view = ModifyAttributeView(self.bot, self.user, self.user_data, self.author)

        await interaction.response.send_message(
            "Sélectionnez l'attribut à modifier :",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Supprimer", emoji="<:undone:1398729502028333218>", style=discord.ButtonStyle.danger)
    async def remove_attribute(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sélecteur pour supprimer un attribut"""
        if not self.user_data['attributes']:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Aucun attribut à supprimer",
                ephemeral=True
            )
            return

        # Crée le select menu
        view = RemoveAttributeView(self.bot, self.user, self.user_data, self.author)

        await interaction.response.send_message(
            "Sélectionnez l'attribut à supprimer :",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Retour", emoji="<:back:1401600847733067806>", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour au menu principal"""
        # Recharge les données
        self.parent_view.user_data = await self.bot.db.get_user(self.user.id)

        # Crée un contexte factice
        class FakeContext:
            def __init__(self, author):
                self.author = author

        fake_ctx = FakeContext(self.author)

        # Recrée l'embed principal
        embed = UserManagement._create_user_embed(self.bot, self.user, self.parent_view.user_data, fake_ctx)

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class UserActionsView(discord.ui.View):
    """Vue avec les actions utilisateur"""

    def __init__(self, bot, user: discord.User, user_data: Dict[str, Any], author: discord.User, parent_view):
        super().__init__(timeout=300)
        self.bot = bot
        self.user = user
        self.user_data = user_data
        self.author = author
        self.parent_view = parent_view

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.author

    @discord.ui.button(label="Donner Premium", emoji="<:verified:1398729677601902635>", style=discord.ButtonStyle.success)
    async def give_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Donne le premium à l'utilisateur"""
        try:
            await self.bot.db.set_attribute(
                'user', self.user.id, 'PREMIUM', True,
                self.author.id, f"Donné via panel par {self.author}"
            )

            embed = ModdyResponse.success(
                "Premium activé",
                f"<:done:1398729525277229066> {self.user.mention} a maintenant le premium !"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )

    @discord.ui.button(label="Blacklist", emoji="<:undone:1398729502028333218>", style=discord.ButtonStyle.danger)
    async def blacklist_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Blacklist l'utilisateur"""
        # Demande confirmation
        view = ConfirmView()

        embed = discord.Embed(
            title="Confirmation requise",
            description=f"Êtes-vous sûr de vouloir blacklist {self.user.mention} ?\n"
                        "Il ne pourra plus utiliser le bot.",
            color=COLORS["error"]
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        # Attendre la réponse
        await view.wait()

        if view.value:
            try:
                await self.bot.db.set_attribute(
                    'user', self.user.id, 'BLACKLISTED', True,
                    self.author.id, f"Blacklist via panel par {self.author}"
                )

                await interaction.edit_original_response(
                    content=f"<:done:1398729525277229066> {self.user.mention} a été blacklist.",
                    embed=None,
                    view=None
                )
            except Exception as e:
                await interaction.edit_original_response(
                    content=f"<:undone:1398729502028333218> Erreur : {str(e)}",
                    embed=None,
                    view=None
                )

    @discord.ui.button(label="Réinitialiser", emoji="<:sync:1398729150885269546>", style=discord.ButtonStyle.danger)
    async def reset_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Réinitialise toutes les données de l'utilisateur"""
        # Demande confirmation
        modal = ResetConfirmModal(self.bot, self.user, self.author)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Exporter", emoji="<:import:1398729171584421958>", style=discord.ButtonStyle.secondary)
    async def export_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Exporte toutes les données de l'utilisateur"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Prépare les données complètes
            export_data = {
                "user": {
                    "id": self.user.id,
                    "username": str(self.user),
                    "created_at": self.user.created_at.isoformat()
                },
                "database": {
                    "attributes": self.user_data['attributes'],
                    "data": self.user_data['data'],
                    "created_at": self.user_data.get('created_at', 'N/A'),
                    "updated_at": self.user_data.get('updated_at', 'N/A')
                },
                "export_info": {
                    "exported_by": str(self.author),
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "bot_version": "Moddy v1.0"
                }
            }

            # Crée le fichier JSON
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)

            # Crée un fichier Discord
            file = discord.File(
                io.StringIO(json_str),
                filename=f"user_{self.user.id}_export.json"
            )

            await interaction.followup.send(
                f"<:done:1398729525277229066> Export complet de {self.user.mention}",
                file=file,
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )

    @discord.ui.button(label="Retour", emoji="<:back:1401600847733067806>", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour au menu principal"""
        # Recharge les données
        self.parent_view.user_data = await self.bot.db.get_user(self.user.id)

        # Crée un contexte factice
        class FakeContext:
            def __init__(self, author):
                self.author = author

        fake_ctx = FakeContext(self.author)

        # Recrée l'embed principal
        embed = UserManagement._create_user_embed(self.bot, self.user, self.parent_view.user_data, fake_ctx)

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class BackButtonView(discord.ui.View):
    """Vue simple avec juste un bouton retour"""

    def __init__(self, parent_view, message):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self.message = message

    @discord.ui.button(label="Retour", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour au menu principal"""
        # Recharge les données
        self.parent_view.user_data = await self.parent_view.bot.db.get_user(self.parent_view.user.id)

        # Crée un contexte factice
        class FakeContext:
            def __init__(self, author):
                self.author = author

        fake_ctx = FakeContext(self.parent_view.author)

        # Recrée l'embed principal
        embed = UserManagement(self.parent_view.bot)._create_user_embed(
            self.parent_view.user,
            self.parent_view.user_data,
            fake_ctx
        )

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class AddAttributeModal(discord.ui.Modal, title="Ajouter un attribut"):
    """Modal pour ajouter un attribut"""

    def __init__(self, bot, user: discord.User, author: discord.User):
        super().__init__()
        self.bot = bot
        self.user = user
        self.author = author

    attribute_name = discord.ui.TextInput(
        label="Nom de l'attribut",
        placeholder="Ex: BETA, PREMIUM, LANG...",
        max_length=50,
        required=True
    )

    attribute_value = discord.ui.TextInput(
        label="Valeur",
        placeholder="true, false, FR, EN... (laisser vide pour true)",
        max_length=100,
        required=False
    )

    reason = discord.ui.TextInput(
        label="Raison",
        placeholder="Pourquoi cet attribut est ajouté",
        max_length=200,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Parse la valeur
        value = self.attribute_value.value or "true"
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        try:
            await self.bot.db.set_attribute(
                'user', self.user.id,
                self.attribute_name.value.upper(),
                value,
                self.author.id,
                self.reason.value or "Ajout via panel"
            )

            embed = ModdyResponse.success(
                "Attribut ajouté",
                f"<:done:1398729525277229066> `{self.attribute_name.value.upper()}` = `{value}`"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class ModifyAttributeView(discord.ui.View):
    """Vue pour sélectionner un attribut à modifier"""

    def __init__(self, bot, user: discord.User, user_data: Dict[str, Any], author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.user_data = user_data
        self.author = author

        # Crée le select menu
        options = []
        for attr, value in user_data['attributes'].items():
            options.append(
                discord.SelectOption(
                    label=attr,
                    value=attr,
                    description=f"Valeur actuelle : {value}"
                )
            )

        self.select = discord.ui.Select(
            placeholder="Choisissez un attribut",
            options=options[:25]  # Limite Discord
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        """Quand un attribut est sélectionné"""
        selected = self.select.values[0]
        current_value = self.user_data['attributes'][selected]

        # Ouvre un modal pour modifier
        modal = ModifyAttributeModal(self.bot, self.user, self.author, selected, current_value)
        await interaction.response.send_modal(modal)


class RemoveAttributeView(discord.ui.View):
    """Vue pour sélectionner un attribut à supprimer"""

    def __init__(self, bot, user: discord.User, user_data: Dict[str, Any], author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.user_data = user_data
        self.author = author

        # Crée le select menu
        options = []
        for attr, value in user_data['attributes'].items():
            options.append(
                discord.SelectOption(
                    label=attr,
                    value=attr,
                    description=f"Valeur : {value}",
                    emoji="<:undone:1398729502028333218>"
                )
            )

        self.select = discord.ui.Select(
            placeholder="Choisissez un attribut à supprimer",
            options=options[:25]  # Limite Discord
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        """Quand un attribut est sélectionné"""
        selected = self.select.values[0]

        try:
            await self.bot.db.set_attribute(
                'user', self.user.id, selected, None,
                self.author.id, f"Suppression via panel"
            )

            embed = ModdyResponse.success(
                "Attribut supprimé",
                f"<:done:1398729525277229066> L'attribut `{selected}` a été supprimé"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class ModifyAttributeModal(discord.ui.Modal, title="Modifier un attribut"):
    """Modal pour modifier un attribut"""

    def __init__(self, bot, user: discord.User, author: discord.User, attr_name: str, current_value):
        super().__init__()
        self.bot = bot
        self.user = user
        self.author = author
        self.attr_name = attr_name

        # Ajoute dynamiquement le champ avec la valeur actuelle
        self.value_input = discord.ui.TextInput(
            label=f"Nouvelle valeur pour {attr_name}",
            placeholder=f"Valeur actuelle : {current_value}",
            default=str(current_value),
            max_length=100,
            required=True
        )
        self.add_item(self.value_input)

        self.reason = discord.ui.TextInput(
            label="Raison de la modification",
            placeholder="Optionnel",
            max_length=200,
            required=False
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        # Parse la valeur
        value = self.value_input.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        try:
            await self.bot.db.set_attribute(
                'user', self.user.id, self.attr_name, value,
                self.author.id, self.reason.value or "Modification via panel"
            )

            embed = ModdyResponse.success(
                "Attribut modifié",
                f"<:done:1398729525277229066> `{self.attr_name}` = `{value}`"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class ConfirmView(discord.ui.View):
    """Vue de confirmation simple"""

    def __init__(self):
        super().__init__(timeout=30)
        self.value = None

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = True
        self.stop()

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = False
        self.stop()


class ResetConfirmModal(discord.ui.Modal, title="Réinitialiser l'utilisateur"):
    """Modal de confirmation pour reset"""

    def __init__(self, bot, user: discord.User, author: discord.User):
        super().__init__()
        self.bot = bot
        self.user = user
        self.author = author

        # Configure le placeholder dynamiquement après l'init
        self.confirm_text.placeholder = f"Tapez exactement : {user.name}"

    confirm_text = discord.ui.TextInput(
        label="Tapez le nom d'utilisateur pour confirmer",
        placeholder="Tapez le nom exact de l'utilisateur",
        max_length=100,
        required=True
    )

    reason = discord.ui.TextInput(
        label="Raison de la réinitialisation",
        placeholder="Pourquoi réinitialiser cet utilisateur ?",
        max_length=200,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm_text.value != self.user.name:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Confirmation incorrecte. Vous devez taper exactement : `{self.user.name}`",
                ephemeral=True
            )
            return

        try:
            # Récupère d'abord les données actuelles
            user_data = await self.bot.db.get_user(self.user.id)

            # Supprime tous les attributs
            for attr in list(user_data['attributes'].keys()):
                await self.bot.db.set_attribute(
                    'user', self.user.id, attr, None,
                    self.author.id, f"Reset complet : {self.reason.value}"
                )

            # Reset la data
            async with self.bot.db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE users 
                    SET data = '{}'::jsonb, updated_at = NOW()
                    WHERE user_id = $1
                """, self.user.id)

            embed = ModdyResponse.success(
                "Utilisateur réinitialisé",
                f"<:done:1398729525277229066> Toutes les données de {self.user.mention} ont été supprimées."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


# Import pour StringIO supprimé car déjà dans les imports en haut


async def setup(bot):
    await bot.add_cog(UserManagement(bot))