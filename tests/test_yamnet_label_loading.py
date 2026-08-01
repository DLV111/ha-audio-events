from __future__ import annotations

from pathlib import Path

from app.classifiers.yamnet import YAMNetClassifier


def test_loads_display_names_from_yamnet_class_map_csv(tmp_path: Path) -> None:
    model_path = tmp_path / "yamnet.tflite"
    labels_path = tmp_path / "yamnet_class_map.csv"
    labels_path.write_text(
        "index,mid,display_name\n"
        "0,/m/09x0r,Speech\n"
        "1,/m/05zppz,Dog\n"
        "2,/m/02zsn,Train\n",
        encoding="utf-8",
    )
    model_path.write_bytes(b"fake")

    classifier = YAMNetClassifier.__new__(YAMNetClassifier)
    classifier.model_path = model_path
    classifier.labels_path = labels_path
    classifier.model_name = "yamnet"

    labels = classifier._load_labels()

    assert labels == ["Speech", "Dog", "Train"]
