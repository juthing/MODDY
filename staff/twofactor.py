"""
Commandes de gestion de l'authentification à deux facteurs
Pour sécuriser les commandes sensibles
"""

import discord
from discord.ext import commands
from datetime import datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils.embeds import ModdyEmbed, ModdyResponse
from utils.two_factor import two_factor
from config import COLORS


class TwoFactorCommands(commands.Cog):
    """Gestion de l'authentification 2FA"""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.group(name="2fa", aliases=["tfa", "totp"], invoke_without_command=True)
    async def two_factor_group(self, ctx):
        """Groupe de commandes 2FA"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Authentification à deux facteurs",
                description=(
                    "Système de sécurité pour les commandes sensibles.\n\n"
                    "**Commandes disponibles :**\n"
                    "`2fa enable` - Active la 2FA\n"
                    "`2fa disable` - Désactive la 2FA\n"
                    "`2fa status` - Vérifie ton statut 2FA\n"
                    "`2fa test <code>` - Teste un code\n"
                    "`2fa backup` - Génère des codes de secours"
                ),
                color=COLORS["info"]
            )

            # Statut actuel
            has_2fa = two_factor.has_2fa(ctx.author.id)
            status = "✅ Activée" if has_2fa else "❌ Désactivée"
            embed.add_field(
                name="Ton statut",
                value=status,
                inline=False
            )

            await ctx.send(embed=embed)

    @two_factor_group.command(name="enable", aliases=["activate", "on"])
    async def enable_2fa(self, ctx):
        """Active l'authentification à deux facteurs"""
        if two_factor.has_2fa(ctx.author.id):
            embed = ModdyResponse.warning(
                "2FA déjà activée",
                "L'authentification à deux facteurs est déjà activée sur ton compte."
            )
            await ctx.send(embed=embed)
            return

        # Génère un nouveau secret
        secret = two_factor.generate_secret(ctx.author.id)

        # Message d'avertissement
        embed = discord.Embed(
            title="Configuration de la 2FA",
            description=(
                "Je vais t'envoyer un QR code en DM pour configurer Google Authenticator.\n\n"
                "**Important :**\n"
                "• Garde ton secret en sécurité\n"
                "• Fais une sauvegarde des codes de secours\n"
                "• Tu en auras besoin pour les commandes sensibles"
            ),
            color=COLORS["warning"]
        )
        await ctx.send(embed=embed)

        # Génère le QR code
        qr_file = two_factor.generate_qr_code(ctx.author, secret)

        # Envoie en DM
        try:
            dm_embed = discord.Embed(
                title="Configuration Google Authenticator",
                description=(
                    "**1.** Ouvre Google Authenticator\n"
                    "**2.** Tape sur + puis 'Scanner un QR code'\n"
                    "**3.** Scanne le QR code ci-dessous\n"
                    "**4.** Entre le code à 6 chiffres avec `2fa test <code>`\n\n"
                    f"**Secret manuel :** `{secret}`\n"
                    "*Garde ce secret en sécurité !*"
                ),
                color=COLORS["primary"]
            )
            dm_embed.set_image(url="attachment://2fa_qr_code.png")

            await ctx.author.send(embed=dm_embed, file=qr_file)

            # Confirmation
            confirm_embed = ModdyResponse.success(
                "QR Code envoyé",
                "Vérifie tes DMs pour configurer Google Authenticator !"
            )
            await ctx.send(embed=confirm_embed)

        except discord.Forbidden:
            embed = ModdyResponse.error(
                "DMs bloqués",
                "Je ne peux pas t'envoyer de DM. Active tes DMs et réessaye."
            )
            await ctx.send(embed=embed)
            # Annule l'activation
            two_factor.disable_2fa(ctx.author.id)

    @two_factor_group.command(name="disable", aliases=["deactivate", "off"])
    async def disable_2fa(self, ctx):
        """Désactive l'authentification à deux facteurs"""
        if not two_factor.has_2fa(ctx.author.id):
            embed = ModdyResponse.warning(
                "2FA non activée",
                "L'authentification à deux facteurs n'est pas activée sur ton compte."
            )
            await ctx.send(embed=embed)
            return

        # Demande confirmation avec un code 2FA
        embed = discord.Embed(
            title="Confirmation requise",
            description="Entre ton code 2FA pour confirmer la désactivation.",
            color=COLORS["warning"]
        )
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit() and len(m.content) == 6

        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)

            # Supprime le message avec le code
            try:
                await msg.delete()
            except:
                pass

            # Vérifie le code
            if not two_factor.verify_code(ctx.author.id, msg.content):
                embed = ModdyResponse.error(
                    "Code invalide",
                    "Le code 2FA est incorrect. Désactivation annulée."
                )
                await ctx.send(embed=embed)
                return

            # Désactive la 2FA
            two_factor.disable_2fa(ctx.author.id)

            embed = ModdyResponse.success(
                "2FA désactivée",
                "L'authentification à deux facteurs a été désactivée avec succès."
            )
            await ctx.send(embed=embed)

        except asyncio.TimeoutError:
            embed = ModdyResponse.error(
                "Temps écoulé",
                "Tu n'as pas entré de code dans le temps imparti."
            )
            await ctx.send(embed=embed)

    @two_factor_group.command(name="test", aliases=["verify", "check"])
    async def test_2fa(self, ctx, code: str = None):
        """Teste un code 2FA"""
        if not two_factor.has_2fa(ctx.author.id):
            embed = ModdyResponse.error(
                "2FA non activée",
                "Tu dois d'abord activer la 2FA avec `2fa enable`."
            )
            await ctx.send(embed=embed)
            return

        if not code:
            embed = ModdyResponse.error(
                "Code manquant",
                "Tu dois fournir un code à 6 chiffres."
            )
            await ctx.send(embed=embed)
            return

        if not code.isdigit() or len(code) != 6:
            embed = ModdyResponse.error(
                "Format invalide",
                "Le code doit être composé de 6 chiffres."
            )
            await ctx.send(embed=embed)
            return

        # Teste le code
        if two_factor.verify_code(ctx.author.id, code):
            embed = ModdyResponse.success(
                "Code valide",
                "Le code 2FA est correct ! Ta configuration fonctionne."
            )
        else:
            embed = ModdyResponse.error(
                "Code invalide",
                "Le code est incorrect ou a expiré. Vérifie l'heure de ton appareil."
            )

        await ctx.send(embed=embed)

    @two_factor_group.command(name="status", aliases=["info"])
    async def status_2fa(self, ctx):
        """Affiche le statut 2FA"""
        has_2fa = two_factor.has_2fa(ctx.author.id)

        embed = discord.Embed(
            title="Statut 2FA",
            color=COLORS["success"] if has_2fa else COLORS["error"],
            timestamp=datetime.now()
        )

        embed.add_field(
            name="État",
            value="✅ Activée" if has_2fa else "❌ Désactivée",
            inline=True
        )

        embed.add_field(
            name="Utilisateur",
            value=f"{ctx.author.mention}",
            inline=True
        )

        if has_2fa:
            embed.add_field(
                name="Commandes protégées",
                value="`exec`, `eval`",
                inline=False
            )

            embed.add_field(
                name="Application",
                value="Google Authenticator, Authy, ou toute app TOTP",
                inline=False
            )
        else:
            embed.add_field(
                name="Activation",
                value="Utilise `2fa enable` pour activer",
                inline=False
            )

        await ctx.send(embed=embed)

    @two_factor_group.command(name="backup", aliases=["codes", "recovery"])
    async def backup_codes(self, ctx):
        """Génère des codes de secours (non implémenté)"""
        embed = discord.Embed(
            title="Codes de secours",
            description=(
                "Cette fonctionnalité n'est pas encore implémentée.\n\n"
                "**En cas de perte d'accès :**\n"
                "• Garde ton secret initial en sécurité\n"
                "• Contacte un autre développeur pour désactiver ta 2FA\n"
                "• Utilise un backup de Google Authenticator"
            ),
            color=COLORS["info"]
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TwoFactorCommands(bot))