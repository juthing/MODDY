import discord
from discord.ext import commands

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="test", description="Commande de test pour vérifier que le bot répond bien !")
    async def test(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Salut {interaction.user.mention} ! Le bot fonctionne correctement.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Test(bot))
