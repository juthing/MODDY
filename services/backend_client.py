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
