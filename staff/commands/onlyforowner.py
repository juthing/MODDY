from discord.ext import commands

class MaCommandeStaff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def onlyforowner(self, ctx):
        await ctx.send("Seul l'owner peut utiliser cette commande.")

async def setup(bot):
    await bot.add_cog(MaCommandeStaff(bot))
