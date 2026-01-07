"""
API interne pour la communication avec le backend.
Basé sur /documentation/internal-api.md
"""

from .server import app, set_bot

__all__ = ["app", "set_bot"]
