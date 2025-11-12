"""
Système de vérification de blacklist - INTERCEPTION TOTALE
Bloque TOUTES les interactions des utilisateurs blacklistés AVANT qu'elles n'arrivent à destination
- Commandes par préfixe: bloquées dans process_commands
- Slash commands: bloquées dans on_interaction (handler principal)
- Boutons/Modals/Selects: bloquées dans on_interaction
- interaction_check: sécurité supplémentaire (backup)
"""

import discord
from discord.ext import commands

BLACKLIST_MESSAGE = (
    "<:undone:1398729502028333218> You cannot interact with Moddy because your account "
    "has been blacklisted by our team."
)
BLACKLIST_LINK = "https://moddy.app/unbl_request"
BLACKLIST_RESPONSE = f"{BLACKLIST_MESSAGE}\n{BLACKLIST_LINK}"


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

        # SÉCURITÉ SUPPLÉMENTAIRE: Ajoute un interaction_check global au CommandTree
        # Note: Le blocage principal se fait dans on_interaction (ci-dessous)
        # Ceci sert de backup au cas où on_interaction ne serait pas appelé
        @bot.tree.interaction_check
        async def blacklist_interaction_check(interaction: discord.Interaction) -> bool:
            """Vérifie la blacklist AVANT l'exécution de toute app command (BACKUP)"""
            # Ignore les bots
            if interaction.user.bot:
                return True

            # Vérifie si l'utilisateur est blacklisté
            if await self.is_blacklisted(interaction.user.id):
                # Envoie le message de blacklist
                view = BlacklistButton()

                try:
                    await interaction.response.send_message(
                        content=BLACKLIST_RESPONSE,
                        view=view,
                        ephemeral=True
                    )
                except:
                    pass

                # Log l'interaction bloquée
                if log_cog := self.bot.get_cog("LoggingSystem"):
                    try:
                        await log_cog.log_critical(
                            title="🚫 Slash Command Blacklistée Bloquée",
                            description=(
                                f"**Utilisateur:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                                f"**Type:** {interaction.type.name}\n"
                                f"**Commande:** {interaction.command.name if interaction.command else 'N/A'}\n"
                                f"**Serveur:** {interaction.guild.name if interaction.guild else 'DM'}\n"
                                f"**Action:** Slash command bloquée AVANT exécution (interaction_check)"
                            ),
                            ping_dev=False
                        )
                    except:
                        pass

                # Retourne False pour bloquer l'exécution de la commande
                return False

            # Autorise l'interaction
            return True

        # Override la méthode process_commands pour bloquer AVANT le traitement
        original_process_commands = bot.process_commands

        async def blacklist_aware_process_commands(message):
            """Intercepte les commandes AVANT qu'elles ne soient traitées"""
            if message.author.bot:
                return await original_process_commands(message)

            # Vérifie si le message commence par un préfixe (commande ou mention)
            # On récupère les préfixes possibles
            prefixes = await self.bot.get_prefix(message)
            if isinstance(prefixes, str):
                prefixes = [prefixes]

            # Vérifie si le message commence par un des préfixes
            is_command = any(message.content.startswith(prefix) for prefix in prefixes)

            # Si ce n'est pas une commande (pas de préfixe), laisse passer sans vérifier la blacklist
            if not is_command:
                return await original_process_commands(message)

            # C'est une commande (commence par un préfixe), vérifie maintenant si l'utilisateur est blacklisté
            if await self.is_blacklisted(message.author.id):
                # Envoie le message de blacklist
                view = BlacklistButton()

                try:
                    await message.reply(
                        content=BLACKLIST_RESPONSE,
                        view=view,
                        mention_author=False
                    )
                except:
                    try:
                        await message.channel.send(
                            content=BLACKLIST_RESPONSE,
                            view=view
                        )
                    except:
                        pass

                # NE PAS traiter la commande - return sans appeler original_process_commands
                return

            # Si pas blacklisté, traite normalement
            return await original_process_commands(message)

        bot.process_commands = blacklist_aware_process_commands

        # Override on_interaction pour bloquer les interactions AVANT dispatch
        original_on_interaction = bot.on_interaction if hasattr(bot, 'on_interaction') else None

        async def blacklist_aware_on_interaction(interaction: discord.Interaction):
            """Intercepte TOUTES les interactions AVANT dispatch - AUCUNE EXCEPTION"""
            # Ignore les bots
            if interaction.user.bot:
                if original_on_interaction:
                    return await original_on_interaction(interaction)
                return

            # CRITIQUE : Vérifie la blacklist pour TOUTES les interactions
            # On ne fait AUCUNE exception, même pas pour les app commands
            # Toutes les interactions des utilisateurs blacklistés sont bloquées ICI
            if await self.is_blacklisted(interaction.user.id):
                # BLOQUE l'interaction en y répondant immédiatement
                try:
                    # Envoie directement le message de blacklist
                    view = BlacklistButton()

                    # Vérifie si l'interaction n'a pas déjà été répondue
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                            content=BLACKLIST_RESPONSE,
                            view=view,
                            ephemeral=True
                        )
                    else:
                        # Si déjà répondue, utilise followup
                        await interaction.followup.send(
                            content=BLACKLIST_RESPONSE,
                            view=view,
                            ephemeral=True
                        )
                except Exception as e:
                    # Fallback ultime si tout échoue
                    try:
                        if not interaction.response.is_done():
                            await interaction.response.send_message(
                                BLACKLIST_RESPONSE,
                                ephemeral=True
                            )
                    except:
                        pass

                # Log l'interaction bloquée
                if log_cog := self.bot.get_cog("LoggingSystem"):
                    try:
                        interaction_type = interaction.type.name
                        # Récupère le custom_id ou le nom de commande selon le type
                        if interaction.type == discord.InteractionType.application_command:
                            identifier = f"Commande: {interaction.command.name if interaction.command else 'N/A'}"
                        else:
                            identifier = f"Custom ID: {interaction.data.get('custom_id', 'N/A') if hasattr(interaction, 'data') else 'N/A'}"

                        await log_cog.log_critical(
                            title="🚫 Interaction Blacklistée Bloquée (on_interaction)",
                            description=(
                                f"**Utilisateur:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                                f"**Type:** {interaction_type}\n"
                                f"**{identifier}**\n"
                                f"**Serveur:** {interaction.guild.name if interaction.guild else 'DM'}\n"
                                f"**Action:** Interaction bloquée AVANT dispatch (on_interaction handler)"
                            ),
                            ping_dev=False
                        )
                    except:
                        pass

                # NE PAS appeler original_on_interaction - on bloque complètement
                return

            # Si pas blacklisté, laisse l'interaction continuer normalement
            if original_on_interaction:
                return await original_on_interaction(interaction)

        # Replace la méthode au niveau du bot
        bot.on_interaction = blacklist_aware_on_interaction

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
        view = BlacklistButton()

        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    content=BLACKLIST_RESPONSE,
                    view=view,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    content=BLACKLIST_RESPONSE,
                    view=view,
                    ephemeral=True
                )
        except:
            # Si tout échoue, essaye en message normal
            try:
                await interaction.channel.send(
                    content=BLACKLIST_RESPONSE,
                    view=view
                )
            except:
                pass

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

        view = BlacklistButton()

        await ctx.send(
            f"**[TEST MODE]** Voici ce que verrait un utilisateur blacklisté:\n{BLACKLIST_RESPONSE}",
            view=view
        )


async def setup(bot):
    await bot.add_cog(BlacklistCheck(bot))
