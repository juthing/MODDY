#!/usr/bin/env python3
"""
Moddy - Script de lancement
Lance le bot Discord
"""

import asyncio
import sys
import logging
from pathlib import Path

# Windows : fix pour les couleurs
if sys.platform == "win32":
    try:
        import colorama

        colorama.init()
    except ImportError:
        pass

# Vérifie la version de Python
if sys.version_info < (3, 11):
    print("❌ Python 3.11+ est requis !")
    sys.exit(1)

# Configure le logging de base
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Lance le bot"""
    try:
        # Import ici pour avoir les erreurs après le logging
        from bot import ModdyBot
        from config import TOKEN

        if not TOKEN:
            logging.error("❌ Token Discord manquant ! Vérifiez votre fichier .env")
            return

        # Crée et lance le bot
        bot = ModdyBot()
        await bot.start(TOKEN)

    except ImportError as e:
        logging.error(f"❌ Erreur d'import : {e}")
        logging.error("Vérifiez que bot.py et config.py existent.")
        sys.exit(1)
    except KeyboardInterrupt:
        logging.info("⏹️ Arrêt demandé")
    except Exception as e:
        logging.error(f"❌ Erreur fatale : {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 À bientôt !")