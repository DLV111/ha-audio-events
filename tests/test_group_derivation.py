"""Tests for the AudioSet ontology → yamnet_groups.json derivation.

Runs entirely offline against a checked-in ontology fixture (no network).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# scripts/update_yamnet_groups.py is a plain module at repo root;
# import it for its pure functions.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))
import update_yamnet_groups as g

ONTOLOGY_FX = _REPO / "tests/fixtures/audioset_ontology_mini.json"
CLASSMAP_FX = _REPO / "tests/fixtures/audioset_class_map_mini.csv"
GROUPS = json.loads((_REPO / "models/yamnet_groups.json").read_text())[
    "top_level_groups"
]


def _fixture_ontology() -> list[dict]:
    return json.loads(ONTOLOGY_FX.read_text())


def _fixture_classmap() -> list[dict]:
    return list(g.load_class_map(CLASSMAP_FX))


def _by_id(ontology: list[dict]) -> dict[str, str]:
    return {n["id"]: n["name"] for n in ontology}


# ------------------------------------------------------------------
# unit tests on the small offline fixture
# ------------------------------------------------------------------


def test_parent_chain_resolution():
    """A label 3 levels deep (Hammer) resolves under Sounds of things > Tools."""
    parents = g.build_parent_map(_fixture_ontology())
    path = g.resolve_path_ids("HAMMER", parents)
    assert path[0] == "ROOT_SOUNDS"
    assert path[-1] == "HAMMER"
    gp = g.label_group_path(path, _by_id(_fixture_ontology()))
    assert gp == ["Sounds of things", "Tools"], f"got {gp}"


def test_label_with_no_children_is_mapped():
    """Leaf labels (e.g. 'Hammer', 'Drill') appear in their parent group."""
    tree, _ = g.build_tree(
        _fixture_classmap(),
        g.build_parent_map(_fixture_ontology()),
        _by_id(_fixture_ontology()),
    )
    tools = tree["Sounds of things"]["subgroups"]["Tools"]
    assert "Hammer" in tools["labels"]
    assert "Drill" in tools["labels"]


def test_missing_mid_lands_in_unknown():
    """A mid that does not exist in the ontology must fall back to Unknown."""
    tree, paths = g.build_tree(
        _fixture_classmap(),
        g.build_parent_map(_fixture_ontology()),
        _by_id(_fixture_ontology()),
    )
    assert "Unknown" in tree, tree.keys()
    assert "Mystery sound" in tree["Unknown"]["labels"]
    assert paths.get("Mystery sound") == "Unknown"


def test_deterministic_output():
    """Two runs on identical inputs produce identical trees."""
    tree1, paths1 = g.build_tree(
        _fixture_classmap(),
        g.build_parent_map(_fixture_ontology()),
        _by_id(_fixture_ontology()),
    )
    tree2, paths2 = g.build_tree(
        _fixture_classmap(),
        g.build_parent_map(_fixture_ontology()),
        _by_id(_fixture_ontology()),
    )
    assert tree1 == tree2
    assert paths1 == paths2


def test_counts_consistency():
    """Every group's count equals len(allLabels)."""
    tree, _ = g.build_tree(
        _fixture_classmap(),
        g.build_parent_map(_fixture_ontology()),
        _by_id(_fixture_ontology()),
    )

    def walk(node: dict) -> None:
        assert node["count"] == len(
            node["allLabels"]
        ), f"count mismatch in {node['labels']}"
        for c in node["subgroups"].values():
            walk(c)

    for top in tree.values():
        walk(top)


# ------------------------------------------------------------------
# real-data sanity checks against the committed groups file
# ------------------------------------------------------------------


def test_real_class_map_all_521_labels_mapped():
    """Every row of yamnet_class_map.csv appears in label_paths."""
    committed = json.loads((_REPO / "models/yamnet_groups.json").read_text())
    mapped = set(committed["label_paths"].keys())
    expected = {
        r["display_name"].strip()
        for r in g.load_class_map(_REPO / "models/yamnet_class_map.csv")
        if r["display_name"].strip()
    }
    assert expected <= mapped, f"unmapped labels: {expected - mapped}"
    assert len(mapped) == 521


def test_real_top_level_group_counts_sum_to_521():
    """Top-level group counts sum to 521 (every label accounted for once)."""
    total = sum(v["count"] for v in GROUPS.values())
    assert total == 521, f"total {total}"


def test_real_no_unknown_bucket():
    """The real ontology covers all 521 mids — no Unknown bucket appears."""
    assert "Unknown" not in GROUPS


def test_real_bark_path():
    """The task's example: Bark -> Animal > Domestic animals, pets > Dog."""
    committed = json.loads((_REPO / "models/yamnet_groups.json").read_text())
    assert committed["label_paths"]["Bark"] == "Animal > Domestic animals, pets > Dog"
