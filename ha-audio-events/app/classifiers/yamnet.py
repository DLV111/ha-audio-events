from __future__ import annotations

import asyncio
import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np

from app.classifiers.base import AudioClassifier, Detection

try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:  # pragma: no cover
    Interpreter = None  # type: ignore[assignment]


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
        waveform = self._prepare_waveform(audio)
        scores = await asyncio.to_thread(self._run_inference, waveform)
        return self._build_detections(scores)

    def _prepare_waveform(self, audio: np.ndarray) -> np.ndarray:
        waveform = audio.astype(np.float32)
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        if waveform.size == 0:
            return waveform
        # YAMNet expects a batch-like input with shape [n_samples, 1]
        return waveform.reshape(1, -1, 1)

    def _run_inference(self, waveform: np.ndarray) -> np.ndarray:
        input_index = self._input_details[0]["index"]
        self.interpreter.set_tensor(input_index, waveform)
        self.interpreter.invoke()
        output_index = self._output_details[0]["index"]
        result = self.interpreter.get_tensor(output_index)
        if result.ndim == 3:
            result = np.mean(result, axis=1)
        return result.squeeze().astype(np.float32)

    def _build_detections(self, scores: np.ndarray) -> list[Detection]:
        if scores.size == 0:
            return []
        top_k = min(10, scores.shape[-1])
        indices = np.argsort(scores)[::-1][:top_k]
        now = datetime.utcnow()
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
