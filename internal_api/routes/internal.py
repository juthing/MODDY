"""
Endpoints internes pour la communication avec le backend.
Basé sur /documentation/internal-api.md
"""

from fastapi import APIRouter, HTTPException, status
import logging
from typing import Optional
import discord

from schemas.internal import (
    InternalNotifyUserRequest,
    InternalNotifyUserResponse,
    InternalUpdateRoleRequest,
    InternalUpdateRoleResponse,
    InternalHealthResponse,
)

router = APIRouter(prefix="/internal", tags=["Internal"])
logger = logging.getLogger('moddy.internal_api.routes')

# Référence globale au bot Discord (sera définie au démarrage)
_bot_instance: Optional[discord.Client] = None


def set_bot_instance(bot):
    """
    Définit l'instance du bot Discord pour les routes internes.

    Args:
        bot: Instance de ModdyBot
    """
    global _bot_instance
    _bot_instance = bot
    logger.info("✅ Bot instance set for internal API routes")


def get_bot():
    """
    Récupère l'instance du bot Discord.

    Returns:
        Instance de ModdyBot

    Raises:
        HTTPException: Si le bot n'est pas disponible
    """
    if _bot_instance is None:
        logger.error("❌ Bot instance not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Bot instance not available"
        )
    return _bot_instance


@router.get("/health", response_model=InternalHealthResponse)
async def health_check():
    """
    Health check pour vérifier que le bot est accessible.

    Returns:
        InternalHealthResponse avec le statut du service
    """
    try:
        bot = get_bot()

        # Vérifier que le bot est connecté à Discord
        if not bot.is_ready():
            return InternalHealthResponse(
                status="unhealthy",
                service="discord-bot",
                version="1.0.0"
            )

        return InternalHealthResponse(
            status="healthy",
            service="discord-bot",
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}", exc_info=True)
        return InternalHealthResponse(
            status="unhealthy",
            service="discord-bot",
            version="1.0.0"
        )


@router.post("/notify", response_model=InternalNotifyUserResponse)
async def notify_user(payload: InternalNotifyUserRequest):
    """
    Notifie le bot d'un événement utilisateur.

    Cette fonction:
    1. Récupère l'utilisateur Discord par son ID
    2. Lui envoie un message privé (DM) avec les informations
    3. Met à jour l'attribut PREMIUM dans la base de données si nécessaire
    4. Logger l'événement

    Args:
        payload: Données de notification (discord_id, action, plan, metadata)

    Returns:
        InternalNotifyUserResponse avec le statut de l'opération
    """
    logger.info(f"📩 Notification reçue pour discord_id={payload.discord_id}, action={payload.action}")

    try:
        bot = get_bot()

        # Récupérer l'utilisateur Discord
        try:
            user = await bot.fetch_user(int(payload.discord_id))
        except discord.NotFound:
            logger.warning(f"⚠️ User {payload.discord_id} not found on Discord")
            return InternalNotifyUserResponse(
                success=False,
                message=f"User {payload.discord_id} not found",
                notification_sent=False
            )
        except discord.HTTPException as e:
            logger.error(f"❌ Failed to fetch user {payload.discord_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch user: {str(e)}"
            )

        # Mettre à jour l'attribut PREMIUM dans la base de données
        await _update_premium_attribute(bot, payload)

        # Créer le message de notification basé sur l'action
        message = _create_notification_message(payload)

        # Envoyer le message en DM
        try:
            await user.send(message)
            logger.info(f"✅ Notification envoyée à {user} ({payload.discord_id})")
            notification_sent = True
        except discord.Forbidden:
            logger.warning(f"⚠️ Cannot send DM to {user} ({payload.discord_id}) - DMs disabled")
            notification_sent = False
        except discord.HTTPException as e:
            logger.error(f"❌ Failed to send DM to {user}: {e}")
            notification_sent = False

        return InternalNotifyUserResponse(
            success=True,
            message="User notified successfully" if notification_sent else "User found but DM failed",
            notification_sent=notification_sent
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la notification: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/roles/update", response_model=InternalUpdateRoleResponse)
async def update_user_role(payload: InternalUpdateRoleRequest):
    """
    Met à jour les rôles Discord d'un utilisateur.

    Cette fonction:
    1. Récupère le membre du serveur Discord principal (MODDY_GUILD_ID)
    2. Ajoute/retire les rôles spécifiés
    3. Retourne le statut

    Args:
        payload: Données de mise à jour (discord_id, plan, add_roles, remove_roles)

    Returns:
        InternalUpdateRoleResponse avec le statut de l'opération
    """
    logger.info(f"📝 Mise à jour des rôles pour discord_id={payload.discord_id}, plan={payload.plan}")

    try:
        bot = get_bot()

        # Récupérer l'ID du serveur principal depuis les variables d'environnement
        import os
        guild_id_str = os.getenv("MODDY_GUILD_ID")
        if not guild_id_str:
            logger.error("❌ MODDY_GUILD_ID environment variable not set")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MODDY_GUILD_ID not configured"
            )

        guild_id = int(guild_id_str)

        # Récupérer le serveur Discord
        guild = bot.get_guild(guild_id)
        if not guild:
            logger.error(f"❌ Guild {guild_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Guild {guild_id} not found"
            )

        # Récupérer le membre
        try:
            member = await guild.fetch_member(int(payload.discord_id))
        except discord.NotFound:
            logger.warning(f"⚠️ Member {payload.discord_id} not found in guild {guild_id}")
            return InternalUpdateRoleResponse(
                success=False,
                message=f"Member {payload.discord_id} not in guild",
                roles_updated=False,
                guild_id=str(guild_id)
            )
        except discord.HTTPException as e:
            logger.error(f"❌ Failed to fetch member {payload.discord_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch member: {str(e)}"
            )

        # Ajouter les rôles
        if payload.add_roles:
            for role_id_str in payload.add_roles:
                role = guild.get_role(int(role_id_str))
                if role:
                    try:
                        await member.add_roles(role, reason=f"Plan update: {payload.plan}")
                        logger.info(f"✅ Added role {role.name} to {member}")
                    except discord.Forbidden:
                        logger.error(f"❌ Missing permissions to add role {role.name}")
                    except discord.HTTPException as e:
                        logger.error(f"❌ Failed to add role {role.name}: {e}")
                else:
                    logger.warning(f"⚠️ Role {role_id_str} not found in guild")

        # Retirer les rôles
        if payload.remove_roles:
            for role_id_str in payload.remove_roles:
                role = guild.get_role(int(role_id_str))
                if role:
                    try:
                        await member.remove_roles(role, reason=f"Plan update: {payload.plan}")
                        logger.info(f"✅ Removed role {role.name} from {member}")
                    except discord.Forbidden:
                        logger.error(f"❌ Missing permissions to remove role {role.name}")
                    except discord.HTTPException as e:
                        logger.error(f"❌ Failed to remove role {role.name}: {e}")
                else:
                    logger.warning(f"⚠️ Role {role_id_str} not found in guild")

        return InternalUpdateRoleResponse(
            success=True,
            message="Roles updated successfully",
            roles_updated=True,
            guild_id=str(guild_id)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur lors de la mise à jour des rôles: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def _update_premium_attribute(bot, payload: InternalNotifyUserRequest):
    """
    Met à jour l'attribut PREMIUM dans la base de données selon l'action.

    Args:
        bot: Instance du bot Discord
        payload: Données de notification

    Returns:
        None
    """
    # Déterminer si l'utilisateur doit avoir l'attribut PREMIUM
    should_be_premium = False
    reason = ""

    # Liste des plans premium
    premium_plans = ["moddy_max", "premium", "moddy_premium"]

    if payload.action == "subscription_created":
        # Nouvelle souscription créée
        if payload.plan and payload.plan.lower() in premium_plans:
            should_be_premium = True
            reason = f"Subscription created: {payload.plan}"

    elif payload.action == "subscription_updated":
        # Abonnement mis à jour
        if payload.plan and payload.plan.lower() in premium_plans:
            should_be_premium = True
            reason = f"Subscription updated: {payload.plan}"

    elif payload.action == "subscription_cancelled":
        # Abonnement annulé - retirer PREMIUM
        should_be_premium = False
        reason = "Subscription cancelled"

    elif payload.action == "plan_upgraded":
        # Plan amélioré
        if payload.plan and payload.plan.lower() in premium_plans:
            should_be_premium = True
            reason = f"Plan upgraded to: {payload.plan}"

    elif payload.action == "plan_downgraded":
        # Plan rétrogradé - vérifier si toujours premium
        if payload.plan and payload.plan.lower() in premium_plans:
            should_be_premium = True
            reason = f"Plan downgraded to: {payload.plan}"
        else:
            should_be_premium = False
            reason = f"Plan downgraded to: {payload.plan}"

    # Mettre à jour l'attribut dans la base de données
    try:
        # ID système pour les changements automatiques
        SYSTEM_USER_ID = 0

        if should_be_premium:
            # Ajouter l'attribut PREMIUM
            await bot.db.set_attribute(
                'user',
                int(payload.discord_id),
                'PREMIUM',
                True,
                SYSTEM_USER_ID,
                reason
            )
            logger.info(f"✅ Attribut PREMIUM ajouté pour user {payload.discord_id}: {reason}")
        else:
            # Supprimer l'attribut PREMIUM
            await bot.db.set_attribute(
                'user',
                int(payload.discord_id),
                'PREMIUM',
                None,
                SYSTEM_USER_ID,
                reason
            )
            logger.info(f"✅ Attribut PREMIUM retiré pour user {payload.discord_id}: {reason}")

    except Exception as e:
        # Logger l'erreur mais ne pas faire échouer la notification
        logger.error(f"❌ Erreur lors de la mise à jour de l'attribut PREMIUM: {e}", exc_info=True)


def _create_notification_message(payload: InternalNotifyUserRequest) -> str:
    """
    Crée un message de notification basé sur l'action.

    Args:
        payload: Données de notification

    Returns:
        Message formaté pour l'utilisateur
    """
    action_messages = {
        "subscription_created": f"🎉 Votre abonnement **{payload.plan}** a été activé avec succès !",
        "subscription_updated": f"✅ Votre abonnement **{payload.plan}** a été mis à jour.",
        "subscription_cancelled": f"❌ Votre abonnement a été annulé.",
        "plan_upgraded": f"⬆️ Votre plan a été amélioré vers **{payload.plan}** !",
        "plan_downgraded": f"⬇️ Votre plan a été rétrogradé vers **{payload.plan}**.",
    }

    message = action_messages.get(
        payload.action,
        f"📬 Notification: {payload.action}"
    )

    # Ajouter des métadonnées si disponibles
    if payload.metadata:
        if "email" in payload.metadata:
            message += f"\n\n📧 Email: {payload.metadata['email']}"

    message += "\n\nMerci d'utiliser Moddy ! 🤖"

    return message
