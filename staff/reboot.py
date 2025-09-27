"""
Reboot command for developers
Restarts the bot and modifies the original message
"""

import discord
from discord.ext import commands
import asyncio
import os
import sys
import subprocess
import json
import tempfile
from datetime import datetime

# Import of the clean embeds system
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse, ModdyColors
from config import COLORS


class Reboot(commands.Cog):
    """Command to restart the bot"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Checks if the user is a developer"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="reboot", aliases=["restart"])
    async def reboot(self, ctx):
        """Restarts the bot automatically"""

        # Initial embed
        embed = discord.Embed(
            title="Reboot in progress...",
            description="The bot will restart in a few seconds.",
            color=COLORS["warning"],
            timestamp=datetime.utcnow()
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url
        )

        # Send the message
        msg = await ctx.send(embed=embed)

        # Log the action
        import logging
        logger = logging.getLogger('moddy')
        logger.info(f"Reboot requested by {ctx.author} ({ctx.author.id})")

        # Save info for after the reboot
        reboot_info = {
            "channel_id": ctx.channel.id,
            "message_id": msg.id,
            "author_name": str(ctx.author),
            "author_avatar": str(ctx.author.display_avatar.url),
            "start_time": datetime.utcnow().isoformat()
        }

        # Temporary file to store info
        temp_file = os.path.join(tempfile.gettempdir(), "moddy_reboot.json")

        with open(temp_file, 'w') as f:
            json.dump(reboot_info, f)

        # Short delay to ensure the message is sent
        await asyncio.sleep(0.5)

        # Log for debugging
        logger.info(f"Temporary file created: {temp_file}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Executable: {sys.executable}")
        logger.info(f"Arguments: {sys.argv}")

        try:
            # Close all connections cleanly
            await self.bot.close()

            # Wait for the bot to be completely closed
            await asyncio.sleep(1)

            # Prepare arguments for restart
            args = [sys.executable] + sys.argv

            # On Windows
            if sys.platform == "win32":
                # Use CREATE_NEW_CONSOLE to ensure the process continues
                subprocess.Popen(
                    args,
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
                    close_fds=True
                )
            else:
                # On Linux/Mac, use subprocess with nohup to detach the process
                subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    close_fds=True,
                    preexec_fn=os.setsid  # Create a new session
                )

            # Force exit of the current process
            os._exit(0)

        except Exception as e:
            logger.error(f"Error during reboot: {e}")
            # In case of error, still try to close cleanly
            sys.exit(1)


class RebootNotifier(commands.Cog):
    """Updates the message after the reboot"""

    def __init__(self, bot):
        self.bot = bot
        self._checked = False

    @commands.Cog.listener()
    async def on_ready(self):
        """Checks and updates the reboot message"""
        # Avoid checking multiple times
        if self._checked:
            return
        self._checked = True

        temp_file = os.path.join(tempfile.gettempdir(), "moddy_reboot.json")

        # Log for debugging
        import logging
        logger = logging.getLogger('moddy')
        logger.info(f"Checking for reboot file: {temp_file}")

        if not os.path.exists(temp_file):
            logger.info("No reboot file found")
            return

        try:
            # Read the info
            with open(temp_file, 'r') as f:
                info = json.load(f)

            logger.info(f"Reboot info found: channel {info['channel_id']}, message {info['message_id']}")

            # Calculate reboot time
            start_time = datetime.fromisoformat(info["start_time"])
            reboot_duration = (datetime.utcnow() - start_time).total_seconds()

            # Get the channel and message
            channel = self.bot.get_channel(info["channel_id"])
            if not channel:
                logger.warning(f"Channel {info['channel_id']} not found")
                os.remove(temp_file)
                return

            try:
                message = await channel.fetch_message(info["message_id"])
            except Exception as e:
                logger.warning(f"Message not found: {e}")
                os.remove(temp_file)
                return

            # Determine the speed
            if reboot_duration < 5:
                speed = "Ultra fast"
            elif reboot_duration < 10:
                speed = "Fast"
            elif reboot_duration < 20:
                speed = "Normal"
            else:
                speed = "Slow"

            # Create the new embed
            embed = discord.Embed(
                title="Reboot complete!",
                color=COLORS["success"],
                timestamp=datetime.utcnow()
            )

            # Description with details
            embed.description = f"**{speed}** - `{reboot_duration:.1f}` seconds"

            # Add fields
            embed.add_field(
                name="Steps",
                value="✓ Discord Connection\n"
                      "✓ Modules Loaded\n"
                      "✓ Database\n"
                      "✓ Commands Synced",
                inline=False
            )

            embed.add_field(
                name="Statistics",
                value=f"**Servers:** `{len(self.bot.guilds)}`\n"
                      f"**Users:** `{len(self.bot.users)}`\n"
                      f"**Latency:** `{round(self.bot.latency * 1000)}ms`",
                inline=True
            )

            embed.add_field(
                name="System",
                value=f"**Commands:** `{len(self.bot.commands)}`\n"
                      f"**Cogs:** `{len(self.bot.cogs)}`\n"
                      f"**Version:** discord.py `{discord.__version__}`",
                inline=True
            )

            # Footer with original info
            embed.set_footer(
                text=f"Requested by {info['author_name']}",
                icon_url=info["author_avatar"]
            )

            # Update the message
            await message.edit(embed=embed)

            # Delete the temporary file
            os.remove(temp_file)

            logger.info(f"Reboot notification sent (duration: {reboot_duration:.1f}s)")

        except Exception as e:
            logger.error(f"Reboot notification error: {e}")

            # Delete the file in case of error
            if os.path.exists(temp_file):
                os.remove(temp_file)


async def setup(bot):
    await bot.add_cog(Reboot(bot))
    await bot.add_cog(RebootNotifier(bot))