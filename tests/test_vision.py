import pytest
from trend_rover.vision.opencv import OpenCVDetector

LOGO = "tests/fixtures/logo.png"
THUMBNAIL_MATCH = "tests/fixtures/thumbnail_match.png"
THUMBNAIL_NO_MATCH = "tests/fixtures/thumbnail_no_match.png"


def test_opencv_detects_exact_match():
    detector = OpenCVDetector(threshold=0.8)
    matched, score = detector.detect(THUMBNAIL_MATCH, LOGO)
    assert matched is True
    assert score >= 0.8


def test_opencv_no_match():
    detector = OpenCVDetector(threshold=0.8)
    matched, score = detector.detect(THUMBNAIL_NO_MATCH, LOGO)
    assert matched is False


def test_opencv_missing_thumbnail_returns_false():
    detector = OpenCVDetector()
    matched, score = detector.detect("/nonexistent/path.jpg", LOGO)
    assert matched is False
    assert score == 0.0


def test_opencv_missing_logo_returns_false():
    detector = OpenCVDetector()
    matched, score = detector.detect(THUMBNAIL_MATCH, "/nonexistent/logo.png")
    assert matched is False
    assert score == 0.0


def test_opencv_threshold_respected():
    detector_loose = OpenCVDetector(threshold=0.5)
    matched_loose, _ = detector_loose.detect(THUMBNAIL_MATCH, LOGO)
    assert matched_loose is True
