import tempfile
import os
import pytest
from trend_rover.config import Config, load_config


def test_default_config():
    config = Config()
    assert config.scraper_delay_min == 2
    assert config.scraper_delay_max == 5
    assert config.scraper_max_retries == 3
    assert config.vision_engine == "opencv"
    assert config.vision_threshold == 0.8
    assert config.x_cookies_file is None


def test_load_from_toml():
    toml_content = """
[scraper]
delay_min = 1
delay_max = 3
max_retries = 5

[scraper.x]
cookies_file = "/home/user/.trend-rover/x_cookies.json"

[vision]
engine = "llm"
threshold = 0.9

[vision.llm]
provider = "claude"
api_key = "sk-test"
model = "claude-sonnet-4-6"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(toml_content)
        path = f.name

    try:
        config = load_config(path)
        assert config.scraper_delay_min == 1
        assert config.scraper_delay_max == 3
        assert config.scraper_max_retries == 5
        assert config.x_cookies_file == "/home/user/.trend-rover/x_cookies.json"
        assert config.vision_engine == "llm"
        assert config.vision_threshold == 0.9
        assert config.llm_provider == "claude"
        assert config.llm_api_key == "sk-test"
        assert config.llm_model == "claude-sonnet-4-6"
    finally:
        os.unlink(path)


def test_missing_config_file_returns_defaults():
    config = load_config("/nonexistent/path/config.toml")
    assert config.scraper_delay_min == 2
