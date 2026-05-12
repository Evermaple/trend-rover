from abc import ABC, abstractmethod


class BaseDetector(ABC):
    @abstractmethod
    def detect(self, thumbnail_path: str, logo_path: str) -> tuple[bool, float]:
        """
        Check if thumbnail contains logo.
        Returns (matched, confidence_score).
        """
