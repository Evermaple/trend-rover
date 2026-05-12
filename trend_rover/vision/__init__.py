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
