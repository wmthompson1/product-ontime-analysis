"""Bridge Policy Verifier

Checks that elevation weights in `manufacturing.db` align with the
collision rules (perspective -> elevated concept -> winner/loser source fields).

Exit code: 0 if all rules pass, non-zero otherwise.
"""
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "app_schema", "manufacturing.db")

# Standardized Collision Resolution Table (source of truth)
COLLISION_RULES = [
    {
        "perspective": "Quality",
        "elevated_concept": "MATERIAL_NON_CONFORMANCE",
        "winner": {"table": "stg_non_conformant_materials", "field": "severity"},
        "loser": {"table": "stg_product_defects", "field": "severity"},
    },
    {
        "perspective": "Finance",
        "elevated_concept": "FINANCIAL_LIABILITY_NCM",
        "winner": {"table": "stg_non_conformant_materials", "field": "cost_impact"},
        "loser": {"table": "stg_product_defects", "field": "cost_impact"},
    },
]


def find_concept_by_field(conn, table_name, field_name):
    cur = conn.cursor()
    cur.execute(
        "SELECT c.concept_id, c.concept_name FROM schema_concept_fields cf JOIN schema_concepts c ON cf.concept_id = c.concept_id WHERE cf.table_name = ? AND cf.field_name = ?",
        (table_name, field_name),
    )
    row = cur.fetchone()
    return row[0], row[1] if row else (None, None)


def find_perspective_id(conn, perspective_name):
    cur = conn.cursor()
    cur.execute("SELECT perspective_id FROM schema_perspectives WHERE perspective_name = ?", (perspective_name,))
    r = cur.fetchone()
    return r[0] if r else None


def concept_elevated_in_perspective(conn, concept_id, perspective_id):
    cur = conn.cursor()
    # Find any intent that elevates this concept (intent_factor_weight = 1.0)
    cur.execute(
        "SELECT ic.intent_id FROM schema_intent_concepts ic WHERE ic.concept_id = ? AND ic.intent_factor_weight = 1.0",
        (concept_id,)
    )
    intent_rows = cur.fetchall()
    if not intent_rows:
        return False, []

    intent_ids = [r[0] for r in intent_rows]
    # Check if any of those intents are associated with the perspective at weight=1.0
    matching = []
    for intent_id in intent_ids:
        cur.execute(
            "SELECT 1 FROM schema_intent_perspectives ip WHERE ip.intent_id = ? AND ip.perspective_id = ? AND ip.intent_factor_weight = 1.0",
            (intent_id, perspective_id),
        )
        if cur.fetchone():
            matching.append(intent_id)

    return (len(matching) > 0), matching


def check_rule(conn, rule):
    ok = True
    messages = []

    p_name = rule["perspective"]
    p_id = find_perspective_id(conn, p_name)
    if not p_id:
        messages.append(f"MISSING: perspective '{p_name}' not present in DB")
        return False, messages

    w_table = rule["winner"]["table"]
    w_field = rule["winner"]["field"]
    l_table = rule["loser"]["table"]
    l_field = rule["loser"]["field"]

    w_cid, w_concept = find_concept_by_field(conn, w_table, w_field)
    l_cid, l_concept = find_concept_by_field(conn, l_table, l_field)

    if not w_cid:
        messages.append(f"MISSING WINNER MAPPING: no concept found for {w_table}.{w_field}")
        ok = False
    else:
        messages.append(f"Found winner concept '{w_concept}' (id={w_cid}) for {w_table}.{w_field}")

    if not l_cid:
        messages.append(f"MISSING LOSER MAPPING: no concept found for {l_table}.{l_field}")
        ok = False
    else:
        messages.append(f"Found loser concept '{l_concept}' (id={l_cid}) for {l_table}.{l_field}")

    if not ok:
        return ok, messages

    # Ensure winner concept is elevated within the perspective
    elevated, intent_ids = concept_elevated_in_perspective(conn, w_cid, p_id)
    if elevated:
        messages.append(f"OK: winner concept '{w_concept}' is elevated in perspective '{p_name}' via intent(s): {intent_ids}")
    else:
        messages.append(f"FAIL: winner concept '{w_concept}' is NOT elevated in perspective '{p_name}' (no intent with weight=1.0 mapped to perspective)")
        ok = False

    # Ensure loser concept is not elevated within the perspective (weight should be 0.0 or absent)
    cur = conn.cursor()
    cur.execute(
        "SELECT ic.intent_id, ic.intent_factor_weight FROM schema_intent_concepts ic WHERE ic.concept_id = ?",
        (l_cid,)
    )
    rows = cur.fetchall()
    loser_elevated_in_perspective = False
    for intent_id, weight in rows:
        if float(weight) == 1.0:
            # check if this intent is tied to the perspective
            cur.execute("SELECT 1 FROM schema_intent_perspectives ip WHERE ip.intent_id = ? AND ip.perspective_id = ? AND ip.intent_factor_weight = 1.0", (intent_id, p_id))
            if cur.fetchone():
                loser_elevated_in_perspective = True
                break

    if loser_elevated_in_perspective:
        messages.append(f"WARN: loser concept '{l_concept}' appears elevated in perspective '{p_name}' (conflict)")
        ok = False
    else:
        messages.append(f"OK: loser concept '{l_concept}' not elevated in perspective '{p_name}'")

    return ok, messages


def main():
    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB not found at {DB_PATH}")
        return 2

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    overall_ok = True
    for rule in COLLISION_RULES:
        print(f"\nChecking rule: Perspective={rule['perspective']}, Elevated={rule['elevated_concept']}")
        ok, msgs = check_rule(conn, rule)
        for m in msgs:
            print(" -", m)
        if not ok:
            overall_ok = False

    conn.close()

    if overall_ok:
        print("\nAll collision rules validated: OK")
        return 0
    else:
        print("\nOne or more collision rules failed validation")
        return 1


if __name__ == '__main__':
    sys.exit(main())
