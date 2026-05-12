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


from unittest.mock import patch, MagicMock
from trend_rover.vision.llm import LLMDetector


def test_llm_detector_claude_yes():
    detector = LLMDetector(provider="claude", api_key="sk-test", model="claude-sonnet-4-6")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="yes")]
    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response
        matched, score = detector.detect(THUMBNAIL_MATCH, LOGO)
    assert matched is True
    assert score == 1.0


def test_llm_detector_claude_no():
    detector = LLMDetector(provider="claude", api_key="sk-test", model="claude-sonnet-4-6")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="no")]
    with patch("anthropic.Anthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create.return_value = mock_response
        matched, score = detector.detect(THUMBNAIL_MATCH, LOGO)
    assert matched is False
    assert score == 0.0


def test_llm_detector_missing_file_returns_false():
    detector = LLMDetector(provider="claude", api_key="sk-test", model="claude-sonnet-4-6")
    matched, score = detector.detect("/nonexistent.jpg", LOGO)
    assert matched is False
    assert score == 0.0


from trend_rover.vision import get_detector
from trend_rover.config import Config


def test_factory_returns_opencv_by_default():
    config = Config()  # vision_engine = "opencv"
    detector = get_detector(config)
    assert isinstance(detector, OpenCVDetector)


def test_factory_returns_llm_when_configured():
    config = Config(vision_engine="llm", llm_provider="claude", llm_api_key="sk-x", llm_model="claude-sonnet-4-6")
    detector = get_detector(config)
    assert isinstance(detector, LLMDetector)
