# Trend Rover Plan 4: Vision Module (Logo Detection)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement two logo detection backends — OpenCV multi-scale template matching (default, no API key needed) and a multi-modal LLM backend (Claude/OpenAI) — both behind the `BaseDetector` interface.

**Architecture:** `OpenCVDetector` uses `cv2.matchTemplate` at scales 0.5x–2.0x. `LLMDetector` encodes both images to base64 and sends them to the configured provider. A factory function `get_detector(config)` returns the right implementation based on config.

**Tech Stack:** Python 3.11+, opencv-python, httpx, anthropic SDK, openai SDK, pytest

**Prerequisites:** Plan 1 complete (BaseDetector ABC, Config).

---

## File Map

| File | Responsibility |
|------|---------------|
| `trend_rover/vision/opencv.py` | `OpenCVDetector` |
| `trend_rover/vision/llm.py` | `LLMDetector` |
| `trend_rover/vision/__init__.py` | `get_detector` factory |
| `tests/test_vision.py` | Tests for both detectors |
| `tests/fixtures/logo.png` | Tiny test logo image |
| `tests/fixtures/thumbnail_match.png` | Thumbnail containing the logo |
| `tests/fixtures/thumbnail_no_match.png` | Thumbnail without the logo |

---

### Task 1: Create Test Fixtures

**Files:**
- Create: `tests/fixtures/logo.png`
- Create: `tests/fixtures/thumbnail_match.png`
- Create: `tests/fixtures/thumbnail_no_match.png`

- [ ] **Step 1: Generate test images programmatically**

```python
# run this once to generate fixtures
import os
import numpy as np
import cv2

os.makedirs("tests/fixtures", exist_ok=True)

# 50x50 red square as logo
logo = np.zeros((50, 50, 3), dtype=np.uint8)
logo[:, :] = (0, 0, 255)  # BGR red
cv2.imwrite("tests/fixtures/logo.png", logo)

# 480x360 gray thumbnail with the logo embedded at (100, 100)
thumbnail_match = np.ones((360, 480, 3), dtype=np.uint8) * 200
thumbnail_match[100:150, 100:150] = (0, 0, 255)
cv2.imwrite("tests/fixtures/thumbnail_match.png", thumbnail_match)

# 480x360 gray thumbnail without the logo
thumbnail_no_match = np.ones((360, 480, 3), dtype=np.uint8) * 200
cv2.imwrite("tests/fixtures/thumbnail_no_match.png", thumbnail_no_match)

print("Fixtures created")
```

Run:
```bash
python -c "
import os, numpy as np, cv2
os.makedirs('tests/fixtures', exist_ok=True)
logo = np.zeros((50, 50, 3), dtype=np.uint8); logo[:, :] = (0, 0, 255)
cv2.imwrite('tests/fixtures/logo.png', logo)
tm = np.ones((360, 480, 3), dtype=np.uint8) * 200; tm[100:150, 100:150] = (0, 0, 255)
cv2.imwrite('tests/fixtures/thumbnail_match.png', tm)
tnm = np.ones((360, 480, 3), dtype=np.uint8) * 200
cv2.imwrite('tests/fixtures/thumbnail_no_match.png', tnm)
print('Fixtures created')
"
```

Expected: `Fixtures created`

- [ ] **Step 2: Commit fixtures**

```bash
git add tests/fixtures/
git commit -m "test: add vision fixture images"
```

---

### Task 2: OpenCV Detector

**Files:**
- Create: `trend_rover/vision/opencv.py`
- Create: `tests/test_vision.py` (partial)

- [ ] **Step 1: Write failing tests**

`tests/test_vision.py`:
```python
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
    detector_strict = OpenCVDetector(threshold=0.99)
    detector_loose = OpenCVDetector(threshold=0.5)
    _, score = detector_loose.detect(THUMBNAIL_MATCH, LOGO)
    # With threshold=0.5 and our synthetic match, should detect
    matched_loose, _ = detector_loose.detect(THUMBNAIL_MATCH, LOGO)
    assert matched_loose is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_vision.py -v -k "opencv"
```

Expected: `ImportError`

- [ ] **Step 3: Implement OpenCVDetector**

`trend_rover/vision/opencv.py`:
```python
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
                result = cv2.matchTemplate(thumbnail, resized, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                best_score = max(best_score, float(max_val))
            except Exception:
                continue

        return best_score >= self._threshold, best_score
```

- [ ] **Step 4: Run OpenCV tests**

```bash
pytest tests/test_vision.py -v -k "opencv"
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/vision/opencv.py tests/test_vision.py
git commit -m "feat: OpenCV multi-scale logo detector"
```

---

### Task 3: LLM Detector

**Files:**
- Modify: `trend_rover/vision/llm.py`
- Modify: `tests/test_vision.py` (add LLM tests)

- [ ] **Step 1: Write failing LLM tests (using mocks)**

Append to `tests/test_vision.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_vision.py -v -k "llm"
```

Expected: `ImportError`

- [ ] **Step 3: Implement LLMDetector**

`trend_rover/vision/llm.py`:
```python
import base64
from pathlib import Path

from trend_rover.vision.base import BaseDetector

_PROMPT = (
    "I will show you two images. The first is a video thumbnail. "
    "The second is a brand logo. "
    "Does the thumbnail contain the logo? Reply with only 'yes' or 'no'."
)


def _encode_image(path: str) -> tuple[str, str]:
    """Return (base64_data, media_type)."""
    data = Path(path).read_bytes()
    b64 = base64.standard_b64encode(data).decode()
    suffix = Path(path).suffix.lower()
    media_type = {"jpg": "image/jpeg", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(suffix, "image/jpeg")
    return b64, media_type


class LLMDetector(BaseDetector):
    def __init__(self, provider: str, api_key: str, model: str):
        self._provider = provider.lower()
        self._api_key = api_key
        self._model = model

    def detect(self, thumbnail_path: str, logo_path: str) -> tuple[bool, float]:
        try:
            thumb_b64, thumb_type = _encode_image(thumbnail_path)
            logo_b64, logo_type = _encode_image(logo_path)
        except (FileNotFoundError, OSError):
            return False, 0.0

        try:
            answer = self._call_llm(thumb_b64, thumb_type, logo_b64, logo_type)
        except Exception:
            return False, 0.0

        matched = answer.strip().lower().startswith("yes")
        return matched, 1.0 if matched else 0.0

    def _call_llm(self, thumb_b64: str, thumb_type: str, logo_b64: str, logo_type: str) -> str:
        if self._provider == "claude":
            return self._call_claude(thumb_b64, thumb_type, logo_b64, logo_type)
        if self._provider == "openai":
            return self._call_openai(thumb_b64, thumb_type, logo_b64, logo_type)
        raise ValueError(f"Unknown provider: {self._provider}")

    def _call_claude(self, thumb_b64, thumb_type, logo_b64, logo_type) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": thumb_type, "data": thumb_b64}},
                    {"type": "image", "source": {"type": "base64", "media_type": logo_type, "data": logo_b64}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
        return response.content[0].text

    def _call_openai(self, thumb_b64, thumb_type, logo_b64, logo_type) -> str:
        import openai
        client = openai.OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:{thumb_type};base64,{thumb_b64}"}},
                    {"type": "image_url", "image_url": {"url": f"data:{logo_type};base64,{logo_b64}"}},
                    {"type": "text", "text": _PROMPT},
                ],
            }],
        )
        return response.choices[0].message.content
```

- [ ] **Step 4: Run LLM tests**

```bash
pytest tests/test_vision.py -v -k "llm"
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add trend_rover/vision/llm.py tests/test_vision.py
git commit -m "feat: LLM logo detector (Claude + OpenAI)"
```

---

### Task 4: Detector Factory

**Files:**
- Modify: `trend_rover/vision/__init__.py`
- Modify: `tests/test_vision.py` (add factory tests)

- [ ] **Step 1: Write failing factory tests**

Append to `tests/test_vision.py`:
```python
from trend_rover.vision import get_detector
from trend_rover.vision.opencv import OpenCVDetector
from trend_rover.vision.llm import LLMDetector
from trend_rover.config import Config


def test_factory_returns_opencv_by_default():
    config = Config()  # vision_engine = "opencv"
    detector = get_detector(config)
    assert isinstance(detector, OpenCVDetector)


def test_factory_returns_llm_when_configured():
    config = Config(vision_engine="llm", llm_provider="claude", llm_api_key="sk-x", llm_model="claude-sonnet-4-6")
    detector = get_detector(config)
    assert isinstance(detector, LLMDetector)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_vision.py -v -k "factory"
```

Expected: `ImportError` on `get_detector`

- [ ] **Step 3: Implement factory**

`trend_rover/vision/__init__.py`:
```python
from trend_rover.config import Config
from trend_rover.vision.base import BaseDetector


def get_detector(config: Config) -> BaseDetector:
    if config.vision_engine == "llm":
        from trend_rover.vision.llm import LLMDetector
        return LLMDetector(
            provider=config.llm_provider or "claude",
            api_key=config.llm_api_key or "",
            model=config.llm_model or "claude-sonnet-4-6",
        )
    from trend_rover.vision.opencv import OpenCVDetector
    return OpenCVDetector(threshold=config.vision_threshold)
```

- [ ] **Step 4: Run all vision tests**

```bash
pytest tests/test_vision.py -v
```

Expected: all tests pass

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add trend_rover/vision/__init__.py tests/test_vision.py
git commit -m "feat: detector factory — opencv default, llm optional"
```

---

### Task 5: Final Verification

- [ ] **Step 1: Final full test run**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests pass, 0 errors

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "chore: plan 4 complete — vision module"
```
