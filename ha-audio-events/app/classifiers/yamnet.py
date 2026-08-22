from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from app.classifiers.base import AudioClassifier, Detection

try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:  # pragma: no cover
    try:
        from tflite_runtime.interpreter import Interpreter  # type: ignore
    except ImportError:  # pragma: no cover
        Interpreter = None  # type: ignore[assignment]

# Safety cap so a very large buffer_seconds can't explode inference cost:
# at most this many model frames are evaluated per classify() call.
MAX_INFERENCE_FRAMES = 10


@dataclass
class YAMNetClassifier(AudioClassifier):
    model_path: Path
    labels_path: Path | None = None
    model_name: str = "yamnet"

    def __post_init__(self) -> None:
        if Interpreter is None:
            raise RuntimeError("tflite-runtime is required for YAMNetClassifier")
        self.interpreter = Interpreter(model_path=str(self.model_path))
        self.interpreter.allocate_tensors()
        self._input_details = self.interpreter.get_input_details()
        self._output_details = self.interpreter.get_output_details()
        self.labels = self._load_labels()

    def _load_labels(self) -> list[str]:
        candidates = []
        if self.labels_path is not None:
            candidates.append(self.labels_path)
        candidates.extend(
            [
                self.model_path.with_name("yamnet_class_map.csv"),
                self.model_path.with_name("yamnet_labels.txt"),
            ]
        )

        for path in candidates:
            if not path.exists():
                continue
            if path.suffix.lower() == ".csv":
                with path.open("r", encoding="utf-8", newline="") as handle:
                    reader = csv.DictReader(handle)
                    labels = []
                    for row in reader:
                        display_name = (row.get("display_name") or "").strip()
                        if display_name:
                            labels.append(display_name)
                    if labels:
                        return labels
            with path.open("r", encoding="utf-8") as handle:
                return [line.strip() for line in handle if line.strip()]
        return ["unknown"]

    async def classify(self, audio: np.ndarray) -> list[Detection]:
        frames = self._prepare_frames(audio)
        scores = await asyncio.to_thread(self._run_inference, frames)
        return self._build_detections(scores)

    def _frame_length(self) -> int:
        return int(self._input_details[0]["shape"][0])

    def _prepare_waveform(self, audio: np.ndarray) -> np.ndarray:
        """Mono-float waveform trimmed/padded to exactly one model frame."""
        waveform = audio.astype(np.float32)
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        expected_len = self._frame_length()
        if waveform.size != expected_len:
            if waveform.size > expected_len:
                waveform = waveform[:expected_len]
            else:
                waveform = np.pad(
                    waveform, (0, expected_len - waveform.size), mode="constant"
                )
        return waveform.reshape(-1)

    def _prepare_frames(self, audio: np.ndarray) -> list[np.ndarray]:
        """Split the buffer into model-sized frames covering the whole window.

        The YAMNet TFLite graph consumes a single 0.975s frame per invoke.
        Classifying only the first frame of a multi-second buffer would ignore
        the rest, so tile the buffer into consecutive frames (padding the
        final partial frame with silence) and let _run_inference average them.
        """
        waveform = audio.astype(np.float32)
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        frame_len = self._frame_length()
        if waveform.size == 0:
            return [np.zeros(frame_len, dtype=np.float32)]
        if waveform.size <= frame_len:
            return [self._prepare_waveform(waveform)]

        frames: list[np.ndarray] = []
        for start in range(0, waveform.size, frame_len):
            chunk = waveform[start : start + frame_len]
            if chunk.size < frame_len:
                chunk = np.pad(chunk, (0, frame_len - chunk.size), mode="constant")
            frames.append(chunk.astype(np.float32))
            if len(frames) >= MAX_INFERENCE_FRAMES:
                break
        return frames

    def _run_inference(self, frames: list[np.ndarray]) -> np.ndarray:
        input_index = self._input_details[0]["index"]
        output_index = self._output_details[0]["index"]
        total: np.ndarray | None = None
        for frame in frames:
            self.interpreter.set_tensor(input_index, frame)
            self.interpreter.invoke()
            result = self.interpreter.get_tensor(output_index)
            if result.ndim == 3:
                result = np.mean(result, axis=1)
            scores = result.squeeze().astype(np.float32)
            total = scores if total is None else total + scores
        assert total is not None, "classify() must pass at least one frame"
        return (total / len(frames)).astype(np.float32)

    def _build_detections(self, scores: np.ndarray) -> list[Detection]:
        if scores.size == 0:
            return []
        top_k = min(10, scores.shape[-1])
        indices = np.argsort(scores)[::-1][:top_k]
        now = datetime.now(UTC)
        detections: list[Detection] = []
        for index in indices:
            label = self.labels[index] if index < len(self.labels) else f"label_{index}"
            detections.append(
                Detection(
                    label=label,
                    confidence=float(scores[index]),
                    timestamp=now,
                    model=self.model_name,
                )
            )
        return detections
