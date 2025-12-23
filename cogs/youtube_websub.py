"""
YouTube WebSub Webhook Handler
Handles incoming WebSub notifications from YouTube for video uploads
"""

import discord
from discord.ext import commands
import logging
from aiohttp import web
import asyncio
from typing import Optional

logger = logging.getLogger('moddy.cogs.youtube_websub')


class YouTubeWebSubHandler(commands.Cog):
    """
    Handles WebSub (PubSubHubbub) webhook notifications from YouTube
    """

    def __init__(self, bot):
        self.bot = bot
        self.app = None
        self.runner = None
        self.site = None
        self.webhook_port = 8080  # Configure this based on your deployment
        self.webhook_path = "/websub/youtube"

    async def cog_load(self):
        """Called when the cog is loaded"""
        # Start the webhook server
        await self.start_webhook_server()

    async def cog_unload(self):
        """Called when the cog is unloaded"""
        # Stop the webhook server
        await self.stop_webhook_server()

    async def start_webhook_server(self):
        """Start the aiohttp webhook server"""
        try:
            self.app = web.Application()
            self.app.router.add_route('GET', self.webhook_path, self.handle_verification)
            self.app.router.add_route('POST', self.webhook_path, self.handle_notification)

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, '0.0.0.0', self.webhook_port)
            await self.site.start()

            logger.info(f"✅ YouTube WebSub webhook server started on port {self.webhook_port}")
        except Exception as e:
            logger.error(f"❌ Failed to start webhook server: {e}", exc_info=True)

    async def stop_webhook_server(self):
        """Stop the aiohttp webhook server"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()

            logger.info("✅ YouTube WebSub webhook server stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping webhook server: {e}", exc_info=True)

    async def handle_verification(self, request: web.Request) -> web.Response:
        """
        Handle WebSub verification (challenge) requests

        When subscribing to a YouTube channel, Google sends a GET request with:
        - hub.mode: subscribe or unsubscribe
        - hub.topic: The YouTube feed URL
        - hub.challenge: A random string to echo back
        - hub.lease_seconds: Subscription duration
        """
        try:
            params = request.query

            mode = params.get('hub.mode')
            topic = params.get('hub.topic')
            challenge = params.get('hub.challenge')
            lease_seconds = params.get('hub.lease_seconds')

            logger.info(f"📬 WebSub verification request: mode={mode}, topic={topic}")

            # Verify this is a valid YouTube topic
            if topic and 'youtube.com/xml/feeds/videos.xml' in topic:
                # Extract channel ID from topic
                channel_id = None
                if 'channel_id=' in topic:
                    channel_id = topic.split('channel_id=')[1].split('&')[0]

                logger.info(f"✅ WebSub verification successful for channel {channel_id}")

                # Return the challenge to confirm subscription
                return web.Response(text=challenge, status=200)
            else:
                logger.warning(f"❌ Invalid WebSub verification topic: {topic}")
                return web.Response(text='Invalid topic', status=404)

        except Exception as e:
            logger.error(f"❌ Error handling WebSub verification: {e}", exc_info=True)
            return web.Response(text='Error', status=500)

    async def handle_notification(self, request: web.Request) -> web.Response:
        """
        Handle WebSub notification (POST) requests

        When a YouTube channel posts a video, Google sends a POST request with:
        - Content-Type: application/atom+xml
        - Body: Atom feed XML with video information
        """
        try:
            # Read the request body (Atom XML feed)
            body = await request.text()

            logger.info(f"📺 Received YouTube WebSub notification")
            logger.debug(f"Notification body: {body[:500]}...")  # Log first 500 chars

            # Process the notification asynchronously
            asyncio.create_task(self.process_notification(body))

            # Return 200 immediately to acknowledge receipt
            return web.Response(text='OK', status=200)

        except Exception as e:
            logger.error(f"❌ Error handling WebSub notification: {e}", exc_info=True)
            return web.Response(text='Error', status=500)

    async def process_notification(self, feed_xml: str):
        """
        Process a YouTube notification asynchronously

        Args:
            feed_xml: The Atom XML feed from YouTube
        """
        try:
            # Parse the XML to extract channel ID
            import xml.etree.ElementTree as ET

            root = ET.fromstring(feed_xml)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'yt': 'http://www.youtube.com/xml/schemas/2015'
            }

            entry = root.find('atom:entry', ns)
            if entry is None:
                logger.warning("No entry found in YouTube notification")
                return

            channel_id_elem = entry.find('yt:channelId', ns)
            if channel_id_elem is None:
                logger.warning("No channel ID found in YouTube notification")
                return

            channel_id = channel_id_elem.text

            logger.info(f"📺 Processing notification for YouTube channel {channel_id}")

            # Find all guilds with subscriptions to this channel
            await self.notify_subscribed_guilds(channel_id, feed_xml)

        except Exception as e:
            logger.error(f"❌ Error processing YouTube notification: {e}", exc_info=True)

    async def notify_subscribed_guilds(self, youtube_channel_id: str, feed_xml: str):
        """
        Notify all guilds that are subscribed to this YouTube channel

        Args:
            youtube_channel_id: The YouTube channel ID
            feed_xml: The Atom XML feed
        """
        try:
            # Get all guilds
            for guild in self.bot.guilds:
                try:
                    # Get the YouTube notifications module for this guild
                    module = await self.bot.module_manager.get_module_instance(
                        guild.id,
                        'youtube_notifications'
                    )

                    if not module or not module.enabled:
                        continue

                    # Check if this guild has a subscription for this channel
                    subscription = module.get_subscription_by_channel(youtube_channel_id)

                    if subscription:
                        logger.info(f"✅ Found subscription in guild {guild.name} ({guild.id})")

                        # Handle the notification
                        await module.handle_notification(feed_xml)

                except Exception as e:
                    logger.error(f"❌ Error notifying guild {guild.id}: {e}", exc_info=True)
                    continue

        except Exception as e:
            logger.error(f"❌ Error notifying subscribed guilds: {e}", exc_info=True)

    def get_callback_url(self) -> str:
        """
        Get the public callback URL for WebSub subscriptions

        This should be configured based on your deployment environment.
        For production, this should be a publicly accessible HTTPS URL.

        Returns:
            str: The callback URL
        """
        # TODO: Configure this based on environment variables
        # For now, return a placeholder
        # In production, this should be something like:
        # https://your-bot-domain.com/websub/youtube

        # Try to get from environment or config
        import os
        callback_url = os.getenv('YOUTUBE_WEBSUB_CALLBACK_URL')

        if callback_url:
            return callback_url

        # Default fallback (will not work in production)
        return f"http://localhost:{self.webhook_port}{self.webhook_path}"

    @commands.Cog.listener()
    async def on_module_config_save(self, guild_id: int, module_id: str, config: dict):
        """
        Called when a module configuration is saved
        Subscribe/unsubscribe from YouTube channels as needed
        """
        if module_id != 'youtube_notifications':
            return

        try:
            # Get the module instance
            module = await self.bot.module_manager.get_module_instance(
                guild_id,
                'youtube_notifications'
            )

            if not module:
                return

            # Get callback URL
            callback_url = self.get_callback_url()

            # Subscribe to all channels in the config
            subscriptions = config.get('subscriptions', [])

            for sub in subscriptions:
                channel_id = sub.get('channel_id')
                if channel_id:
                    logger.info(f"📺 Subscribing to YouTube channel {channel_id} for guild {guild_id}")
                    success = await module.subscribe_to_channel(channel_id, callback_url)

                    if success:
                        logger.info(f"✅ Successfully subscribed to {channel_id}")
                    else:
                        logger.error(f"❌ Failed to subscribe to {channel_id}")

        except Exception as e:
            logger.error(f"❌ Error handling module config save: {e}", exc_info=True)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(YouTubeWebSubHandler(bot))
