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
        await conn.execute(text("""
            CREATE TABLE run_history (
                id VARCHAR(32) PRIMARY KEY,
                task_id VARCHAR(32),
                run_index INTEGER DEFAULT 1,
                status VARCHAR(32) DEFAULT 'completed',
                created_at DATETIME
            )
        """))
        await conn.execute(text("""
            CREATE TABLE metrics (
                id VARCHAR(32) PRIMARY KEY,
                task_id VARCHAR(32),
                source_count INTEGER DEFAULT 0,
                claim_count INTEGER DEFAULT 0,
                evidence_coverage_rate FLOAT DEFAULT 0.0,
                manual_correction_count INTEGER DEFAULT 0,
                calculated_at DATETIME
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
        run_history_columns = {
            row[1]
            for row in (await conn.execute(text("PRAGMA table_info(run_history)"))).fetchall()
        }
        metrics_columns = {
            row[1]
            for row in (await conn.execute(text("PRAGMA table_info(metrics)"))).fetchall()
        }

    await engine.dispose()

    assert "our_product_notes" in task_columns
    assert "focus_areas" in task_columns
    assert "target_website" in task_columns
    assert "human_review_required" in task_columns
    assert "manual_correction_count" in task_columns
    assert "last_qa_feedback" in task_columns
    assert "last_handoff" in task_columns
    assert "last_curation_summary" in task_columns
    assert "reliability_score" in source_columns
    assert "included_in_analysis" in source_columns
    assert "curation_reason" in source_columns
    assert "curation_tags" in source_columns
    assert "curated_excerpt" in source_columns
    assert "quality_score" in metrics_columns
    assert "quality_breakdown" in metrics_columns
    assert "quality_score" in run_history_columns
    assert "quality_breakdown" in run_history_columns
    assert "curation_summary" in run_history_columns
    assert "constraints" in run_history_columns
    assert "analysis" in run_history_columns
    assert "report" in run_history_columns
    assert "trace_events" in run_history_columns
