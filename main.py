import os
import logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv('TOKEN')
STAFF_ROLE_ID = int(os.getenv('STAFF_ROLE_ID', 0))
PREFIX = commands.when_mentioned

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

def is_staff():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        return (
            ctx.author.guild_permissions.administrator or
            any(r.id == STAFF_ROLE_ID for r in ctx.author.roles)
        )
    return commands.check(predicate)

def load_staff_commands():
    staff_commands_path = os.path.join(os.path.dirname(__file__), 'staff', 'commands')
    for file in os.listdir(staff_commands_path):
        if file.endswith('.py') and not file.startswith('_'):
            bot.load_extension(f"staff.commands.{file[:-3]}")

def load_public_commands():
    cogs_path = os.path.join(os.path.dirname(__file__), 'cogs')
    for file in os.listdir(cogs_path):
        if file.endswith('.py') and not file.startswith('_'):
            bot.load_extension(f"cogs.{file[:-3]}")

@bot.event
async def on_ready():
    logging.info(f'Connecté en tant que {bot.user}')
    print(f'✅ Bot prêt : {bot.user} ({bot.user.id})')

if __name__ == "__main__":
    load_staff_commands()
    load_public_commands()
    bot.run(TOKEN)
