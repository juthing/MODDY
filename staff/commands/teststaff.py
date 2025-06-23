from discord.ext import commands

class StaffTestCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="teststaff")
    @commands.is_owner()
    async def teststaff(self, ctx):
        """Commande staff de test réservée à l'owner."""
        await ctx.send("✅ Test réussi : tu es bien owner !")

async def setup(bot):
    await bot.add_cog(StaffTestCommand(bot))
