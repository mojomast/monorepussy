"""Tests for actuary.db — Database Storage."""

import os
import tempfile
import pytest
from actuary.db import (
    get_connection,
    insert_cve_cohort,
    insert_life_table_row,
    insert_dev_triangle_row,
    insert_credibility_params,
    insert_ibnr_reserve,
    insert_copula_model,
    query_life_table,
    query_dev_triangle,
)


@pytest.fixture
def db_conn():
    """Create a temporary database connection."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = get_connection(db_path)
    yield conn
    conn.close()
    os.unlink(db_path)


class TestGetConnection:
    """Tests for get_connection."""

    def test_creates_database(self, db_conn):
        assert db_conn is not None

    def test_tables_exist(self, db_conn):
        tables = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        assert "cve_cohorts" in table_names
        assert "life_tables" in table_names
        assert "development_triangles" in table_names
        assert "credibility_params" in table_names
        assert "ibnr_reserves" in table_names
        assert "copula_models" in table_names

    def test_indexes_exist(self, db_conn):
        indexes = db_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
        idx_names = [t[0] for t in indexes]
        assert "idx_cve_cohorts_cohort" in idx_names


class TestInsertCVECohort:
    """Tests for insert_cve_cohort."""

    def test_insert(self, db_conn):
        row_id = insert_cve_cohort(
            conn=db_conn,
            cohort_id="Q1-2025",
            cve_id="CVE-2025-0001",
            disclosure_date="2025-01-15",
            exploited=0,
        )
        assert row_id > 0

    def test_insert_exploited(self, db_conn):
        row_id = insert_cve_cohort(
            conn=db_conn,
            cohort_id="Q1-2025",
            cve_id="CVE-2025-0002",
            disclosure_date="2025-01-20",
            exploited=1,
            exploit_date="2025-02-01",
            severity=9.8,
        )
        assert row_id > 0

    def test_query_back(self, db_conn):
        insert_cve_cohort(
            conn=db_conn,
            cohort_id="Q1-2025",
            cve_id="CVE-2025-0003",
            disclosure_date="2025-01-15",
        )
        rows = db_conn.execute(
            "SELECT * FROM cve_cohorts WHERE cve_id = 'CVE-2025-0003'"
        ).fetchall()
        assert len(rows) == 1


class TestInsertLifeTableRow:
    """Tests for insert_life_table_row."""

    def test_insert(self, db_conn):
        row_id = insert_life_table_row(
            conn=db_conn,
            cohort_id="Q1-2025",
            age_days=0,
            l_v=847,
            d_v=12,
            q_v=0.0142,
            mu_v=0.0143,
            e_v=287.3,
        )
        assert row_id > 0

    def test_query_life_table(self, db_conn):
        insert_life_table_row(
            conn=db_conn,
            cohort_id="Q1-2025",
            age_days=0,
            l_v=847,
            d_v=12,
            q_v=0.0142,
            mu_v=0.0143,
            e_v=287.3,
        )
        insert_life_table_row(
            conn=db_conn,
            cohort_id="Q1-2025",
            age_days=30,
            l_v=812,
            d_v=28,
            q_v=0.0345,
            mu_v=0.0351,
            e_v=142.7,
        )
        rows = query_life_table(db_conn, "Q1-2025")
        assert len(rows) == 2
        assert rows[0]["age_days"] == 0


class TestInsertDevTriangle:
    """Tests for insert_dev_triangle_row."""

    def test_insert(self, db_conn):
        row_id = insert_dev_triangle_row(
            conn=db_conn,
            repo_id="my-repo",
            cohort_quarter="Q1-2024",
            dev_quarter=0,
            vuln_count=12,
        )
        assert row_id > 0

    def test_query_dev_triangle(self, db_conn):
        insert_dev_triangle_row(
            conn=db_conn,
            repo_id="my-repo",
            cohort_quarter="Q1-2024",
            dev_quarter=0,
            vuln_count=12,
        )
        rows = query_dev_triangle(db_conn, "my-repo")
        assert len(rows) == 1


class TestInsertCredibilityParams:
    """Tests for insert_credibility_params."""

    def test_insert(self, db_conn):
        row_id = insert_credibility_params(
            conn=db_conn,
            org_id="myorg",
            n_obs=52,
            epv=0.01,
            vhm=0.001,
            Z=0.95,
            internal_mean=0.05,
            population_mean=0.03,
            blended_mean=0.048,
        )
        assert row_id > 0


class TestInsertIBNRReserve:
    """Tests for insert_ibnr_reserve."""

    def test_insert(self, db_conn):
        row_id = insert_ibnr_reserve(
            conn=db_conn,
            repo_id="my-repo",
            method="bf",
            reported_count=3,
            prior_ultimate=20.0,
            bf_reserve=17.0,
            bf_ultimate=20.0,
        )
        assert row_id > 0


class TestInsertCopulaModel:
    """Tests for insert_copula_model."""

    def test_insert(self, db_conn):
        row_id = insert_copula_model(
            conn=db_conn,
            model_id="clayton_100",
            copula_type="clayton",
            n_assets=100,
            n_simulations=10000,
            var_level=0.99,
            var_value=500.0,
            tvar_value=750.0,
        )
        assert row_id > 0
