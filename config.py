"""
Configuration de Moddy pour Railway
Les variables sont récupérées directement depuis l'environnement Railway
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

# =============================================================================
# CONFIGURATION DISCORD
# =============================================================================

# Token du bot (obligatoire) - Variable Railway: DISCORD_TOKEN
TOKEN: str = os.environ.get("DISCORD_TOKEN", "")

# Préfixe par défaut pour les commandes
DEFAULT_PREFIX: str = os.environ.get("DEFAULT_PREFIX", "!")

# Mode debug
DEBUG: bool = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes", "on")

# IDs des développeurs (optionnel, le bot récupère depuis l'API Discord)
dev_ids_str = os.environ.get("DEVELOPER_IDS", "")
DEVELOPER_IDS: List[int] = [int(id.strip()) for id in dev_ids_str.split(",") if id.strip()]

# =============================================================================
# BASE DE DONNÉES
# =============================================================================

# URL de connexion Neon PostgreSQL - Variable Railway: DATABASE_URL
DATABASE_URL: Optional[str] = os.environ.get("DATABASE_URL")

# Pool de connexions
DB_POOL_MIN_SIZE: int = int(os.environ.get("DB_POOL_MIN_SIZE", "1"))
DB_POOL_MAX_SIZE: int = int(os.environ.get("DB_POOL_MAX_SIZE", "10"))

# =============================================================================
# API KEYS
# =============================================================================

# DeepL API pour les traductions - Variable Railway: DEEPL_API_KEY
DEEPL_API_KEY: str = os.environ.get("DEEPL_API_KEY", "")

# =============================================================================
# PARAMÈTRES DU BOT
# =============================================================================

# Intervalle de mise à jour du statut (en minutes)
STATUS_UPDATE_INTERVAL: int = int(os.environ.get("STATUS_UPDATE_INTERVAL", "10"))

# Intervalle de vérification des rappels (en secondes)
REMINDER_CHECK_INTERVAL: int = int(os.environ.get("REMINDER_CHECK_INTERVAL", "60"))

# Taille maximale du cache de préfixes
PREFIX_CACHE_SIZE: int = int(os.environ.get("PREFIX_CACHE_SIZE", "1000"))

# Timeout des commandes (en secondes)
COMMAND_TIMEOUT: int = int(os.environ.get("COMMAND_TIMEOUT", "60"))

# =============================================================================
# LIMITES ET SÉCURITÉ
# =============================================================================

# Nombre max de rappels par utilisateur
MAX_REMINDERS_PER_USER: int = int(os.environ.get("MAX_REMINDERS_PER_USER", "10"))

# Longueur max d'un tag
MAX_TAG_LENGTH: int = int(os.environ.get("MAX_TAG_LENGTH", "2000"))

# Nombre max de tags par serveur
MAX_TAGS_PER_GUILD: int = int(os.environ.get("MAX_TAGS_PER_GUILD", "50"))

# =============================================================================
# CHEMINS DU PROJET
# =============================================================================

# Racine du projet
ROOT_DIR: Path = Path(__file__).parent

# Dossiers principaux
COGS_DIR: Path = ROOT_DIR / "cogs"
STAFF_DIR: Path = ROOT_DIR / "staff"

# Fichier de logs
LOG_FILE: Path = ROOT_DIR / "moddy.log"

# =============================================================================
# COULEURS DU BOT
# =============================================================================

COLORS = {
    "primary": 0x5865F2,  # Bleu Discord
    "success": 0x57F287,  # Vert
    "warning": 0xFEE75C,  # Jaune
    "error": 0xED4245,  # Rouge
    "info": 0x5865F2,  # Bleu
    "neutral": 0x99AAB5,  # Gris
    "developer": 0x9B59B6 # Violet
}

# =============================================================================
# EMOJIS PERSONNALISÉS
# =============================================================================

EMOJIS = {
    # Status
    "done": "<:done:1398729525277229066>",
    "undone": "<:undone:1398729502028333218>",
    "loading": "<a:loading:1395047662092550194>",

    # Icônes
    "settings": "<:settings:1398729549323440208>",
    "info": "<:info:1398729537201930270>",
    "warning": "<:warning:1398729560895422505>",
    "error": "<:error:1398729514099335228>",

    # Actions
    "add": "<:add:1398729490724679720>",
    "remove": "<:remove:1398729478435393598>",
    "edit": "<:edit:1398729467756752906>",

    # Bot
    "moddy": "<:moddy:1398729456117551207>",
    "developer": "<:developer:1398729444520325202>",
    "staff": "<:staff:1398729432759476245>",
    "ping": "<:support:1398734366670065726>"
}


# =============================================================================
# VALIDATION DE LA CONFIGURATION
# =============================================================================

def validate_config():
    """Vérifie que la configuration est valide"""
    errors = []

    # Token obligatoire
    if not TOKEN:
        errors.append("❌ DISCORD_TOKEN manquant dans les variables d'environnement Railway")

    # Vérifier que les dossiers existent
    if not COGS_DIR.exists():
        COGS_DIR.mkdir(exist_ok=True)
        print(f"📁 Dossier créé : {COGS_DIR}")

    if not STAFF_DIR.exists():
        STAFF_DIR.mkdir(exist_ok=True)
        print(f"📁 Dossier créé : {STAFF_DIR}")

    # Avertissements non bloquants
    if not DATABASE_URL:
        print("⚠️ DATABASE_URL non configurée - Mode sans base de données")

    if not DEEPL_API_KEY:
        print("⚠️ DEEPL_API_KEY non configurée - Commande translate désactivée")

    if DEBUG:
        print("🔧 Mode DEBUG activé")
        print("🚂 Environnement Railway détecté")

    # Si erreurs critiques, arrêter
    if errors:
        for error in errors:
            print(error)
        sys.exit(1)

    print("✅ Configuration validée pour Railway")


# Valider au chargement du module
if __name__ != "__main__":
    validate_config()

# =============================================================================
# EXPORT POUR DEBUG
# =============================================================================

if __name__ == "__main__":
    # Pour tester la config : python config.py
    print("\n🚂 Configuration Railway actuelle :")
    print(f"  DISCORD_TOKEN: {'✅ Configuré' if TOKEN else '❌ Manquant'}")
    print(f"  DATABASE_URL: {'✅ Configuré' if DATABASE_URL else '⚠️ Non configuré'}")
    print(f"  DEEPL_API_KEY: {'✅ Configuré' if DEEPL_API_KEY else '⚠️ Non configuré'}")
    print(f"  DEBUG: {DEBUG}")
    print(f"  DEFAULT_PREFIX: {DEFAULT_PREFIX}")
    print(f"  DEVELOPER_IDS: {DEVELOPER_IDS or 'Auto-détection'}")
    print(f"\n📁 Chemins :")
    print(f"  ROOT_DIR: {ROOT_DIR}")
    print(f"  COGS_DIR: {COGS_DIR}")
    print(f"  STAFF_DIR: {STAFF_DIR}")
    print(f"  LOG_FILE: {LOG_FILE}")

    # Affiche toutes les variables d'environnement Railway (pour debug)
    if DEBUG:
        print(f"\n🔍 Variables d'environnement Railway détectées :")
        railway_vars = [k for k in os.environ.keys() if
                        'RAILWAY' in k or 'DISCORD' in k or 'DATABASE' in k or 'DEEPL' in k]
        for var in sorted(railway_vars):
            value = os.environ.get(var)
            if 'TOKEN' in var or 'KEY' in var or 'PASSWORD' in var:
                value = '***' if value else 'Non défini'
            print(f"  {var}: {value}")