from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.session import _migrate_add_columns


async def test_migrate_add_columns_repairs_legacy_sqlite_schema(tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE tasks (
                id VARCHAR(32) PRIMARY KEY,
                industry VARCHAR(255) DEFAULT '',
                target_product VARCHAR(255) DEFAULT '',
                competitors JSON,
                status VARCHAR(32) DEFAULT 'pending',
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        await conn.execute(text("""
            CREATE TABLE sources (
                id VARCHAR(32) PRIMARY KEY,
                task_id VARCHAR(32),
                type VARCHAR(32) DEFAULT 'url',
                url TEXT,
                title VARCHAR(512) DEFAULT '',
                content_snippet TEXT DEFAULT '',
                fetched_at DATETIME
            )
        """))

        await _migrate_add_columns(conn)

        task_columns = {
            row[1]
            for row in (await conn.execute(text("PRAGMA table_info(tasks)"))).fetchall()
        }
        source_columns = {
            row[1]
            for row in (await conn.execute(text("PRAGMA table_info(sources)"))).fetchall()
        }

    await engine.dispose()

    assert "our_product_notes" in task_columns
    assert "reliability_score" in source_columns
