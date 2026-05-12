import numpy as np

from trend_rover.vision.base import BaseDetector


class OpenCVDetector(BaseDetector):
    def __init__(self, threshold: float = 0.8, scales: list[float] = None):
        self._threshold = threshold
        self._scales = scales or [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

    def detect(self, thumbnail_path: str, logo_path: str) -> tuple[bool, float]:
        try:
            import cv2
        except ImportError:
            return False, 0.0

        try:
            thumbnail = cv2.imread(thumbnail_path)
            logo = cv2.imread(logo_path)
        except Exception:
            return False, 0.0

        if thumbnail is None or logo is None:
            return False, 0.0

        th, tw = thumbnail.shape[:2]
        lh, lw = logo.shape[:2]

        best_score = 0.0
        for scale in self._scales:
            new_h = int(lh * scale)
            new_w = int(lw * scale)
            if new_h < 1 or new_w < 1 or new_h > th or new_w > tw:
                continue
            try:
                resized = cv2.resize(logo, (new_w, new_h))
                # TM_SQDIFF_NORMED: 0.0 = perfect match, 1.0 = no match.
                # Invert so that score follows the convention: 1.0 = perfect match.
                result = cv2.matchTemplate(thumbnail, resized, cv2.TM_SQDIFF_NORMED)
                min_val, _, _, _ = cv2.minMaxLoc(result)
                score = 1.0 - float(min_val)
                best_score = max(best_score, score)
            except Exception:
                continue

        return best_score >= self._threshold, best_score
