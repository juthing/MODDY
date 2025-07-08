"""
Commandes dev amusantes et utiles
Pour se détendre entre deux sessions de debug
"""

import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime
import string

from config import COLORS


class DevFun(commands.Cog):
    """Commandes fun pour développeurs"""

    def __init__(self, bot):
        self.bot = bot
        self.chaos_mode = False

    async def cog_check(self, ctx):
        """Vérifie que l'utilisateur est développeur"""
        return self.bot.is_developer(ctx.author.id)

    @commands.command(name="chaos")
    async def chaos_mode(self, ctx):
        """Active/désactive le mode chaos (répond n'importe quoi aux messages)"""
        self.chaos_mode = not self.chaos_mode

        if self.chaos_mode:
            embed = discord.Embed(
                title="MODE CHAOS ACTIVÉ",
                description="Je vais maintenant répondre de manière... imprévisible",
                color=COLORS["error"]
            )
            await ctx.send(embed=embed)

            # Réactions random pendant 30 secondes
            self.bot.loop.create_task(self._chaos_reactions(ctx.channel))
        else:
            embed = discord.Embed(
                title="Mode chaos désactivé",
                description="Retour à la normale... pour l'instant",
                color=COLORS["success"]
            )
            await ctx.send(embed=embed)

    async def _chaos_reactions(self, channel):
        """Ajoute des réactions random pendant 30 secondes"""
        emojis = ["🤔", "🤯", "👀", "💀", "🔥", "✨", "🎉", "🤖", "👻", "🦆"]
        end_time = asyncio.get_event_loop().time() + 30

        while self.chaos_mode and asyncio.get_event_loop().time() < end_time:
            await asyncio.sleep(5)
            async for message in channel.history(limit=1):
                if not message.author.bot:
                    try:
                        await message.add_reaction(random.choice(emojis))
                    except:
                        pass

        self.chaos_mode = False

    @commands.command(name="spam")
    async def spam_user(self, ctx, user: discord.User = None, count: int = 5):
        """Spam un utilisateur en DM (max 10 messages)"""
        if user is None:
            embed = discord.Embed(
                title="Utilisation de la commande spam",
                description="**Usage:** `spam @utilisateur [nombre]`\n\n"
                           "**Exemples:**\n"
                           "`spam @Jules 5` - Spam Jules 5 fois\n"
                           "`spam @Jules` - Spam Jules 5 fois (par défaut)",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        if count > 10:
            await ctx.send("Pas plus de 10 messages, restons raisonnables !")
            return

        messages = [
            "Coucou !",
            "Tu dors ?",
            "RÉVEILLE-TOI",
            "J'ai un secret à te dire...",
            "C'est une blague",
            "Tu me manques",
            "On fait un UNO ?",
            "J'ai cassé la production",
            "Oups mauvaise personne",
            "Tu as vu mon dernier commit ?"
        ]

        embed = discord.Embed(
            title="Spam en cours...",
            description=f"J'embête {user.mention}",
            color=COLORS["warning"]
        )
        await ctx.send(embed=embed)

        try:
            for i in range(count):
                await user.send(random.choice(messages))
                await asyncio.sleep(1)
            await ctx.send("Mission accomplie !")
        except discord.Forbidden:
            await ctx.send("Il a bloqué ses DMs, le lâche !")

    @commands.command(name="rickroll")
    async def rickroll(self, ctx, channel: discord.TextChannel = None):
        """Rickroll un canal (ou le canal actuel)"""
        target = channel or ctx.channel

        embed = discord.Embed(
            title="🎵 Nouvelle musique exclusive !",
            description="Clique pour écouter en avant-première !",
            color=COLORS["primary"]
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Écouter maintenant",
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            style=discord.ButtonStyle.link
        ))

        await target.send(embed=embed, view=view)

        if channel:
            await ctx.send(f"Piège posé dans {channel.mention} !")

    @commands.command(name="matrix")
    async def matrix_effect(self, ctx, duration: int = 5):
        """Effet Matrix dans le chat (max 10 secondes)"""
        if duration > 10:
            duration = 10

        chars = "01"
        msg = await ctx.send("```\nInitialisation...\n```")

        for _ in range(duration * 2):  # 2 updates par seconde
            matrix = "\n".join(
                "".join(random.choice(chars) for _ in range(30))
                for _ in range(10)
            )
            await msg.edit(content=f"```\n{matrix}\n```")
            await asyncio.sleep(0.5)

        await msg.edit(content="```\nACCÈS AUTORISÉ - BIENVENUE NEO\n```")

    @commands.command(name="bomb")
    async def emoji_bomb(self, ctx, emoji: str = "💣", count: int = 10):
        """Bombe d'emojis qui explose"""
        if count > 20:
            count = 20

        # Animation de compte à rebours
        bomb_msg = await ctx.send(f"{emoji} **3**")
        await asyncio.sleep(1)
        await bomb_msg.edit(content=f"{emoji} **2**")
        await asyncio.sleep(1)
        await bomb_msg.edit(content=f"{emoji} **1**")
        await asyncio.sleep(1)

        # EXPLOSION
        explosion = " ".join([emoji for _ in range(count)])
        await bomb_msg.edit(content=f"**BOOM!**\n{explosion}")

        # Nettoyer après 5 secondes
        await asyncio.sleep(5)
        await bomb_msg.edit(content="💨 *fumée...*")

    @commands.command(name="hack")
    async def fake_hack(self, ctx, user: discord.User = None):
        """Fait semblant de hacker quelqu'un"""
        target = user or ctx.author

        steps = [
            f"Initialisation du hack sur {target.mention}...",
            "Connexion au mainframe...",
            "Bypass du firewall... [████░░░░░░] 40%",
            "Accès aux données... [███████░░░] 70%",
            "Téléchargement de l'historique... [█████████░] 90%",
            f"**ACCÈS TOTAL À {target.name.upper()}**",
            f"Mot de passe trouvé : `hunter2`",
            f"Solde bancaire : `{random.randint(1, 100)}€`",
            f"Recherches Google embarrassantes : `comment faire cuire des pâtes`",
            "...",
            "**C'était une blague !** 😄"
        ]

        msg = await ctx.send(steps[0])

        for step in steps[1:]:
            await asyncio.sleep(2)
            await msg.edit(content=step)

    @commands.command(name="reverse")
    async def reverse_text(self, ctx, *, text: str = None):
        """Inverse le texte"""
        if text is None:
            embed = discord.Embed(
                title="Utilisation de la commande reverse",
                description="**Usage:** `reverse <texte>`\n\n"
                           "**Exemple:**\n"
                           "`reverse Hello World` - dlroW olleH",
                color=COLORS["info"]
            )
            await ctx.send(embed=embed)
            return

        reversed_text = text[::-1]

        embed = discord.Embed(
            title=reversed_text[:256],  # Limite titre Discord
            description="!srevne'l à tircé te al snad siov eJ",
            color=COLORS["primary"]
        )

        await ctx.send(embed=embed)

        # Bonus : le bot parle à l'envers pendant 30 secondes
        original_send = ctx.send
        async def reversed_send(content=None, **kwargs):
            if content and isinstance(content, str):
                content = content[::-1]
            return await original_send(content, **kwargs)

        ctx.send = reversed_send
        await asyncio.sleep(30)
        ctx.send = original_send

    @commands.command(name="rainbow")
    async def rainbow_role(self, ctx, role: discord.Role, duration: int = 10):
        """Fait clignoter un rôle en arc-en-ciel (max 30 sec)"""
        if duration > 30:
            duration = 30

        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send("J'ai pas les perms pour ça !")
            return

        colors = [
            0xFF0000,  # Rouge
            0xFF7F00,  # Orange
            0xFFFF00,  # Jaune
            0x00FF00,  # Vert
            0x0000FF,  # Bleu
            0x4B0082,  # Indigo
            0x9400D3   # Violet
        ]

        original_color = role.color
        await ctx.send(f"🌈 Activation du mode arc-en-ciel sur {role.mention} !")

        end_time = asyncio.get_event_loop().time() + duration
        i = 0

        while asyncio.get_event_loop().time() < end_time:
            try:
                await role.edit(color=discord.Color(colors[i % len(colors)]))
                i += 1
                await asyncio.sleep(0.5)
            except:
                break

        # Restaurer la couleur originale
        try:
            await role.edit(color=original_color)
        except:
            pass

        await ctx.send("Fin du spectacle !")

    @commands.command(name="secret")
    async def secret_message(self, ctx):
        """Envoie un message secret qui s'autodétruit"""
        secrets = [
            "Le café de la machine est en réalité... du déca",
            "J'ai utilisé ChatGPT pour cette feature",
            "Le bug en prod ? C'était moi",
            "Je push sur master en secret",
            "Les tests unitaires ? Jamais fait",
            "Mon code fonctionne, mais je sais pas pourquoi",
            "J'ai fermé 50 issues en marquant 'Can't reproduce'"
        ]

        embed = discord.Embed(
            title="🤫 Message Ultra Secret",
            description=f"||{random.choice(secrets)}||",
            color=COLORS["developer"],
            footer={"text": "Ce message s'autodétruira dans 10 secondes"}
        )

        msg = await ctx.send(embed=embed)

        for i in range(10, 0, -1):
            embed.set_footer(text=f"Autodestruction dans {i} secondes")
            await msg.edit(embed=embed)
            await asyncio.sleep(1)

        await msg.delete()
        await ctx.send("💥 *Message détruit*")

    @commands.command(name="impostor")
    async def impostor_mode(self, ctx, user: discord.Member = None):
        """Imite un utilisateur (change le nickname du bot)"""
        if not user:
            user = ctx.author

        if not ctx.guild.me.guild_permissions.change_nickname:
            await ctx.send("J'ai pas les perms pour changer mon pseudo !")
            return

        original_nick = ctx.guild.me.nick

        try:
            await ctx.guild.me.edit(nick=f"{user.display_name} (bot)")

            embed = discord.Embed(
                title="Mode Imposteur Activé",
                description=f"Je suis maintenant {user.mention} ! (pendant 1 minute)",
                color=COLORS["warning"]
            )
            embed.set_thumbnail(url=user.display_avatar.url)

            await ctx.send(embed=embed)

            # Messages d'imitation
            messages = [
                "Salut c'est moi !",
                "Je suis un vrai humain",
                "Beep boop... euh je veux dire, bonjour !",
                "Comment allez-vous, mes chers collègues humains ?"
            ]

            for _ in range(3):
                await asyncio.sleep(10)
                await ctx.send(random.choice(messages))

            # Restaurer après 1 minute
            await asyncio.sleep(30)
            await ctx.guild.me.edit(nick=original_nick)
            await ctx.send("Bon okay c'était moi tout le temps 🤖")

        except discord.Forbidden:
    async def cog_command_error(self, ctx, error):
        """Gestion des erreurs pour ce cog"""
        if isinstance(error, commands.UserNotFound):
            await ctx.send(f"Utilisateur introuvable ! Utilise une mention : `@username`")
        elif isinstance(error, commands.MissingRequiredArgument):
            # Afficher l'aide de la commande
            if ctx.command:
                await ctx.send(f"Argument manquant ! Utilise `fun help` pour voir comment utiliser les commandes.")
        else:
            # Laisser le gestionnaire global gérer les autres erreurs
            await self.bot.on_command_error(ctx, error)


    @commands.command(name="fun", aliases=["help"])
    async def fun_help(self, ctx):
        """Affiche toutes les commandes fun disponibles"""
        embed = discord.Embed(
            title="Commandes Fun pour Développeurs",
            description="Voici toutes les commandes amusantes disponibles :",
            color=COLORS["primary"]
        )

        commands_list = [
            ("chaos", "Active/désactive le mode chaos", "`chaos`"),
            ("spam", "Spam un utilisateur en DM", "`spam @user [nombre]`"),
            ("rickroll", "Pose un piège rickroll", "`rickroll [#channel]`"),
            ("matrix", "Effet Matrix", "`matrix [durée]`"),
            ("bomb", "Bombe d'emojis", "`bomb [emoji] [nombre]`"),
            ("hack", "Faux hack", "`hack [@user]`"),
            ("reverse", "Inverse le texte", "`reverse <texte>`"),
            ("rainbow", "Arc-en-ciel sur un rôle", "`rainbow @role [durée]`"),
            ("secret", "Message secret", "`secret`"),
            ("impostor", "Imite un utilisateur", "`impostor [@user]`")
        ]

        for name, desc, usage in commands_list:
            embed.add_field(
                name=f"**{name}**",
                value=f"{desc}\n{usage}",
                inline=True
            )

        embed.set_footer(text="Utilise ces commandes avec modération !")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(DevFun(bot))