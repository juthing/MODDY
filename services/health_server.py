
import asyncio
from aiohttp import web
import logging

logger = logging.getLogger('moddy.health_server')

async def health_check(request):
    """A simple health check endpoint."""
    return web.json_response({"status": "ok"})

class HealthServerWrapper:
    def __init__(self, runner):
        self.runner = runner

    async def stop(self):
        await self.runner.cleanup()
        logger.info("✅ Health server stopped.")

async def setup_health_server(bot):
    """Sets up and starts the aiohttp health server."""
    app = web.Application()
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    logger.info("🏥 Health check server listening on port 8080")
    return HealthServerWrapper(runner)
