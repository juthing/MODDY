"""
Commands to manage user/server attributes.
Reserved for developers.
"""

import discord
from discord.ext import commands
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse
from config import COLORS


class AttributeCommands(commands.Cog):
    """System attribute management."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Checks if the user is a developer."""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="attr", aliases=["attribute"])
    async def attribute(self, ctx, action: str = None, target: discord.User = None, attr_name: str = None, *,
                        value: str = None):
        """Manages user attributes."""

        if not self.bot.db:
            await ctx.send("<:undone:1398729502028333218> Database not connected.")
            return

        if not action:
            # Display help
            embed = discord.Embed(
                title="<:manageuser:1398729745293774919> Attribute Management",
                description=(
                    "**Usage:**\n"
                    "`attr get @user` - View a user's attributes\n"
                    "`attr set @user ATTRIBUTE value` - Set an attribute\n"
                    "`attr remove @user ATTRIBUTE` - Remove an attribute\n"
                    "`attr list` - List all users with attributes\n\n"
                    "**Available attributes:**\n"
                    "`DEVELOPER`, `BETA`, `PREMIUM`, `BLACKLISTED`, `VERIFIED`"
                ),
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        if action.lower() == "get":
            if not target:
                target = ctx.author

            # Get the user
            user_data = await self.bot.db.get_user(target.id)

            embed = discord.Embed(
                title=f"<:label:1398729473649676440> Attributes for {target}",
                color=COLORS["info"]
            )

            if user_data['attributes']:
                attrs_text = "\n".join([f"`{k}`: **{v}**" for k, v in user_data['attributes'].items()])
                embed.add_field(name="Attributes", value=attrs_text, inline=False)
            else:
                embed.description = "No attributes set."

            # Add DB info
            embed.add_field(
                name="<:info:1401614681440784477> Information",
                value=(
                    f"**ID:** `{target.id}`\n"
                    f"**Created:** <t:{int(user_data.get('created_at', datetime.now()).timestamp())}:R>\n"
                    f"**Modified:** <t:{int(user_data.get('updated_at', datetime.now()).timestamp())}:R>"
                ),
                inline=False
            )

            await ctx.send(embed=embed)

        elif action.lower() == "set":
            if not target or not attr_name:
                await ctx.send("<:undone:1398729502028333218> Usage: `attr set @user ATTRIBUTE value`")
                return

            # Convert the value
            if value and value.lower() in ['true', 'yes', '1']:
                value = True
            elif value and value.lower() in ['false', 'no', '0']:
                value = False
            elif value and value.isdigit():
                value = int(value)

            # Set the attribute
            try:
                await self.bot.db.set_attribute(
                    'user', target.id, attr_name.upper(),
                    value, ctx.author.id, f"Manual command by {ctx.author}"
                )

                embed = ModdyResponse.success(
                    "Attribute Set",
                    f"**{attr_name.upper()}** = `{value}` for {target.mention}"
                )
                await ctx.send(embed=embed)

            except Exception as e:
                embed = ModdyResponse.error(
                    "Error",
                    f"Could not set attribute: {str(e)}"
                )
                await ctx.send(embed=embed)

        elif action.lower() == "remove":
            if not target or not attr_name:
                await ctx.send("<:undone:1398729502028333218> Usage: `attr remove @user ATTRIBUTE`")
                return

            try:
                await self.bot.db.set_attribute(
                    'user', target.id, attr_name.upper(),
                    None, ctx.author.id, f"Deletion by {ctx.author}"
                )

                embed = ModdyResponse.success(
                    "Attribute Removed",
                    f"**{attr_name.upper()}** removed for {target.mention}"
                )
                await ctx.send(embed=embed)

            except Exception as e:
                embed = ModdyResponse.error(
                    "Error",
                    f"Could not remove attribute: {str(e)}"
                )
                await ctx.send(embed=embed)

        elif action.lower() == "list":
            # List all users with attributes
            try:
                # Get users with attributes
                async with self.bot.db.pool.acquire() as conn:
                    rows = await conn.fetch("""
                        SELECT user_id, attributes
                        FROM users
                        WHERE attributes != '{}'::jsonb
                        LIMIT 20
                    """)

                if not rows:
                    await ctx.send("<:info:1401614681440784477> No users with attributes found.")
                    return

                embed = discord.Embed(
                    title="<:user:1398729712204779571> Users with Attributes",
                    color=COLORS["info"]
                )

                for row in rows:
                    user_id = row['user_id']
                    attrs = row['attributes']

                    # Try to get the user
                    try:
                        user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                        user_str = f"{user} ({user_id})"
                    except:
                        user_str = f"User {user_id}"

                    attrs_str = ", ".join([f"`{k}`" for k in attrs.keys()])
                    embed.add_field(
                        name=user_str,
                        value=attrs_str or "None",
                        inline=False
                    )

                await ctx.send(embed=embed)

            except Exception as e:
                await ctx.send(f"<:undone:1398729502028333218> Error: {str(e)}")

    @commands.command(name="fixdev", aliases=["devfix"])
    async def fix_developers(self, ctx):
        """Forces adding the DEVELOPER attribute."""
        if not self.bot.db:
            await ctx.send("<:undone:1398729502028333218> Database not connected.")
            return

        embed = discord.Embed(
            title="<:settings:1398729549323440208> Updating Developers",
            description="<:loading:1395047662092550194> Assigning DEVELOPER status...",
            color=COLORS["warning"]
        )
        msg = await ctx.send(embed=embed)

        success = []
        errors = []

        for dev_id in self.bot._dev_team_ids:
            try:
                # Create user if they don't exist
                await self.bot.db.get_user(dev_id)

                # Set the DEVELOPER attribute (True in the new system)
                await self.bot.db.set_attribute(
                    'user', dev_id, 'DEVELOPER', True,
                    ctx.author.id, "fixdev command"
                )

                # Verify
                if await self.bot.db.has_attribute('user', dev_id, 'DEVELOPER'):
                    success.append(dev_id)
                else:
                    errors.append((dev_id, "Attribute not set"))

            except Exception as e:
                errors.append((dev_id, str(e)))

        # Update the embed
        embed.color = COLORS["success"] if not errors else COLORS["warning"]
        embed.description = ""

        if success:
            embed.add_field(
                name="<:done:1398729525277229066> Success",
                value="\n".join([f"<@{uid}>" for uid in success]),
                inline=True
            )

        if errors:
            embed.add_field(
                name="<:undone:1398729502028333218> Errors",
                value="\n".join([f"<@{uid}>: {err}" for uid, err in errors]),
                inline=True
            )

        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(AttributeCommands(bot))