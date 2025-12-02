"""
Test Error Command - Intentionally raises an error to test error_handler
"""
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal, Optional


class TestError(commands.Cog):
    """Command to test error handling system"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="test-error",
        description="🧪 Test command that intentionally raises an error"
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(
        error_type="Type of error to raise",
        incognito="Make response visible only to you"
    )
    async def test_error(
        self,
        interaction: discord.Interaction,
        error_type: Literal[
            "ValueError",
            "AttributeError",
            "RuntimeError",
            "ZeroDivisionError",
            "KeyError",
            "TypeError"
        ] = "RuntimeError",
        incognito: Optional[bool] = True
    ):
        """Test command that raises various types of errors"""

        # Send initial response
        await interaction.response.send_message(
            f"🧪 Generating a `{error_type}` for testing...",
            ephemeral=incognito
        )

        # Raise the specified error type
        if error_type == "ValueError":
            raise ValueError("Test error: Invalid value provided!")
        elif error_type == "AttributeError":
            raise AttributeError("Test error: Attribute does not exist!")
        elif error_type == "RuntimeError":
            raise RuntimeError("Test error: Something went wrong at runtime!")
        elif error_type == "ZeroDivisionError":
            # Actually perform a division by zero
            result = 1 / 0
        elif error_type == "KeyError":
            test_dict = {"key": "value"}
            value = test_dict["nonexistent_key"]
        elif error_type == "TypeError":
            raise TypeError("Test error: Type mismatch!")


async def setup(bot):
    await bot.add_cog(TestError(bot))
