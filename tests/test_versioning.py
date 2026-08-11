from __future__ import annotations

from pathlib import Path

from app.versioning import bump_version


def test_bump_version_updates_all_manifests(tmp_path: Path) -> None:
    (tmp_path / "ha-audio-events").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.2"\n',
        encoding="utf-8",
    )
    (tmp_path / "ha-audio-events" / "config.yaml").write_text(
        "name: Demo\nversion: 0.1.2\n",
        encoding="utf-8",
    )
    (tmp_path / "ha-audio-events" / "config.json").write_text(
        '{"name": "Demo", "version": "0.1.2"}',
        encoding="utf-8",
    )

    updated = bump_version("0.2.0", root=tmp_path)

    assert len(updated) == 3
    assert (tmp_path / "pyproject.toml").read_text(
        encoding="utf-8"
    ) == '[project]\nname = "demo"\nversion = "0.2.0"\n'
    assert (tmp_path / "ha-audio-events" / "config.yaml").read_text(
        encoding="utf-8"
    ) == "name: Demo\nversion: 0.2.0\n"
    assert (tmp_path / "ha-audio-events" / "config.json").read_text(
        encoding="utf-8"
    ) == '{\n  "name": "Demo",\n  "version": "0.2.0"\n}\n'
