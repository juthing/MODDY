"""
Gestionnaire de base de données PostgreSQL pour Moddy
Base de données locale sur le VPS
"""

import asyncpg
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Union
from enum import Enum
import logging

logger = logging.getLogger('moddy.database')


class ModdyDatabase:
    """Gestionnaire principal de la base de données"""

    def __init__(self, database_url: str = None):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = database_url or "postgresql://moddy:password@localhost/moddy"

    async def connect(self):
        """Establishes the database connection"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={
                    'application_name': 'Moddy Bot',
                    'jit': 'off'
                }
            )
            logger.info("✅ PostgreSQL database connected")

            # Initialize tables
            await self._init_tables()

        except Exception as e:
            logger.error(f"❌ PostgreSQL connection error: {e}")
            raise

    async def close(self):
        """Closes the connection"""
        if self.pool:
            await self.pool.close()

    async def _init_tables(self):
        """Creates tables if they do not exist"""
        async with self.pool.acquire() as conn:
            # Errors table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    error_code VARCHAR(8) PRIMARY KEY,
                    error_type VARCHAR(100),
                    message TEXT,
                    file_source VARCHAR(255),
                    line_number INTEGER,
                    traceback TEXT,
                    user_id BIGINT,
                    guild_id BIGINT,
                    command VARCHAR(100),
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    context JSONB DEFAULT '{}'::jsonb
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_user ON errors(user_id)
            """)

            # Table des utilisateurs
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    attributes JSONB DEFAULT '{}'::jsonb,
                    data JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_attributes ON users USING GIN (attributes)
            """)

            # Table des serveurs
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id BIGINT PRIMARY KEY,
                    attributes JSONB DEFAULT '{}'::jsonb,
                    data JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_guilds_attributes ON guilds USING GIN (attributes)
            """)

            # Table d'audit des attributs
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS attribute_changes (
                    id SERIAL PRIMARY KEY,
                    entity_type VARCHAR(10) CHECK (entity_type IN ('user', 'guild')),
                    entity_id BIGINT NOT NULL,
                    attribute_name VARCHAR(50),
                    old_value TEXT,
                    new_value TEXT,
                    changed_by BIGINT,
                    changed_at TIMESTAMPTZ DEFAULT NOW(),
                    reason TEXT
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_attribute_changes_entity
                ON attribute_changes(entity_type, entity_id)
            """)

            # Table des permissions staff
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS staff_permissions (
                    user_id BIGINT PRIMARY KEY,
                    roles JSONB DEFAULT '[]'::jsonb,
                    denied_commands JSONB DEFAULT '[]'::jsonb,
                    role_permissions JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    created_by BIGINT,
                    updated_by BIGINT
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_staff_permissions_roles
                ON staff_permissions USING GIN (roles)
            """)

            # Table des rappels
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    guild_id BIGINT,
                    channel_id BIGINT,
                    message TEXT NOT NULL,
                    remind_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMPTZ,
                    failed BOOLEAN DEFAULT FALSE,
                    send_in_channel BOOLEAN DEFAULT FALSE
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders(remind_at)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reminders_sent ON reminders(sent)
            """)

            # Table des messages sauvegardés
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_messages (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    message_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    guild_id BIGINT,
                    author_id BIGINT NOT NULL,
                    author_username TEXT,
                    content TEXT,
                    attachments JSONB DEFAULT '[]'::jsonb,
                    embeds JSONB DEFAULT '[]'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL,
                    saved_at TIMESTAMPTZ DEFAULT NOW(),
                    message_url TEXT,
                    note TEXT,
                    raw_message_data JSONB DEFAULT '{}'::jsonb
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_messages_user_id ON saved_messages(user_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_messages_saved_at ON saved_messages(saved_at)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_saved_messages_author_id ON saved_messages(author_id)
            """)

            # Migration: Add role_permissions column if it doesn't exist
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'staff_permissions'
                        AND column_name = 'role_permissions'
                    ) THEN
                        ALTER TABLE staff_permissions
                        ADD COLUMN role_permissions JSONB DEFAULT '{}'::jsonb;
                    END IF;
                END $$;
            """)

            # Migration: Add author_username and raw_message_data to saved_messages if they don't exist
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'saved_messages'
                        AND column_name = 'author_username'
                    ) THEN
                        ALTER TABLE saved_messages
                        ADD COLUMN author_username TEXT;
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'saved_messages'
                        AND column_name = 'raw_message_data'
                    ) THEN
                        ALTER TABLE saved_messages
                        ADD COLUMN raw_message_data JSONB DEFAULT '{}'::jsonb;
                    END IF;
                END $$;
            """)

            logger.info("✅ Tables initialisées")

    # ================ GESTION DES ERREURS ================

    async def log_error(self, error_code: str, error_data: Dict[str, Any]):
        """Enregistre une erreur dans la base de données"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO errors (error_code, error_type, message, file_source,
                                    line_number, traceback, user_id, guild_id,
                                    command, context)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                error_code,
                error_data.get('type'),
                error_data.get('message'),
                error_data.get('file'),
                error_data.get('line'),
                error_data.get('traceback'),
                error_data.get('user_id'),
                error_data.get('guild_id'),
                error_data.get('command'),
                error_data.get('context', {})
            )

    async def get_error(self, error_code: str) -> Optional[Dict[str, Any]]:
        """Récupère une erreur par son code"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM errors WHERE error_code = $1",
                error_code
            )
            if not row:
                return None

            error_data = dict(row)
            # Compatibility: if context is a string, load it as JSON
            if isinstance(error_data.get('context'), str):
                try:
                    error_data['context'] = json.loads(error_data['context'])
                except (json.JSONDecodeError, TypeError):
                    error_data['context'] = {} # Fallback to empty dict

            return error_data

    # ================ GESTION DES UTILISATEURS ET SERVEURS ================

    async def get_user(self, user_id: int) -> Dict[str, Any]:
        """Récupère ou crée un utilisateur"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )

            if not row:
                # Crée l'utilisateur s'il n'existe pas, gère la concurrence
                await conn.execute(
                    "INSERT INTO users (user_id) VALUES ($1) ON CONFLICT (user_id) DO NOTHING",
                    user_id
                )
                # Re-fetch pour être sûr d'avoir les données
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE user_id = $1",
                    user_id
                )

            return {
                'user_id': row['user_id'],
                'attributes': json.loads(row['attributes']) if row['attributes'] else {},
                'data': json.loads(row['data']) if row['data'] else {},
                'created_at': row.get('created_at', datetime.now(timezone.utc)),
                'updated_at': row.get('updated_at', datetime.now(timezone.utc))
            }

    async def get_guild(self, guild_id: int) -> Dict[str, Any]:
        """Récupère ou crée un serveur"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM guilds WHERE guild_id = $1",
                guild_id
            )

            if not row:
                # Crée le serveur s'il n'existe pas, gère la concurrence
                await conn.execute(
                    "INSERT INTO guilds (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING",
                    guild_id
                )
                # Re-fetch pour être sûr d'avoir les données
                row = await conn.fetchrow(
                    "SELECT * FROM guilds WHERE guild_id = $1",
                    guild_id
                )

            return {
                'guild_id': row['guild_id'],
                'attributes': json.loads(row['attributes']) if row['attributes'] else {},
                'data': json.loads(row['data']) if row['data'] else {},
                'created_at': row.get('created_at', datetime.now(timezone.utc)),
                'updated_at': row.get('updated_at', datetime.now(timezone.utc))
            }

    # ================ GESTION DES ATTRIBUTS ================

    async def set_attribute(self, entity_type: str, entity_id: int,
                            attribute: str, value: Optional[Union[str, bool]],
                            changed_by: int, reason: str = None):
        """Définit un attribut pour un utilisateur ou serveur

        Pour les attributs booléens : si value est True, on stocke juste l'attribut
        Pour les attributs avec valeur : on stocke la valeur (ex: LANG=FR)
        Si value est None, on supprime l'attribut
        """
        table = 'users' if entity_type == 'user' else 'guilds'

        async with self.pool.acquire() as conn:
            # S'assure que l'entité existe d'abord
            if entity_type == 'user':
                await self.get_user(entity_id)
            else:
                await self.get_guild(entity_id)

            # Récupère l'ancienne valeur
            row = await conn.fetchrow(
                f"SELECT attributes FROM {table} WHERE {entity_type}_id = $1",
                entity_id
            )

            # Gère proprement le cas où attributes est None
            if row and row['attributes']:
                old_attributes = json.loads(row['attributes'])
            else:
                old_attributes = {}

            old_value = old_attributes.get(attribute)

            # Met à jour l'attribut selon le nouveau système
            if value is None:
                # Supprime l'attribut
                if attribute in old_attributes:
                    del old_attributes[attribute]
            elif value is True:
                # Pour les booléens True, on stocke juste la clé sans valeur
                old_attributes[attribute] = True
            elif value is False:
                # Pour les booléens False, on supprime l'attribut
                if attribute in old_attributes:
                    del old_attributes[attribute]
            else:
                # Pour les autres valeurs (string, int, etc), on stocke la valeur
                old_attributes[attribute] = value

            # Sauvegarde
            await conn.execute(f"""
                UPDATE {table} 
                SET attributes = $1::jsonb, updated_at = NOW()
                WHERE {entity_type}_id = $2
            """, json.dumps(old_attributes), entity_id)

            # Log le changement
            await conn.execute("""
                INSERT INTO attribute_changes (entity_type, entity_id, attribute_name,
                                               old_value, new_value, changed_by, reason)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                entity_type, entity_id, attribute,
                str(old_value) if old_value is not None else None,
                str(value) if value is not None else None,
                changed_by, reason
            )

    async def has_attribute(self, entity_type: str, entity_id: int, attribute: str) -> bool:
        """Vérifie si une entité a un attribut spécifique"""
        entity = await self.get_user(entity_id) if entity_type == 'user' else await self.get_guild(entity_id)
        return attribute in entity['attributes']

    async def get_attribute(self, entity_type: str, entity_id: int, attribute: str) -> Any:
        """Récupère la valeur d'un attribut

        Retourne True pour les attributs booléens présents
        Retourne la valeur pour les attributs avec valeur
        Retourne None si l'attribut n'existe pas
        """
        entity = await self.get_user(entity_id) if entity_type == 'user' else await self.get_guild(entity_id)
        return entity['attributes'].get(attribute)

    # ================ GESTION DE LA DATA ================

    async def update_user_data(self, user_id: int, path: str, value: Any):
        """Met à jour une partie spécifique de la data utilisateur"""
        async with self.pool.acquire() as conn:
            # Utilise jsonb_set pour mettre à jour un chemin spécifique
            path_parts = path.split('.')
            # Use UPSERT to ensure the user exists and update the data
            await conn.execute("""
                INSERT INTO users (user_id, data, created_at, updated_at)
                VALUES ($1, jsonb_set('{}'::jsonb, $2, $3, true), NOW(), NOW())
                ON CONFLICT (user_id)
                DO UPDATE SET
                    data = jsonb_set(users.data, $2, $3, true),
                    updated_at = NOW()
            """,
                user_id,
                path_parts,
                json.dumps(value)
            )

    async def update_guild_data(self, guild_id: int, path: str, value: Any):
        """Met à jour une partie spécifique de la data serveur"""
        async with self.pool.acquire() as conn:
            path_parts = path.split('.')
            # Use UPSERT to ensure the guild exists and update the data
            await conn.execute("""
                INSERT INTO guilds (guild_id, data, created_at, updated_at)
                VALUES ($1, jsonb_set('{}'::jsonb, $2, $3, true), NOW(), NOW())
                ON CONFLICT (guild_id)
                DO UPDATE SET
                    data = jsonb_set(guilds.data, $2, $3, true),
                    updated_at = NOW()
            """,
                guild_id,
                path_parts,
                json.dumps(value)
            )

    # ================ REQUÊTES UTILES ================

    async def get_users_with_attribute(self, attribute: str, value: Any = None) -> List[int]:
        """Récupère tous les utilisateurs ayant un attribut spécifique

        Si value est None, cherche juste la présence de l'attribut
        Si value est fournie, cherche cette valeur spécifique
        """
        async with self.pool.acquire() as conn:
            if value is None:
                # Cherche juste la présence de l'attribut
                rows = await conn.fetch("""
                    SELECT user_id FROM users 
                    WHERE attributes ? $1
                """, attribute)
            else:
                # Cherche une valeur spécifique
                rows = await conn.fetch("""
                    SELECT user_id FROM users 
                    WHERE attributes @> $1
                """, json.dumps({attribute: value}))

            return [row['user_id'] for row in rows]

    async def get_guilds_with_attribute(self, attribute: str, value: Any = None) -> List[int]:
        """Récupère tous les serveurs ayant un attribut spécifique"""
        async with self.pool.acquire() as conn:
            if value is None:
                rows = await conn.fetch("""
                    SELECT guild_id FROM guilds 
                    WHERE attributes ? $1
                """, attribute)
            else:
                rows = await conn.fetch("""
                    SELECT guild_id FROM guilds 
                    WHERE attributes @> $1
                """, json.dumps({attribute: value}))

            return [row['guild_id'] for row in rows]

    async def cleanup_old_errors(self, days: int = 30):
        """Nettoie les erreurs de plus de X jours"""
        async with self.pool.acquire() as conn:
            deleted = await conn.execute(f"""
                DELETE FROM errors 
                WHERE timestamp < NOW() - INTERVAL '{days} days'
            """)
            return deleted

    async def get_stats(self) -> Dict[str, int]:
        """Récupère des statistiques sur la base de données"""
        async with self.pool.acquire() as conn:
            stats = {}

            # Compte les enregistrements (sans guilds_cache)
            for table in ['errors', 'users', 'guilds']:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                stats[table] = count

            # Statistiques spécifiques avec le nouveau système
            # Compte les utilisateurs ayant l'attribut BETA
            stats['beta_users'] = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE attributes ? 'BETA'
            """)

            # Compte les utilisateurs ayant l'attribut PREMIUM
            stats['premium_users'] = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE attributes ? 'PREMIUM'
            """)

            # Compte les utilisateurs blacklistés
            stats['blacklisted_users'] = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE attributes ? 'BLACKLISTED'
            """)

            return stats

    # ================ GESTION DES PERMISSIONS STAFF ================

    async def get_staff_permissions(self, user_id: int) -> Dict[str, Any]:
        """Récupère les permissions staff d'un utilisateur"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM staff_permissions WHERE user_id = $1",
                user_id
            )

            if not row:
                return {
                    'user_id': user_id,
                    'roles': [],
                    'denied_commands': [],
                    'role_permissions': {},
                    'created_at': None,
                    'updated_at': None
                }

            return {
                'user_id': row['user_id'],
                'roles': json.loads(row['roles']) if row['roles'] else [],
                'denied_commands': json.loads(row['denied_commands']) if row['denied_commands'] else [],
                'role_permissions': json.loads(row['role_permissions']) if row.get('role_permissions') else {},
                'created_at': row.get('created_at'),
                'updated_at': row.get('updated_at'),
                'created_by': row.get('created_by'),
                'updated_by': row.get('updated_by')
            }

    async def set_staff_roles(self, user_id: int, roles: List[str], updated_by: int):
        """Définit les rôles staff d'un utilisateur"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO staff_permissions (user_id, roles, updated_by, created_by)
                VALUES ($1, $2, $3, $3)
                ON CONFLICT (user_id)
                DO UPDATE SET roles = $2, updated_by = $3, updated_at = NOW()
            """, user_id, json.dumps(roles), updated_by)

            # Set TEAM attribute automatically
            await self.set_attribute('user', user_id, 'TEAM', True, updated_by, "Added to staff team")

    async def add_staff_role(self, user_id: int, role: str, updated_by: int):
        """Ajoute un rôle staff à un utilisateur"""
        perms = await self.get_staff_permissions(user_id)
        roles = perms['roles']

        if role not in roles:
            roles.append(role)
            await self.set_staff_roles(user_id, roles, updated_by)

    async def remove_staff_role(self, user_id: int, role: str, updated_by: int):
        """Retire un rôle staff d'un utilisateur"""
        perms = await self.get_staff_permissions(user_id)
        roles = perms['roles']

        if role in roles:
            roles.remove(role)
            await self.set_staff_roles(user_id, roles, updated_by)

            # If no more roles, remove TEAM attribute
            if not roles:
                await self.set_attribute('user', user_id, 'TEAM', None, updated_by, "Removed from staff team")

    async def set_denied_commands(self, user_id: int, denied_commands: List[str], updated_by: int):
        """Définit les commandes interdites pour un utilisateur"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO staff_permissions (user_id, denied_commands, updated_by, created_by)
                VALUES ($1, $2, $3, $3)
                ON CONFLICT (user_id)
                DO UPDATE SET denied_commands = $2, updated_by = $3, updated_at = NOW()
            """, user_id, json.dumps(denied_commands), updated_by)

    async def add_denied_command(self, user_id: int, command: str, updated_by: int):
        """Ajoute une commande à la liste des commandes interdites"""
        perms = await self.get_staff_permissions(user_id)
        denied = perms['denied_commands']

        if command not in denied:
            denied.append(command)
            await self.set_denied_commands(user_id, denied, updated_by)

    async def remove_denied_command(self, user_id: int, command: str, updated_by: int):
        """Retire une commande de la liste des commandes interdites"""
        perms = await self.get_staff_permissions(user_id)
        denied = perms['denied_commands']

        if command in denied:
            denied.remove(command)
            await self.set_denied_commands(user_id, denied, updated_by)

    async def remove_staff_permissions(self, user_id: int):
        """Supprime complètement les permissions staff d'un utilisateur"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM staff_permissions WHERE user_id = $1",
                user_id
            )

    async def get_all_staff_members(self) -> List[Dict[str, Any]]:
        """Récupère tous les membres du staff"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM staff_permissions ORDER BY created_at"
            )

            return [{
                'user_id': row['user_id'],
                'roles': json.loads(row['roles']) if row['roles'] else [],
                'denied_commands': json.loads(row['denied_commands']) if row['denied_commands'] else [],
                'role_permissions': json.loads(row['role_permissions']) if row.get('role_permissions') else {},
                'created_at': row.get('created_at'),
                'updated_at': row.get('updated_at')
            } for row in rows]

    async def set_role_permissions(self, user_id: int, role: str, permissions: List[str], updated_by: int):
        """Définit les permissions pour un rôle spécifique d'un utilisateur"""
        perms = await self.get_staff_permissions(user_id)
        role_perms = perms['role_permissions']
        role_perms[role] = permissions

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO staff_permissions (user_id, role_permissions, updated_by, created_by)
                VALUES ($1, $2, $3, $3)
                ON CONFLICT (user_id)
                DO UPDATE SET role_permissions = $2, updated_by = $3, updated_at = NOW()
            """, user_id, json.dumps(role_perms), updated_by)

    async def get_role_permissions(self, user_id: int, role: str) -> List[str]:
        """Récupère les permissions d'un rôle spécifique"""
        perms = await self.get_staff_permissions(user_id)
        return perms['role_permissions'].get(role, [])

    # ================ GESTION DES RAPPELS ================

    async def create_reminder(self, user_id: int, message: str, remind_at: datetime,
                              guild_id: int = None, channel_id: int = None,
                              send_in_channel: bool = False) -> int:
        """Crée un nouveau rappel et retourne son ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO reminders (user_id, guild_id, channel_id, message, remind_at, send_in_channel)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, user_id, guild_id, channel_id, message, remind_at, send_in_channel)
            return row['id']

    async def get_reminder(self, reminder_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un rappel par son ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM reminders WHERE id = $1",
                reminder_id
            )
            if not row:
                return None
            return dict(row)

    async def get_user_reminders(self, user_id: int, include_sent: bool = False) -> List[Dict[str, Any]]:
        """Récupère tous les rappels d'un utilisateur"""
        async with self.pool.acquire() as conn:
            if include_sent:
                rows = await conn.fetch(
                    "SELECT * FROM reminders WHERE user_id = $1 ORDER BY remind_at ASC",
                    user_id
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM reminders WHERE user_id = $1 AND sent = FALSE ORDER BY remind_at ASC",
                    user_id
                )
            return [dict(row) for row in rows]

    async def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """Récupère tous les rappels non envoyés dont l'heure est passée"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM reminders
                WHERE sent = FALSE AND remind_at <= NOW()
                ORDER BY remind_at ASC
            """)
            return [dict(row) for row in rows]

    async def get_upcoming_reminders(self, limit_minutes: int = 5) -> List[Dict[str, Any]]:
        """Récupère les rappels à envoyer dans les prochaines minutes"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM reminders
                WHERE sent = FALSE AND remind_at <= NOW() + INTERVAL '%s minutes'
                ORDER BY remind_at ASC
            """ % limit_minutes)
            return [dict(row) for row in rows]

    async def mark_reminder_sent(self, reminder_id: int, failed: bool = False):
        """Marque un rappel comme envoyé"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE reminders
                SET sent = TRUE, sent_at = NOW(), failed = $2
                WHERE id = $1
            """, reminder_id, failed)

    async def delete_reminder(self, reminder_id: int, user_id: int) -> bool:
        """Supprime un rappel (vérifie que l'utilisateur est le propriétaire)"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM reminders WHERE id = $1 AND user_id = $2",
                reminder_id, user_id
            )
            return result == "DELETE 1"

    async def update_reminder(self, reminder_id: int, user_id: int,
                              message: str = None, remind_at: datetime = None) -> bool:
        """Met à jour un rappel"""
        async with self.pool.acquire() as conn:
            # Vérifie d'abord que le rappel appartient à l'utilisateur
            existing = await conn.fetchrow(
                "SELECT * FROM reminders WHERE id = $1 AND user_id = $2",
                reminder_id, user_id
            )
            if not existing:
                return False

            if message is not None:
                await conn.execute(
                    "UPDATE reminders SET message = $1 WHERE id = $2",
                    message, reminder_id
                )
            if remind_at is not None:
                await conn.execute(
                    "UPDATE reminders SET remind_at = $1 WHERE id = $2",
                    remind_at, reminder_id
                )
            return True

    async def get_user_past_reminders(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Récupère les rappels passés d'un utilisateur"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM reminders
                WHERE user_id = $1 AND sent = TRUE
                ORDER BY sent_at DESC
                LIMIT $2
            """, user_id, limit)
            return [dict(row) for row in rows]

    async def cleanup_old_reminders(self, days: int = 30):
        """Nettoie les rappels envoyés de plus de X jours"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM reminders
                WHERE sent = TRUE AND sent_at < NOW() - INTERVAL '%s days'
            """ % days)

    # ================ GESTION DES MESSAGES SAUVEGARDÉS ================

    async def save_message(self, user_id: int, message_id: int, channel_id: int,
                          guild_id: int, author_id: int, author_username: str, content: str,
                          attachments: List[Dict], embeds: List[Dict],
                          created_at: datetime, message_url: str, raw_message_data: Dict,
                          note: str = None) -> int:
        """Sauvegarde un message dans la bibliothèque de l'utilisateur"""
        async with self.pool.acquire() as conn:
            # Vérifie si le message n'est pas déjà sauvegardé
            existing = await conn.fetchrow(
                "SELECT id FROM saved_messages WHERE user_id = $1 AND message_id = $2",
                user_id, message_id
            )
            if existing:
                return existing['id']

            # Sauvegarde le message
            row = await conn.fetchrow("""
                INSERT INTO saved_messages (
                    user_id, message_id, channel_id, guild_id, author_id, author_username,
                    content, attachments, embeds, created_at, message_url, note, raw_message_data
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
            """, user_id, message_id, channel_id, guild_id, author_id, author_username,
                content, json.dumps(attachments), json.dumps(embeds),
                created_at, message_url, note, json.dumps(raw_message_data))
            return row['id']

    async def get_saved_messages(self, user_id: int, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Récupère les messages sauvegardés d'un utilisateur"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM saved_messages
                WHERE user_id = $1
                ORDER BY saved_at DESC
                LIMIT $2 OFFSET $3
            """, user_id, limit, offset)

            result = []
            for row in rows:
                msg_dict = dict(row)
                # Parse JSON fields
                msg_dict['attachments'] = json.loads(msg_dict['attachments']) if msg_dict['attachments'] else []
                msg_dict['embeds'] = json.loads(msg_dict['embeds']) if msg_dict['embeds'] else []
                msg_dict['raw_message_data'] = json.loads(msg_dict['raw_message_data']) if msg_dict.get('raw_message_data') else {}
                result.append(msg_dict)
            return result

    async def get_saved_message(self, saved_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un message sauvegardé spécifique"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM saved_messages WHERE id = $1 AND user_id = $2",
                saved_id, user_id
            )
            if not row:
                return None

            msg_dict = dict(row)
            msg_dict['attachments'] = json.loads(msg_dict['attachments']) if msg_dict['attachments'] else []
            msg_dict['embeds'] = json.loads(msg_dict['embeds']) if msg_dict['embeds'] else []
            msg_dict['raw_message_data'] = json.loads(msg_dict['raw_message_data']) if msg_dict.get('raw_message_data') else {}
            return msg_dict

    async def delete_saved_message(self, saved_id: int, user_id: int) -> bool:
        """Supprime un message sauvegardé"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM saved_messages WHERE id = $1 AND user_id = $2",
                saved_id, user_id
            )
            return result == "DELETE 1"

    async def update_saved_message_note(self, saved_id: int, user_id: int, note: str) -> bool:
        """Met à jour la note d'un message sauvegardé"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE saved_messages SET note = $1 WHERE id = $2 AND user_id = $3",
                note, saved_id, user_id
            )
            return result == "UPDATE 1"

    async def count_saved_messages(self, user_id: int) -> int:
        """Compte le nombre de messages sauvegardés par un utilisateur"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM saved_messages WHERE user_id = $1",
                user_id
            )
            return row['count']

    async def search_saved_messages(self, user_id: int, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Recherche dans les messages sauvegardés"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM saved_messages
                WHERE user_id = $1 AND (
                    content ILIKE $2 OR
                    note ILIKE $2
                )
                ORDER BY saved_at DESC
                LIMIT $3
            """, user_id, f"%{query}%", limit)

            result = []
            for row in rows:
                msg_dict = dict(row)
                msg_dict['attachments'] = json.loads(msg_dict['attachments']) if msg_dict['attachments'] else []
                msg_dict['embeds'] = json.loads(msg_dict['embeds']) if msg_dict['embeds'] else []
                result.append(msg_dict)
            return result


# Instance globale (sera initialisée dans bot.py)
db = None


async def setup_database(database_url: str = None) -> ModdyDatabase:
    """Initialise et retourne l'instance de base de données"""
    global db
    db = ModdyDatabase(database_url)
    await db.connect()
    return db