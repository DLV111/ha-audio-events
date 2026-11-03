"""Derive models/class_groups.json — the grouped audio-class mapping.

The Web UI filter controls are "menu driven": a chip bar of AudioSet
top-level groups, and per-group checkbox lists of the YAMNet labels that
belong to that group. Building that menu needs a stable, committed mapping
from group -> classes, so this script derives one from the AudioSet ontology
data already baked into ``models/yamnet_groups.json`` (see
``scripts/update_yamnet_groups.py``) plus ``models/yamnet_class_map.csv``.

Nothing is hand-written here: the groups and their membership come from the
ontology, and the class ``value`` is simply the lowercased YAMNet display
name -- which is exactly the normalised form the pipeline and the
``classifier.include`` / ``classifier.exclude`` add-on options use.

The output shape is::

    {
      "groups": [
        {
          "group_id": "<slug>",
          "name": "<human readable AudioSet top-level group>",
          "classes": [{"display_name": "...", "value": "<lowercased>"}, ...]
        },
        ...
      ]
    }

Usage (from the repo root)::

    make generate-class-groups

The generated file is mirrored into ``ha-audio-events/models/`` because that
directory is what ships inside the add-on container (there ``/app`` *is*
``ha-audio-events/``). Keep both copies in sync by re-running this script.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

GROUPS_IN = Path("models/yamnet_groups.json")
CLASS_MAP = Path("models/yamnet_class_map.csv")
OUTPUTS = [Path("models/class_groups.json"), Path("ha-audio-events/models/class_groups.json")]


def slugify(name: str) -> str:
    """Stable, url/DOM-safe group id derived from the group display name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "unknown"


def load_class_map_values(path: Path) -> list[str]:
    """Return the lowercased YAMNet display names, in CSV order, deduped."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values: list[str] = []
    for row in rows:
        name = (row.get("display_name") or "").strip()
        if name and name.lower() not in values:
            values.append(name.lower())
    return values


def build_class_groups(groups_json: dict) -> dict:
    """Project the ontology-derived group tree into the flat menu mapping."""
    top_level = groups_json.get("top_level_groups") or {}
    groups = []
    for name, node in top_level.items():
        classes = [
            {"display_name": display_name, "value": display_name.lower()}
            for display_name in node.get("allLabels") or []
        ]
        groups.append({"group_id": slugify(name), "name": name, "classes": classes})
    return {
        "generated_from": "models/yamnet_groups.json (AudioSet ontology)",
        "class_map": str(CLASS_MAP),
        "groups": groups,
    }


def main() -> None:
    if not GROUPS_IN.exists():
        raise SystemExit(
            f"{GROUPS_IN} not found — run `make update-yamnet-groups` first"
        )

    groups_json = json.loads(GROUPS_IN.read_text(encoding="utf-8"))
    payload = build_class_groups(groups_json)

    # Sanity check: the groups must partition the YAMNet class map. If a label
    # falls outside the ontology (or is duplicated) the picker would silently
    # hide it from the user, so fail loudly instead of writing bad data.
    csv_values = load_class_map_values(CLASS_MAP)
    mapped = [cls["value"] for group in payload["groups"] for cls in group["classes"]]
    missing = sorted(set(csv_values) - set(mapped))
    unknown = sorted(set(mapped) - set(csv_values))
    duplicates = sorted({v for v in mapped if mapped.count(v) > 1})
    for problem, items in (
        ("not covered by any group", missing),
        ("not present in the class map", unknown),
        ("listed in more than one group", duplicates),
    ):
        if items:
            raise SystemExit(f"ERROR: {len(items)} class(es) {problem}: {items[:10]}")

    text = json.dumps(payload, indent=2, sort_keys=False) + "\n"
    for path in OUTPUTS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"Wrote {path} ({path.stat().st_size:,} bytes)")

    print(f"Groups: {len(payload['groups'])} | classes mapped: {len(mapped)}")
    for group in payload["groups"]:
        print(f"  {group['name']} ({group['group_id']}): {len(group['classes'])}")


if __name__ == "__main__":
    main()
