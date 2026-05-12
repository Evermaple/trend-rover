import sys
import pytest
from trend_rover.cli import build_parser


def test_search_parses_required_args():
    parser = build_parser()
    args = parser.parse_args([
        "search", "Pokekara",
        "--platform", "youtube",
        "--since", "2026-04-01",
        "--until", "2026-05-12",
    ])
    assert args.keyword == "Pokekara"
    assert args.platform == ["youtube"]
    assert args.since == "2026-04-01"
    assert args.until == "2026-05-12"


def test_search_parses_multi_platform():
    parser = build_parser()
    args = parser.parse_args([
        "search", "Pokekara",
        "--platform", "youtube", "x",
        "--since", "2026-04-01",
        "--until", "2026-05-12",
    ])
    assert args.platform == ["youtube", "x"]


def test_search_parses_optional_filters():
    parser = build_parser()
    args = parser.parse_args([
        "search", "Pokekara",
        "--platform", "youtube",
        "--since", "2026-04-01",
        "--until", "2026-05-12",
        "--type", "shorts",
        "--duration", "short",
        "--sort-by", "views",
        "--limit", "200",
        "--logo", "./logo.png",
        "--vision-engine", "llm",
    ])
    assert args.type == "shorts"
    assert args.duration == "short"
    assert args.sort_by == "views"
    assert args.limit == 200
    assert args.logo == "./logo.png"
    assert args.vision_engine == "llm"


def test_stats_parses_args():
    parser = build_parser()
    args = parser.parse_args([
        "stats", "Pokekara",
        "--platform", "youtube", "x",
        "--since", "2026-04-01",
        "--until", "2026-05-12",
        "--group-by", "week",
    ])
    assert args.keyword == "Pokekara"
    assert args.group_by == "week"


def test_export_parses_args():
    parser = build_parser()
    args = parser.parse_args([
        "export", "Pokekara",
        "--platform", "youtube", "x",
        "--date", "20260426",
        "--output", "./report.csv",
    ])
    assert args.date == "20260426"
    assert args.output == "./report.csv"


def test_dashboard_parses_port():
    parser = build_parser()
    args = parser.parse_args(["dashboard", "--port", "8080"])
    assert args.port == 8080
