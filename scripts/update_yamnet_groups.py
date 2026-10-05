"""Fetch AudioSet ontology and build models/yamnet_groups.json.

Maps each YAMNet label (from yamnet_class_map.csv) to its AudioSet
ontology parent chain and bakes the result into a committed JSON file
so the add-on and tests need no network at runtime.

Usage (from repo root):
    make update-yamnet-groups

Usage (from a checkout that includes this script):
    python3 scripts/update_yamnet_groups.py
"""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

ONTOLOGY_URL = (
    "https://raw.githubusercontent.com/audioset/ontology/master/ontology.json"
)
CLASS_MAP = Path("models/yamnet_class_map.csv")
OUT = Path("models/yamnet_groups.json")
TOP_LEVEL = "Top"


def load_ontology(url: str) -> list[dict]:
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data


def load_class_map(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def build_parent_map(ontology: list[dict]) -> dict[str, str]:
    """Reverse child_ids → {child_mid: parent_mid}."""
    parents: dict[str, str] = {}
    for node in ontology:
        for child_id in node.get("child_ids", []):
            parents[child_id] = node["id"]
    return parents


def resolve_path_ids(mid: str, parents: dict[str, str]) -> list[str]:
    """Resolve a mid to its full parent chain of node ids (root first)."""
    chain: list[str] = []
    visited: set[str] = set()
    current = mid
    while current and current not in visited:
        visited.add(current)
        chain.append(current)
        current = parents.get(current)
    chain.reverse()
    return chain if chain else []


def label_group_path(path_ids: list[str], by_id: dict[str, str]) -> list[str]:
    """Return the group path (names) where this label lives.

    The label is a leaf node whose parent chain defines the tree. The
    leaf label is stored under its parent group; if it has no parent
    (it is a top-level root itself) the label becomes its own group.
    """
    ancestors = [by_id.get(p, p) for p in path_ids[:-1]]
    if not ancestors:
        return [by_id.get(path_ids[-1], path_ids[-1])]
    return ancestors


def _new_node() -> dict:
    return {"labels": [], "allLabels": [], "subgroups": {}}


def _count(node: dict) -> int:
    return len(node["labels"]) + sum(_count(c) for c in node["subgroups"].values())


def build_tree(
    class_map: list[dict],
    parents: dict[str, str],
    by_id: dict[str, str],
) -> tuple[dict, dict[str, str]]:
    """Build {top_group_name: {labels, allLabels, subgroups}}."""
    label_to_path: dict[str, list[str]] = {}
    label_paths: dict[str, str] = {}
    for row in class_map:
        mid = row["mid"].strip()
        name = (row.get("display_name") or "").strip()
        if not name:
            continue
        if mid not in by_id:
            # Label's mid is not a valid ontology node: fall back to a stable
            # "Unknown" bucket so it still shows in the picker.
            label_to_path[name] = ["Unknown"]
            label_paths[name] = "Unknown"
            continue
        path_ids = resolve_path_ids(mid, parents)
        path = label_group_path(path_ids, by_id)
        label_to_path[name] = path
        label_paths[name] = " > ".join(path)

    # First pass: insert labels, incrementing direct labels only.
    groups: dict[str, dict] = {}
    for name in sorted(label_to_path):
        path = label_to_path[name]
        node = groups
        for part in path[:-1]:
            node = node.setdefault(part, _new_node())["subgroups"]
        leaf = path[-1]
        node[leaf] = node.setdefault(leaf, _new_node())
        node[leaf]["labels"].append(name)

    # Second pass: annotate descendant counts and full label lists (in-place).
    def annotate(node: dict) -> dict:
        for c in node["subgroups"].values():
            annotate(c)
        node["count"] = _count(node)
        node["allLabels"] = sorted(
            node["labels"]
            + [l for c in node["subgroups"].values() for l in c["allLabels"]]
        )
        return node

    tree = {
        k: annotate(v)
        for k, v in sorted(groups.items(), key=lambda kv: (-_count(kv[1]), kv[0]))
    }
    return tree, label_paths


def main() -> None:
    print(f"Downloading AudioSet ontology from {ONTOLOGY_URL} ...")
    ontology = load_ontology(ONTOLOGY_URL)
    print(f"Ontology nodes: {len(ontology)}")

    parents = build_parent_map(ontology)
    by_id = {node["id"]: node["name"] for node in ontology}
    roots = sorted(
        {node["id"] for node in ontology} - set(parents),
        key=lambda x: by_id.get(x, x),
    )
    print(f"Root (top-level) groups: {len(roots)}")
    for r in roots:
        print(f"  {r} -> {by_id.get(r, r)}")

    rows = load_class_map(CLASS_MAP)
    print(f"Class map entries: {len(rows)}")

    groups, label_paths = build_tree(rows, parents, by_id)

    total = sum(g["count"] for g in groups.values())
    print(f"Top-level groups: {len(groups)} | total labels: {total}")
    for name, g in groups.items():
        print(f"  {name}: {g['count']}")

    payload = {
        "generated_from": ONTOLOGY_URL,
        "class_map": str(CLASS_MAP),
        "top_level_groups": groups,
        "label_paths": label_paths,
    }
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
