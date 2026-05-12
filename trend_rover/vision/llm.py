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
