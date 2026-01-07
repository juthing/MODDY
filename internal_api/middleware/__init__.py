"""
Middleware pour l'API interne
"""

from .auth import verify_internal_auth

__all__ = ["verify_internal_auth"]
