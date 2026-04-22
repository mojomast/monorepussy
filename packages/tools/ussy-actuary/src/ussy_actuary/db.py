"""Database storage for actuarial models using SQLite."""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional


DEFAULT_DB_PATH = Path.home() / ".actuary" / "actuary.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cve_cohorts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cohort_id TEXT NOT NULL,
    cve_id TEXT NOT NULL,
    disclosure_date TEXT NOT NULL,
    exploited INTEGER DEFAULT 0,
    exploit_date TEXT,
    severity REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS life_tables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cohort_id TEXT NOT NULL,
    age_days INTEGER NOT NULL,
    l_v INTEGER NOT NULL,
    d_v INTEGER NOT NULL,
    q_v REAL NOT NULL,
    mu_v REAL NOT NULL,
    e_v REAL NOT NULL,
    q_v_graduated REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS development_triangles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id TEXT NOT NULL,
    cohort_quarter TEXT NOT NULL,
    dev_quarter INTEGER NOT NULL,
    vuln_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS credibility_params (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL,
    n_obs INTEGER NOT NULL,
    epv REAL NOT NULL,
    vhm REAL NOT NULL,
    Z REAL NOT NULL,
    internal_mean REAL,
    population_mean REAL,
    blended_mean REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ibnr_reserves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_id TEXT NOT NULL,
    method TEXT NOT NULL,
    reported_count INTEGER NOT NULL,
    prior_ultimate REAL NOT NULL,
    bf_reserve REAL NOT NULL,
    bf_ultimate REAL NOT NULL,
    cape_cod_prior REAL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS copula_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL,
    copula_type TEXT NOT NULL,
    n_assets INTEGER NOT NULL,
    n_simulations INTEGER NOT NULL,
    var_level REAL NOT NULL,
    var_value REAL,
    tvar_value REAL,
    params TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cve_cohorts_cohort ON cve_cohorts(cohort_id);
CREATE INDEX IF NOT EXISTS idx_life_tables_cohort ON life_tables(cohort_id);
CREATE INDEX IF NOT EXISTS idx_dev_tri_repo ON development_triangles(repo_id);
CREATE INDEX IF NOT EXISTS idx_cred_params_org ON credibility_params(org_id);
CREATE INDEX IF NOT EXISTS idx_ibnr_repo ON ibnr_reserves(repo_id);
CREATE INDEX IF NOT EXISTS idx_copula_model ON copula_models(model_id);
"""


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get a SQLite connection, creating the DB and schema if needed."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_cve_cohort(conn: sqlite3.Connection, cohort_id: str, cve_id: str,
                      disclosure_date: str, exploited: int = 0,
                      exploit_date: Optional[str] = None,
                      severity: Optional[float] = None) -> int:
    """Insert a CVE into a cohort."""
    cur = conn.execute(
        """INSERT INTO cve_cohorts
           (cohort_id, cve_id, disclosure_date, exploited, exploit_date, severity, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cohort_id, cve_id, disclosure_date, exploited, exploit_date, severity, _now())
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def insert_life_table_row(conn: sqlite3.Connection, cohort_id: str,
                          age_days: int, l_v: int, d_v: int,
                          q_v: float, mu_v: float, e_v: float,
                          q_v_graduated: Optional[float] = None) -> int:
    """Insert a single row into a life table."""
    cur = conn.execute(
        """INSERT INTO life_tables
           (cohort_id, age_days, l_v, d_v, q_v, mu_v, e_v, q_v_graduated, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (cohort_id, age_days, l_v, d_v, q_v, mu_v, e_v, q_v_graduated, _now())
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def insert_dev_triangle_row(conn: sqlite3.Connection, repo_id: str,
                            cohort_quarter: str, dev_quarter: int,
                            vuln_count: int) -> int:
    """Insert a row into the development triangle."""
    cur = conn.execute(
        """INSERT INTO development_triangles
           (repo_id, cohort_quarter, dev_quarter, vuln_count, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (repo_id, cohort_quarter, dev_quarter, vuln_count, _now())
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def insert_credibility_params(conn: sqlite3.Connection, org_id: str,
                              n_obs: int, epv: float, vhm: float,
                              Z: float, internal_mean: Optional[float] = None,
                              population_mean: Optional[float] = None,
                              blended_mean: Optional[float] = None) -> int:
    """Insert credibility parameters."""
    cur = conn.execute(
        """INSERT INTO credibility_params
           (org_id, n_obs, epv, vhm, Z, internal_mean, population_mean, blended_mean, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (org_id, n_obs, epv, vhm, Z, internal_mean, population_mean, blended_mean, _now())
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def insert_ibnr_reserve(conn: sqlite3.Connection, repo_id: str,
                        method: str, reported_count: int,
                        prior_ultimate: float, bf_reserve: float,
                        bf_ultimate: float,
                        cape_cod_prior: Optional[float] = None) -> int:
    """Insert an IBNR reserve estimate."""
    cur = conn.execute(
        """INSERT INTO ibnr_reserves
           (repo_id, method, reported_count, prior_ultimate, bf_reserve, bf_ultimate,
            cape_cod_prior, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (repo_id, method, reported_count, prior_ultimate, bf_reserve, bf_ultimate,
         cape_cod_prior, _now())
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def insert_copula_model(conn: sqlite3.Connection, model_id: str,
                        copula_type: str, n_assets: int,
                        n_simulations: int, var_level: float,
                        var_value: Optional[float] = None,
                        tvar_value: Optional[float] = None,
                        params: Optional[str] = None) -> int:
    """Insert a copula model result."""
    cur = conn.execute(
        """INSERT INTO copula_models
           (model_id, copula_type, n_assets, n_simulations, var_level,
            var_value, tvar_value, params, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (model_id, copula_type, n_assets, n_simulations, var_level,
         var_value, tvar_value, params, _now())
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def query_life_table(conn: sqlite3.Connection, cohort_id: str) -> list[dict[str, Any]]:
    """Query all rows of a life table for a cohort."""
    rows = conn.execute(
        "SELECT * FROM life_tables WHERE cohort_id = ? ORDER BY age_days",
        (cohort_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def query_dev_triangle(conn: sqlite3.Connection, repo_id: str) -> list[dict[str, Any]]:
    """Query the development triangle for a repo."""
    rows = conn.execute(
        "SELECT * FROM development_triangles WHERE repo_id = ? ORDER BY cohort_quarter, dev_quarter",
        (repo_id,)
    ).fetchall()
    return [dict(r) for r in rows]
