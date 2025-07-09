"""
Système d'authentification à deux facteurs pour les commandes sensibles
Utilise Google Authenticator (TOTP)
"""

import pyotp
import qrcode
import io
import discord
from typing import Optional, Dict
import json
from pathlib import Path


class TwoFactorAuth:
    """Gère l'authentification 2FA pour les développeurs"""

    def __init__(self):
        self.secrets_file = Path("data/2fa_secrets.json")
        self.secrets_file.parent.mkdir(exist_ok=True)
        self.secrets = self.load_secrets()
        self.pending_verifications = {}  # user_id: command_callback

    def load_secrets(self) -> Dict[int, str]:
        """Charge les secrets 2FA depuis le fichier"""
        if self.secrets_file.exists():
            with open(self.secrets_file, 'r') as f:
                data = json.load(f)
                # Convertit les clés string en int
                return {int(k): v for k, v in data.items()}
        return {}

    def save_secrets(self):
        """Sauvegarde les secrets 2FA"""
        with open(self.secrets_file, 'w') as f:
            json.dump(self.secrets, f, indent=2)

    def generate_secret(self, user_id: int) -> str:
        """Génère un nouveau secret pour un utilisateur"""
        secret = pyotp.random_base32()
        self.secrets[user_id] = secret
        self.save_secrets()
        return secret

    def get_secret(self, user_id: int) -> Optional[str]:
        """Récupère le secret d'un utilisateur"""
        return self.secrets.get(user_id)

    def has_2fa(self, user_id: int) -> bool:
        """Vérifie si un utilisateur a activé la 2FA"""
        return user_id in self.secrets

    def verify_code(self, user_id: int, code: str) -> bool:
        """Vérifie un code 2FA"""
        secret = self.get_secret(user_id)
        if not secret:
            return False

        totp = pyotp.TOTP(secret)
        # Accepte les codes avec une tolérance de 30 secondes
        return totp.verify(code, valid_window=1)

    def generate_qr_code(self, user: discord.User, secret: str) -> discord.File:
        """Génère un QR code pour configurer Google Authenticator"""
        # URI pour Google Authenticator
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=f"{user.name}#{user.discriminator}",
            issuer_name="Moddy Bot"
        )

        # Génère le QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(totp_uri)
        qr.make(fit=True)

        # Crée l'image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convertit en bytes pour Discord
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        return discord.File(buffer, filename="2fa_qr_code.png")

    def disable_2fa(self, user_id: int):
        """Désactive la 2FA pour un utilisateur"""
        if user_id in self.secrets:
            del self.secrets[user_id]
            self.save_secrets()

    def add_pending_verification(self, user_id: int, callback):
        """Ajoute une vérification en attente"""
        self.pending_verifications[user_id] = callback

    def get_pending_verification(self, user_id: int):
        """Récupère et supprime une vérification en attente"""
        return self.pending_verifications.pop(user_id, None)


# Instance globale
two_factor = TwoFactorAuth()