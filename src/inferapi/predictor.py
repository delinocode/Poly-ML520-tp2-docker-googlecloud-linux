"""The serving-side model seam: what the HTTP layer needs from a model, and no more."""

from abc import ABC, abstractmethod
from pathlib import Path

import joblib
import pandas as pd

from inferapi.utils import file_creation_time


class Predictor(ABC):
    """Represents a model that predicts things

    NOTE(LAB): The best ABC is yet to be discovered, varies per use case.
    """

    @abstractmethod
    def predict(self, features: pd.DataFrame) -> tuple[int, float]:
        """Return (label, subscription probability) for a single-row frame of raw features."""

    # NOTE(LAB): Default implementation, should override
    def get_version(self) -> str:
        """Whatever identifies the weights being served."""
        return "unknown"


class SklearnPredictor(Predictor):
    def __init__(self, artifact_path: Path, threshold: float = 0.5):
        self._pipeline = joblib.load(artifact_path)
        self._threshold = threshold
        # We don't a version set, so use the file timestamp.
        # More advanced MLOps tools solve this problem of awkard way of versioning
        self._version = file_creation_time(artifact_path).isoformat()

    def predict(self, features: pd.DataFrame) -> tuple[int, float]:
        probability = float(self._pipeline.predict_proba(features)[0, 1])
        return int(probability >= self._threshold), probability

    def get_version(self) -> str:
        return self._version
