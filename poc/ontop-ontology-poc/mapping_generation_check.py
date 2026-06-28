#!/usr/bin/env python3
"""
OBDA mapping generation equivalence check (offline, file-vs-file).
==================================================================

``generate_mapping.py`` derives the On-Time Delivery OBDA mapping (and the
mechanically-derivable ontology vocabulary terms) from the governed schema
(``replit_integrations/graph_metadata.json``) plus the small publishing manifest
(``mapping/on_time_delivery_manifest.json``). This check proves the switch to the
generator is **provably lossless** for the committed showcase, completely offline
(no database, no network, no JVM) — mirroring the project's other coverage gates.

It asserts three things:

  1. MAPPING EQUIVALENCE — the freshly-rendered ``.obda`` is BYTE-IDENTICAL to the
     committed hand-authored ``mapping/on_time_delivery.obda``. Byte identity is
     the strongest possible equivalence proof: the generated mapping is the same
     mapping, so it necessarily returns the same SPARQL answers.
  2. VOCABULARY FRESHNESS — the committed generated vocabulary artifact
     (``ontology/on_time_delivery.generated.vocab.ttl``) matches what the
     generator renders now (so it cannot go stale relative to the schema).
  3. VOCABULARY CLOSURE — every term the generator produces is declared in the
     hand-authored runtime ontology (``ontology/on_time_delivery.ttl``), so the
     generated vocabulary is a faithful subset of the runtime ontology (whose
     extra subPropertyOf hierarchy + prose remain hand-authored governance).

Exit codes:
    0  — generated artifacts are equivalent (or skipped in --skip-on-missing)
    1  — a mismatch was found (a clear diff is printed)
    2  — a required input was missing (and --skip-on-missing not set), or the
         generator raised on the governed schema

Run:

    python poc/ontop-ontology-poc/mapping_generation_check.py
"""
from __future__ import annotations

import argparse
import difflib
import os
import sys
from typing import List, Optional

POC_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, POC_DIR)

import generate_mapping as gen  # noqa: E402
from mapping_drift_check import parse_ttl  # noqa: E402

DEFAULT_MANIFEST = gen.DEFAULT_MANIFEST
DEFAULT_GRAPH = gen.DEFAULT_GRAPH
DEFAULT_OBDA = gen.DEFAULT_OBDA
DEFAULT_VOCAB = gen.DEFAULT_VOCAB
DEFAULT_ONTOLOGY = os.path.join(POC_DIR, "ontology", "on_time_delivery.ttl")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _unified_diff(expected: str, actual: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile=f"committed {path}",
            tofile="freshly generated",
        )
    )


def check(
    manifest_path: str,
    graph_path: str,
    obda_path: str,
    vocab_path: str,
    ontology_path: str,
) -> int:
    try:
        manifest = gen.load_manifest(manifest_path)
        graph = gen.load_graph(graph_path)
        rendered_obda = gen.render_obda(manifest, graph)
        rendered_vocab = gen.render_vocab_ttl(manifest, graph)
        produced_terms = gen.generated_terms(manifest, graph)
    except gen.GenError as exc:
        print(f"[mapping_generation] ERROR — generator failed: {exc}", file=sys.stderr)
        return 2

    failed = False

    # 1. Mapping equivalence — byte-identical to the committed .obda.
    committed_obda = _read(obda_path)
    if committed_obda == rendered_obda:
        print(
            f"[mapping_generation] OK — generated .obda is byte-identical to "
            f"{os.path.relpath(obda_path, gen.REPO_ROOT)} "
            f"({len(manifest['mappings'])} mappings)."
        )
    else:
        failed = True
        print(
            "FAIL: the generated .obda differs from the committed mapping. The "
            "committed file is stale (or was hand-edited) — regenerate with "
            "`python poc/ontop-ontology-poc/generate_mapping.py`:"
        )
        print(_unified_diff(committed_obda, rendered_obda, os.path.basename(obda_path)))

    # 2. Vocabulary freshness — committed generated artifact matches render.
    committed_vocab = _read(vocab_path)
    if committed_vocab == rendered_vocab:
        print(
            f"[mapping_generation] OK — generated vocabulary is byte-identical to "
            f"{os.path.relpath(vocab_path, gen.REPO_ROOT)}."
        )
    else:
        failed = True
        print(
            "FAIL: the committed generated vocabulary is stale — regenerate with "
            "`python poc/ontop-ontology-poc/generate_mapping.py`:"
        )
        print(_unified_diff(committed_vocab, rendered_vocab, os.path.basename(vocab_path)))

    # 3. Vocabulary closure — every generated term is in the runtime ontology.
    classes, properties, _ = parse_ttl(ontology_path)
    declared = classes | properties
    missing = sorted(produced_terms - declared)
    if missing:
        failed = True
        print(
            f"FAIL: {len(missing)} generated term(s) are not declared in the "
            f"runtime ontology {os.path.relpath(ontology_path, gen.REPO_ROOT)}:"
        )
        for term in missing:
            print(f"  - :{term}")
    else:
        print(
            f"[mapping_generation] OK — all {len(produced_terms)} generated terms "
            "are declared in the runtime ontology."
        )

    if failed:
        print("[mapping_generation] FAIL — generated artifacts are not equivalent.")
        return 1
    print(
        "[mapping_generation] OK — the generated mapping is provably equivalent to "
        "the committed showcase."
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--graph", default=DEFAULT_GRAPH)
    parser.add_argument("--obda", default=DEFAULT_OBDA)
    parser.add_argument("--vocab", default=DEFAULT_VOCAB)
    parser.add_argument("--ontology", default=DEFAULT_ONTOLOGY)
    parser.add_argument(
        "--skip-on-missing",
        action="store_true",
        help="Exit 0 instead of erroring when an input file is absent.",
    )
    args = parser.parse_args(argv)

    for label, path in (
        ("manifest", args.manifest),
        ("graph metadata", args.graph),
        ("committed .obda", args.obda),
        ("committed vocabulary", args.vocab),
        ("runtime ontology", args.ontology),
    ):
        if not os.path.exists(path):
            msg = f"{label} not found: {path}"
            if args.skip_on_missing:
                print(f"[mapping_generation] SKIP — {msg}")
                return 0
            print(f"[mapping_generation] ERROR — {msg}", file=sys.stderr)
            return 2

    return check(args.manifest, args.graph, args.obda, args.vocab, args.ontology)


if __name__ == "__main__":
    raise SystemExit(main())
