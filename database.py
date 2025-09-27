"""
database.py - Gestion de la base de données PostgreSQL pour Moddy
Corrige le problème de timezone lors de cache_guild_info
"""

import json
import asyncpg
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
from utils.logger import logger


class UpdateSource(Enum):
    """Sources possibles pour les mises à jour du cache"""
    BOT_JOIN = "bot_join"
    USER_PROFILE = "user_profile"
    API_CALL = "api_call"
    MANUAL = "manual"


class ModdyDatabase:
    def __init__(self, database_url: str = None):
        self.database_url = database_url or "postgresql://localhost/moddy"
        self.pool = None

    async def connect(self):
        """Établit la connexion avec la base de données"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            await self.init_tables()
            logger.info("✅ Pool de connexion BDD établi")
        except Exception as e:
            logger.error(f"❌ Erreur connexion BDD : {e}")
            raise

    async def close(self):
        """Ferme le pool de connexions"""
        if self.pool:
            await self.pool.close()
            logger.info("Pool de connexion BDD fermé")

    async def init_tables(self):
        """Initialise les tables si elles n'existent pas"""
        async with self.pool.acquire() as conn:
            # Table des erreurs
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
                    timestamp TIMESTAMP DEFAULT NOW(),
                    context JSONB DEFAULT '{}'::jsonb
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON errors(timestamp)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_errors_user ON errors(user_id)
            """)

            # Cache des serveurs
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds_cache (
                    guild_id BIGINT PRIMARY KEY,
                    name VARCHAR(100),
                    icon_url TEXT,
                    features TEXT[],
                    member_count INTEGER,
                    created_at TIMESTAMP,
                    last_updated TIMESTAMP DEFAULT NOW(),
                    update_source VARCHAR(50),
                    raw_data JSONB DEFAULT '{}'::jsonb
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_guilds_cache_updated ON guilds_cache(last_updated)
            """)

            # Table des utilisateurs (fonctionnelle)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    attributes JSONB DEFAULT '{}'::jsonb,
                    data JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_attributes ON users USING GIN (attributes)
            """)

            # Table des serveurs (fonctionnelle)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    guild_id BIGINT PRIMARY KEY,
                    attributes JSONB DEFAULT '{}'::jsonb,
                    data JSONB DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
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
                    changed_at TIMESTAMP DEFAULT NOW(),
                    reason TEXT
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_attribute_changes_entity 
                ON attribute_changes(entity_type, entity_id)
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
                json.dumps(error_data.get('context', {}))
            )

    async def get_error(self, error_code: str) -> Optional[Dict[str, Any]]:
        """Récupère une erreur par son code"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM errors WHERE error_code = $1",
                error_code
            )
            return dict(row) if row else None

    # ================ CACHE DES LOOKUPS ================

    async def cache_guild_info(self, guild_id: int, info: Dict[str, Any],
                               source: UpdateSource = UpdateSource.API_CALL):
        """Met en cache les informations d'un serveur avec gestion correcte des timezones"""
        # Crée une copie des données pour la sérialisation JSON
        serializable_info = info.copy()
        
        # Gère le datetime pour la colonne TIMESTAMP PostgreSQL
        created_at = info.get('created_at')
        if created_at:
            # Si c'est un datetime avec timezone, le convertit en naive (sans timezone)
            if hasattr(created_at, 'tzinfo') and created_at.tzinfo is not None:
                created_at = created_at.replace(tzinfo=None)
            
            # Pour le JSONB, on garde en format ISO string
            if isinstance(created_at, datetime):
                serializable_info['created_at'] = created_at.isoformat()

        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO guilds_cache (guild_id, name, icon_url, features, member_count,
                                          created_at, update_source, raw_data)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (guild_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    icon_url = EXCLUDED.icon_url,
                    features = EXCLUDED.features,
                    member_count = EXCLUDED.member_count,
                    last_updated = NOW(),
                    update_source = EXCLUDED.update_source,
                    raw_data = EXCLUDED.raw_data
            """,
                guild_id,
                info.get('name'),
                info.get('icon_url'),
                info.get('features', []),
                info.get('member_count'),
                created_at,  # Utilise le datetime converti (sans timezone)
                source.value,
                json.dumps(serializable_info)  # Utilise la copie sérialisable pour JSONB
            )

    async def get_cached_guild(self, guild_id: int, max_age_days: int = 7) -> Optional[Dict[str, Any]]:
        """Récupère les infos cachées d'un serveur si elles sont assez récentes"""
        async with self.pool.acquire() as conn:
            query = f"""
                SELECT * FROM guilds_cache 
                WHERE guild_id = $1 
                AND last_updated > NOW() - INTERVAL '{max_age_days} days'
            """
            row = await conn.fetchrow(query, guild_id)

            if row:
                data = dict(row)
                data['raw_data'] = json.loads(data['raw_data']) if data['raw_data'] else {}
                return data
            return None

    # ================ GESTION DES ATTRIBUTS ================

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

    async def set_attribute(self, entity_type: str, entity_id: int, attribute: str,
                           value: Any, changed_by: int, reason: str = None):
        """Définit un attribut pour un utilisateur ou serveur avec audit trail"""
        table = "users" if entity_type == "user" else "guilds"
        id_column = "user_id" if entity_type == "user" else "guild_id"

        async with self.pool.acquire() as conn:
            # Récupère l'ancienne valeur
            old_value_row = await conn.fetchrow(f"""
                SELECT attributes->>$1 as old_value FROM {table}
                WHERE {id_column} = $2
            """, attribute, entity_id)

            old_value = old_value_row['old_value'] if old_value_row else None

            # Met à jour l'attribut
            if value is False or value is None:
                # Supprime l'attribut si False ou None
                await conn.execute(f"""
                    UPDATE {table}
                    SET attributes = attributes - $1,
                        updated_at = NOW()
                    WHERE {id_column} = $2
                """, attribute, entity_id)
            else:
                # Ajoute/modifie l'attribut
                await conn.execute(f"""
                    UPDATE {table}
                    SET attributes = jsonb_set(attributes, $1, $2, true),
                        updated_at = NOW()
                    WHERE {id_column} = $3
                """, 
                    f'{{{attribute}}}',
                    json.dumps(value),
                    entity_id
                )

            # Enregistre le changement dans l'audit trail
            await conn.execute("""
                INSERT INTO attribute_changes (entity_type, entity_id, attribute_name,
                                              old_value, new_value, changed_by, reason)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                entity_type,
                entity_id,
                attribute,
                str(old_value) if old_value is not None else None,
                str(value) if value not in [False, None] else None,
                changed_by,
                reason
            )

    async def update_user_data(self, user_id: int, path: str, value: Any):
        """Met à jour une donnée spécifique dans le JSON data d'un utilisateur"""
        # Convertit le chemin en format PostgreSQL
        path_parts = path.split('.')
        json_path = '{' + ','.join(path_parts) + '}'

        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE users 
                SET data = jsonb_set(data, $1, $2, true),
                    updated_at = NOW()
                WHERE user_id = $3
            """,
                json_path,
                json.dumps(value),
                user_id
            )

    async def update_guild_data(self, guild_id: int, path: str, value: Any):
        """Met à jour une donnée spécifique dans le JSON data d'un serveur"""
        path_parts = path.split('.')
        json_path = '{' + ','.join(path_parts) + '}'
        
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE guilds 
                SET data = jsonb_set(data, $1, $2, true),
                    updated_at = NOW()
                WHERE guild_id = $3
            """,
                json_path,
                json.dumps(value),
                guild_id
            )

    # ================ REQUÊTES UTILES ================

    async def get_users_with_attribute(self, attribute: str, value: Any = None) -> List[int]:
        """Récupère tous les utilisateurs ayant un attribut spécifique"""
        async with self.pool.acquire() as conn:
            if value is None:
                rows = await conn.fetch("""
                    SELECT user_id FROM users 
                    WHERE attributes ? $1
                """, attribute)
            else:
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

            # Compte les enregistrements
            for table in ['errors', 'users', 'guilds', 'guilds_cache']:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                stats[table] = count

            # Statistiques spécifiques
            stats['beta_users'] = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE attributes ? 'BETA'
            """)

            stats['premium_users'] = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE attributes ? 'PREMIUM'
            """)

            stats['blacklisted_users'] = await conn.fetchval("""
                SELECT COUNT(*) FROM users 
                WHERE attributes ? 'BLACKLISTED'
            """)

            return stats


# Instance globale (sera initialisée dans bot.py)
db = None


async def setup_database(database_url: str = None) -> ModdyDatabase:
    """Initialise et retourne l'instance de base de données"""
    global db
    db = ModdyDatabase(database_url)
    await db.connect()
    return db
