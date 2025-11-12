"""
Base class for all staff command cogs
Provides automatic message deletion tracking and helper methods
"""

import discord
from discord.ext import commands
import logging
from typing import Optional, Union
from discord.ui import LayoutView

logger = logging.getLogger('moddy.staff_base')


class StaffCommandsCog(commands.Cog):
    """
    Base class for all staff command cogs

    Provides automatic message deletion tracking:
    - When a staff command message is deleted, the bot's response is automatically deleted
    - All cogs inheriting from this class get this behavior by default

    Usage:
        class MyCog(StaffCommandsCog):
            def __init__(self, bot):
                super().__init__(bot)

            async def handle_my_command(self, message: discord.Message, args: str):
                # Use reply_with_tracking for automatic deletion tracking
                reply_msg = await self.reply_with_tracking(message, view)
    """

    def __init__(self, bot):
        self.bot = bot
        # Store command message -> response message mapping for auto-deletion
        self.command_responses = {}  # {command_msg_id: response_msg_id}

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """
        Handle message deletion to auto-delete command responses

        When a staff command message is deleted, this automatically finds and deletes
        the bot's response message, keeping channels clean.
        """
        # Check if this message is a command that has a response
        if message.id in self.command_responses:
            response_msg_id = self.command_responses[message.id]
            try:
                # Try to fetch and delete the response message
                response_msg = await message.channel.fetch_message(response_msg_id)
                await response_msg.delete()
                logger.info(f"Auto-deleted response {response_msg_id} for deleted command {message.id}")
            except (discord.NotFound, discord.Forbidden, discord.HTTPException) as e:
                logger.debug(f"Could not delete response message {response_msg_id}: {e}")
            finally:
                # Clean up the mapping
                del self.command_responses[message.id]

    async def reply_with_tracking(
        self,
        message: discord.Message,
        view: Optional[LayoutView] = None,
        content: Optional[str] = None,
        mention_author: bool = False
    ) -> discord.Message:
        """
        Reply to a message and automatically track it for deletion

        This is a convenience method that:
        1. Replies to the command message
        2. Automatically stores the mapping for auto-deletion
        3. Returns the reply message for further use if needed

        Args:
            message: The command message to reply to
            view: Optional LayoutView to send
            content: Optional text content to send
            mention_author: Whether to mention the author in the reply

        Returns:
            The reply message object

        Example:
            view = create_success_message("Done", "Command executed successfully")
            reply_msg = await self.reply_with_tracking(message, view)
        """
        reply_msg = await message.reply(view=view, content=content, mention_author=mention_author)
        # Store for auto-deletion
        self.command_responses[message.id] = reply_msg.id
        return reply_msg
