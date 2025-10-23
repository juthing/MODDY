"""
Moddy - Main bot class
Handles all core logic and events
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

from services.health_server import setup_health_server
from config import (
    DEBUG,
    DEFAULT_PREFIX,
    DATABASE_URL,
    DEVELOPER_IDS,
    COLORS
)
from database import setup_database, db

logger = logging.getLogger('moddy')


class ModdyBot(commands.Bot):
    """Main Moddy class"""

    def __init__(self):
        # Required intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        # Bot configuration
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            help_command=None,  # We make our own help command
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="servers | /help"
            ),
            status=discord.Status.online,
            case_insensitive=True
        )

        # Internal variables
        self.launch_time = datetime.now(timezone.utc)
        self.db = None  # ModdyDatabase instance
        self._dev_team_ids: Set[int] = set()
        self.maintenance_mode = False
        self.health_server = None

        # Cache for server prefixes
        self.prefix_cache = {}

        # Configure global error handler
        self.setup_error_handler()

    def setup_error_handler(self):
        """Configure uncaught error handler"""

        def handle_exception(loop, context):
            # Get the exception
            exception = context.get('exception')
            if exception:
                logger.error(f"Uncaught error: {exception}", exc_info=exception)

                # Try to send to Discord if the bot is connected
                if self.is_ready():
                    asyncio.create_task(self.log_fatal_error(exception, context))

        # Configure the handler
        asyncio.get_event_loop().set_exception_handler(handle_exception)

    async def log_fatal_error(self, exception: Exception, context: dict):
        """Log a fatal error in Discord"""
        try:
            # Use the ErrorTracker cog if it's loaded
            error_cog = self.get_cog("ErrorTracker")
            if error_cog:
                error_code = error_cog.generate_error_code(exception)
                error_details = {
                    "type": type(exception).__name__,
                    "message": str(exception),
                    "file": "System error",
                    "line": "N/A",
                    "context": str(context),
                    "traceback": traceback.format_exc()
                }
                error_cog.store_error(error_code, error_details)
                await error_cog.send_error_log(error_code, error_details, is_fatal=True)
        except Exception as e:
            logger.error(f"Could not log fatal error: {e}")

    async def setup_hook(self):
        """Called once on bot startup"""
        logger.info("🔧 Initial setup...")

        # Configure error handler for slash commands
        self.tree.on_error = self.on_app_command_error

        # Fetch development team
        await self.fetch_dev_team()

        # Connect the database
        if DATABASE_URL:
            await self.setup_database()

        # Load extensions
        await self.load_extensions()

        # Start the health check server
        await self.start_health_server()

        # Start background tasks
        self.status_update.start()

        # Sync slash commands
        if DEBUG:
            # In debug, sync only on the test server
            guild = discord.Object(id=1234567890)  # Replace with your test server id
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("✅ Commands synced (debug mode)")
        else:
            # In production, sync globally
            await self.tree.sync()
            logger.info("✅ Commands synced globally")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Slash command error handling"""
        # Use the ErrorTracker cog if it's loaded
        error_cog = self.get_cog("ErrorTracker")
        if error_cog:
            # Create a fake context to reuse the existing system
            class FakeContext:
                def __init__(self, interaction):
                    self.interaction = interaction
                    self.command = interaction.command
                    self.author = interaction.user
                    self.guild = interaction.guild
                    self.channel = interaction.channel
                    # Create a fake message object
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

            # Use the existing handler
            await error_cog.on_command_error(fake_ctx, error)
        else:
            # Fallback if the system is not loaded
            logger.error(f"Slash command error: {error}", exc_info=error)

    async def start_health_server(self):
        """Démarre le serveur de health check"""
        try:
            # Démarrage du serveur
            self.health_server = await setup_health_server(self)
            logger.info("✅ Health server started")

        except ImportError:
            logger.warning("⚠️ Health server module not found, skipping")
            self.health_server = None
        except Exception as e:
            logger.error(f"❌ Failed to start health server: {e}")
            self.health_server = None

    async def stop_health_server(self):
        """Arrête le serveur de health check"""
        if hasattr(self, 'health_server') and self.health_server:
            try:
                await self.health_server.stop()
                logger.info("✅ Health server stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping health server: {e}")

    async def fetch_dev_team(self):
        """Fetch development team from Discord"""
        try:
            app_info = await self.application_info()

            if app_info.team:
                # Filter to keep only real users (not bots)
                self._dev_team_ids = {
                    member.id for member in app_info.team.members
                    if not member.bot and member.id != app_info.id
                }
                logger.info(f"✅ Dev team: {len(self._dev_team_ids)} members")
                logger.info(f"   IDs: {list(self._dev_team_ids)}")
            else:
                self._dev_team_ids = {app_info.owner.id}
                logger.info(f"✅ Owner: {app_info.owner} ({app_info.owner.id})")

            # Also add IDs from config
            if DEVELOPER_IDS:
                self._dev_team_ids.update(DEVELOPER_IDS)
                logger.info(f"   + IDs from config: {DEVELOPER_IDS}")

        except Exception as e:
            logger.error(f"❌ Error fetching team: {e}")
            # Fallback to IDs in config if available
            if DEVELOPER_IDS:
                self._dev_team_ids = set(DEVELOPER_IDS)

    def is_developer(self, user_id: int) -> bool:
        """Checks if a user is a developer"""
        return user_id in self._dev_team_ids

    async def get_prefix(self, message: discord.Message):
        """Gets the prefix for a message"""
        # In DMs, use the default prefix
        if not message.guild:
            return [DEFAULT_PREFIX, f'<@{self.user.id}> ', f'<@!{self.user.id}> ']

        # Check the cache
        guild_id = message.guild.id
        if guild_id in self.prefix_cache:
            prefix = self.prefix_cache[guild_id]
        else:
            # Fetch from DB or use default
            prefix = await self.get_guild_prefix(guild_id) or DEFAULT_PREFIX
            self.prefix_cache[guild_id] = prefix

        # Return the prefix and mentions
        return [prefix, f'<@{self.user.id}> ', f'<@!{self.user.id}> ']

    async def get_guild_prefix(self, guild_id: int) -> Optional[str]:
        """Gets a server's prefix from the DB"""
        if not self.db:
            return None

        try:
            guild_data = await self.db.get_guild(guild_id)
            return guild_data['data'].get('config', {}).get('prefix')
        except Exception as e:
            logger.error(f"DB Error (prefix): {e}")
            return None

    async def setup_database(self):
        """Initialize the database connection"""
        try:
            self.db = await setup_database(DATABASE_URL)
            logger.info("✅ Database connected (ModdyDatabase)")

            # Property for compatibility with old code
            self.db_pool = self.db.pool

        except Exception as e:
            logger.error(f"❌ DB connection error: {e}")
            self.db = None
            self.db_pool = None

    async def load_extensions(self):
        """Load all cogs and staff commands"""
        # Load the error system first
        try:
            await self.load_extension("cogs.error_handler")
            logger.info("✅ Error system loaded")
        except Exception as e:
            logger.error(f"❌ CRITICAL: Could not load the error system: {e}")

        # Load the blacklist check system with PRIORITY
        try:
            await self.load_extension("cogs.blacklist_check")
            logger.info("✅ Blacklist check system loaded")
        except Exception as e:
            logger.error(f"❌ Error loading blacklist check: {e}")

        # Load the dev logging system
        try:
            await self.load_extension("cogs.dev_logger")
            logger.info("✅ Dev logging system loaded")
        except Exception as e:
            logger.error(f"❌ Error loading dev logger: {e}")

        # Load user cogs
        cogs_dir = Path("cogs")
        if cogs_dir.exists():
            for file in cogs_dir.glob("*.py"):
                if file.name.startswith("_") or file.name in ["error_handler.py", "blacklist_check.py", "dev_logger.py"]:
                    continue

                try:
                    await self.load_extension(f"cogs.{file.stem}")
                    logger.info(f"✅ Cog loaded: {file.stem}")
                except Exception as e:
                    logger.error(f"❌ Cog error {file.stem}: {e}")
                    # Log to Discord if possible
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

        # Load staff commands
        staff_dir = Path("staff")
        if staff_dir.exists():
            for file in staff_dir.glob("*.py"):
                if file.name.startswith("_"):
                    continue

                try:
                    await self.load_extension(f"staff.{file.stem}")
                    logger.info(f"✅ Staff command loaded: {file.stem}")
                except Exception as e:
                    logger.error(f"❌ Staff command error {file.stem}: {e}")
                    # Log to Discord if possible
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
        """Called when the bot is ready"""
        logger.info(f"✅ {self.user} is connected!")
        logger.info(f"📊 {len(self.guilds)} servers | {len(self.users)} users")
        logger.info(f"🏓 Latency: {round(self.latency * 1000)}ms")

        # Update DEVELOPER attributes now that self.user is available
        if self.db and self._dev_team_ids:
            logger.info(f"📝 Automatically updating DEVELOPER attributes...")
            for dev_id in self._dev_team_ids:
                try:
                    # Get or create user
                    await self.db.get_user(dev_id)

                    # Set the DEVELOPER attribute (True = present in the simplified system)
                    await self.db.set_attribute(
                        'user', dev_id, 'DEVELOPER', True,
                        self.user.id, "Auto-detection at startup"
                    )
                    logger.info(f"✅ DEVELOPER attribute set for {dev_id}")

                except Exception as e:
                    logger.error(f"❌ Error setting DEVELOPER attribute for {dev_id}: {e}")

        # DB stats if connected
        if self.db:
            try:
                stats = await self.db.get_stats()
                logger.info(f"📊 DB: {stats['users']} users, {stats['guilds']} guilds, {stats['errors']} errors")
            except:
                pass

    async def on_guild_join(self, guild: discord.Guild):
        """When the bot joins a server"""
        logger.info(f"➕ New server: {guild.name} ({guild.id})")

        # Check if the server owner is blacklisted
        if self.db:
            try:
                if await self.db.has_attribute('user', guild.owner_id, 'BLACKLISTED'):
                    logger.warning(f"⚠️ Add attempt by blacklisted user: {guild.owner_id}")

                    # Send a message to the owner if possible
                    try:
                        embed = discord.Embed(
                            description=(
                                "<:blacklist:1401596864784777363> You cannot add Moddy to servers while blacklisted.\n"
                                "<:blacklist:1401596864784777363> Vous ne pouvez pas ajouter Moddy à des serveurs en étant blacklisté."
                            ),
                            color=COLORS["error"]
                        )
                        embed.set_footer(text=f"ID: {guild.owner_id}")

                        # Create the button
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(
                            label="Unblacklist request",
                            url="https://moddy.app/unbl_request",
                            style=discord.ButtonStyle.link
                        ))

                        await guild.owner.send(embed=embed, view=view)
                    except:
                        pass

                    # Leave the server
                    await guild.leave()

                    # Log the action
                    if log_cog := self.get_cog("LoggingSystem"):
                        await log_cog.log_critical(
                            title="Join Blocked - Blacklisted User",
                            description=(
                                f"**Server:** {guild.name} (`{guild.id}`)\n"
                                f"**Owner:** {guild.owner} (`{guild.owner_id}`)\n"
                                f"**Members:** {guild.member_count}\n"
                                f"**Action:** Bot left automatically"
                            ),
                            ping_dev=False
                        )

                    return

                # If not blacklisted, continue normally
                # Create the server entry in the guilds table
                await self.db.get_guild(guild.id)  # This creates the entry if it doesn't exist

            except Exception as e:
                logger.error(f"DB Error (guild_join): {e}")

    async def on_guild_remove(self, guild: discord.Guild):
        """When the bot leaves a server"""
        logger.info(f"➖ Server left: {guild.name} ({guild.id})")

        # Clean the cache
        self.prefix_cache.pop(guild.id, None)

    async def on_message(self, message: discord.Message):
        """Process each message"""
        # Ignore its own messages
        if message.author == self.user:
            return

        # Maintenance mode - only devs can use the bot
        if self.maintenance_mode and not self.is_developer(message.author.id):
            return

        # Blacklist check is now handled by the BlacklistCheck cog
        # which intercepts all interactions BEFORE they are processed

        # Process commands
        await self.process_commands(message)

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Global error handling"""
        # The ErrorTracker cog handles everything now
        # This method is kept for compatibility but delegates to the cog
        pass

    @tasks.loop(minutes=10)
    async def status_update(self):
        """Update the bot's status"""
        # Security checks
        if not self.is_ready() or not self.ws:
            return

        statuses = [
            ("watching", f"{len(self.guilds)} servers"),
            ("playing", "/help"),
            ("watching", "moderators"),
            ("playing", f"with {len(self.users)} users")
        ]

        # Add special statuses if connected to the DB
        if self.db:
            try:
                stats = await self.db.get_stats()
                if stats.get('beta_users', 0) > 0:
                    statuses.append(("playing", f"in beta with {stats['beta_users']} testers"))
            except:
                pass

        # Random choice
        import random
        activity_type, name = random.choice(statuses)

        activity = discord.Activity(
            type=getattr(discord.ActivityType, activity_type),
            name=name
        )

        try:
            await self.change_presence(activity=activity)
        except (AttributeError, ConnectionError):
            # Ignore if we are closing
            pass
        except Exception as e:
            logger.error(f"Error changing status: {e}")

    @status_update.before_loop
    async def before_status_update(self):
        """Wait for the bot to be ready before starting the task"""
        await self.wait_until_ready()

    async def close(self):
        """Cleanly closing the bot"""
        logger.info("🔄 Shutting down...")

        # Stop tasks BEFORE closing
        if self.status_update.is_running():
            self.status_update.cancel()

        # Wait a bit for tasks to finish
        await asyncio.sleep(0.1)

        # Stop health server
        await self.stop_health_server()

        # Close DB connection
        if self.db:
            await self.db.close()

        # Close the HTTP client cleanly
        if hasattr(self, 'http') and self.http and hasattr(self.http, '_HTTPClient__session'):
            await self.http._HTTPClient__session.close()

        # Close the bot
        await super().close()