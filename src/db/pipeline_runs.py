from psycopg2.extras import Json

from db.connection import get_connection

_JSONB_COLUMNS = {
    "document_text",
    "semantic_chunks",
    "requirements",
    "scenarios",
    "test_cases",
    "execution_report",
}

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id UUID PRIMARY KEY,

    project_name VARCHAR(255) NOT NULL,
    document_name VARCHAR(50),

    status VARCHAR(30) DEFAULT 'IN_PROGRESS',

    document_text JSONB,
    semantic_chunks JSONB,
    requirements JSONB,
    scenarios JSONB,
    test_cases JSONB,

    execution_report JSONB,

    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def ensure_schema() -> None:
    """Creates the pipeline_runs table if it doesn't already exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_TABLE_SQL)


def create_run(run_id: str, project_name: str, document_name: str | None) -> None:
    """Inserts a new IN_PROGRESS row for this pipeline run, if it doesn't already exist."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_runs (run_id, project_name, document_name, status)
                VALUES (%s, %s, %s, 'IN_PROGRESS')
                ON CONFLICT (run_id) DO NOTHING
                """,
                (run_id, project_name, document_name[:50] if document_name else None),
            )


def update_output(run_id: str, column: str, data) -> None:
    """Overwrites one JSONB output column (document_text, requirements, scenarios, ...)."""
    if column not in _JSONB_COLUMNS:
        raise ValueError(f"Unknown pipeline_runs output column: {column}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE pipeline_runs SET {column} = %s, updated_at = NOW() WHERE run_id = %s",
                (Json(data), run_id),
            )


def mark_status(run_id: str, status: str) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pipeline_runs SET status = %s, updated_at = NOW() WHERE run_id = %s",
                (status, run_id),
            )
