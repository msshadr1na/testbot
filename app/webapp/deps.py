from infrastructure.database import get_db_pool
from asyncpg import Pool

async def get_db():
    pool = await get_db_pool()
    try:
        yield pool
    finally:
        pass