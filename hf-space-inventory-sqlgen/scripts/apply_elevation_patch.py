#!/usr/bin/env python3
"""Apply an idempotent elevation patch to hf-space-inventory-sqlgen/app_schema/manufacturing.db

Creates a timestamped backup before mutating. Ensures MATERIAL_NON_CONFORMANCE
intents are elevated for Quality and Finance (weight=1.0) and that
PRODUCTION_DEFECT intents are suppressed (weight=0.5) for those perspectives.
"""
import os
import shutil
import sqlite3
from datetime import datetime


def get_db_path():
    # Prefer cwd-based path so script works when invoked from repo root
    return os.path.abspath(os.path.join('hf-space-inventory-sqlgen', 'app_schema', 'manufacturing.db'))


def backup_db(db_path):
    backup_dir = os.path.abspath('arango_backups')
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    dest = os.path.join(backup_dir, f"manufacturing.db.{ts}.bak")
    shutil.copy2(db_path, dest)
    print(f'Backed up {db_path} -> {dest}')
    return dest


def upsert_perspective(conn, intent_id, perspective_id, weight):
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM schema_intent_perspectives WHERE intent_id=? AND perspective_id=?", (intent_id, perspective_id))
    if cur.fetchone():
        cur.execute("UPDATE schema_intent_perspectives SET intent_factor_weight=? WHERE intent_id=? AND perspective_id=?", (weight, intent_id, perspective_id))
        print(f'Updated intent_id={intent_id} perspective_id={perspective_id} -> {weight}')
    else:
        cur.execute("INSERT INTO schema_intent_perspectives (intent_id, perspective_id, intent_factor_weight) VALUES (?,?,?)", (intent_id, perspective_id, weight))
        print(f'Inserted intent_id={intent_id} perspective_id={perspective_id} -> {weight}')


def main():
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f'ERROR: database not found at {db_path}')
        return 2

    backup_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute('PRAGMA foreign_keys = ON')
        cur = conn.cursor()

        # Elevate MATERIAL_NON_CONFORMANCE
        cur.execute(
            """
            SELECT ic.intent_id
            FROM schema_intent_concepts ic
            JOIN schema_concepts c ON ic.concept_id = c.concept_id
            WHERE c.concept_name = ?
            """,
            ('MATERIAL_NON_CONFORMANCE',),
        )
        intent_ids = [r[0] for r in cur.fetchall()]
        # If there are no explicit intent->concept mappings, create a safe mapping
        if not intent_ids:
            print('No explicit intent mappings found for MATERIAL_NON_CONFORMANCE; creating a mapping to a default intent')
            # find concept_id
            cur.execute("SELECT concept_id FROM schema_concepts WHERE concept_name=?", ('MATERIAL_NON_CONFORMANCE',))
            c_row = cur.fetchone()
            if c_row:
                concept_id = c_row[0]
                # pick an intent to attach (prefer intent named 'Solder')
                cur.execute("SELECT intent_id FROM schema_intents WHERE intent_name='Solder' LIMIT 1")
                r = cur.fetchone()
                if not r:
                    cur.execute("SELECT intent_id FROM schema_intents LIMIT 1")
                    r = cur.fetchone()
                if r:
                    intent_to_use = r[0]
                    # insert mapping if not exists
                    cur.execute("SELECT 1 FROM schema_intent_concepts WHERE intent_id=? AND concept_id=?", (intent_to_use, concept_id))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO schema_intent_concepts (intent_id, concept_id, intent_factor_weight, explanation) VALUES (?,?,?,?)", (intent_to_use, concept_id, 1, 'Auto-elevated by patch'))
                        print(f'Inserted schema_intent_concepts mapping intent_id={intent_to_use} -> concept_id={concept_id}')
                        intent_ids = [intent_to_use]
                else:
                    print('ERROR: no intents available to map; cannot auto-create mapping')
            else:
                print('ERROR: MATERIAL_NON_CONFORMANCE concept not found')
        # resolve perspective ids
        cur.execute("SELECT perspective_id, perspective_name FROM schema_perspectives")
        persp_map = {r[1]: r[0] for r in cur.fetchall()}
        q_id = persp_map.get('Quality')
        f_id = persp_map.get('Finance')
        for intent_id in intent_ids:
            if q_id is not None:
                upsert_perspective(conn, intent_id, q_id, 1.0)
            else:
                print('ERROR: Quality perspective id not found')
            if f_id is not None:
                upsert_perspective(conn, intent_id, f_id, 1.0)
            else:
                print('ERROR: Finance perspective id not found')

        # Suppress PRODUCTION_DEFECT
        cur.execute(
            """
            SELECT ic.intent_id
            FROM schema_intent_concepts ic
            JOIN schema_concepts c ON ic.concept_id = c.concept_id
            WHERE c.concept_name = ?
            """,
            ('PRODUCTION_DEFECT',),
        )
        loser_intents = [r[0] for r in cur.fetchall()]
        if not loser_intents:
            print('WARNING: no intents found for PRODUCTION_DEFECT')
        for intent_id in loser_intents:
            if q_id is not None:
                upsert_perspective(conn, intent_id, q_id, 0.5)
            if f_id is not None:
                upsert_perspective(conn, intent_id, f_id, 0.5)

        conn.commit()
        print('Elevation patch applied successfully.')
        return 0
    except Exception as e:
        print('ERROR during patch:', e)
        return 3
    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
