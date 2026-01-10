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


# =====================
# Schémas Subscription
# =====================

class SubscriptionType(str, Enum):
    """Types d'abonnements disponibles"""
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    """Statuts possibles d'un abonnement Stripe"""
    ACTIVE = "active"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    UNPAID = "unpaid"


class SubscriptionInfo(BaseModel):
    """Informations détaillées d'un abonnement"""
    subscription_id: str = Field(..., description="ID Stripe de l'abonnement")
    customer_id: str = Field(..., description="ID Stripe du customer")
    status: SubscriptionStatus = Field(..., description="Statut de l'abonnement")
    subscription_type: SubscriptionType = Field(..., description="Type d'abonnement (monthly/yearly)")
    current_period_start: str = Field(..., description="Début de la période actuelle (ISO 8601)")
    current_period_end: str = Field(..., description="Fin de la période actuelle (ISO 8601)")
    cancel_at_period_end: bool = Field(..., description="Si l'abonnement sera annulé à la fin")
    amount: int = Field(..., description="Montant en centimes (9900 = 99.00€)")
    currency: str = Field(..., description="Devise (eur, usd, etc.)")


class BotSubscriptionInfoRequest(BaseModel):
    """Requête pour récupérer les informations d'abonnement d'un utilisateur"""
    discord_id: str = Field(..., description="Discord ID de l'utilisateur")


class BotSubscriptionInfoResponse(BaseModel):
    """Réponse avec les informations d'abonnement"""
    success: bool = Field(..., description="Si la requête a réussi")
    message: str = Field(..., description="Message de confirmation")
    has_subscription: bool = Field(..., description="Si l'utilisateur a un abonnement actif")
    subscription: Optional[SubscriptionInfo] = Field(None, description="Détails de l'abonnement")


class InvoiceInfo(BaseModel):
    """Informations d'une facture Stripe"""
    invoice_id: str = Field(..., description="ID Stripe de la facture")
    amount: int = Field(..., description="Montant payé en centimes")
    currency: str = Field(..., description="Devise (eur, usd, etc.)")
    status: str = Field(..., description="Statut (paid, open, void, uncollectible)")
    created: str = Field(..., description="Date de création (ISO 8601)")
    invoice_pdf: Optional[str] = Field(None, description="URL du PDF de la facture")


class BotInvoicesRequest(BaseModel):
    """Requête pour récupérer les factures d'un utilisateur"""
    discord_id: str = Field(..., description="Discord ID de l'utilisateur")
    limit: int = Field(10, description="Nombre maximum de factures à récupérer")


class BotInvoicesResponse(BaseModel):
    """Réponse avec la liste des factures"""
    success: bool = Field(..., description="Si la requête a réussi")
    message: str = Field(..., description="Message de confirmation")
    invoices: list[InvoiceInfo] = Field(..., description="Liste des factures")


class BotRefundPaymentRequest(BaseModel):
    """Requête pour rembourser un paiement"""
    discord_id: str = Field(..., description="Discord ID de l'utilisateur")
    amount: Optional[int] = Field(None, description="Montant à rembourser en centimes (None = remboursement total)")
    reason: Optional[str] = Field(None, description="Raison du remboursement")


class BotRefundPaymentResponse(BaseModel):
    """Réponse après un remboursement"""
    success: bool = Field(..., description="Si le remboursement a réussi")
    message: str = Field(..., description="Message de confirmation")
    refunded: bool = Field(..., description="Si le remboursement a été effectué")
    refund_id: Optional[str] = Field(None, description="ID Stripe du remboursement")
    amount_refunded: Optional[int] = Field(None, description="Montant remboursé en centimes")
