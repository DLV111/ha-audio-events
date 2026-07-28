from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import numpy as np


@dataclass
class Detection:
    label: str
    confidence: float
    timestamp: datetime | None
    model: str


class AudioClassifier(ABC):
    @abstractmethod
    async def classify(self, audio: np.ndarray) -> list[Detection]:
        ...
