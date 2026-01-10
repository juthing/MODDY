"""
Client HTTP pour la communication Bot → Backend.
Permet au bot d'appeler les endpoints internes du backend.

Basé sur /documentation/internal-api.md
"""

import httpx
import logging
from typing import Optional, Dict, Any
import os

logger = logging.getLogger('moddy.services.backend_client')

# Configuration depuis les variables d'environnement
BACKEND_INTERNAL_URL = os.getenv(
    "BACKEND_INTERNAL_URL",
    "http://website-backend.railway.internal:8080"
)
INTERNAL_API_SECRET = os.getenv("INTERNAL_API_SECRET")

if not INTERNAL_API_SECRET:
    logger.warning("⚠️ INTERNAL_API_SECRET not set - backend communication will fail")


class BackendClientError(Exception):
    """Exception levée lors d'erreurs de communication avec le backend."""
    pass


class BackendClient:
    """
    Client HTTP pour communiquer avec le backend via Railway Private Network.

    Ce client permet au bot Discord d'appeler les endpoints internes du backend
    pour récupérer des informations utilisateur et notifier des événements.
    """

    def __init__(self, backend_url: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialise le client backend.

        Args:
            backend_url: URL interne du backend (défaut: BACKEND_INTERNAL_URL)
            api_secret: Secret partagé pour l'authentification (défaut: INTERNAL_API_SECRET)
        """
        self.backend_url = backend_url or BACKEND_INTERNAL_URL
        self.api_secret = api_secret or INTERNAL_API_SECRET

        if not self.api_secret:
            logger.error("❌ BackendClient initialized without INTERNAL_API_SECRET")
            raise BackendClientError("INTERNAL_API_SECRET is required")

        self.client = httpx.AsyncClient(
            base_url=self.backend_url,
            timeout=10.0,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Moddy-Bot/1.0",
            }
        )

        logger.info(f"🌐 BackendClient initialized with URL: {self.backend_url}")

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Génère les headers d'authentification.

        Returns:
            Dict avec le header Authorization
        """
        return {
            "Authorization": f"Bearer {self.api_secret}"
        }

    async def test_connection(self) -> bool:
        """
        Test la connexion au backend avec des logs de diagnostic détaillés.

        Cette méthode est utile pour diagnostiquer les problèmes de connectivité,
        particulièrement dans un environnement Railway avec Private Networking.

        Returns:
            True si la connexion est réussie, False sinon
        """
        logger.info("=" * 60)
        logger.info("🔍 BACKEND CONNECTION TEST")
        logger.info("=" * 60)
        logger.info(f"Backend URL: {self.backend_url}")
        logger.info(f"Timeout: {self.client.timeout.read}s")
        logger.info(f"API Secret configured: {'Yes' if self.api_secret else 'No'}")
        logger.info(f"API Secret length: {len(self.api_secret) if self.api_secret else 0} chars")
        logger.info("-" * 60)

        try:
            logger.info("Testing connection to backend...")
            response = await self.client.get(
                "/internal/health",
                headers=self._get_auth_headers()
            )

            logger.info(f"HTTP Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Backend status: {data.get('status', 'unknown')}")
                logger.info(f"✅ Backend message: {data.get('message', 'N/A')}")
                logger.info("=" * 60)
                logger.info("✅ BACKEND CONNECTION SUCCESSFUL")
                logger.info("=" * 60)
                return True

            elif response.status_code == 401 or response.status_code == 403:
                logger.error(f"❌ Authentication failed (HTTP {response.status_code})")
                logger.error("   Possible causes:")
                logger.error("   - INTERNAL_API_SECRET is incorrect")
                logger.error("   - INTERNAL_API_SECRET differs between bot and backend")
                logger.error("   - Missing Authorization header")
                logger.error("=" * 60)
                return False

            else:
                logger.error(f"❌ Unexpected HTTP status: {response.status_code}")
                logger.error(f"   Response: {response.text[:200]}")
                logger.error("=" * 60)
                return False

        except httpx.ConnectError as e:
            logger.error("❌ CONNECTION ERROR - Cannot connect to backend")
            logger.error(f"   Error: {e}")
            logger.error("   Possible causes:")
            logger.error("   - Backend service is not running")
            logger.error("   - Wrong service name in BACKEND_INTERNAL_URL")
            logger.error("   - Services not in the same Railway project")
            logger.error("   - Railway Private Network not enabled")
            logger.error(f"   Current URL: {self.backend_url}")
            logger.error("=" * 60)
            return False

        except httpx.TimeoutException as e:
            logger.error("❌ TIMEOUT ERROR - Backend did not respond in time")
            logger.error(f"   Error: {e}")
            logger.error("   Possible causes:")
            logger.error("   - Backend is starting up (check backend logs)")
            logger.error("   - Backend is overloaded")
            logger.error("   - Network issues between services")
            logger.error(f"   Timeout configured: {self.client.timeout.read}s")
            logger.error("=" * 60)
            return False

        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"❌ UNEXPECTED ERROR - {error_type}")
            logger.error(f"   Error: {e}")

            # Special handling for DNS errors
            if "Name or service not known" in str(e) or "nodename nor servname provided" in str(e):
                logger.error("   This is a DNS RESOLUTION error")
                logger.error("   Possible causes:")
                logger.error("   - Backend service name is incorrect")
                logger.error("   - Services are not in the same Railway project")
                logger.error("   - Railway Private Network DNS not working")
                logger.error("   Current service name in URL: " + self.backend_url.split("//")[1].split(":")[0])
                logger.error("   Expected format: <service-name>.railway.internal")

            logger.error("=" * 60)
            logger.error(f"Full error details:", exc_info=True)
            logger.error("=" * 60)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        Vérifie si le backend est accessible.

        Returns:
            Dict avec le statut de santé du backend

        Raises:
            BackendClientError: Si le backend n'est pas accessible
        """
        try:
            response = await self.client.get(
                "/internal/health",
                headers=self._get_auth_headers()
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"✅ Backend health check: {data.get('status', 'unknown')}")
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Backend health check failed: HTTP {e.response.status_code}")
            raise BackendClientError(f"Backend health check failed: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"❌ Backend health check failed: {e}")
            raise BackendClientError(f"Failed to connect to backend: {e}") from e
        except Exception as e:
            logger.error(f"❌ Backend health check failed: {e}", exc_info=True)
            raise BackendClientError(f"Unexpected error: {e}") from e

    async def get_user_info(self, discord_id: str) -> Dict[str, Any]:
        """
        Récupère les informations d'un utilisateur depuis le backend.

        Args:
            discord_id: Discord ID de l'utilisateur

        Returns:
            Dict avec les informations utilisateur (user_found, email, etc.)

        Raises:
            BackendClientError: Si la requête échoue
        """
        try:
            response = await self.client.post(
                "/internal/user/info",
                headers=self._get_auth_headers(),
                json={"discord_id": discord_id}
            )
            response.raise_for_status()
            data = response.json()

            if data.get("user_found"):
                logger.info(f"✅ User {discord_id} found in backend database")
            else:
                logger.info(f"⚠️ User {discord_id} not found in backend database")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to get user info: HTTP {e.response.status_code}")
            raise BackendClientError(f"Failed to get user info: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"❌ Failed to get user info: {e}")
            raise BackendClientError(f"Failed to connect to backend: {e}") from e
        except Exception as e:
            logger.error(f"❌ Failed to get user info: {e}", exc_info=True)
            raise BackendClientError(f"Unexpected error: {e}") from e

    async def notify_event(
        self,
        event_type: str,
        discord_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Notifie le backend d'un événement Discord.

        Args:
            event_type: Type d'événement (member_joined, member_left, etc.)
            discord_id: Discord ID concerné
            metadata: Métadonnées additionnelles (optionnel)

        Returns:
            Dict avec la réponse du backend

        Raises:
            BackendClientError: Si la requête échoue
        """
        try:
            payload = {
                "event_type": event_type,
                "discord_id": discord_id,
                "metadata": metadata or {}
            }

            response = await self.client.post(
                "/internal/event/notify",
                headers=self._get_auth_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            logger.info(f"✅ Event {event_type} notified to backend for user {discord_id}")
            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to notify event: HTTP {e.response.status_code}")
            raise BackendClientError(f"Failed to notify event: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"❌ Failed to notify event: {e}")
            raise BackendClientError(f"Failed to connect to backend: {e}") from e
        except Exception as e:
            logger.error(f"❌ Failed to notify event: {e}", exc_info=True)
            raise BackendClientError(f"Unexpected error: {e}") from e

    async def get_subscription_info(self, discord_id: str) -> Dict[str, Any]:
        """
        Récupère les informations d'abonnement Stripe d'un utilisateur.

        Args:
            discord_id: Discord ID de l'utilisateur

        Returns:
            Dict avec les informations d'abonnement (has_subscription, subscription, etc.)

        Raises:
            BackendClientError: Si la requête échoue
        """
        try:
            response = await self.client.post(
                "/internal/subscription/info",
                headers=self._get_auth_headers(),
                json={"discord_id": discord_id}
            )
            response.raise_for_status()
            data = response.json()

            if data.get("has_subscription"):
                logger.info(f"✅ Subscription found for user {discord_id}")
            else:
                logger.info(f"⚠️ No subscription found for user {discord_id}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to get subscription info: HTTP {e.response.status_code}")
            raise BackendClientError(f"Failed to get subscription info: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"❌ Failed to get subscription info: {e}")
            raise BackendClientError(f"Failed to connect to backend: {e}") from e
        except Exception as e:
            logger.error(f"❌ Failed to get subscription info: {e}", exc_info=True)
            raise BackendClientError(f"Unexpected error: {e}") from e

    async def get_subscription_invoices(
        self,
        discord_id: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Récupère la liste des factures Stripe d'un utilisateur.

        Args:
            discord_id: Discord ID de l'utilisateur
            limit: Nombre maximum de factures à récupérer (défaut: 10)

        Returns:
            Dict avec la liste des factures (invoices, success, message)

        Raises:
            BackendClientError: Si la requête échoue
        """
        try:
            response = await self.client.post(
                "/internal/subscription/invoices",
                headers=self._get_auth_headers(),
                json={
                    "discord_id": discord_id,
                    "limit": limit
                }
            )
            response.raise_for_status()
            data = response.json()

            invoice_count = len(data.get("invoices", []))
            logger.info(f"✅ Retrieved {invoice_count} invoice(s) for user {discord_id}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to get invoices: HTTP {e.response.status_code}")
            raise BackendClientError(f"Failed to get invoices: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"❌ Failed to get invoices: {e}")
            raise BackendClientError(f"Failed to connect to backend: {e}") from e
        except Exception as e:
            logger.error(f"❌ Failed to get invoices: {e}", exc_info=True)
            raise BackendClientError(f"Unexpected error: {e}") from e

    async def refund_payment(
        self,
        discord_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rembourse un paiement Stripe d'un utilisateur.

        Args:
            discord_id: Discord ID de l'utilisateur
            amount: Montant à rembourser en centimes (None = remboursement total)
            reason: Raison du remboursement (optionnel)

        Returns:
            Dict avec le résultat du remboursement (refunded, refund_id, amount_refunded)

        Raises:
            BackendClientError: Si la requête échoue
        """
        try:
            payload = {
                "discord_id": discord_id,
                "amount": amount,
                "reason": reason
            }

            response = await self.client.post(
                "/internal/subscription/refund",
                headers=self._get_auth_headers(),
                json=payload
            )
            response.raise_for_status()
            data = response.json()

            if data.get("refunded"):
                amount_euros = data.get("amount_refunded", 0) / 100
                logger.info(f"✅ Refund processed for user {discord_id}: {amount_euros}€")
            else:
                logger.warning(f"⚠️ Refund failed for user {discord_id}: {data.get('message')}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Failed to process refund: HTTP {e.response.status_code}")
            raise BackendClientError(f"Failed to process refund: {e}") from e
        except httpx.RequestError as e:
            logger.error(f"❌ Failed to process refund: {e}")
            raise BackendClientError(f"Failed to connect to backend: {e}") from e
        except Exception as e:
            logger.error(f"❌ Failed to process refund: {e}", exc_info=True)
            raise BackendClientError(f"Unexpected error: {e}") from e

    async def close(self):
        """Ferme le client HTTP."""
        await self.client.aclose()
        logger.info("🔌 BackendClient closed")


# Instance globale singleton
_backend_client: Optional[BackendClient] = None


def get_backend_client() -> BackendClient:
    """
    Retourne une instance singleton du BackendClient.

    Returns:
        Instance de BackendClient

    Raises:
        BackendClientError: Si le client ne peut pas être initialisé
    """
    global _backend_client

    if _backend_client is None:
        _backend_client = BackendClient()

    return _backend_client


async def close_backend_client():
    """Ferme l'instance globale du BackendClient."""
    global _backend_client

    if _backend_client is not None:
        await _backend_client.close()
        _backend_client = None
