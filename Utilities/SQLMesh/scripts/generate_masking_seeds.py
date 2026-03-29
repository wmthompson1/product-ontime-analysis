#!/usr/bin/env python3
"""
generate_masking_seeds.py
=========================
Generates faux SQLMesh seed CSVs for the masking-matrix pipeline (pod908.md).

Outputs
-------
  seeds/vendor_seed.csv   — 20 rows  (DAG 1.1: vendor.id is PII)
  seeds/part_seed.csv     — 30 rows  (DAG 1.2: part.pref_vendor is PII)

Also prints the SHA-256 fixture values used in YAML unit tests so they stay
in sync with the seed generator.

Usage
-----
  python scripts/generate_masking_seeds.py
  # or from repo root:
  python Utilities/SQLMesh/scripts/generate_masking_seeds.py
"""

import csv
import hashlib
import os
from faker import Faker

SEED = 42
N_VENDORS = 20
N_PARTS = 30

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEEDS_DIR = os.path.join(SCRIPT_DIR, "..", "seeds")

# Fixed test-fixture rows referenced in tests/test_*_masking.yaml
FIXTURE_VENDOR_ID = "vendor-test-001"
FIXTURE_VENDOR_NAME = "Acme Corp"
FIXTURE_VENDOR_EMAIL = "contact@acme-corp.example"
FIXTURE_VENDOR_COUNTRY = "US"

FIXTURE_PART_NO = "PT-FIXTURE"
FIXTURE_PART_DESC = "Widget Assembly Unit"
FIXTURE_PART_UNIT_COST = 42.00


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def generate_vendor_seed(fake: Faker) -> list[dict]:
    rows = []
    for _ in range(N_VENDORS):
        rows.append({
            "id": fake.uuid4(),
            "name": fake.company(),
            "contact_email": fake.company_email(),
            "country": fake.country_code(),
        })
    return rows


def generate_part_seed(fake: Faker, vendor_ids: list[str]) -> list[dict]:
    rows = []
    for _ in range(N_PARTS):
        rows.append({
            "part_no": fake.bothify("PT-####"),
            "description": fake.catch_phrase(),
            "pref_vendor": fake.random_element(vendor_ids),
            "unit_cost": round(fake.pyfloat(min_value=1, max_value=500, right_digits=2), 2),
            "buyer_email": fake.email(),
        })
    return rows


def write_csv(path: str, rows: list[dict]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    fake = Faker()
    Faker.seed(SEED)

    # --- vendor ----------------------------------------------------------
    vendor_rows = generate_vendor_seed(fake)
    vendor_path = os.path.join(SEEDS_DIR, "vendor_seed.csv")
    write_csv(vendor_path, vendor_rows)
    print(f"[OK] {vendor_path}  ({len(vendor_rows)} rows)")

    # --- part ------------------------------------------------------------
    vendor_ids = [r["id"] for r in vendor_rows]
    part_rows = generate_part_seed(fake, vendor_ids)
    part_path = os.path.join(SEEDS_DIR, "part_seed.csv")
    write_csv(part_path, part_rows)
    print(f"[OK] {part_path}  ({len(part_rows)} rows)")

    # --- YAML test-fixture hashes ----------------------------------------
    vendor_id_hash = sha256_hex(FIXTURE_VENDOR_ID)
    pref_vendor_hash = sha256_hex(FIXTURE_VENDOR_ID)   # part's FK points at this vendor

    print("\n--- YAML test fixture hashes (copy into tests/*.yaml) ---")
    print(f"  vendor_seed fixture id:          {FIXTURE_VENDOR_ID!r}")
    print(f"  sha256(vendor.id):               {vendor_id_hash}")
    print(f"  part fixture pref_vendor:        {FIXTURE_VENDOR_ID!r}  (same UUID)")
    print(f"  sha256(part.pref_vendor):        {pref_vendor_hash}")
    print("-" * 60)


if __name__ == "__main__":
    main()
