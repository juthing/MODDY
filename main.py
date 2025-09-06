#!/usr/bin/env python3
"""
Moddy - Script de lancement avec services intégrés
Lance le bot Discord et tous les services associés (webhook JSK, etc.)
"""

import asyncio
import sys
import logging
import subprocess
import threading
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any
import signal
import atexit

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


class ServiceManager:
    """Gestionnaire des services Moddy (webhook JSK, etc.)"""

    def __init__(self):
        self.services: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger('moddy.services')
        self.running = True

        # S'assure de tout nettoyer à la fin
        atexit.register(self.cleanup)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Gère les signaux d'arrêt."""
        self.logger.info("📍 Signal d'arrêt reçu, fermeture des services...")
        self.cleanup()

    def start_service(self, name: str, command: list, health_check_url: Optional[str] = None):
        """
        Démarre un service en subprocess avec redirection des logs.

        Args:
            name: Nom du service
            command: Commande à exécuter
            health_check_url: URL pour vérifier que le service est prêt
        """
        if name in self.services and self.services[name].get('process'):
            if self.services[name]['process'].poll() is None:
                self.logger.info(f"✅ {name} déjà actif")
                return True

        try:
            self.logger.info(f"🚀 Démarrage du service {name}...")

            # Lance le processus
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=Path(__file__).parent
            )

            # Thread pour lire et afficher les logs
            log_thread = threading.Thread(
                target=self._stream_logs,
                args=(name, process),
                daemon=True
            )
            log_thread.start()

            self.services[name] = {
                'process': process,
                'command': command,
                'log_thread': log_thread,
                'health_check_url': health_check_url
            }

            # Attendre que le service soit prêt
            if health_check_url:
                if self._wait_for_service(name, health_check_url):
                    self.logger.info(f"✅ {name} opérationnel")
                    return True
                else:
                    self.logger.error(f"❌ {name} n'a pas démarré correctement")
                    self.stop_service(name)
                    return False
            else:
                # Pas de health check, on assume que c'est bon après un délai
                time.sleep(2)
                if process.poll() is None:
                    self.logger.info(f"✅ {name} lancé (pas de health check)")
                    return True
                else:
                    self.logger.error(f"❌ {name} s'est arrêté immédiatement")
                    return False

        except Exception as e:
            self.logger.error(f"❌ Erreur démarrage {name}: {e}")
            return False

    def _stream_logs(self, service_name: str, process: subprocess.Popen):
        """
        Lit et affiche les logs d'un service en temps réel.
        """
        logger = logging.getLogger(f'moddy.services.{service_name}')

        try:
            while self.running:
                if process.stdout:
                    line = process.stdout.readline()
                    if not line:
                        break

                    # Nettoie et affiche la ligne
                    line = line.strip()
                    if line:
                        # Détermine le niveau de log
                        if 'ERROR' in line or 'CRITICAL' in line or '❌' in line:
                            logger.error(line)
                        elif 'WARNING' in line or 'WARN' in line or '⚠️' in line:
                            logger.warning(line)
                        elif 'DEBUG' in line:
                            logger.debug(line)
                        else:
                            logger.info(line)

                # Vérifie si le processus est toujours actif
                if process.poll() is not None:
                    if self.running:
                        logger.warning(f"⚠️ {service_name} s'est arrêté (code: {process.returncode})")
                    break

        except Exception as e:
            if self.running:
                logger.error(f"Erreur lecture logs: {e}")

    def _wait_for_service(self, name: str, health_check_url: str, timeout: int = 10) -> bool:
        """
        Attend qu'un service soit prêt en vérifiant son endpoint de santé.
        """
        import urllib.request
        import urllib.error

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                with urllib.request.urlopen(health_check_url, timeout=1) as response:
                    if response.status == 200:
                        return True
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.5)
                continue

            # Vérifie que le processus est toujours actif
            if name in self.services and self.services[name]['process'].poll() is not None:
                return False

        return False

    def stop_service(self, name: str):
        """Arrête un service proprement."""
        if name not in self.services:
            return

        service = self.services[name]
        if service.get('process'):
            process = service['process']

            if process.poll() is None:
                self.logger.info(f"⏹️  Arrêt du service {name}...")

                # Essaie d'arrêter proprement
                process.terminate()
                try:
                    process.wait(timeout=5)
                    self.logger.info(f"✅ {name} arrêté proprement")
                except subprocess.TimeoutExpired:
                    # Force l'arrêt
                    self.logger.warning(f"⚠️ Force l'arrêt de {name}")
                    process.kill()
                    process.wait()

            del self.services[name]

    def restart_service(self, name: str):
        """Redémarre un service."""
        if name in self.services:
            service_info = self.services[name].copy()
            self.stop_service(name)
            time.sleep(1)
            self.start_service(
                name,
                service_info['command'],
                service_info.get('health_check_url')
            )

    def cleanup(self):
        """Arrête tous les services."""
        self.running = False
        for name in list(self.services.keys()):
            self.stop_service(name)

    def get_status(self) -> Dict[str, str]:
        """Retourne le statut de tous les services."""
        status = {}
        for name, service in self.services.items():
            if service.get('process'):
                if service['process'].poll() is None:
                    status[name] = "🟢 Running"
                else:
                    status[name] = f"🔴 Stopped (code: {service['process'].returncode})"
            else:
                status[name] = "⚫ Not started"
        return status


# Instance globale du gestionnaire de services
service_manager = ServiceManager()


def setup_logging():
    """Configure le système de logging unifié."""

    # Format des logs
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Handler console avec couleurs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Formateur personnalisé avec couleurs (si disponible)
    try:
        from colorlog import ColoredFormatter
        colored_format = '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        console_handler.setFormatter(ColoredFormatter(
            colored_format,
            datefmt=date_format,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        ))
    except ImportError:
        console_handler.setFormatter(logging.Formatter(log_format, date_format))

    # Handler fichier
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    file_handler = logging.FileHandler(
        log_dir / f'moddy_{time.strftime("%Y%m%d")}.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Réduit le bruit de certains modules
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    return logging.getLogger('moddy')


async def start_services():
    """Démarre tous les services nécessaires avant le bot."""
    logger = logging.getLogger('moddy')

    # Vérifie si le webhook JSK doit être lancé
    if os.environ.get('ENABLE_JSK_WEBHOOK', 'true').lower() == 'true':
        # Vérifie si le module existe
        jsk_webhook_path = Path(__file__).parent / 'services' / 'jsk_webhook.py'

        if jsk_webhook_path.exists():
            # Lance le webhook JSK
            jsk_port = os.environ.get('JSK_WEBHOOK_PORT', '8100')
            success = service_manager.start_service(
                'JSK-Webhook',
                [sys.executable, '-m', 'services.jsk_webhook'],
                f'http://localhost:{jsk_port}/health'
            )

            if not success:
                logger.warning("⚠️ Le webhook JSK n'a pas pu démarrer, mais le bot continue")
        else:
            logger.info("ℹ️ Module webhook JSK non trouvé, skip")

    # Ici on peut ajouter d'autres services si besoin
    # service_manager.start_service('autre-service', [...])

    # Affiche le statut des services
    status = service_manager.get_status()
    if status:
        logger.info("📊 Statut des services:")
        for name, state in status.items():
            logger.info(f"  • {name}: {state}")


async def main():
    """Lance le bot et tous les services."""

    # Configure le logging
    logger = setup_logging()
    logger.info("🔧 Initialisation de Moddy...")

    try:
        # Démarre les services externes
        await start_services()

        # Import ici pour avoir les erreurs après le logging
        from bot import ModdyBot
        from config import TOKEN

        if not TOKEN:
            logger.error("❌ Token Discord manquant ! Vérifiez votre fichier .env")
            return

        # Crée le bot avec référence au service manager
        bot = ModdyBot()
        bot.service_manager = service_manager  # Ajoute la référence

        # Ajoute une commande pour gérer les services (pour les devs)
        @bot.command(name='services')
        async def services_command(ctx):
            """Affiche le statut des services (dev only)."""
            if not bot.is_developer(ctx.author.id):
                return

            status = service_manager.get_status()
            if not status:
                await ctx.send("📭 Aucun service actif")
                return

            embed = discord.Embed(
                title="📊 Statut des services",
                color=discord.Color.blue()
            )

            for name, state in status.items():
                embed.add_field(name=name, value=state, inline=False)

            await ctx.send(embed=embed)

        @bot.command(name='restart-service')
        async def restart_service_command(ctx, service_name: str):
            """Redémarre un service spécifique (dev only)."""
            if not bot.is_developer(ctx.author.id):
                return

            if service_name not in service_manager.services:
                await ctx.send(f"❌ Service '{service_name}' introuvable")
                return

            await ctx.send(f"🔄 Redémarrage de {service_name}...")
            service_manager.restart_service(service_name)
            await asyncio.sleep(3)

            status = service_manager.get_status()
            state = status.get(service_name, "Unknown")
            await ctx.send(f"Service {service_name}: {state}")

        # Lance le bot
        logger.info("🚀 Démarrage du bot Discord...")
        await bot.start(TOKEN)

    except ImportError as e:
        logger.error(f"❌ Erreur d'import : {e}")
        logger.error("Vérifiez que bot.py et config.py existent.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("⏹️ Arrêt demandé")
    except RuntimeError as e:
        if "Session is closed" in str(e):
            logger.info("🔄 Fermeture pour redémarrage")
        else:
            logger.error(f"❌ Erreur runtime : {e}")
    except Exception as e:
        logger.error(f"❌ Erreur fatale : {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Nettoie les services
        logger.info("🧹 Nettoyage des services...")
        service_manager.cleanup()


if __name__ == "__main__":
    try:
        # Importe discord pour la commande services
        import discord

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 À bientôt !")
    finally:
        # S'assure que tout est bien nettoyé
        service_manager.cleanup()