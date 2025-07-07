"""
Configuration centralisée pour Moddy
Charge les variables d'environnement et définit les paramètres
"""

import os
import sys
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Charge le fichier .env
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Fichier .env chargé depuis {env_path}")
else:
    print("⚠️ Fichier .env non trouvé - Utilisation des variables d'environnement système")

# =============================================================================
# CONFIGURATION DISCORD
# =============================================================================

# Token du bot (obligatoire)
TOKEN: str = os.getenv("DISCORD_TOKEN", "")

# Préfixe par défaut pour les commandes
DEFAULT_PREFIX: str = os.getenv("DEFAULT_PREFIX", "!")

# Mode debug
DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes", "on")

# IDs des développeurs (optionnel, le bot récupère depuis l'API Discord)
dev_ids_str = os.getenv("DEVELOPER_IDS", "")
DEVELOPER_IDS: List[int] = [int(id.strip()) for id in dev_ids_str.split(",") if id.strip()]

# =============================================================================
# BASE DE DONNÉES
# =============================================================================

# URL de connexion Neon PostgreSQL
DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

# Pool de connexions
DB_POOL_MIN_SIZE: int = int(os.getenv("DB_POOL_MIN_SIZE", "1"))
DB_POOL_MAX_SIZE: int = int(os.getenv("DB_POOL_MAX_SIZE", "10"))

# =============================================================================
# PARAMÈTRES DU BOT
# =============================================================================

# Intervalle de mise à jour du statut (en minutes)
STATUS_UPDATE_INTERVAL: int = int(os.getenv("STATUS_UPDATE_INTERVAL", "10"))

# Intervalle de vérification des rappels (en secondes)
REMINDER_CHECK_INTERVAL: int = int(os.getenv("REMINDER_CHECK_INTERVAL", "60"))

# Taille maximale du cache de préfixes
PREFIX_CACHE_SIZE: int = int(os.getenv("PREFIX_CACHE_SIZE", "1000"))

# Timeout des commandes (en secondes)
COMMAND_TIMEOUT: int = int(os.getenv("COMMAND_TIMEOUT", "60"))

# =============================================================================
# LIMITES ET SÉCURITÉ
# =============================================================================

# Nombre max de rappels par utilisateur
MAX_REMINDERS_PER_USER: int = int(os.getenv("MAX_REMINDERS_PER_USER", "25"))

# Nombre max de tags par serveur
MAX_TAGS_PER_GUILD: int = int(os.getenv("MAX_TAGS_PER_GUILD", "100"))

# Longueur max d'un tag
MAX_TAG_LENGTH: int = int(os.getenv("MAX_TAG_LENGTH", "2000"))

# Cooldown global des commandes (en secondes)
GLOBAL_COOLDOWN: int = int(os.getenv("GLOBAL_COOLDOWN", "3"))

# =============================================================================
# EMOJIS ET APPARENCE
# =============================================================================

# Emojis utilisés dans le bot
EMOJIS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "loading": "⏳",
    "arrow": "➡️",
    "bot": "🤖",
    "developer": "🔧",
    "reminder": "⏰",
    "tag": "🏷️",
    "server": "🏢",
    "user": "👤",
    "stats": "📊",
    "ping": "🏓",
    "help": "❓",
    "settings": "⚙️"
}

# Couleurs pour les embeds
COLORS = {
    "primary": 0x5865F2,  # Blurple Discord
    "success": 0x57F287,  # Vert
    "error": 0xED4245,  # Rouge
    "warning": 0xFEE75C,  # Jaune
    "info": 0x5865F2,  # Bleu
    "developer": 0xEB459E  # Rose (pour les commandes dev)
}

# =============================================================================
# CHEMINS ET FICHIERS
# =============================================================================

# Dossier racine du projet
ROOT_DIR: Path = Path(__file__).parent

# Dossiers importants
COGS_DIR: Path = ROOT_DIR / "cogs"
STAFF_DIR: Path = ROOT_DIR / "staff"
LOGS_DIR: Path = ROOT_DIR / "logs"

# Créer le dossier logs s'il n'existe pas
LOGS_DIR.mkdir(exist_ok=True)

# Fichier de log
LOG_FILE: Path = LOGS_DIR / "moddy.log"


# =============================================================================
# VALIDATION
# =============================================================================

def validate_config():
    """Vérifie que la configuration est valide"""
    errors = []

    # Token obligatoire
    if not TOKEN:
        errors.append("❌ TOKEN Discord manquant dans le fichier .env")

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

    if DEBUG:
        print("🔧 Mode DEBUG activé")

    # Si erreurs critiques, arrêter
    if errors:
        for error in errors:
            print(error)
        sys.exit(1)

    print("✅ Configuration validée")


# Valider au chargement du module
if __name__ != "__main__":
    validate_config()

# =============================================================================
# EXPORT POUR DEBUG
# =============================================================================

if __name__ == "__main__":
    # Pour tester la config : python config.py
    print("\n📋 Configuration actuelle :")
    print(f"  TOKEN: {'✅ Configuré' if TOKEN else '❌ Manquant'}")
    print(f"  DATABASE_URL: {'✅ Configuré' if DATABASE_URL else '⚠️ Non configuré'}")
    print(f"  DEBUG: {DEBUG}")
    print(f"  DEFAULT_PREFIX: {DEFAULT_PREFIX}")
    print(f"  DEVELOPER_IDS: {DEVELOPER_IDS or 'Auto-détection'}")
    print(f"\n📁 Chemins :")
    print(f"  ROOT_DIR: {ROOT_DIR}")
    print(f"  COGS_DIR: {COGS_DIR}")
    print(f"  STAFF_DIR: {STAFF_DIR}")
    print(f"  LOG_FILE: {LOG_FILE}")