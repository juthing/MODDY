"""
Système de vérification de blacklist
Intercepte toutes les interactions avant traitement
"""

import discord
from discord.ext import commands
from typing import Union

from config import COLORS, EMOJIS


class BlacklistButton(discord.ui.View):
    """Vue avec le bouton de demande d'unblacklist"""

    def __init__(self):
        super().__init__()
        # Ajoute le bouton avec un lien
        self.add_item(discord.ui.Button(
            label="Unblacklist request",
            url="https://moddy.app/unbl_request",
            style=discord.ButtonStyle.link
        ))


class BlacklistCheck(commands.Cog):
    """Vérifie le statut blacklist avant toute interaction"""

    def __init__(self, bot):
        self.bot = bot
        self.blacklist_cache = {}  # Cache pour éviter trop de requêtes DB

        # Enregistre le check global pour bloquer AVANT l'exécution des commandes
        @bot.check
        async def global_blacklist_check(ctx):
            """Check global qui s'exécute avant TOUTE commande"""
            # Pour les commandes classiques (prefix)
            if hasattr(ctx, 'author'):
                user_id = ctx.author.id
                is_bot = ctx.author.bot
                is_interaction = False
            # Pour les interactions (slash commands, etc.)
            elif hasattr(ctx, 'user'):
                user_id = ctx.user.id
                is_bot = ctx.user.bot
                is_interaction = True
            else:
                return True  # Pas d'utilisateur identifiable, on laisse passer

            # Ignore les bots
            if is_bot:
                return True

            # Vérifie le blacklist
            if await self.is_blacklisted(user_id):
                # Envoie le message de blacklist avant de bloquer
                try:
                    if isinstance(ctx, discord.Interaction):
                        # Pour les interactions (slash commands, boutons, etc.)
                        await self.send_blacklist_message(ctx)
                    else:
                        # Pour les commandes préfixe
                        embed = discord.Embed(
                            description=(
                                f"{EMOJIS['undone']} You cannot interact with Moddy because your account has been blacklisted by our team.\n\n"
                                f"*Vous ne pouvez pas interagir avec Moddy car votre compte a été blacklisté par notre équipe.*"
                            ),
                            color=COLORS["error"]
                        )
                        embed.set_footer(text=f"User ID: {user_id}")
                        view = BlacklistButton()

                        try:
                            await ctx.reply(embed=embed, view=view, mention_author=False)
                        except:
                            await ctx.send(embed=embed, view=view)
                except Exception as e:
                    # Si l'envoi échoue, on bloque quand même
                    pass

                # Bloque la commande en levant l'exception
                raise commands.CheckFailure(f"User {user_id} is blacklisted")

            return True

    async def is_blacklisted(self, user_id: int) -> bool:
        """Vérifie si un utilisateur est blacklisté (avec cache)"""
        # Vérifie le cache d'abord
        if user_id in self.blacklist_cache:
            return self.blacklist_cache[user_id]

        # Sinon vérifie la DB
        if self.bot.db:
            try:
                is_bl = await self.bot.db.has_attribute('user', user_id, 'BLACKLISTED')
                self.blacklist_cache[user_id] = is_bl
                return is_bl
            except:
                return False
        return False

    async def send_blacklist_message(self, interaction: discord.Interaction):
        """Envoie le message de blacklist"""
        embed = discord.Embed(
            description=(
                f"{EMOJIS['undone']} You cannot interact with Moddy because your account has been blacklisted by our team.\n\n"
                f"*Vous ne pouvez pas interagir avec Moddy car votre compte a été blacklisté par notre équipe.*"
            ),
            color=COLORS["error"]
        )

        embed.set_footer(text=f"User ID: {interaction.user.id}")

        view = BlacklistButton()

        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        except:
            # Si tout échoue, essaye en message normal
            try:
                await interaction.channel.send(embed=embed, view=view)
            except:
                pass

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Bloque TOUTES les interactions des utilisateurs blacklistés AVANT traitement"""
        # Ignore les interactions du bot lui-même
        if interaction.user.bot:
            return

        # Vérifie tous les types d'interactions (commandes, boutons, selects, modals, etc.)
        if interaction.type not in [
            discord.InteractionType.application_command,
            discord.InteractionType.component,
            discord.InteractionType.modal_submit
        ]:
            return

        # CRITIQUE: Vérifie le blacklist AVANT que l'interaction ne soit traitée
        if await self.is_blacklisted(interaction.user.id):
            # Bloque l'interaction en répondant immédiatement
            # Cela empêche les autres handlers de traiter cette interaction
            try:
                await self.send_blacklist_message(interaction)
            except Exception as e:
                # Si l'envoi échoue, essaye quand même de bloquer
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            "🚫 You cannot interact with Moddy.",
                            ephemeral=True
                        )
                except:
                    pass

            # Log l'interaction bloquée
            if log_cog := self.bot.get_cog("LoggingSystem"):
                await log_cog.log_critical(
                    title="🚫 Interaction Blacklistée Bloquée",
                    description=(
                        f"**Utilisateur:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                        f"**Type:** {interaction.type.name}\n"
                        f"**Commande:** {getattr(interaction.command, 'name', 'N/A')}\n"
                        f"**Custom ID:** {interaction.data.get('custom_id', 'N/A')}\n"
                        f"**Serveur:** {interaction.guild.name if interaction.guild else 'DM'}\n"
                        f"**Action:** Interaction bloquée AVANT traitement"
                    ),
                    ping_dev=False
                )

            # IMPORTANT: Ne pas propager l'interaction aux autres handlers
            # En répondant à l'interaction, on empêche les autres handlers de la traiter
            return

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Log les commandes préfixe blacklistées (le blocage est fait par le check global)"""
        # Ignore les bots
        if message.author.bot:
            return

        # Vérifie si c'est potentiellement une commande
        if message.content:
            # Récupère les préfixes possibles
            prefixes = await self.bot.get_prefix(message)

            # Vérifie si le message commence par un préfixe
            for prefix in prefixes:
                if message.content.startswith(prefix):
                    # C'est une commande, vérifie le blacklist pour log
                    if await self.is_blacklisted(message.author.id):
                        if log_cog := self.bot.get_cog("LoggingSystem"):
                            await log_cog.log_critical(
                                title="🚫 Commande Préfixe Blacklistée Bloquée",
                                description=(
                                    f"**Utilisateur:** {message.author.mention} (`{message.author.id}`)\n"
                                    f"**Commande:** `{message.content[:100]}`\n"
                                    f"**Serveur:** {message.guild.name if message.guild else 'DM'}\n"
                                    f"**Action:** Commande bloquée par le check global avant exécution"
                                ),
                                ping_dev=False
                            )
                        # Le check global bloquera la commande, pas besoin de répondre ici
                        return

    @commands.command(name="clearcache", aliases=["cc"])
    async def clear_blacklist_cache(self, ctx):
        """Vide le cache de blacklist (commande dev)"""
        if not self.bot.is_developer(ctx.author.id):
            return

        self.blacklist_cache.clear()
        await ctx.send("<:done:1398729525277229066> Cache de blacklist vidé")

    @commands.command(name="testbl")
    async def test_blacklist(self, ctx):
        """Teste le message de blacklist (commande dev)"""
        if not self.bot.is_developer(ctx.author.id):
            return

        # Crée une fausse interaction
        class FakeInteraction:
            def __init__(self, user, channel):
                self.user = user
                self.channel = channel
                self.response = type('obj', (object,), {'is_done': lambda: False})()

            async def response(self):
                return self.response

        fake_interaction = FakeInteraction(ctx.author, ctx.channel)

        # Simule l'envoi du message
        embed = discord.Embed(
            description=(
                f"{EMOJIS['undone']} You cannot interact with Moddy because your account has been blacklisted by our team.\n\n"
                f"*Vous ne pouvez pas interagir avec Moddy car votre compte a été blacklisté par notre équipe.*"
            ),
            color=COLORS["error"]
        )

        embed.set_footer(text=f"User ID: {ctx.author.id}")

        view = BlacklistButton()

        await ctx.send("**[TEST MODE]** Voici ce que verrait un utilisateur blacklisté:", embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(BlacklistCheck(bot))