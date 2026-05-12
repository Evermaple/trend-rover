from datetime import date
from typing import Optional


_PLATFORM_DISPLAY_TO_KEY = {"YouTube": "youtube", "X": "x"}

_STAT_ROWS = [
    ("帖子数量", "count"),
    ("查看次数", "views"),
    ("点赞", "likes"),
    ("评论", "comments"),
    ("转发", "shares"),
    ("收藏", "bookmarks"),
]


def format_stats_for_display(
    platform_totals: dict,
    platforms: list[str],
) -> list[list]:
    rows = []
    for label, key in _STAT_ROWS:
        row = [label]
        for platform in platforms:
            row.append(platform_totals.get(platform, {}).get(key, 0))
        rows.append(row)
    return rows


def validate_date_range(since: str, until: str) -> Optional[str]:
    try:
        start = date.fromisoformat(since)
        end = date.fromisoformat(until)
    except (ValueError, TypeError):
        return "Invalid date format. Use YYYY-MM-DD."
    if end < start:
        return "End date must be after or equal to start date."
    return None


def platforms_from_checkboxes(selected: list[str]) -> list[str]:
    return [_PLATFORM_DISPLAY_TO_KEY[s] for s in selected if s in _PLATFORM_DISPLAY_TO_KEY]


def launch(port: int = 7860) -> None:
    import gradio as gr
    from datetime import datetime
    from trend_rover.orchestrator import run_search, run_stats, run_export, SearchResult

    today = datetime.now().strftime("%Y-%m-%d")
    month_ago = datetime.now().replace(day=1).strftime("%Y-%m-%d")

    with gr.Blocks(title="Trend Rover") as demo:
        gr.Markdown("# Trend Rover\nTrack brand keyword trends across YouTube and X")

        with gr.Tab("Search"):
            with gr.Row():
                search_keyword = gr.Textbox(label="Keyword", placeholder="e.g. Pokekara")
                search_platforms = gr.CheckboxGroup(["YouTube", "X"], value=["YouTube", "X"], label="Platforms")
            with gr.Row():
                search_since = gr.Textbox(label="Since (YYYY-MM-DD)", value=month_ago)
                search_until = gr.Textbox(label="Until (YYYY-MM-DD)", value=today)
            with gr.Accordion("YouTube Filters", open=False):
                yt_type = gr.Dropdown(["", "video", "shorts", "live"], label="Type", value="")
                yt_duration = gr.Dropdown(["", "short", "medium", "long"], label="Duration", value="")
                yt_sort = gr.Dropdown(["relevance", "upload_date", "views", "rating"], label="Sort By", value="relevance")
                yt_limit = gr.Slider(10, 500, value=50, step=10, label="Limit per platform")
            with gr.Accordion("Logo Detection (YouTube)", open=False):
                logo_file = gr.File(label="Upload Logo Image", file_types=["image"])
                vision_engine = gr.Radio(["opencv", "llm"], value="opencv", label="Detection Engine")
            search_btn = gr.Button("Search & Store", variant="primary")
            search_status = gr.Textbox(label="Status", interactive=False)
            search_result_table = gr.Dataframe(headers=["Platform", "Found"], label="Results")

            def do_search(keyword, platforms_sel, since, until, type_, duration, sort_by, limit, logo, engine):
                error = validate_date_range(since, until)
                if error:
                    return error, []
                if not keyword.strip():
                    return "Please enter a keyword.", []
                platforms = platforms_from_checkboxes(platforms_sel)
                logo_path = logo.name if logo else None
                try:
                    result: SearchResult = run_search(
                        keyword=keyword,
                        platforms=platforms,
                        start_date=date.fromisoformat(since),
                        end_date=date.fromisoformat(until),
                        logo_path=logo_path,
                        vision_engine=engine if logo_path else None,
                        limit=int(limit),
                        video_type=type_ or None,
                        duration=duration or None,
                        sort_by=sort_by if sort_by != "relevance" else None,
                    )
                    rows = [[p.upper(), c] for p, c in result.by_platform.items()]
                    return f"Done. {result.total} feeds stored.", rows
                except Exception as e:
                    return f"Error: {e}", []

            search_btn.click(
                do_search,
                inputs=[search_keyword, search_platforms, search_since, search_until,
                        yt_type, yt_duration, yt_sort, yt_limit, logo_file, vision_engine],
                outputs=[search_status, search_result_table],
            )

        with gr.Tab("Stats"):
            with gr.Row():
                stats_keyword = gr.Textbox(label="Keyword")
                stats_platforms = gr.CheckboxGroup(["YouTube", "X"], value=["YouTube", "X"], label="Platforms")
            with gr.Row():
                stats_since = gr.Textbox(label="Since (YYYY-MM-DD)", value=month_ago)
                stats_until = gr.Textbox(label="Until (YYYY-MM-DD)", value=today)
            stats_btn = gr.Button("Get Stats", variant="primary")
            stats_table = gr.Dataframe(label="Aggregated Stats")

            def do_stats(keyword, platforms_sel, since, until):
                error = validate_date_range(since, until)
                if error:
                    return [[error]]
                platforms = platforms_from_checkboxes(platforms_sel)
                result = run_stats(
                    keyword=keyword,
                    platforms=platforms,
                    start_date=date.fromisoformat(since) if since else None,
                    end_date=date.fromisoformat(until) if until else None,
                )
                headers = ["指标"] + [p.upper() for p in platforms]
                rows = format_stats_for_display(result.platform_totals, platforms)
                return gr.Dataframe(value=rows, headers=headers)

            stats_btn.click(do_stats, inputs=[stats_keyword, stats_platforms, stats_since, stats_until], outputs=[stats_table])

        with gr.Tab("Detail"):
            with gr.Row():
                detail_keyword = gr.Textbox(label="Keyword")
                detail_platform = gr.Dropdown(["youtube", "x"], label="Platform", value="youtube")
            detail_btn = gr.Button("Load Feeds")
            detail_table = gr.Dataframe(
                headers=["ID", "Title", "Author", "Published", "Views", "Likes", "Comments", "Shares", "Logo"],
                label="Feed List",
            )

            def do_detail(keyword, platform):
                from trend_rover.storage.db import Database
                db = Database()
                feeds = db.query(keyword=keyword, platform=platform)
                db.close()
                rows = [
                    [f.feed_id, f.title[:60], f.author, f.published_at.strftime("%Y-%m-%d"),
                     f.views, f.likes, f.comments, f.shares, "✓" if f.logo_matched else ""]
                    for f in feeds
                ]
                return rows

            detail_btn.click(do_detail, inputs=[detail_keyword, detail_platform], outputs=[detail_table])

        with gr.Tab("Export"):
            with gr.Row():
                export_keyword = gr.Textbox(label="Keyword")
                export_platforms = gr.CheckboxGroup(["YouTube", "X"], value=["YouTube", "X"], label="Platforms")
            export_date = gr.Textbox(label="Date (YYYYMMDD)", placeholder="20260426")
            export_btn = gr.Button("Export CSV", variant="primary")
            export_file = gr.File(label="Download CSV")

            def do_export(keyword, platforms_sel, date_str):
                import tempfile, os
                platforms = platforms_from_checkboxes(platforms_sel)
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w", encoding="utf-8") as f:
                    path = f.name
                run_export(keyword=keyword, platforms=platforms, date_str=date_str, output_path=path)
                return path

            export_btn.click(do_export, inputs=[export_keyword, export_platforms, export_date], outputs=[export_file])

    demo.launch(server_port=port)
