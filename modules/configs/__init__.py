"""
Configurations UI pour les modules de serveur
Ce package contient les interfaces de configuration pour chaque module
"""

from .welcome_channel_config import WelcomeChannelConfigView
from .welcome_dm_config import WelcomeDmConfigView
from .starboard_config import StarboardConfigView

__all__ = ['WelcomeChannelConfigView', 'WelcomeDmConfigView', 'StarboardConfigView']
