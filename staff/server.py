"""
Commande de gestion serveur pour développeurs
Panel complet avec boutons pour gérer les serveurs
"""

import discord
from discord.ext import commands
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import io

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from config import COLORS


class ServerManagement(commands.Cog):
    """Gestion complète des serveurs"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="server", aliases=["s", "guild", "g"])
    async def server_management(self, ctx, *, guild_input: str = None):
        """Panel de gestion d'un serveur"""

        if not guild_input:
            embed = discord.Embed(
                title="<:server:1398840906248671354> Gestion Serveur",
                description=(
                    "**Usage :** `server [nom/ID]`\n\n"
                    "Affiche un panel complet pour gérer le serveur :\n"
                    "• Voir et modifier les attributs\n"
                    "• Consulter la configuration\n"
                    "• Gérer les permissions\n"
                    "• Voir l'historique et le cache"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        # Essaye de trouver le serveur
        guild = None

        # D'abord par ID
        if guild_input.isdigit():
            guild = self.bot.get_guild(int(guild_input))

        # Ensuite par nom
        if not guild:
            for g in self.bot.guilds:
                if g.name.lower() == guild_input.lower():
                    guild = g
                    break

        # Si toujours pas trouvé et qu'on a la BDD, cherche dans le cache
        if not guild and self.bot.db and guild_input.isdigit():
            try:
                cached_info = await self.bot.db.get_cached_guild(int(guild_input))
                if cached_info:
                    # Crée un objet guild partiel
                    guild = discord.Object(id=int(guild_input))
                    guild.name = cached_info['name']
                    guild._cached_data = cached_info
            except:
                pass

        if not guild:
            await ctx.send(f"<:undone:1398729502028333218> Serveur `{guild_input}` introuvable")
            return

        # Vérifie la BDD
        if not self.bot.db:
            await ctx.send("<:undone:1398729502028333218> Base de données non connectée")
            return

        # Récupère les données serveur
        try:
            guild_data = await self.bot.db.get_guild(guild.id)
        except Exception as e:
            embed = ModdyResponse.error(
                "Erreur BDD",
                f"Impossible de récupérer les données : {str(e)}"
            )
            await ctx.send(embed=embed)
            return

        # Crée l'embed principal
        embed = ServerManagement._create_guild_embed(self.bot, guild, guild_data, ctx)

        # Crée la vue avec les boutons
        view = ServerManagementView(self.bot, guild, guild_data, ctx.author)

        # Envoie le message
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

        # Log l'action
        if log_cog := self.bot.get_cog("LoggingSystem"):
            await log_cog.log_command(ctx, "server", {"target": getattr(guild, 'name', 'Unknown'), "id": guild.id})

    @staticmethod
    def _create_guild_embed(bot, guild, guild_data: Dict[str, Any], ctx: commands.Context) -> discord.Embed:
        """Crée l'embed principal avec les infos serveur"""

        # Si c'est un serveur depuis le cache
        is_cached = hasattr(guild, '_cached_data')

        if is_cached:
            created_at = guild._cached_data['created_at']
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at)
            created_timestamp = int(created_at.timestamp())
        else:
            created_timestamp = int(guild.created_at.timestamp())

        # Badges
        badges = []
        if guild_data['attributes'].get('OFFICIAL_SERVER'):
            badges.append("<:verified:1398729677601902635>")
        if guild_data['attributes'].get('PREMIUM_GUILD'):
            badges.append("<:premium:1401602724801548381>")
        if guild_data['attributes'].get('BETA_FEATURES'):
            badges.append("<:idea:1398729314597343313>")
        if guild_data['attributes'].get('VERIFIED_GUILD'):
            badges.append("<:done:1398729525277229066>")
        if guild_data['attributes'].get('LEGACY'):
            badges.append("<:time:1398729780723060736>")

        badges_str = " ".join(badges) if badges else "Aucun"

        # Infos selon la source
        if is_cached:
            info_source = f"(Cache - {guild._cached_data['update_source']})"
            member_count = guild._cached_data.get('member_count', 'N/A')
            icon_url = guild._cached_data.get('icon_url')
        else:
            info_source = "(Bot présent)"
            member_count = guild.member_count
            icon_url = guild.icon.url if guild.icon else None

        embed = discord.Embed(
            title=f"<:server:1398840906248671354> Gestion de {guild.name}",
            description=f"*{info_source}*",
            color=COLORS["primary"]
        )

        # Icon
        if icon_url:
            embed.set_thumbnail(url=icon_url)

        # Informations principales
        embed.add_field(
            name="<:info:1401614681440784477> Informations",
            value=(
                f"**ID :** `{guild.id}`\n"
                f"**Créé :** <t:{created_timestamp}:R>\n"
                f"**Membres :** `{member_count}`"
            ),
            inline=True
        )

        embed.add_field(
            name="<:settings:1398729549323440208> Statut",
            value=(
                f"**Badges :** {badges_str}\n"
                f"**Attributs :** `{len(guild_data['attributes'])}`\n"
                f"**Config :** {'<:done:1398729525277229066>' if guild_data['data'].get('config') else '<:undone:1398729502028333218>'}\n"
                f"**Préfixe :** `{guild_data['data'].get('config', {}).get('prefix', '!')}`"
            ),
            inline=True
        )

        # Attributs principaux
        if guild_data['attributes']:
            attrs_preview = []
            for attr, value in list(guild_data['attributes'].items())[:3]:
                if isinstance(value, bool):
                    val_str = "<:done:1398729525277229066>" if value else "<:undone:1398729502028333218>"
                else:
                    val_str = str(value)
                attrs_preview.append(f"`{attr}` : {val_str}")

            if len(guild_data['attributes']) > 3:
                attrs_preview.append(f"*+{len(guild_data['attributes']) - 3} autres...*")

            embed.add_field(
                name="<:label:1398729473649676440> Attributs",
                value="\n".join(attrs_preview),
                inline=False
            )

        # Config preview si disponible
        if guild_data['data']:
            preview_lines = []

            # Préfixe si dans config
            config = guild_data['data'].get('config', {})
            if config.get('prefix'):
                preview_lines.append(f"**Préfixe :** `{config['prefix']}`")

            # Nombre de tags
            if guild_data['data'].get('tags'):
                preview_lines.append(f"**Tags :** `{len(guild_data['data']['tags'])}`")

            # Autres clés importantes
            other_keys = [k for k in guild_data['data'].keys() if k not in ['config', 'tags']]
            if other_keys:
                preview_lines.append(f"**Autres clés :** `{len(other_keys)}`")

            if preview_lines:
                embed.add_field(
                    name="<:data_object:1401600908323852318> Data",
                    value="\n".join(preview_lines),
                    inline=False
                )

        # Footer avec timestamp
        embed.set_footer(
            text=f"Demandé par {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )
        embed.timestamp = datetime.now(timezone.utc)

        return embed


class ServerManagementView(discord.ui.View):
    """Vue avec les boutons de gestion"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User):
        super().__init__(timeout=600)  # 10 minutes
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author
        self.current_page = "main"
        self.message = None

    async def on_timeout(self):
        """Appelé quand la vue expire"""
        try:
            for item in self.children:
                item.disabled = True

            if self.message:
                await self.message.edit(view=self)
        except:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Seul l'auteur peut utiliser les boutons ET doit être développeur"""
        if not self.bot.is_developer(interaction.user.id):
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Cette action est réservée aux développeurs.",
                ephemeral=True
            )
            return False

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
            title=f"<:label:1398729473649676440> Attributs de {self.guild.name}",
            color=COLORS["info"]
        )

        if self.guild_data['attributes']:
            for attr, value in self.guild_data['attributes'].items():
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
            embed.description = "Aucun attribut défini pour ce serveur."

        view = GuildAttributeActionView(self.bot, self.guild, self.guild_data, self.author, self)
        view.message = interaction.message

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Data", emoji="<:data_object:1401600908323852318>", style=discord.ButtonStyle.primary)
    async def show_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche la data stockée"""

        embed = discord.Embed(
            title=f"<:data_object:1401600908323852318> Data de {self.guild.name}",
            color=COLORS["info"]
        )

        if self.guild_data['data']:
            data_str = json.dumps(self.guild_data['data'], indent=2, ensure_ascii=False)

            if len(data_str) > 1000:
                data_str = data_str[:997] + "..."

            embed.description = f"```json\n{data_str}\n```"

            embed.add_field(
                name="<:settings:1398729549323440208> Informations",
                value=(
                    f"**Taille :** `{len(json.dumps(self.guild_data['data']))}` octets\n"
                    f"**Clés principales :** `{len(self.guild_data['data'])}`"
                ),
                inline=False
            )
        else:
            embed.description = "Aucune data stockée pour ce serveur."

        view = GuildDataManagementView(self.bot, self.guild, self.guild_data, self.author, self)

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Actions", emoji="<:settings:1398729549323440208>", style=discord.ButtonStyle.secondary)
    async def show_actions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche les actions disponibles"""

        embed = discord.Embed(
            title=f"<:settings:1398729549323440208> Actions pour {self.guild.name}",
            description="Choisissez une action à effectuer :",
            color=COLORS["warning"]
        )

        view = GuildActionsView(self.bot, self.guild, self.guild_data, self.author, self)
        view.message = interaction.message

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Historique", emoji="<:history:1401600464587456512>", style=discord.ButtonStyle.secondary)
    async def show_history(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Affiche l'historique des changements"""

        embed = discord.Embed(
            title=f"<:history:1401600464587456512> Historique de {self.guild.name}",
            color=COLORS["info"]
        )

        try:
            async with self.bot.db.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM attribute_changes
                    WHERE entity_type = 'guild' AND entity_id = $1
                    ORDER BY changed_at DESC
                    LIMIT 10
                """, self.guild.id)

            if rows:
                for row in rows:
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
                embed.description = "Aucun historique trouvé pour ce serveur."

        except Exception as e:
            embed.description = f"<:undone:1398729502028333218> Erreur : {str(e)}"

        view = BackButtonView(self, interaction.message)

        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Rafraîchir", emoji="<:sync:1398729150885269546>", style=discord.ButtonStyle.secondary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Rafraîchit les données"""

        await interaction.response.defer()

        try:
            # Rafraîchit les données
            self.guild_data = await self.bot.db.get_guild(self.guild.id)

            # Si le bot est dans le serveur, met à jour le cache
            if real_guild := self.bot.get_guild(self.guild.id):
                from database import UpdateSource
                guild_info = {
                    'name': real_guild.name,
                    'icon_url': str(real_guild.icon.url) if real_guild.icon else None,
                    'features': real_guild.features,
                    'member_count': real_guild.member_count,
                    'created_at': real_guild.created_at
                }
                await self.bot.db.cache_guild_info(self.guild.id, guild_info, UpdateSource.MANUAL)

            class FakeContext:
                def __init__(self, author):
                    self.author = author

            fake_ctx = FakeContext(self.author)

            embed = ServerManagement._create_guild_embed(self.bot, self.guild, self.guild_data, fake_ctx)

            new_view = ServerManagementView(self.bot, self.guild, self.guild_data, self.author)
            new_view.message = self.message

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


class GuildAttributeActionView(discord.ui.View):
    """Vue pour gérer les attributs serveur"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
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
        """Vérifie que c'est un développeur ET l'auteur"""
        if not self.bot.is_developer(interaction.user.id):
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Cette action est réservée aux développeurs.",
                ephemeral=True
            )
            return False

        if interaction.user != self.author:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Seul l'auteur de la commande peut utiliser ces boutons.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Ajouter", emoji="<:add:1401608434230493254>", style=discord.ButtonStyle.success)
    async def add_attribute(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Modal pour ajouter un attribut"""
        modal = AddGuildAttributeModal(self.bot, self.guild, self.author, self)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Modifier", emoji="<:edit:1401600709824086169>", style=discord.ButtonStyle.primary)
    async def modify_attribute(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sélecteur pour modifier un attribut"""
        if not self.guild_data['attributes']:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Aucun attribut à modifier",
                ephemeral=True
            )
            return

        view = ModifyGuildAttributeView(self.bot, self.guild, self.guild_data, self.author)

        await interaction.response.send_message(
            "Sélectionnez l'attribut à modifier :",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Supprimer", emoji="<:undone:1398729502028333218>", style=discord.ButtonStyle.danger)
    async def remove_attribute(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Sélecteur pour supprimer un attribut"""
        if not self.guild_data['attributes']:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Aucun attribut à supprimer",
                ephemeral=True
            )
            return

        view = RemoveGuildAttributeView(self.bot, self.guild, self.guild_data, self.author)

        await interaction.response.send_message(
            "Sélectionnez l'attribut à supprimer :",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Retour", emoji="<:back:1401600847733067806>", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour au menu principal"""
        self.parent_view.guild_data = await self.bot.db.get_guild(self.guild.id)

        class FakeContext:
            def __init__(self, author):
                self.author = author

        fake_ctx = FakeContext(self.author)

        embed = ServerManagement._create_guild_embed(self.bot, self.guild, self.parent_view.guild_data, fake_ctx)

        await interaction.response.edit_message(embed=embed, view=self.parent_view)

    async def refresh_parent_data(self):
        """Rafraîchit les données du parent view"""
        self.parent_view.guild_data = await self.bot.db.get_guild(self.guild.id)
        self.guild_data = self.parent_view.guild_data


class GuildActionsView(discord.ui.View):
    """Vue avec les actions serveur"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author
        self.parent_view = parent_view
        self.message = None

        # Ajoute les boutons dynamiquement
        self._add_dynamic_buttons()

    def _add_dynamic_buttons(self):
        """Ajoute les boutons avec les bonnes couleurs selon l'état"""
        # Bouton Premium
        has_premium = self.guild_data['attributes'].get('PREMIUM_GUILD', False)
        premium_btn = discord.ui.Button(
            label="Premium",
            emoji="<:premium:1401602724801548381>",
            style=discord.ButtonStyle.success if has_premium else discord.ButtonStyle.danger,
            row=0
        )
        premium_btn.callback = self.toggle_premium
        self.add_item(premium_btn)

        # Bouton Beta
        has_beta = self.guild_data['attributes'].get('BETA_FEATURES', False)
        beta_btn = discord.ui.Button(
            label="Beta",
            emoji="<:idea:1398729314597343313>",
            style=discord.ButtonStyle.success if has_beta else discord.ButtonStyle.danger,
            row=0
        )
        beta_btn.callback = self.toggle_beta
        self.add_item(beta_btn)

        # Bouton Officiel
        is_official = self.guild_data['attributes'].get('OFFICIAL_SERVER', False)
        official_btn = discord.ui.Button(
            label="Officiel",
            emoji="<:verified:1398729677601902635>",
            style=discord.ButtonStyle.success if is_official else discord.ButtonStyle.danger,
            row=0
        )
        official_btn.callback = self.toggle_official
        self.add_item(official_btn)

        # Autres boutons
        if not hasattr(self.guild, '_cached_data'):  # Seulement si le bot est présent
            leave_btn = discord.ui.Button(
                label="Quitter",
                emoji="<:import:1398729171584421958>",
                style=discord.ButtonStyle.danger,
                row=1
            )
            leave_btn.callback = self.leave_guild
            self.add_item(leave_btn)

        reset_btn = discord.ui.Button(
            label="Réinitialiser",
            emoji="<:sync:1398729150885269546>",
            style=discord.ButtonStyle.danger,
            row=1
        )
        reset_btn.callback = self.reset_guild
        self.add_item(reset_btn)

        export_btn = discord.ui.Button(
            label="Exporter",
            emoji="<:download:1401600503867248730>",
            style=discord.ButtonStyle.secondary,
            row=1
        )
        export_btn.callback = self.export_data
        self.add_item(export_btn)

        back_btn = discord.ui.Button(
            label="Retour",
            emoji="<:back:1401600847733067806>",
            style=discord.ButtonStyle.secondary,
            row=1
        )
        back_btn.callback = self.back
        self.add_item(back_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie que c'est un développeur ET l'auteur"""
        if not self.bot.is_developer(interaction.user.id):
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Cette action est réservée aux développeurs.",
                ephemeral=True
            )
            return False
        return interaction.user == self.author

    async def toggle_premium(self, interaction: discord.Interaction):
        """Active/désactive le premium"""
        has_premium = self.guild_data['attributes'].get('PREMIUM_GUILD', False)
        new_value = not has_premium

        try:
            await self.bot.db.set_attribute(
                'guild', self.guild.id, 'PREMIUM_GUILD', new_value,
                self.author.id, f"{'Retrait' if has_premium else 'Ajout'} via panel par {self.author}"
            )

            # Rafraîchit les données
            self.guild_data = await self.bot.db.get_guild(self.guild.id)
            self.parent_view.guild_data = self.guild_data

            # Recrée la vue
            new_view = GuildActionsView(self.bot, self.guild, self.guild_data, self.author, self.parent_view)
            new_view.message = self.message

            # Recrée l'embed
            embed = discord.Embed(
                title=f"<:settings:1398729549323440208> Actions pour {self.guild.name}",
                description=f"<:done:1398729525277229066> Premium {'activé' if new_value else 'désactivé'} !",
                color=COLORS["success"]
            )

            await interaction.response.edit_message(embed=embed, view=new_view)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )

    async def toggle_beta(self, interaction: discord.Interaction):
        """Active/désactive les features beta"""
        has_beta = self.guild_data['attributes'].get('BETA_FEATURES', False)
        new_value = not has_beta

        try:
            await self.bot.db.set_attribute(
                'guild', self.guild.id, 'BETA_FEATURES', new_value,
                self.author.id, f"{'Retrait' if has_beta else 'Ajout'} beta via panel"
            )

            # Rafraîchit les données
            self.guild_data = await self.bot.db.get_guild(self.guild.id)
            self.parent_view.guild_data = self.guild_data

            # Recrée la vue
            new_view = GuildActionsView(self.bot, self.guild, self.guild_data, self.author, self.parent_view)
            new_view.message = self.message

            # Recrée l'embed
            embed = discord.Embed(
                title=f"<:settings:1398729549323440208> Actions pour {self.guild.name}",
                description=f"<:done:1398729525277229066> Features beta {'activées' if new_value else 'désactivées'} !",
                color=COLORS["success"]
            )

            await interaction.response.edit_message(embed=embed, view=new_view)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )

    async def toggle_official(self, interaction: discord.Interaction):
        """Active/désactive le statut officiel"""
        is_official = self.guild_data['attributes'].get('OFFICIAL_SERVER', False)

        if not is_official:
            # Demande confirmation
            view = ConfirmView()
            embed = discord.Embed(
                title="Confirmation requise",
                description=f"Êtes-vous sûr de vouloir marquer **{self.guild.name}** comme serveur officiel ?",
                color=COLORS["warning"]
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            await view.wait()

            if not view.value:
                return

        try:
            new_value = not is_official
            await self.bot.db.set_attribute(
                'guild', self.guild.id, 'OFFICIAL_SERVER', new_value,
                self.author.id, f"{'Retrait' if is_official else 'Ajout'} statut officiel"
            )

            # Rafraîchit les données
            self.guild_data = await self.bot.db.get_guild(self.guild.id)
            self.parent_view.guild_data = self.guild_data

            # Recrée la vue
            new_view = GuildActionsView(self.bot, self.guild, self.guild_data, self.author, self.parent_view)
            new_view.message = self.message

            # Recrée l'embed
            embed = discord.Embed(
                title=f"<:settings:1398729549323440208> Actions pour {self.guild.name}",
                description=f"<:done:1398729525277229066> Statut officiel {'activé' if new_value else 'retiré'} !",
                color=COLORS["success"]
            )

            if is_official:
                await interaction.response.edit_message(embed=embed, view=new_view)
            else:
                await interaction.edit_original_response(embed=embed, view=new_view)

        except Exception as e:
            if is_official:
                await interaction.response.send_message(
                    f"<:undone:1398729502028333218> Erreur : {str(e)}",
                    ephemeral=True
                )
            else:
                await interaction.edit_original_response(
                    content=f"<:undone:1398729502028333218> Erreur : {str(e)}",
                    embed=None,
                    view=None
                )

    async def leave_guild(self, interaction: discord.Interaction):
        """Fait quitter le bot du serveur"""
        view = ConfirmView()
        embed = discord.Embed(
            title="Confirmation requise",
            description=f"Êtes-vous sûr de vouloir faire quitter le bot de **{self.guild.name}** ?",
            color=COLORS["error"]
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            try:
                real_guild = self.bot.get_guild(self.guild.id)
                if real_guild:
                    await real_guild.leave()
                    await interaction.edit_original_response(
                        content=f"<:done:1398729525277229066> Le bot a quitté **{self.guild.name}**",
                        embed=None,
                        view=None
                    )
                else:
                    await interaction.edit_original_response(
                        content="<:undone:1398729502028333218> Le bot n'est pas dans ce serveur",
                        embed=None,
                        view=None
                    )
            except Exception as e:
                await interaction.edit_original_response(
                    content=f"<:undone:1398729502028333218> Erreur : {str(e)}",
                    embed=None,
                    view=None
                )

    async def reset_guild(self, interaction: discord.Interaction):
        """Réinitialise toutes les données du serveur"""
        modal = ResetGuildConfirmModal(self.bot, self.guild, self.author)
        await interaction.response.send_modal(modal)

    async def export_data(self, interaction: discord.Interaction):
        """Exporte toutes les données du serveur"""
        await interaction.response.defer(ephemeral=True)

        try:
            # Récupère aussi les infos du cache si disponibles
            cached_info = None
            if self.bot.db:
                cached_info = await self.bot.db.get_cached_guild(self.guild.id, max_age_days=365)

            export_data = {
                "guild": {
                    "id": self.guild.id,
                    "name": self.guild.name,
                    "created_at": str(getattr(self.guild, 'created_at', 'N/A'))
                },
                "database": {
                    "attributes": self.guild_data['attributes'],
                    "data": self.guild_data['data'],
                    "created_at": str(self.guild_data.get('created_at', 'N/A')),
                    "updated_at": str(self.guild_data.get('updated_at', 'N/A'))
                },
                "cache": cached_info if cached_info else None,
                "export_info": {
                    "exported_by": str(self.author),
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                    "bot_version": "Moddy v1.0"
                }
            }

            json_str = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)

            file = discord.File(
                io.StringIO(json_str),
                filename=f"guild_{self.guild.id}_export.json"
            )

            await interaction.followup.send(
                f"<:done:1398729525277229066> Export complet de **{self.guild.name}**",
                file=file,
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )

    async def back(self, interaction: discord.Interaction):
        """Retour au menu principal"""
        self.parent_view.guild_data = await self.bot.db.get_guild(self.guild.id)

        class FakeContext:
            def __init__(self, author):
                self.author = author

        fake_ctx = FakeContext(self.author)

        embed = ServerManagement._create_guild_embed(self.bot, self.guild, self.parent_view.guild_data, fake_ctx)

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class GuildDataManagementView(discord.ui.View):
    """Vue pour gérer la data serveur"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author
        self.parent_view = parent_view

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie que c'est un développeur ET l'auteur"""
        if not self.bot.is_developer(interaction.user.id):
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Cette action est réservée aux développeurs.",
                ephemeral=True
            )
            return False
        return interaction.user == self.author

    @discord.ui.button(label="Modifier JSON", emoji="<:edit:1401600709824086169>", style=discord.ButtonStyle.primary)
    async def edit_json(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ouvre un modal pour éditer le JSON complet"""
        modal = EditGuildDataModal(self.bot, self.guild, self.guild_data, self.author)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Ajouter une clé", emoji="<:add:1401608434230493254>", style=discord.ButtonStyle.success)
    async def add_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ajoute une nouvelle clé à la data"""
        modal = AddGuildDataKeyModal(self.bot, self.guild, self.author)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Supprimer une clé", emoji="<:undone:1398729502028333218>", style=discord.ButtonStyle.danger)
    async def remove_key(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Supprime une clé de la data"""
        if not self.guild_data['data']:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Aucune data à supprimer",
                ephemeral=True
            )
            return

        view = RemoveGuildDataKeyView(self.bot, self.guild, self.guild_data, self.author)
        await interaction.response.send_message(
            "Sélectionnez la clé à supprimer :",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Réinitialiser", emoji="<:sync:1398729150885269546>", style=discord.ButtonStyle.danger)
    async def reset_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Réinitialise toute la data"""
        view = ConfirmView()
        embed = discord.Embed(
            title="Confirmation requise",
            description=f"Êtes-vous sûr de vouloir réinitialiser toute la data de **{self.guild.name}** ?",
            color=COLORS["error"]
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            try:
                async with self.bot.db.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE guilds 
                        SET data = '{}'::jsonb, updated_at = NOW()
                        WHERE guild_id = $1
                    """, self.guild.id)

                await interaction.edit_original_response(
                    content=f"<:done:1398729525277229066> Data réinitialisée pour **{self.guild.name}**",
                    embed=None,
                    view=None
                )
            except Exception as e:
                await interaction.edit_original_response(
                    content=f"<:undone:1398729502028333218> Erreur : {str(e)}",
                    embed=None,
                    view=None
                )

    @discord.ui.button(label="Retour", emoji="<:back:1401600847733067806>", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour au menu principal"""
        self.parent_view.guild_data = await self.bot.db.get_guild(self.guild.id)

        class FakeContext:
            def __init__(self, author):
                self.author = author

        fake_ctx = FakeContext(self.author)

        embed = ServerManagement._create_guild_embed(self.bot, self.guild, self.parent_view.guild_data, fake_ctx)

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class TagManagementView(discord.ui.View):
    """Vue pour gérer les tags"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User, parent_view):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author
        self.parent_view = parent_view

    @discord.ui.button(label="Ajouter", emoji="<:add:1401608434230493254>", style=discord.ButtonStyle.success)
    async def add_tag(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Ajoute un nouveau tag"""
        modal = AddTagModal(self.bot, self.guild, self.author)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Supprimer", emoji="<:undone:1398729502028333218>", style=discord.ButtonStyle.danger)
    async def remove_tag(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Supprime un tag"""
        tags = self.guild_data['data'].get('tags', {})

        if not tags:
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Aucun tag à supprimer",
                ephemeral=True
            )
            return

        view = RemoveTagView(self.bot, self.guild, tags, self.author)

        await interaction.response.send_message(
            "Sélectionnez le tag à supprimer :",
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Retour", emoji="<:back:1401600847733067806>", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour à la config"""
        # Rafraîchit les données
        self.parent_view.guild_data = await self.bot.db.get_guild(self.guild.id)

        embed = discord.Embed(
            title=f"<:panel:1398720151980998789> Configuration de {self.guild.name}",
            color=COLORS["info"]
        )

        config = self.parent_view.guild_data['data'].get('config', {})

        if config:
            embed.add_field(
                name="<:settings:1398729549323440208> Paramètres",
                value=(
                    f"**Préfixe :** `{config.get('prefix', '!')}`\n"
                    f"**Canal de bienvenue :** {f'<#{config["welcome_channel"]}>' if config.get('welcome_channel') else 'Non défini'}\n"
                    f"**Canal de logs :** {f'<#{config["log_channel"]}>' if config.get('log_channel') else 'Non défini'}"
                ),
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


# === MODALS ===

class AddGuildAttributeModal(discord.ui.Modal, title="Ajouter un attribut"):
    """Modal pour ajouter un attribut serveur"""

    def __init__(self, bot, guild, author: discord.User, parent_view=None):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.author = author
        self.parent_view = parent_view

    attribute_name = discord.ui.TextInput(
        label="Nom de l'attribut",
        placeholder="Ex: BETA_FEATURES, PREMIUM_GUILD, LANG...",
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
        value = self.attribute_value.value or "true"
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        try:
            await self.bot.db.set_attribute(
                'guild', self.guild.id,
                self.attribute_name.value.upper(),
                value,
                self.author.id,
                self.reason.value or "Ajout via panel"
            )

            if self.parent_view and hasattr(self.parent_view, 'refresh_parent_data'):
                await self.parent_view.refresh_parent_data()

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


class ModifyGuildAttributeView(discord.ui.View):
    """Vue pour sélectionner un attribut à modifier"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author

        options = []
        for attr, value in guild_data['attributes'].items():
            options.append(
                discord.SelectOption(
                    label=attr,
                    value=attr,
                    description=f"Valeur actuelle : {value}"
                )
            )

        self.select = discord.ui.Select(
            placeholder="Choisissez un attribut",
            options=options[:25]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        """Quand un attribut est sélectionné"""
        selected = self.select.values[0]
        current_value = self.guild_data['attributes'][selected]

        modal = ModifyGuildAttributeModal(self.bot, self.guild, self.author, selected, current_value)
        await interaction.response.send_modal(modal)


class RemoveGuildAttributeView(discord.ui.View):
    """Vue pour sélectionner un attribut à supprimer"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author

        options = []
        for attr, value in guild_data['attributes'].items():
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
            options=options[:25]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        """Quand un attribut est sélectionné"""
        selected = self.select.values[0]

        try:
            await self.bot.db.set_attribute(
                'guild', self.guild.id, selected, None,
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


class ModifyGuildAttributeModal(discord.ui.Modal, title="Modifier un attribut"):
    """Modal pour modifier un attribut serveur"""

    def __init__(self, bot, guild, author: discord.User, attr_name: str, current_value):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.author = author
        self.attr_name = attr_name

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
        value = self.value_input.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        try:
            await self.bot.db.set_attribute(
                'guild', self.guild.id, self.attr_name, value,
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


class EditGuildDataModal(discord.ui.Modal, title="Modifier la data JSON"):
    """Modal pour éditer le JSON complet de la data serveur"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author

        # Prépare le JSON actuel
        current_json = json.dumps(guild_data['data'], indent=2, ensure_ascii=False)

        # Limite à 1024 caractères pour le champ Discord
        if len(current_json) > 1024:
            current_json = current_json[:1021] + "..."

        self.json_input = discord.ui.TextInput(
            label="Data JSON",
            style=discord.TextStyle.paragraph,
            placeholder='{"key": "value"}',
            default=current_json,
            max_length=4000,
            required=True
        )
        self.add_item(self.json_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse le JSON
            new_data = json.loads(self.json_input.value)

            # Met à jour dans la BDD
            async with self.bot.db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE guilds 
                    SET data = $1::jsonb, updated_at = NOW()
                    WHERE guild_id = $2
                """, json.dumps(new_data), self.guild.id)

            # Invalide le cache de préfixe si le préfixe est dans la config
            if 'config' in new_data and 'prefix' in new_data.get('config', {}):
                self.bot.prefix_cache.pop(self.guild.id, None)

            embed = ModdyResponse.success(
                "Data modifiée",
                f"<:done:1398729525277229066> La data de **{self.guild.name}** a été mise à jour"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except json.JSONDecodeError as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> JSON invalide : {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class AddGuildDataKeyModal(discord.ui.Modal, title="Ajouter une clé à la data"):
    """Modal pour ajouter une nouvelle clé à la data serveur"""

    def __init__(self, bot, guild, author: discord.User):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.author = author

    key_path = discord.ui.TextInput(
        label="Chemin de la clé",
        placeholder="Ex: config.prefix ou simplement tags",
        max_length=100,
        required=True
    )

    value_input = discord.ui.TextInput(
        label="Valeur (JSON)",
        style=discord.TextStyle.paragraph,
        placeholder='Exemples:\n"texte"\n123\ntrue\n{"key": "value"}\n["item1", "item2"]',
        max_length=1000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse la valeur
            if self.value_input.value.lower() == "true":
                value = True
            elif self.value_input.value.lower() == "false":
                value = False
            elif self.value_input.value.lower() == "null":
                value = None
            else:
                try:
                    value = json.loads(self.value_input.value)
                except:
                    # Si ce n'est pas du JSON valide, traite comme string
                    value = self.value_input.value

            # Met à jour dans la BDD
            await self.bot.db.update_guild_data(self.guild.id, self.key_path.value, value)

            # Invalide le cache si c'est le préfixe
            if self.key_path.value == "config.prefix":
                self.bot.prefix_cache.pop(self.guild.id, None)

            embed = ModdyResponse.success(
                "Clé ajoutée",
                f"<:done:1398729525277229066> `{self.key_path.value}` = `{value}`"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class RemoveGuildDataKeyView(discord.ui.View):
    """Vue pour sélectionner une clé à supprimer de la data serveur"""

    def __init__(self, bot, guild, guild_data: Dict[str, Any], author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild = guild
        self.guild_data = guild_data
        self.author = author

        # Crée les options depuis les clés de premier niveau
        options = []
        for key in guild_data['data'].keys():
            value_preview = str(guild_data['data'][key])
            if len(value_preview) > 50:
                value_preview = value_preview[:47] + "..."

            options.append(
                discord.SelectOption(
                    label=key,
                    value=key,
                    description=value_preview,
                    emoji="<:undone:1398729502028333218>"
                )
            )

        self.select = discord.ui.Select(
            placeholder="Choisissez une clé à supprimer",
            options=options[:25]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        """Quand une clé est sélectionnée"""
        selected = self.select.values[0]

        try:
            # Récupère la data actuelle
            guild_data = await self.bot.db.get_guild(self.guild.id)
            current_data = guild_data['data']

            # Supprime la clé
            if selected in current_data:
                del current_data[selected]

            # Met à jour dans la BDD
            async with self.bot.db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE guilds 
                    SET data = $1::jsonb, updated_at = NOW()
                    WHERE guild_id = $2
                """, json.dumps(current_data), self.guild.id)

            # Invalide le cache si c'était la config
            if selected == 'config':
                self.bot.prefix_cache.pop(self.guild.id, None)

            embed = ModdyResponse.success(
                "Clé supprimée",
                f"<:done:1398729525277229066> La clé `{selected}` a été supprimée"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class ChangePrefixModal(discord.ui.Modal, title="Changer le préfixe"):
    """Modal pour changer le préfixe du serveur"""

    def __init__(self, bot, guild, author: discord.User):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.author = author

    prefix_input = discord.ui.TextInput(
        label="Nouveau préfixe",
        placeholder="Ex: !, ?, //, >>",
        max_length=10,
        min_length=1,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        new_prefix = self.prefix_input.value

        try:
            await self.bot.db.update_guild_data(self.guild.id, 'config.prefix', new_prefix)

            # Invalide le cache
            self.bot.prefix_cache.pop(self.guild.id, None)

            embed = ModdyResponse.success(
                "Préfixe changé",
                f"<:done:1398729525277229066> Le préfixe de **{self.guild.name}** est maintenant `{new_prefix}`"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class AddTagModal(discord.ui.Modal, title="Ajouter un tag"):
    """Modal pour ajouter un tag"""

    def __init__(self, bot, guild, author: discord.User):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.author = author

    tag_name = discord.ui.TextInput(
        label="Nom du tag",
        placeholder="Ex: rules, help, info",
        max_length=50,
        required=True
    )

    tag_content = discord.ui.TextInput(
        label="Contenu du tag",
        style=discord.TextStyle.paragraph,
        placeholder="Le contenu qui sera affiché quand le tag est utilisé",
        max_length=2000,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Récupère les tags actuels
            guild_data = await self.bot.db.get_guild(self.guild.id)
            tags = guild_data['data'].get('tags', {})

            # Ajoute le nouveau tag
            tags[self.tag_name.value.lower()] = self.tag_content.value

            # Met à jour
            await self.bot.db.update_guild_data(self.guild.id, 'tags', tags)

            embed = ModdyResponse.success(
                "Tag ajouté",
                f"<:done:1398729525277229066> Le tag `{self.tag_name.value}` a été créé"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class RemoveTagView(discord.ui.View):
    """Vue pour sélectionner un tag à supprimer"""

    def __init__(self, bot, guild, tags: Dict[str, str], author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild = guild
        self.tags = tags
        self.author = author

        options = []
        for tag_name, tag_content in list(tags.items())[:25]:
            content_preview = tag_content[:50] + "..." if len(tag_content) > 50 else tag_content
            options.append(
                discord.SelectOption(
                    label=tag_name,
                    value=tag_name,
                    description=content_preview,
                    emoji="<:label:1398729473649676440>"
                )
            )

        self.select = discord.ui.Select(
            placeholder="Choisissez un tag à supprimer",
            options=options
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        """Quand un tag est sélectionné"""
        selected = self.select.values[0]

        try:
            # Récupère les tags actuels
            guild_data = await self.bot.db.get_guild(self.guild.id)
            tags = guild_data['data'].get('tags', {})

            # Supprime le tag
            if selected in tags:
                del tags[selected]

            # Met à jour
            await self.bot.db.update_guild_data(self.guild.id, 'tags', tags)

            embed = ModdyResponse.success(
                "Tag supprimé",
                f"<:done:1398729525277229066> Le tag `{selected}` a été supprimé"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class FeatureToggleView(discord.ui.View):
    """Vue pour activer/désactiver des features"""

    def __init__(self, bot, guild, current_features: Dict[str, bool], author: discord.User):
        super().__init__(timeout=60)
        self.bot = bot
        self.guild = guild
        self.current_features = current_features
        self.author = author

        # Features disponibles
        all_features = {
            'welcome_message': 'Messages de bienvenue',
            'auto_roles': 'Rôles automatiques',
            'logging': 'Logs des actions',
            'anti_spam': 'Protection anti-spam',
            'auto_mod': 'Modération automatique',
            'level_system': 'Système de niveaux',
            'custom_commands': 'Commandes personnalisées',
            'starboard': 'Starboard'
        }

        # Crée les boutons
        for feature_key, feature_name in all_features.items():
            is_enabled = current_features.get(feature_key, False)

            btn = discord.ui.Button(
                label=feature_name,
                emoji="<:done:1398729525277229066>" if is_enabled else "<:undone:1398729502028333218>",
                style=discord.ButtonStyle.success if is_enabled else discord.ButtonStyle.danger,
                custom_id=feature_key
            )
            btn.callback = self.toggle_feature
            self.add_item(btn)

    async def toggle_feature(self, interaction: discord.Interaction):
        """Toggle une feature"""
        feature_key = interaction.data['custom_id']

        try:
            # Récupère la config actuelle
            guild_data = await self.bot.db.get_guild(self.guild.id)
            config = guild_data['data'].get('config', {})
            features = config.get('features', {})

            # Toggle la feature
            current_state = features.get(feature_key, False)
            features[feature_key] = not current_state

            # Met à jour la config
            config['features'] = features
            await self.bot.db.update_guild_data(self.guild.id, 'config', config)

            # Feedback
            await interaction.response.send_message(
                f"<:done:1398729525277229066> Feature **{interaction.data['component']['label']}** {'activée' if not current_state else 'désactivée'}!",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class ResetGuildConfirmModal(discord.ui.Modal, title="Réinitialiser le serveur"):
    """Modal de confirmation pour reset serveur"""

    def __init__(self, bot, guild, author: discord.User):
        super().__init__()
        self.bot = bot
        self.guild = guild
        self.author = author

    confirm_text = discord.ui.TextInput(
        label="Tapez le nom du serveur pour confirmer",
        placeholder="Nom exact du serveur",
        max_length=100,
        required=True
    )

    reason = discord.ui.TextInput(
        label="Raison de la réinitialisation",
        placeholder="Pourquoi réinitialiser ce serveur ?",
        max_length=200,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm_text.value != self.guild.name:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Confirmation incorrecte. Vous devez taper exactement : `{self.guild.name}`",
                ephemeral=True
            )
            return

        try:
            # Récupère les données actuelles
            guild_data = await self.bot.db.get_guild(self.guild.id)

            # Supprime tous les attributs
            for attr in list(guild_data['attributes'].keys()):
                await self.bot.db.set_attribute(
                    'guild', self.guild.id, attr, None,
                    self.author.id, f"Reset complet : {self.reason.value}"
                )

            # Réinitialise la data
            async with self.bot.db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE guilds 
                    SET data = '{}'::jsonb, updated_at = NOW()
                    WHERE guild_id = $1
                """, self.guild.id)

            # Invalide le cache de préfixe
            self.bot.prefix_cache.pop(self.guild.id, None)

            embed = ModdyResponse.success(
                "Serveur réinitialisé",
                f"<:done:1398729525277229066> Toutes les données de **{self.guild.name}** ont été supprimées."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"<:undone:1398729502028333218> Erreur : {str(e)}",
                ephemeral=True
            )


class BackButtonView(discord.ui.View):
    """Vue simple avec juste un bouton retour"""

    def __init__(self, parent_view, message):
        super().__init__(timeout=600)
        self.parent_view = parent_view
        self.message = message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Vérifie que c'est un développeur"""
        if not self.parent_view.bot.is_developer(interaction.user.id):
            await interaction.response.send_message(
                "<:undone:1398729502028333218> Cette action est réservée aux développeurs.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Retour", emoji="<:back:1401600847733067806>", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Retour au menu principal"""
        self.parent_view.guild_data = await self.parent_view.bot.db.get_guild(self.parent_view.guild.id)

        class FakeContext:
            def __init__(self, author):
                self.author = author

        fake_ctx = FakeContext(self.parent_view.author)

        embed = ServerManagement._create_guild_embed(
            self.parent_view.bot,
            self.parent_view.guild,
            self.parent_view.guild_data,
            fake_ctx
        )

        await interaction.response.edit_message(embed=embed, view=self.parent_view)


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


async def setup(bot):
    await bot.add_cog(ServerManagement(bot))