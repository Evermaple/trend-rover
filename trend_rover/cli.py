import argparse
import sys
from datetime import date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trend-rover",
        description="Track brand keyword trends across social media",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- search ---
    search_p = subparsers.add_parser("search", help="Search and store feeds")
    search_p.add_argument("keyword", help="Keyword to search for")
    search_p.add_argument("--platform", nargs="+", default=["youtube", "x"],
                          choices=["youtube", "x"], metavar="PLATFORM",
                          help="Platforms to search (youtube, x)")
    search_p.add_argument("--since", required=True, help="Start date YYYY-MM-DD")
    search_p.add_argument("--until", required=True, help="End date YYYY-MM-DD")
    search_p.add_argument("--type", dest="type", default=None,
                          choices=["video", "shorts", "live"],
                          help="YouTube video type filter")
    search_p.add_argument("--duration", default=None,
                          choices=["short", "medium", "long"],
                          help="YouTube duration filter")
    search_p.add_argument("--sort-by", dest="sort_by", default=None,
                          choices=["relevance", "upload_date", "views", "rating"],
                          help="YouTube sort order")
    search_p.add_argument("--limit", type=int, default=50,
                          help="Max results per platform (default 50)")
    search_p.add_argument("--logo", default=None,
                          help="Path to logo image for thumbnail matching")
    search_p.add_argument("--vision-engine", dest="vision_engine",
                          default=None, choices=["opencv", "llm"],
                          help="Logo detection engine")
    search_p.add_argument("--vision-threshold", dest="vision_threshold",
                          type=float, default=0.8,
                          help="OpenCV match threshold (default 0.8)")
    search_p.add_argument("--json", action="store_true", dest="output_json",
                          help="Output results as JSON")

    # --- stats ---
    stats_p = subparsers.add_parser("stats", help="Show aggregated stats")
    stats_p.add_argument("keyword")
    stats_p.add_argument("--platform", nargs="+", default=["youtube", "x"],
                         choices=["youtube", "x"], metavar="PLATFORM")
    stats_p.add_argument("--since", default=None, help="Start date YYYY-MM-DD")
    stats_p.add_argument("--until", default=None, help="End date YYYY-MM-DD")
    stats_p.add_argument("--group-by", dest="group_by", default="day",
                         choices=["day", "week", "month"])
    stats_p.add_argument("--json", action="store_true", dest="output_json")

    # --- export ---
    export_p = subparsers.add_parser("export", help="Export summary CSV")
    export_p.add_argument("keyword")
    export_p.add_argument("--platform", nargs="+", default=["youtube", "x"],
                          choices=["youtube", "x"], metavar="PLATFORM")
    export_p.add_argument("--date", required=True, help="Date YYYYMMDD")
    export_p.add_argument("--output", required=True, help="Output CSV path")

    # --- dashboard ---
    dash_p = subparsers.add_parser("dashboard", help="Launch Gradio dashboard")
    dash_p.add_argument("--port", type=int, default=7860)

    return parser


def _cmd_search(args) -> int:
    from trend_rover.orchestrator import run_search

    start = date.fromisoformat(args.since)
    end = date.fromisoformat(args.until)

    result = run_search(
        keyword=args.keyword,
        platforms=args.platform,
        start_date=start,
        end_date=end,
        logo_path=args.logo,
        vision_engine=args.vision_engine,
        vision_threshold=args.vision_threshold,
        limit=args.limit,
        video_type=args.type,
        duration=args.duration,
        sort_by=args.sort_by,
    )

    if args.output_json:
        import json
        print(json.dumps({"total": result.total, "by_platform": result.by_platform}))
    else:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title=f"Search results for '{args.keyword}'")
        table.add_column("Platform")
        table.add_column("Found", justify="right")
        for platform, count in result.by_platform.items():
            table.add_row(platform.upper(), str(count))
        table.add_row("[bold]Total[/bold]", f"[bold]{result.total}[/bold]")
        console.print(table)
    return 0


def _cmd_stats(args) -> int:
    from trend_rover.orchestrator import run_stats

    start = date.fromisoformat(args.since) if args.since else None
    end = date.fromisoformat(args.until) if args.until else None

    result = run_stats(
        keyword=args.keyword,
        platforms=args.platform,
        start_date=start,
        end_date=end,
    )

    if args.output_json:
        import json
        print(json.dumps(result.platform_totals))
    else:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title=f"Stats for '{result.keyword}'")
        table.add_column("Metric")
        for platform in args.platform:
            table.add_column(platform.upper(), justify="right")
        metrics = ["count", "views", "likes", "comments", "shares", "bookmarks"]
        labels = ["帖子数量", "查看次数", "点赞", "评论", "转发", "收藏"]
        for metric, label in zip(metrics, labels):
            row = [label]
            for platform in args.platform:
                row.append(str(result.platform_totals.get(platform, {}).get(metric, 0)))
            table.add_row(*row)
        console.print(table)
    return 0


def _cmd_export(args) -> int:
    from trend_rover.orchestrator import run_export
    run_export(
        keyword=args.keyword,
        platforms=args.platform,
        date_str=args.date,
        output_path=args.output,
    )
    print(f"Exported to {args.output}")
    return 0


def _cmd_dashboard(args) -> int:
    from trend_rover.dashboard.app import launch
    launch(port=args.port)
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {
        "search": _cmd_search,
        "stats": _cmd_stats,
        "export": _cmd_export,
        "dashboard": _cmd_dashboard,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
