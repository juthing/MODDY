"""
Announcement Channel Setup Utility
Handles automatic following of Moddy's announcement channel in guilds
"""

import discord
import logging
import os
import aiohttp

logger = logging.getLogger('moddy.announcement_setup')

# Source channel ID from Moddy support server
MODDY_ANNOUNCEMENT_CHANNEL_ID = 1410338969107042515


async def setup_announcement_channel(guild: discord.Guild) -> tuple[bool, str]:
    """
    Setup announcement channel following for a guild.

    This function:
    1. Checks if the guild has a community updates channel
    2. If yes, follows Moddy's announcement channel to it
    3. If no, creates a new text channel called "moddy-updates" and follows to it

    Args:
        guild: The Discord guild to setup announcements for

    Returns:
        tuple[bool, str]: (success, message) - Success status and descriptive message
    """
    try:
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            logger.error("DISCORD_TOKEN not found in environment variables")
            return False, "Discord token not configured"

        # Check if the guild has a community updates channel
        updates_channel = guild.public_updates_channel

        if updates_channel:
            # Guild has a community updates channel, use it
            logger.info(f"Found community updates channel: #{updates_channel.name} ({updates_channel.id}) in {guild.name}")
            target_channel_id = updates_channel.id
            channel_type = "community updates"
        else:
            # No community updates channel, create a new channel
            logger.info(f"No community updates channel found in {guild.name}, creating moddy-updates channel")

            try:
                # Create a new text channel
                new_channel = await guild.create_text_channel(
                    name="moddy-updates",
                    topic="Official updates and announcements from Moddy",
                    reason="Automatic setup for Moddy announcements"
                )
                target_channel_id = new_channel.id
                channel_type = "new channel"
                logger.info(f"Created new channel: #{new_channel.name} ({new_channel.id}) in {guild.name}")
            except discord.Forbidden:
                logger.warning(f"Missing permissions to create channel in {guild.name}")
                return False, "Missing permissions to create channel"
            except Exception as e:
                logger.error(f"Error creating channel in {guild.name}: {e}")
                return False, f"Error creating channel: {str(e)}"

        # Follow Moddy's announcement channel to the target channel
        url = f"https://discord.com/api/v10/channels/{MODDY_ANNOUNCEMENT_CHANNEL_ID}/followers"

        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "webhook_channel_id": target_channel_id
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    logger.info(f"✅ Successfully followed announcement channel to {channel_type} in {guild.name}")
                    return True, f"Successfully setup announcements in {channel_type}"
                elif resp.status == 403:
                    # Permission denied
                    logger.warning(f"Permission denied to follow channel in {guild.name}")
                    return False, "Missing permissions to manage webhooks in the target channel"
                elif resp.status == 400:
                    # Bad request - might be invalid channel or already following
                    error_text = await resp.text()
                    logger.warning(f"Bad request when following channel in {guild.name}: {error_text}")

                    # Parse error to see if it's a permission issue or other
                    if "permissions" in error_text.lower():
                        return False, "Missing permissions to manage webhooks"
                    elif "already" in error_text.lower():
                        return False, "Announcement channel is already being followed"
                    else:
                        return False, f"Invalid request: {error_text[:100]}"
                else:
                    error_text = await resp.text()
                    logger.error(f"Failed to follow channel in {guild.name}: Status {resp.status}, Response: {error_text}")
                    return False, f"Discord API error {resp.status}: {error_text[:100]}"

    except discord.Forbidden as e:
        logger.warning(f"Permission denied in {guild.name}: {e}")
        return False, "Missing permissions (Manage Webhooks or Manage Channels required)"
    except discord.HTTPException as e:
        logger.error(f"Discord HTTP error in {guild.name}: {e}")
        return False, f"Discord error: {str(e)}"
    except Exception as e:
        logger.error(f"Error setting up announcement channel for {guild.name}: {e}", exc_info=True)
        return False, f"Unexpected error: {str(e)}"
