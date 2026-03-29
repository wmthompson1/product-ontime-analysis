#!/usr/bin/env python3
"""
SQLMesh Masking Policy Test Suite
==================================
Implements tests for the two-key governance pattern described in pod908.md:

  Policy artifact  → masking_matrix.csv
  Attestation      → certificate/receiving_certificate.json

Rules under test (Part II – Section 4):
  Rule 1  Masking matrix is the source of truth for PII policy.
  Rule 2  Certificate must be updated whenever the matrix changes.
  Rule 3  SQLMesh refuses ingestion when the certificate is invalid / stale.
  Rule 4  Backfills are only triggered after certificate alignment.

All tables and seeds are synthetic (Faker).  No real SQL Server connection needed.
"""

import hashlib
import json
import os
import io
import csv
import copy
import pytest
from faker import Faker

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
MATRIX_PATH = os.path.join(REPO_ROOT, "masking_matrix.csv")
CERT_PATH = os.path.join(REPO_ROOT, "certificate", "receiving_certificate.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sha256_hex(value: str) -> str:
    """Deterministic SHA-256 hash used by every masking rule in the matrix."""
    return hashlib.sha256(value.encode()).hexdigest()


def load_matrix(path: str = MATRIX_PATH) -> list[dict]:
    """Load masking_matrix.csv into a list of row dicts."""
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def load_certificate(path: str = CERT_PATH) -> dict:
    """Load the receiving certificate JSON."""
    with open(path) as fh:
        return json.load(fh)


def matrix_dag_nos(matrix: list[dict]) -> list[str]:
    return [row["dag_no"] for row in matrix]


def cert_dag_nos(cert: dict) -> list[str]:
    return [entry["dag_no"] for entry in cert["masking_matrix_ref"]["dag_lines"]]


# ---------------------------------------------------------------------------
# Mini SQLMesh simulator
# Implements the four enforcement rules from pod908.md §4.
# ---------------------------------------------------------------------------

class SQLMeshSimulator:
    """Lightweight stand-in that enforces masking policy without a real DB."""

    def __init__(self, matrix: list[dict], certificate: dict):
        self.matrix = matrix
        self.certificate = certificate
        self._ingestion_blocked = False
        self._backfill_log: list[str] = []

    # ---- Rule 3 gate -------------------------------------------------------
    def validate_certificate(self) -> tuple[bool, str]:
        """
        Returns (ok, reason).
        Fails when:
          - status != "certified"
          - cert dag_lines don't align with matrix dag_no set
        """
        if self.certificate.get("status") != "certified":
            return False, "Certificate status is not 'certified'."

        matrix_nos = set(matrix_dag_nos(self.matrix))
        cert_nos = set(cert_dag_nos(self.certificate))
        if matrix_nos != cert_nos:
            return False, (
                f"DAG line mismatch. Matrix={sorted(matrix_nos)} "
                f"Certificate={sorted(cert_nos)}"
            )
        return True, "OK"

    # ---- Rule 4 gate -------------------------------------------------------
    def plan_and_backfill(self, changed_dag_nos: list[str]) -> list[str]:
        """
        Returns the ordered list of models that must be rebuilt.
        Only runs if the certificate is valid (Rule 3).
        """
        ok, reason = self.validate_certificate()
        if not ok:
            self._ingestion_blocked = True
            raise RuntimeError(f"Ingestion halted – invalid certificate: {reason}")

        rebuild_order: list[str] = []
        # Collect the changed rows plus every row whose parent is in the changed set
        changed = set(changed_dag_nos)
        for row in self.matrix:
            if row["dag_no"] in changed:
                rebuild_order.append(f"hashed.{row['table_name']}")
            if row.get("parent_table") and any(
                r["table_name"] == row["parent_table"] and r["dag_no"] in changed
                for r in self.matrix
            ):
                rebuild_order.append(f"masked_dims.{row['table_name']}")

        self._backfill_log.extend(rebuild_order)
        return rebuild_order

    # ---- Apply masking ------------------------------------------------------
    def apply_masking(self, table_name: str, rows: list[dict]) -> list[dict]:
        """Apply masking rules for the given table to a list of row dicts."""
        rules = {
            row["column_name"]: row["masking_rule"]
            for row in self.matrix
            if row["table_name"] == table_name and row["status"] == "active"
        }
        masked = []
        for row in rows:
            out = dict(row)
            for col, rule in rules.items():
                if col in out:
                    out[col] = sha256_hex(str(out[col]))
            masked.append(out)
        return masked


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fake():
    f = Faker()
    Faker.seed(42)
    return f


@pytest.fixture(scope="module")
def vendor_seed(fake):
    """20 synthetic vendor rows (faux pre-stage data)."""
    return [
        {
            "id": fake.uuid4(),
            "name": fake.company(),
            "contact_email": fake.company_email(),
            "country": fake.country_code(),
        }
        for _ in range(20)
    ]


@pytest.fixture(scope="module")
def part_seed(fake, vendor_seed):
    """30 synthetic part rows referencing vendor IDs."""
    return [
        {
            "part_no": fake.bothify("PT-####"),
            "description": fake.catch_phrase(),
            "pref_vendor": fake.random_element([v["id"] for v in vendor_seed]),
            "unit_cost": round(fake.pyfloat(min_value=1, max_value=500), 2),
            "buyer_email": fake.email(),
        }
        for _ in range(30)
    ]


@pytest.fixture(scope="module")
def matrix():
    return load_matrix()


@pytest.fixture(scope="module")
def certificate():
    return load_certificate()


@pytest.fixture(scope="module")
def engine(matrix, certificate):
    return SQLMeshSimulator(matrix, certificate)


# ---------------------------------------------------------------------------
# Rule 1 – Masking matrix is the source of truth
# ---------------------------------------------------------------------------

class TestRule1MaskingMatrix:
    """Matrix file exists, is well-formed, and defines every required column."""

    REQUIRED_COLUMNS = {
        "dag_no", "table_name", "column_name",
        "parent_table", "parent_column",
        "masking_rule", "masking_type", "pre_stage_server", "status",
    }

    def test_matrix_file_exists(self):
        assert os.path.isfile(MATRIX_PATH), "masking_matrix.csv is missing from repo root."

    def test_matrix_has_required_columns(self, matrix):
        columns = set(matrix[0].keys())
        missing = self.REQUIRED_COLUMNS - columns
        assert not missing, f"Matrix is missing columns: {missing}"

    def test_matrix_has_vendor_root(self, matrix):
        roots = [r for r in matrix if r["dag_no"] == "1.1"]
        assert roots, "DAG root 1.1 (vendor) not found in matrix."
        assert roots[0]["table_name"] == "vendor"
        assert roots[0]["parent_table"] == ""

    def test_matrix_vendor_column_is_id(self, matrix):
        row = next(r for r in matrix if r["dag_no"] == "1.1")
        assert row["column_name"] == "id"

    def test_matrix_part_references_vendor(self, matrix):
        row = next((r for r in matrix if r["dag_no"] == "1.2"), None)
        assert row is not None, "DAG 1.2 (part) not in matrix."
        assert row["parent_table"] == "vendor"

    def test_all_active_rows_have_masking_rule(self, matrix):
        for row in matrix:
            if row["status"] == "active":
                assert row["masking_rule"], (
                    f"Active row {row['dag_no']} has no masking_rule."
                )

    def test_masking_rules_use_sha256(self, matrix):
        for row in matrix:
            if row["status"] == "active":
                assert "hash_sha256" in row["masking_rule"], (
                    f"Row {row['dag_no']} masking_rule is not SHA-256."
                )


# ---------------------------------------------------------------------------
# Rule 2 – Certificate reflects the matrix
# ---------------------------------------------------------------------------

class TestRule2CertificateAttestation:

    def test_certificate_file_exists(self):
        assert os.path.isfile(CERT_PATH)

    def test_certificate_has_required_fields(self, certificate):
        for field in ("receiving_id", "receiver_id_agent", "trust_boundary",
                      "status", "certificate_version", "masking_matrix_ref"):
            assert field in certificate, f"Certificate missing field: {field}"

    def test_certificate_dag_lines_match_matrix(self, matrix, certificate):
        matrix_nos = sorted(matrix_dag_nos(matrix))
        cert_nos = sorted(cert_dag_nos(certificate))
        assert matrix_nos == cert_nos, (
            f"Matrix dag_nos {matrix_nos} != certificate dag_lines {cert_nos}"
        )

    def test_certificate_status_is_certified(self, certificate):
        assert certificate["status"] == "certified"

    def test_certificate_version_is_set(self, certificate):
        assert certificate.get("certificate_version"), "certificate_version must be non-empty."

    def test_new_matrix_row_invalidates_stale_certificate(self, matrix, certificate):
        """Simulate adding DAG 1.3 to the matrix without updating the cert."""
        stale_cert = copy.deepcopy(certificate)
        augmented_matrix = matrix + [{
            "dag_no": "1.3",
            "table_name": "part",
            "column_name": "buyer_email",
            "parent_table": "vendor",
            "parent_column": "id",
            "masking_rule": "hash_sha256(buyer_email)",
            "masking_type": "deterministic_hash",
            "pre_stage_server": "prestage-sql-01",
            "status": "active",
        }]
        engine = SQLMeshSimulator(augmented_matrix, stale_cert)
        ok, reason = engine.validate_certificate()
        assert not ok, "Expected certificate to be invalid after adding row 1.3."
        assert "mismatch" in reason.lower()


# ---------------------------------------------------------------------------
# Rule 3 – Ingestion is blocked on invalid certificate
# ---------------------------------------------------------------------------

class TestRule3IngestionGate:

    def test_valid_cert_passes_gate(self, engine):
        ok, reason = engine.validate_certificate()
        assert ok, f"Valid cert was rejected: {reason}"

    def test_uncertified_status_blocks_ingestion(self, matrix, certificate):
        bad_cert = copy.deepcopy(certificate)
        bad_cert["status"] = "pending"
        sim = SQLMeshSimulator(matrix, bad_cert)
        ok, _ = sim.validate_certificate()
        assert not ok

    def test_empty_dag_lines_blocks_ingestion(self, matrix, certificate):
        bad_cert = copy.deepcopy(certificate)
        bad_cert["masking_matrix_ref"]["dag_lines"] = []
        sim = SQLMeshSimulator(matrix, bad_cert)
        ok, _ = sim.validate_certificate()
        assert not ok

    def test_mismatched_dag_lines_raises_on_ingest(self, matrix, certificate):
        bad_cert = copy.deepcopy(certificate)
        bad_cert["masking_matrix_ref"]["dag_lines"] = [
            {"dag_no": "9.9", "table_name": "ghost", "column_name": "x", "masking_rule": "none"}
        ]
        sim = SQLMeshSimulator(matrix, bad_cert)
        with pytest.raises(RuntimeError, match="Ingestion halted"):
            sim.plan_and_backfill(["1.1"])

    def test_blocked_flag_set_after_failure(self, matrix, certificate):
        bad_cert = copy.deepcopy(certificate)
        bad_cert["status"] = "revoked"
        sim = SQLMeshSimulator(matrix, bad_cert)
        try:
            sim.plan_and_backfill(["1.1"])
        except RuntimeError:
            pass
        assert sim._ingestion_blocked


# ---------------------------------------------------------------------------
# Rule 4 – Backfills require certificate alignment
# ---------------------------------------------------------------------------

class TestRule4Backfills:

    def test_backfill_rebuilds_changed_hashed_model(self, engine):
        rebuilt = engine.plan_and_backfill(["1.1"])
        assert "hashed.vendor" in rebuilt

    def test_backfill_cascades_to_downstream_part(self, engine):
        rebuilt = engine.plan_and_backfill(["1.1"])
        assert "masked_dims.part" in rebuilt, (
            "Changing vendor (1.1) must cascade a rebuild of masked_dims.part."
        )

    def test_backfill_log_accumulates(self, engine):
        initial_len = len(engine._backfill_log)
        engine.plan_and_backfill(["1.2"])
        assert len(engine._backfill_log) > initial_len

    def test_no_backfill_without_valid_cert(self, matrix, certificate):
        bad_cert = copy.deepcopy(certificate)
        bad_cert["status"] = "expired"
        sim = SQLMeshSimulator(matrix, bad_cert)
        with pytest.raises(RuntimeError):
            sim.plan_and_backfill(["1.1"])
        assert sim._backfill_log == [], "No backfill entries should be written on a blocked run."


# ---------------------------------------------------------------------------
# Masking correctness – SHA-256 applied to faux seed data
# ---------------------------------------------------------------------------

class TestMaskingCorrectness:

    def test_vendor_id_is_hashed(self, engine, vendor_seed):
        masked = engine.apply_masking("vendor", vendor_seed)
        for original, masked_row in zip(vendor_seed, masked):
            assert masked_row["id"] == sha256_hex(original["id"]), (
                "vendor.id was not hashed correctly."
            )

    def test_vendor_non_pii_fields_unchanged(self, engine, vendor_seed):
        """Fields not in the masking matrix must pass through untouched."""
        masked = engine.apply_masking("vendor", vendor_seed)
        for original, masked_row in zip(vendor_seed, masked):
            assert masked_row["country"] == original["country"]

    def test_part_pref_vendor_is_hashed(self, engine, part_seed):
        masked = engine.apply_masking("part", part_seed)
        for original, masked_row in zip(part_seed, masked):
            assert masked_row["pref_vendor"] == sha256_hex(str(original["pref_vendor"]))

    def test_part_non_pii_fields_unchanged(self, engine, part_seed):
        masked = engine.apply_masking("part", part_seed)
        for original, masked_row in zip(part_seed, masked):
            assert masked_row["unit_cost"] == original["unit_cost"]

    def test_masking_is_deterministic(self, engine, vendor_seed):
        """Same input must always produce the same hash."""
        first = engine.apply_masking("vendor", vendor_seed)
        second = engine.apply_masking("vendor", vendor_seed)
        for a, b in zip(first, second):
            assert a["id"] == b["id"]

    def test_hash_length_is_64_hex_chars(self, engine, vendor_seed):
        masked = engine.apply_masking("vendor", vendor_seed)
        for row in masked:
            assert len(row["id"]) == 64, "SHA-256 digest must be 64 hex characters."

    def test_empty_seed_returns_empty(self, engine):
        assert engine.apply_masking("vendor", []) == []

    def test_hashing_does_not_expose_original_value(self, engine, vendor_seed):
        masked = engine.apply_masking("vendor", vendor_seed)
        for original, masked_row in zip(vendor_seed, masked):
            assert original["id"] not in masked_row["id"], (
                "Original vendor.id must not appear in the masked output."
            )


# ---------------------------------------------------------------------------
# DAG traversal integrity
# ---------------------------------------------------------------------------

class TestDAGIntegrity:

    def test_no_circular_dependencies(self, matrix):
        """Simple cycle check: a row's parent must have a lower dag_no."""
        dag_map = {r["dag_no"]: r for r in matrix}
        for row in matrix:
            parent_no = row.get("parent_table") and next(
                (r["dag_no"] for r in matrix if r["table_name"] == row["parent_table"]),
                None,
            )
            if parent_no:
                assert float(parent_no) < float(row["dag_no"]), (
                    f"Cycle detected: {row['dag_no']} references parent {parent_no}."
                )

    def test_parent_references_resolve(self, matrix):
        """Every non-empty parent_table must exist as a table_name in the matrix."""
        table_names = {r["table_name"] for r in matrix}
        for row in matrix:
            if row["parent_table"]:
                assert row["parent_table"] in table_names, (
                    f"Row {row['dag_no']}: parent_table '{row['parent_table']}' not found."
                )

    def test_root_nodes_have_no_parent(self, matrix):
        roots = [r for r in matrix if not r["parent_table"]]
        assert roots, "DAG has no root node (a row with empty parent_table)."

    def test_root_node_is_vendor(self, matrix):
        roots = [r for r in matrix if not r["parent_table"]]
        assert any(r["table_name"] == "vendor" for r in roots)
