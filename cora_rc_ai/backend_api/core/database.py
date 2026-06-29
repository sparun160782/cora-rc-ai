"""
Database session management using asyncpg connection pool.
"""
import asyncpg
import logging
from pgvector.asyncpg import register_vector
from cora_rc_ai.backend_api.core.config import settings

logger = logging.getLogger(__name__)
_pool: asyncpg.Pool | None = None


async def _init_connection(connection: asyncpg.Connection) -> None:
    await register_vector(connection)


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=2,
            max_size=20,
            command_timeout=60,
            init=_init_connection,
        )
        logger.info("PostgreSQL connection pool created.")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL connection pool closed.")
