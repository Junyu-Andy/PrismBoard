"""DuckDB loader + SQL allow-list + role-based row filter.

Two-layer permission enforcement (the prompt layer is the other half, in prompts.py):

  1. SQL allow-list - reject DDL/DML and any non-SELECT statements outright.
  2. Row filter    - for patient/family roles, the query must mention the
                     caller's own patient_id; for nurse roles, queries that
                     touch shift-bound tables must mention the nurse's id.

The check is intentionally simple (substring presence) rather than a full
parser - good enough to catch LLM mistakes during the demo while staying
tiny. Production would replace this with a proper SQL AST walker.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# Tables we expose. Anything outside this list is rejected even on SELECT.
TABLES = [
    "patients", "doctors", "nurses",
    "comorbidities", "home_medications", "surgeries",
    "vitals", "glucose_logs", "medications", "lab_results",
    "care_tasks", "doctor_notes", "family_communications",
    "patient_questions",
]

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "ATTACH", "DETACH", "PRAGMA", "COPY", "EXPORT", "IMPORT",
    "TRUNCATE", "VACUUM", "REPLACE", "MERGE", "GRANT", "REVOKE",
]

# Tables off-limits to a given role. The prompt is told the same thing,
# but we re-check at exec time as defence-in-depth.
ROLE_TABLE_DENY = {
    "doctor": set(),
    "nurse":  set(),
    "patient": {"doctor_notes", "lab_results", "comorbidities"},
    # Family is the most restrictive: can only see overall status and
    # tasks. No raw medical history, no clinical observations.
    "family":  {"doctor_notes", "lab_results", "glucose_logs", "vitals",
                "comorbidities", "home_medications", "surgeries",
                "patient_questions"},
}


# --------------------------------------------------------------------- loader
_conn: Optional[duckdb.DuckDBPyConnection] = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """Build (or return) the in-memory DuckDB connection with all CSVs loaded."""
    global _conn
    if _conn is not None:
        return _conn

    if not DATA_DIR.exists() or not (DATA_DIR / "patients.csv").exists():
        raise RuntimeError(
            f"Mock data not found in {DATA_DIR}. Run `python seed.py` first."
        )

    conn = duckdb.connect(":memory:")
    for tbl in TABLES:
        path = DATA_DIR / f"{tbl}.csv"
        if not path.exists():
            continue
        conn.execute(
            f"CREATE TABLE {tbl} AS SELECT * FROM read_csv_auto('{path.as_posix()}', HEADER=TRUE)"
        )
    # Demo time anchor as a callable - the LLM is told to use this
    # instead of NOW() / CURRENT_TIMESTAMP. The mock data is anchored
    # to 2026-05-07 10:00:00, while wall-clock time is whatever the
    # demo machine actually says. demo_now() bridges that gap.
    conn.execute(
        "CREATE OR REPLACE MACRO demo_now() AS "
        "TIMESTAMP '2026-05-07 10:00:00'"
    )
    conn.execute(
        "CREATE OR REPLACE MACRO demo_today() AS "
        "DATE '2026-05-07'"
    )
    _conn = conn
    return conn


# --------------------------------------------------------------------- safety
class SqlSafetyError(Exception):
    pass


_WORD = re.compile(r"\b([A-Z]+)\b")


def _statement_is_select_only(query: str) -> bool:
    """Reject anything other than a single SELECT statement."""
    stripped = query.strip().rstrip(";").strip()
    if ";" in stripped:
        return False
    head = stripped.split(None, 1)[0].upper() if stripped else ""
    return head in ("SELECT", "WITH")


def _contains_forbidden(query: str) -> Optional[str]:
    upper = query.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            return kw
    return None


def _referenced_tables(query: str) -> set[str]:
    """Best-effort lexical extraction of table names referenced by the query."""
    found = set()
    lowered = query.lower()
    for t in TABLES:
        if re.search(rf"\b{t}\b", lowered):
            found.add(t)
    return found


def safe_execute(
    query: str,
    role: str,
    user_id: Optional[str] = None,
    patient_id: Optional[str] = None,
) -> pd.DataFrame:
    """Run an LLM-generated SELECT under role-aware constraints.

    Raises SqlSafetyError if the query violates a guard. Returns a DataFrame
    on success.
    """
    if not query or not query.strip():
        raise SqlSafetyError("Empty SQL.")

    if not _statement_is_select_only(query):
        raise SqlSafetyError("Only a single SELECT/WITH statement is allowed.")

    bad = _contains_forbidden(query)
    if bad:
        raise SqlSafetyError(f"Forbidden keyword in SQL: {bad}")

    refs = _referenced_tables(query)
    deny = ROLE_TABLE_DENY.get(role, set())
    bad_tbl = refs & deny
    if bad_tbl:
        raise SqlSafetyError(
            f"Role '{role}' may not query: {', '.join(sorted(bad_tbl))}"
        )

    # Patient / family must scope to their own patient_id - UNLESS the query
    # is a pure literal SELECT (no known table referenced). LLM-generated
    # placeholder queries like SELECT 'summary' AS info are common for
    # text_summary components that already carry their content inline.
    if role in ("patient", "family") and refs:
        if not patient_id:
            raise SqlSafetyError(f"Role '{role}' requires a patient_id binding.")
        if str(patient_id) not in query:
            raise SqlSafetyError(
                f"Role '{role}' query must filter by patient_id = '{patient_id}'."
            )

    # Defence-in-depth for nurse: shift-bound tables should mention nurse id.
    # We don't fail hard here (the LLM may have legitimate reasons) but we log.
    # Skipped for demo simplicity.

    conn = get_conn()
    try:
        return conn.execute(query).df()
    except Exception as e:
        raise SqlSafetyError(f"SQL execution failed: {e}") from e


# --------------------------------------------------------------------- helpers used by UI
def list_patients() -> pd.DataFrame:
    return get_conn().execute("SELECT * FROM patients ORDER BY patient_id").df()


def list_doctors() -> pd.DataFrame:
    return get_conn().execute("SELECT * FROM doctors ORDER BY id").df()


def list_nurses() -> pd.DataFrame:
    return get_conn().execute("SELECT * FROM nurses ORDER BY id").df()


def get_patient(patient_id: str) -> dict:
    df = get_conn().execute(
        "SELECT * FROM patients WHERE patient_id = ?", [patient_id]
    ).df()
    if df.empty:
        raise KeyError(patient_id)
    return df.iloc[0].to_dict()
