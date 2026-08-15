from __future__ import annotations

from app.detection.history import EventHistory


def test_recent_returns_most_recent_first() -> None:
    history = EventHistory()
    history.add("dog", 0.9, "started")
    history.add("dog", 0.92, "active")
    history.add("dog", 0.85, "ended")

    recent = history.recent()

    assert [r["state"] for r in recent] == ["ended", "active", "started"]


def test_recent_includes_expected_fields() -> None:
    history = EventHistory()
    history.add("train", 0.77, "started")

    (record,) = history.recent()

    assert record["label"] == "train"
    assert record["confidence"] == 0.77
    assert record["state"] == "started"
    assert record.get("timestamp")


def test_ring_buffer_respects_max_size() -> None:
    history = EventHistory(max_size=3)
    for i in range(5):
        history.add(f"event{i}", 0.5, "started")

    recent = history.recent()

    assert len(recent) == 3
    # Most recent (event4, event3, event2) should be kept; oldest dropped.
    assert [r["label"] for r in recent] == ["event4", "event3", "event2"]


def test_empty_history_returns_empty_list() -> None:
    history = EventHistory()
    assert history.recent() == []
