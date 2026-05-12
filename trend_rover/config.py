import tomllib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    scraper_delay_min: float = 2.0
    scraper_delay_max: float = 5.0
    scraper_max_retries: int = 3
    x_cookies_file: Optional[str] = None
    vision_engine: str = "opencv"
    vision_threshold: float = 0.8
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None


def load_config(path: str = None) -> Config:
    if path is None:
        import os
        path = os.path.expanduser("~/.trend-rover/config.toml")

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        return Config()

    scraper = data.get("scraper", {})
    x_section = scraper.get("x", {})
    vision = data.get("vision", {})
    llm = vision.get("llm", {})

    return Config(
        scraper_delay_min=scraper.get("delay_min", 2.0),
        scraper_delay_max=scraper.get("delay_max", 5.0),
        scraper_max_retries=scraper.get("max_retries", 3),
        x_cookies_file=x_section.get("cookies_file"),
        vision_engine=vision.get("engine", "opencv"),
        vision_threshold=vision.get("threshold", 0.8),
        llm_provider=llm.get("provider"),
        llm_api_key=llm.get("api_key"),
        llm_model=llm.get("model"),
    )
