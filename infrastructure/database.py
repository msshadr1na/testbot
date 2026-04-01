import asyncpg
from config import db_url

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(db_url)
    return _pool

async def close_db_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None