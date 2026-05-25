"""Binding key utilities — Solder Pattern key convention.

Primary binding keys identify a ground-truth SQL snippet by encoding:
  - the source and target ERP tables (first 3 alpha chars of each, lowercase)
  - a zero-padded 3-digit sequence number (unique within the source/target/perspective triple)
  - the perspective slug (lowercase, whitespace → underscore)

Format:  {src3}_{tgt3}_{NNN}_{perspective_slug}

Examples
--------
  make_binding_key("suppliers", "orders", 1, "Finance")
      → "sup_ord_001_finance"

  make_binding_key("quality_incidents", "production_quality", 3, "Operations")
      → "qua_pro_003_operations"

  make_binding_key("stg_manufacturing_flat", "stg_orders", 5, "Supply Chain")
      → "stg_stg_005_supply_chain"

The same scheme applies to intents, concepts, and field_components — the
entity type is NOT embedded in the key so the same lookup works across all
three semantic layer constructs.
"""

from __future__ import annotations

import re


def _alpha3(table_name: str) -> str:
    """Return the first 3 lowercase alphabetic characters of *table_name*.

    Leading digits and underscores are skipped; only [a-z] characters count.
    If the table name contains fewer than 3 alpha chars the full alpha string
    is returned (never padded — callers should treat short names as-is).
    """
    letters = re.sub(r"[^a-zA-Z]", "", table_name)
    return letters[:3].lower()


def _perspective_slug(perspective: str) -> str:
    """Normalise *perspective* to a key-safe lowercase slug.

    Rules:
    - Lowercased
    - Runs of non-alphanumeric characters (spaces, hyphens, dots, …) → single '_'
    - Leading / trailing underscores stripped
    """
    slug = re.sub(r"[^a-z0-9]+", "_", perspective.lower()).strip("_")
    return slug or "default"


def make_binding_key(
    source_table: str,
    target_table: str,
    seq_num: int,
    perspective: str,
) -> str:
    """Build a primary_binding_key from the Solder Pattern hash key convention.

    Parameters
    ----------
    source_table:
        ERP table on the *from* side of the relationship.
    target_table:
        ERP table on the *to* side of the relationship.
    seq_num:
        Sequence number that makes the key unique within a
        (source_table, target_table, perspective) triple.
        Valid range: 1–999.  Values outside that range are accepted but the
        zero-padding is extended automatically (e.g. 1000 → "1000").
    perspective:
        Business perspective label (e.g. "Finance", "Operations",
        "Supply Chain").  Case-insensitive; normalised to a slug.

    Returns
    -------
    str
        Key of the form ``{src3}_{tgt3}_{NNN}_{perspective_slug}``.

    Raises
    ------
    ValueError
        If *source_table* or *target_table* contains no alphabetic characters,
        or if *seq_num* is not a positive integer.
    """
    if not isinstance(seq_num, int) or seq_num < 1:
        raise ValueError(f"seq_num must be a positive integer, got {seq_num!r}")

    src3 = _alpha3(source_table)
    tgt3 = _alpha3(target_table)

    if not src3:
        raise ValueError(
            f"source_table {source_table!r} contains no alphabetic characters"
        )
    if not tgt3:
        raise ValueError(
            f"target_table {target_table!r} contains no alphabetic characters"
        )

    seq = f"{seq_num:03d}"
    persp = _perspective_slug(perspective)

    return f"{src3}_{tgt3}_{seq}_{persp}"


def parse_binding_key(key: str) -> dict:
    """Parse a key produced by :func:`make_binding_key` back into its components.

    Returns a dict with keys ``src3``, ``tgt3``, ``seq_num``, ``perspective_slug``.
    Raises ``ValueError`` if the key does not match the expected pattern.
    """
    pattern = re.compile(
        r"^(?P<src3>[a-z]{1,3})_(?P<tgt3>[a-z]{1,3})_(?P<seq>\d{3,})_(?P<persp>.+)$"
    )
    m = pattern.match(key)
    if not m:
        raise ValueError(
            f"Key {key!r} does not match the binding key pattern "
            f"'{{src3}}_{{tgt3}}_{{NNN}}_{{perspective_slug}}'"
        )
    return {
        "src3": m.group("src3"),
        "tgt3": m.group("tgt3"),
        "seq_num": int(m.group("seq")),
        "perspective_slug": m.group("persp"),
    }
