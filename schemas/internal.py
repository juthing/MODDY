"""
Schémas Pydantic pour la communication interne entre le backend et le bot Discord.
Basé sur /documentation/internal-api.md
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from enum import Enum


# =====================
# Enums
# =====================

class UserAction(str, Enum):
    """Actions possibles pour notifier un utilisateur"""
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_UPDATED = "subscription_updated"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PLAN_UPGRADED = "plan_upgraded"
    PLAN_DOWNGRADED = "plan_downgraded"


class BotEventType(str, Enum):
    """Types d'événements Discord que le bot peut envoyer au backend"""
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    ROLE_UPDATED = "role_updated"
    COMMAND_USED = "command_used"
    MESSAGE_SENT = "message_sent"


# =====================
# Schémas Backend → Bot
# =====================

class InternalNotifyUserRequest(BaseModel):
    """Requête pour notifier un utilisateur d'un événement"""
    discord_id: str = Field(..., description="Discord ID de l'utilisateur (Snowflake)")
    action: UserAction = Field(..., description="Action effectuée")
    plan: Optional[str] = Field(None, description="Nom du plan (moddy_max, free, etc.)")
    metadata: Optional[dict] = Field(None, description="Métadonnées additionnelles")


class InternalNotifyUserResponse(BaseModel):
    """Réponse après notification d'un utilisateur"""
    success: bool = Field(..., description="Si l'opération a réussi")
    message: str = Field(..., description="Message de statut")
    notification_sent: bool = Field(False, description="Si la notification a été envoyée")


class InternalUpdateRoleRequest(BaseModel):
    """Requête pour mettre à jour les rôles Discord d'un utilisateur"""
    discord_id: str = Field(..., description="Discord ID de l'utilisateur")
    plan: str = Field(..., description="Nouveau plan de l'utilisateur")
    add_roles: Optional[list[str]] = Field(None, description="IDs des rôles à ajouter")
    remove_roles: Optional[list[str]] = Field(None, description="IDs des rôles à retirer")


class InternalUpdateRoleResponse(BaseModel):
    """Réponse après mise à jour des rôles"""
    success: bool = Field(..., description="Si l'opération a réussi")
    message: str = Field(..., description="Message de statut")
    roles_updated: bool = Field(False, description="Si les rôles ont été mis à jour")
    guild_id: Optional[str] = Field(None, description="ID du serveur Discord")


class InternalHealthResponse(BaseModel):
    """Réponse du health check"""
    status: Literal["healthy", "unhealthy"] = Field(..., description="État de santé du service")
    service: str = Field(..., description="Nom du service")
    version: Optional[str] = Field(None, description="Version du service")


# =====================
# Schémas Bot → Backend
# =====================

class BotUserInfoRequest(BaseModel):
    """Requête pour récupérer les informations d'un utilisateur"""
    discord_id: str = Field(..., description="Discord ID de l'utilisateur à récupérer")


class BotUserInfoResponse(BaseModel):
    """Réponse avec les informations utilisateur"""
    success: bool = Field(..., description="Si l'opération a réussi")
    message: str = Field(..., description="Message de statut")
    user_found: bool = Field(..., description="Si l'utilisateur existe dans la DB")
    discord_id: Optional[str] = Field(None, description="Discord ID de l'utilisateur")
    email: Optional[str] = Field(None, description="Email de l'utilisateur")
    created_at: Optional[str] = Field(None, description="Date de création du compte")
    updated_at: Optional[str] = Field(None, description="Date de dernière mise à jour")


class BotEventNotifyRequest(BaseModel):
    """Requête pour notifier le backend d'un événement Discord"""
    event_type: BotEventType = Field(..., description="Type d'événement Discord")
    discord_id: str = Field(..., description="Discord ID de l'utilisateur concerné")
    metadata: Optional[dict] = Field(None, description="Métadonnées additionnelles")


class BotEventNotifyResponse(BaseModel):
    """Réponse après notification d'un événement"""
    success: bool = Field(..., description="Si l'opération a réussi")
    message: str = Field(..., description="Message de statut")
    event_received: bool = Field(..., description="Si l'événement a été reçu")
