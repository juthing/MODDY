"""
Moddy - Classe principale du bot
Gère toute la logique centrale et les événements
"""

import discord
from discord.ext import commands, tasks
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Set
import os
import sys
from pathlib import Path
import traceback

from config import (
    DEBUG,
    DEFAULT_PREFIX,
    DATABASE_URL,
    DEVELOPER_IDS
)

logger = logging.getLogger('moddy')


class ModdyBot(commands.Bot):
    """Classe principale de Moddy"""

    def __init__(self):
        # Intents nécessaires
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        # Configuration du bot
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,  # On fait notre propre commande help
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="les serveurs | /help"
            ),
            status=discord.Status.online,
            case_insensitive=True
        )

        # Variables internes
        self.launch_time = datetime.now(timezone.utc)
        self.db_pool = None
        self._dev_team_ids: Set[int] = set()
        self.maintenance_mode = False

        # Cache pour les préfixes des serveurs
        self.prefix_cache = {}

        # Configure le gestionnaire d'erreurs global
        self.setup_error_handler()

    def setup_error_handler(self):
        """Configure le gestionnaire d'erreurs non capturées"""

        def handle_exception(loop, context):
            # Récupère l'exception
            exception = context.get('exception')
            if exception:
                logger.error(f"Erreur non capturée: {exception}", exc_info=exception)

                # Essaye d'envoyer à Discord si le bot est connecté
                if self.is_ready():
                    asyncio.create_task(self.log_fatal_error(exception, context))

        # Configure le handler
        asyncio.get_event_loop().set_exception_handler(handle_exception)

    async def log_fatal_error(self, exception: Exception, context: dict):
        """Log une erreur fatale dans Discord"""
        try:
            # Utilise le cog ErrorTracker s'il est chargé
            error_cog = self.get_cog("ErrorTracker")
            if error_cog:
                error_code = error_cog.generate_error_code(exception)
                error_details = {
                    "type": type(exception).__name__,
                    "message": str(exception),
                    "file": "Erreur système",
                    "line": "N/A",
                    "context": str(context),
                    "traceback": traceback.format_exc()
                }
                error_cog.store_error(error_code, error_details)
                await error_cog.send_error_log(error_code, error_details, is_fatal=True)
        except Exception as e:
            logger.error(f"Impossible de logger l'erreur fatale: {e}")

    async def setup_hook(self):
        """Appelé une fois au démarrage du bot"""
        logger.info("🔧 Configuration initiale...")

        # Configure le gestionnaire d'erreurs pour les commandes slash
        self.tree.on_error = self.on_app_command_error

        # Récupère l'équipe de développement
        await self.fetch_dev_team()

        # Charge les extensions
        await self.load_extensions()

        # Connecte la base de données
        if DATABASE_URL:
            await self.setup_database()

        # Démarre les tâches de fond
        self.status_update.start()

        # Synchronise les commandes slash
        if DEBUG:
            # En debug, sync seulement sur le serveur de test
            guild = discord.Object(id=1234567890)  # Remplace par ton serveur de test
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("✅ Commandes synchronisées (mode debug)")
        else:
            # En production, sync global
            await self.tree.sync()
            logger.info("✅ Commandes synchronisées globalement")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Gestion des erreurs des commandes slash"""
        # Utilise le cog ErrorTracker s'il est chargé
        error_cog = self.get_cog("ErrorTracker")
        if error_cog:
            # Crée un faux contexte pour réutiliser le système existant
            class FakeContext:
                def __init__(self, interaction):
                    self.interaction = interaction
                    self.command = interaction.command
                    self.author = interaction.user
                    self.guild = interaction.guild
                    self.channel = interaction.channel
                    # Crée un objet message factice
                    self.message = type('obj', (object,), {
                        'content': f"/{interaction.command.name} " + " ".join(
                            [f"{k}:{v}" for k, v in interaction.namespace.__dict__.items()])
                    })()

                async def send(self, *args, **kwargs):
                    if interaction.response.is_done():
                        return await interaction.followup.send(*args, **kwargs)
                    else:
                        return await interaction.response.send_message(*args, **kwargs)

            fake_ctx = FakeContext(interaction)

            # Utilise le gestionnaire existant
            await error_cog.on_command_error(fake_ctx, error)
        else:
            # Fallback si le système n'est pas chargé
            logger.error(f"Erreur slash command: {error}", exc_info=error)

    async def fetch_dev_team(self):
        """Récupère l'équipe de développement depuis Discord"""
        try:
            app_info = await self.application_info()

            if app_info.team:
                self._dev_team_ids = {member.id for member in app_info.team.members}
                logger.info(f"✅ Équipe de dev : {len(self._dev_team_ids)} membres")
            else:
                self._dev_team_ids = {app_info.owner.id}
                logger.info(f"✅ Propriétaire : {app_info.owner}")

        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération de l'équipe : {e}")
            # Fallback sur les IDs dans config si disponibles
            if DEVELOPER_IDS:
                self._dev_team_ids = set(DEVELOPER_IDS)

    def is_developer(self, user_id: int) -> bool:
        """Vérifie si un utilisateur est développeur"""
        return user_id in self._dev_team_ids

    async def get_prefix(self, message: discord.Message):
        """Récupère le préfixe pour un message"""
        # En MP, utilise le préfixe par défaut
        if not message.guild:
            return [DEFAULT_PREFIX, f'<@{self.user.id}> ', f'<@!{self.user.id}> ']

        # Vérifie le cache
        guild_id = message.guild.id
        if guild_id in self.prefix_cache:
            prefix = self.prefix_cache[guild_id]
        else:
            # Récupère depuis la BDD ou utilise le défaut
            prefix = await self.get_guild_prefix(guild_id) or DEFAULT_PREFIX
            self.prefix_cache[guild_id] = prefix

        # Retourne le préfixe et les mentions
        return [prefix, f'<@{self.user.id}> ', f'<@!{self.user.id}> ']

    async def get_guild_prefix(self, guild_id: int) -> Optional[str]:
        """Récupère le préfixe d'un serveur depuis la BDD"""
        if not self.db_pool:
            return None

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT prefix FROM guilds WHERE guild_id = $1",
                    guild_id
                )
                return row['prefix'] if row else None
        except Exception as e:
            logger.error(f"Erreur BDD (prefix) : {e}")
            return None

    async def setup_database(self):
        """Initialise la connexion à la base de données"""
        try:
            import asyncpg
            self.db_pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ Base de données connectée")
        except ImportError:
            logger.warning("⚠️ asyncpg non installé - Mode sans BDD")
        except Exception as e:
            logger.error(f"❌ Erreur connexion BDD : {e}")

    async def load_extensions(self):
        """Charge tous les cogs et commandes staff"""
        # Charge d'abord le système d'erreurs
        try:
            await self.load_extension("cogs.error_handler")
            logger.info("✅ Système d'erreurs chargé")
        except Exception as e:
            logger.error(f"❌ CRITIQUE: Impossible de charger le système d'erreurs : {e}")

        # Charge le système de logging dev
        try:
            await self.load_extension("cogs.dev_logger")
            logger.info("✅ Système de logging dev chargé")
        except Exception as e:
            logger.error(f"❌ Erreur chargement logging dev : {e}")

        # Charge les cogs utilisateurs
        cogs_dir = Path("cogs")
        if cogs_dir.exists():
            for file in cogs_dir.glob("*.py"):
                if file.name.startswith("_") or file.name in ["error_handler.py", "dev_logger.py"]:
                    continue

                try:
                    await self.load_extension(f"cogs.{file.stem}")
                    logger.info(f"✅ Cog chargé : {file.stem}")
                except Exception as e:
                    logger.error(f"❌ Erreur cog {file.stem} : {e}")
                    # Log dans Discord si possible
                    if error_cog := self.get_cog("ErrorTracker"):
                        error_code = error_cog.generate_error_code(e)
                        error_details = {
                            "type": type(e).__name__,
                            "message": str(e),
                            "file": f"cogs/{file.name}",
                            "line": "N/A",
                            "traceback": traceback.format_exc()
                        }
                        error_cog.store_error(error_code, error_details)
                        await error_cog.send_error_log(error_code, error_details, is_fatal=False)

        # Charge les commandes staff
        staff_dir = Path("staff")
        if staff_dir.exists():
            for file in staff_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                try:
                    await self.load_extension(f"staff.{file.stem}")
                    logger.info(f"✅ Staff chargé : {file.stem}")
                except Exception as e:
                    logger.error(f"❌ Erreur staff {file.stem} : {e}")
                    # Log dans Discord si possible
                    if error_cog := self.get_cog("ErrorTracker"):
                        error_code = error_cog.generate_error_code(e)
                        error_details = {
                            "type": type(e).__name__,
                            "message": str(e),
                            "file": f"staff/{file.name}",
                            "line": "N/A",
                            "traceback": traceback.format_exc()
                        }
                        error_cog.store_error(error_code, error_details)
                        await error_cog.send_error_log(error_code, error_details, is_fatal=False)

    async def on_ready(self):
        """Appelé quand le bot est prêt"""
        logger.info(f"✅ {self.user} est connecté !")
        logger.info(f"📊 {len(self.guilds)} serveurs | {len(self.users)} utilisateurs")
        logger.info(f"🏓 Latence : {round(self.latency * 1000)}ms")

    async def on_guild_join(self, guild: discord.Guild):
        """Quand le bot rejoint un serveur"""
        logger.info(f"➕ Nouveau serveur : {guild.name} ({guild.id})")

        # Enregistre dans la BDD
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    await conn.execute("""
                                       INSERT INTO guilds (guild_id, joined_at)
                                       VALUES ($1, $2) ON CONFLICT (guild_id) DO NOTHING
                                       """, guild.id, datetime.now(timezone.utc))
            except Exception as e:
                logger.error(f"Erreur BDD (guild_join) : {e}")

    async def on_guild_remove(self, guild: discord.Guild):
        """Quand le bot quitte un serveur"""
        logger.info(f"➖ Serveur quitté : {guild.name} ({guild.id})")

        # Nettoie le cache
        self.prefix_cache.pop(guild.id, None)

    async def on_message(self, message: discord.Message):
        """Traite chaque message"""
        # Ignore ses propres messages
        if message.author == self.user:
            return

        # Mode maintenance - seuls les devs peuvent utiliser le bot
        if self.maintenance_mode and not self.is_developer(message.author.id):
            return

        # Traite les commandes
        await self.process_commands(message)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Gestion globale des erreurs"""
        # Le cog ErrorTracker s'occupe de tout maintenant
        # Cette méthode est gardée pour compatibilité mais délègue au cog
        pass

    @tasks.loop(minutes=10)
    async def status_update(self):
        """Met à jour le statut du bot"""
        # Vérifications de sécurité
        if not self.is_ready() or not self.ws:
            return

        statuses = [
            ("watching", f"{len(self.guilds)} serveurs"),
            ("playing", "/help"),
            ("watching", "les modérateurs"),
            ("playing", f"avec {len(self.users)} utilisateurs")
        ]

        # Choix aléatoire
        import random
        activity_type, name = random.choice(statuses)

        activity = discord.Activity(
            type=getattr(discord.ActivityType, activity_type),
            name=name
        )

        try:
            await self.change_presence(activity=activity)
        except (AttributeError, ConnectionError):
            # Ignorer si on est en train de fermer
            pass
        except Exception as e:
            logger.error(f"Erreur changement de statut : {e}")

    @status_update.before_loop
    async def before_status_update(self):
        """Attendre que le bot soit prêt avant de démarrer la tâche"""
        await self.wait_until_ready()

    async def close(self):
        """Fermeture propre du bot"""
        logger.info("🔄 Fermeture en cours...")

        # Arrête les tâches AVANT de fermer
        if self.status_update.is_running():
            self.status_update.cancel()

        # Attendre un peu pour que les tâches se terminent
        await asyncio.sleep(0.1)

        # Ferme la connexion BDD
        if self.db_pool:
            await self.db_pool.close()

        # Ferme proprement le client HTTP
        if hasattr(self, 'http') and self.http and hasattr(self.http, '_HTTPClient__session'):
            await self.http._HTTPClient__session.close()

        # Ferme le bot
        await super().close()