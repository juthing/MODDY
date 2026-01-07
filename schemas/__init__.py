"""
Schémas Pydantic pour Moddy
"""

from .internal import (
    UserAction,
    BotEventType,
    InternalNotifyUserRequest,
    InternalNotifyUserResponse,
    InternalUpdateRoleRequest,
    InternalUpdateRoleResponse,
    InternalHealthResponse,
    BotUserInfoRequest,
    BotUserInfoResponse,
    BotEventNotifyRequest,
    BotEventNotifyResponse,
)

__all__ = [
    "UserAction",
    "BotEventType",
    "InternalNotifyUserRequest",
    "InternalNotifyUserResponse",
    "InternalUpdateRoleRequest",
    "InternalUpdateRoleResponse",
    "InternalHealthResponse",
    "BotUserInfoRequest",
    "BotUserInfoResponse",
    "BotEventNotifyRequest",
    "BotEventNotifyResponse",
]
