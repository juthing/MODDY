"""
Serveur de health check pour Moddy
Expose des endpoints pour Instatus et la surveillance du bot
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from aiohttp import web
from aiohttp.web_log import AccessLogger
import psutil
import os

logger = logging.getLogger('moddy.health')


class InstatusFilterAccessLogger(AccessLogger):
    def log(self, request, response, time):
        if 'InstatusBot' in request.headers.get('User-Agent', ''):
            return

        super().log(request, response, time)


class HealthServer:
    """Serveur HTTP pour les health checks"""

    def __init__(self, bot=None, port: int = 8080):
        self.bot = bot
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.start_time = datetime.now(timezone.utc)
        self.setup_routes()

    def setup_routes(self):
        """Configure les routes du serveur"""
        self.app.router.add_get('/health', self.global_health)
        self.app.router.add_get('/health/bot', self.bot_health)
        self.app.router.add_get('/health/cogs', self.all_cogs_health)
        self.app.router.add_get('/health/cog/{cog_name}', self.cog_health)
        self.app.router.add_get('/health/database', self.database_health)
        self.app.router.add_get('/health/metrics', self.metrics)
        self.app.router.add_get('/', self.index)

    async def start(self):
        """Démarre le serveur"""
        self.runner = web.AppRunner(self.app, access_log_class=InstatusFilterAccessLogger)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        logger.info(f"🌐 Health server started on port {self.port}")

    async def stop(self):
        """Arrête le serveur"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("🔌 Health server stopped")

    def get_uptime(self) -> float:
        """Retourne l'uptime en secondes"""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    def get_system_metrics(self) -> Dict[str, Any]:
        """Collecte les métriques système"""
        try:
            process = psutil.Process(os.getpid())
            return {
                "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "threads": process.num_threads(),
                "connections": len(process.connections()),
            }
        except:
            return {
                "memory_mb": 0,
                "cpu_percent": 0,
                "threads": 0,
                "connections": 0
            }

    async def index(self, request: web.Request) -> web.Response:
        """Page d'accueil avec liste des endpoints"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Moddy Health Check</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #0d1117;
                    color: #c9d1d9;
                }
                h1 {
                    color: #58a6ff;
                    border-bottom: 1px solid #30363d;
                    padding-bottom: 10px;
                }
                .endpoint {
                    background: #161b22;
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 6px;
                    border: 1px solid #30363d;
                }
                .endpoint code {
                    background: #0d1117;
                    padding: 2px 6px;
                    border-radius: 3px;
                    color: #79c0ff;
                }
                .description {
                    color: #8b949e;
                    margin-top: 5px;
                }
                .badge {
                    display: inline-block;
                    padding: 2px 8px;
                    border-radius: 3px;
                    font-size: 12px;
                    margin-left: 10px;
                }
                .badge.public {
                    background: #3fb950;
                    color: #0d1117;
                }
            </style>
        </head>
        <body>
            <h1>🤖 Moddy Health Check API</h1>
            <p>Endpoints de surveillance pour Instatus et monitoring</p>

            <div class="endpoint">
                <code>GET /health</code>
                <span class="badge public">PUBLIC</span>
                <div class="description">État global du bot (endpoint principal pour Instatus)</div>
            </div>

            <div class="endpoint">
                <code>GET /health/bot</code>
                <div class="description">État détaillé du bot Discord</div>
            </div>

            <div class="endpoint">
                <code>GET /health/cogs</code>
                <div class="description">État de tous les cogs</div>
            </div>

            <div class="endpoint">
                <code>GET /health/cog/{cog_name}</code>
                <div class="description">État d'un cog spécifique</div>
            </div>

            <div class="endpoint">
                <code>GET /health/database</code>
                <div class="description">État de la connexion base de données</div>
            </div>

            <div class="endpoint">
                <code>GET /health/metrics</code>
                <div class="description">Métriques détaillées du système</div>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def global_health(self, request: web.Request) -> web.Response:
        """
        Endpoint principal pour Instatus
        Retourne l'état global du bot
        """
        try:
            # État par défaut
            status = "operational"
            issues = []

            # Vérification du bot
            if not self.bot or not self.bot.is_ready():
                status = "major_outage"
                issues.append("Bot disconnected")
            else:
                # Vérification de la latence
                latency_ms = round(self.bot.latency * 1000) if self.bot.latency != float('inf') else -1
                if latency_ms > 500:
                    status = "partial_outage"
                    issues.append(f"High latency: {latency_ms}ms")
                elif latency_ms > 200:
                    status = "degraded_performance"
                    issues.append(f"Elevated latency: {latency_ms}ms")

                # Vérification des cogs critiques
                critical_cogs = ["ErrorTracker", "BlacklistCheck"]
                for cog_name in critical_cogs:
                    if not self.bot.get_cog(cog_name):
                        if status == "operational":
                            status = "partial_outage"
                        issues.append(f"Critical cog missing: {cog_name}")

                # Vérification de la base de données
                if hasattr(self.bot, 'db') and self.bot.db:
                    try:
                        async with self.bot.db.pool.acquire() as conn:
                            await asyncio.wait_for(
                                conn.fetchval("SELECT 1"),
                                timeout=2.0
                            )
                    except:
                        if status == "operational":
                            status = "degraded_performance"
                        issues.append("Database connectivity issues")

            # Construction de la réponse
            response = {
                "status": status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime": round(self.get_uptime()),
                "version": "1.0.0"
            }

            if issues:
                response["issues"] = issues

            # Code HTTP selon le statut
            http_status = 200
            if status == "major_outage":
                http_status = 503
            elif status in ["partial_outage", "degraded_performance"]:
                http_status = 503

            return web.json_response(response, status=http_status)

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response({
                "status": "major_outage",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status=503)

    async def bot_health(self, request: web.Request) -> web.Response:
        """État détaillé du bot Discord"""
        try:
            if not self.bot:
                return web.json_response({
                    "status": "offline",
                    "error": "Bot not initialized"
                }, status=503)

            is_ready = self.bot.is_ready()
            latency_ms = round(self.bot.latency * 1000) if is_ready and self.bot.latency != float('inf') else -1

            response = {
                "status": "online" if is_ready else "offline",
                "ready": is_ready,
                "latency_ms": latency_ms,
                "guilds": len(self.bot.guilds) if is_ready else 0,
                "users": len(self.bot.users) if is_ready else 0,
                "cogs_loaded": len(self.bot.cogs),
                "commands": len(self.bot.commands),
                "uptime": round(self.get_uptime()),
                "metrics": self.get_system_metrics(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            if hasattr(self.bot, 'user') and self.bot.user:
                response["bot_user"] = {
                    "id": str(self.bot.user.id),
                    "name": self.bot.user.name,
                    "discriminator": self.bot.user.discriminator
                }

            return web.json_response(
                response,
                status=200 if is_ready else 503
            )

        except Exception as e:
            logger.error(f"Bot health check error: {e}")
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=503)

    async def all_cogs_health(self, request: web.Request) -> web.Response:
        """État de tous les cogs"""
        try:
            if not self.bot:
                return web.json_response({
                    "error": "Bot not initialized"
                }, status=503)

            cogs_status = {}

            for cog_name, cog in self.bot.cogs.items():
                cog_info = {
                    "loaded": True,
                    "type": "staff" if "staff" in cog.__module__ else "public",
                    "commands": len([c for c in cog.get_commands() if not c.hidden]),
                    "listeners": len(cog.get_listeners()),
                    "healthy": True
                }

                # Test de santé spécifique pour certains cogs
                if cog_name == "ErrorTracker":
                    cog_info["errors_cached"] = len(cog.error_cache) if hasattr(cog, 'error_cache') else 0
                elif cog_name == "Translate" and hasattr(cog, 'deepl_api_key'):
                    cog_info["api_configured"] = bool(cog.deepl_api_key)

                # Vérification des tasks
                for attr_name in dir(cog):
                    attr = getattr(cog, attr_name)
                    if hasattr(attr, '__class__') and attr.__class__.__name__ == 'Loop':
                        cog_info[f"task_{attr_name}"] = {
                            "running": attr.is_running(),
                            "failed": attr.failed(),
                            "current_loop": attr.current_loop
                        }
                        if attr.failed():
                            cog_info["healthy"] = False

                cogs_status[cog_name] = cog_info

            # Calcul du statut global
            total_cogs = len(cogs_status)
            healthy_cogs = sum(1 for c in cogs_status.values() if c.get("healthy", True))

            response = {
                "total": total_cogs,
                "healthy": healthy_cogs,
                "unhealthy": total_cogs - healthy_cogs,
                "cogs": cogs_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return web.json_response(
                response,
                status=200 if healthy_cogs == total_cogs else 503
            )

        except Exception as e:
            logger.error(f"Cogs health check error: {e}")
            return web.json_response({
                "error": str(e)
            }, status=503)

    async def cog_health(self, request: web.Request) -> web.Response:
        """État d'un cog spécifique"""
        try:
            cog_name = request.match_info.get('cog_name')

            if not self.bot:
                return web.json_response({
                    "error": "Bot not initialized"
                }, status=503)

            cog = self.bot.get_cog(cog_name)

            if not cog:
                return web.json_response({
                    "error": f"Cog '{cog_name}' not found",
                    "available_cogs": list(self.bot.cogs.keys())
                }, status=404)

            response = {
                "name": cog_name,
                "loaded": True,
                "module": cog.__module__,
                "type": "staff" if "staff" in cog.__module__ else "public",
                "commands": [cmd.name for cmd in cog.get_commands() if not cmd.hidden],
                "listeners": [l[0] for l in cog.get_listeners()],
                "healthy": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Métriques spécifiques par cog
            if cog_name == "ErrorTracker" and hasattr(cog, 'error_cache'):
                response["metrics"] = {
                    "errors_cached": len(cog.error_cache),
                    "error_channel_id": cog.error_channel_id
                }
            elif cog_name == "Translate":
                response["metrics"] = {
                    "api_configured": bool(getattr(cog, 'deepl_api_key', None)),
                    "usage_tracking": len(getattr(cog, 'user_usage', {}))
                }

            # Vérification des tasks
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__class__') and attr.__class__.__name__ == 'Loop':
                    if "tasks" not in response:
                        response["tasks"] = {}
                    response["tasks"][attr_name] = {
                        "running": attr.is_running(),
                        "failed": attr.failed(),
                        "current_loop": attr.current_loop
                    }
                    if attr.failed():
                        response["healthy"] = False

            return web.json_response(
                response,
                status=200 if response["healthy"] else 503
            )

        except Exception as e:
            logger.error(f"Cog health check error: {e}")
            return web.json_response({
                "error": str(e)
            }, status=503)

    async def database_health(self, request: web.Request) -> web.Response:
        """État de la base de données"""
        try:
            if not self.bot or not hasattr(self.bot, 'db') or not self.bot.db:
                return web.json_response({
                    "status": "disconnected",
                    "error": "Database not configured"
                }, status=503)

            try:
                # Test de connexion
                async with self.bot.db.pool.acquire() as conn:
                    result = await asyncio.wait_for(
                        conn.fetchval("SELECT 1"),
                        timeout=2.0
                    )

                # Récupération des stats
                stats = await self.bot.db.get_stats()

                # Info sur le pool
                pool = self.bot.db.pool
                pool_info = {
                    "size": pool.get_size(),
                    "free_size": pool.get_idle_size(),
                    "min_size": pool.get_min_size(),
                    "max_size": pool.get_max_size()
                }

                response = {
                    "status": "connected",
                    "pool": pool_info,
                    "stats": stats,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                return web.json_response(response)

            except asyncio.TimeoutError:
                return web.json_response({
                    "status": "timeout",
                    "error": "Database query timeout"
                }, status=503)
            except Exception as e:
                return web.json_response({
                    "status": "error",
                    "error": str(e)
                }, status=503)

        except Exception as e:
            logger.error(f"Database health check error: {e}")
            return web.json_response({
                "status": "error",
                "error": str(e)
            }, status=503)

    async def metrics(self, request: web.Request) -> web.Response:
        """Métriques détaillées du système"""
        try:
            metrics = {
                "system": self.get_system_metrics(),
                "uptime": round(self.get_uptime()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            if self.bot and self.bot.is_ready():
                metrics["bot"] = {
                    "guilds": len(self.bot.guilds),
                    "users": len(self.bot.users),
                    "commands_count": len(self.bot.commands),
                    "cogs_count": len(self.bot.cogs),
                    "latency_ms": round(self.bot.latency * 1000) if self.bot.latency != float('inf') else -1
                }

                # Métriques par cog si disponibles
                if hasattr(self.bot, 'command_stats'):
                    metrics["commands_usage"] = self.bot.command_stats

            return web.json_response(metrics)

        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return web.json_response({
                "error": str(e)
            }, status=503)


async def setup_health_server(bot, port: int = None) -> HealthServer:
    """Initialise et démarre le serveur de health check"""
    port = port or int(os.environ.get('HEALTH_PORT', '8080'))
    server = HealthServer(bot, port)
    await server.start()
    return server