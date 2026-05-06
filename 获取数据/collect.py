from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from 获取数据.monopolygo_wiki.collector import LISTING_URL, SUPPLEMENTAL_SOURCE_PAGES
from 获取数据.monopolygo_wiki.processor import MonopolyGoWikiRawProcessor
from 获取数据.monopolygo_wiki.raw import MonopolyGoWikiRawCollector


DEFAULT_GAME_DATA_DIR = PROJECT_ROOT / "数据" / "monopolygo"
DEFAULT_RAW_OUTPUT = DEFAULT_GAME_DATA_DIR / "monopolygo_wiki_raw.json"
DEFAULT_PROCESSED_OUTPUT = DEFAULT_GAME_DATA_DIR / "monopolygo_wiki_events.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect competitor event calendars.")
    subparsers = parser.add_subparsers(dest="competitor")

    monopoly = subparsers.add_parser(
        "monopolygo-wiki",
        help="Collect Monopoly GO events from monopolygo.wiki.",
    )
    monopoly.add_argument("--pages", type=int, default=1, help="Number of listing pages to scan.")
    monopoly.add_argument(
        "--supplemental-pages",
        type=int,
        default=SUPPLEMENTAL_SOURCE_PAGES,
        help="Number of pages to scan for each supplemental listing source.",
    )
    monopoly.add_argument("--max-posts", type=int, default=None, help="Maximum detail posts to parse.")
    monopoly.add_argument(
        "--source-url",
        default=LISTING_URL,
        help="Listing page URL to start from.",
    )
    monopoly.add_argument(
        "--raw-output",
        default=str(DEFAULT_RAW_OUTPUT),
        help="Path to the cached raw JSON file.",
    )
    monopoly.add_argument(
        "--processed-output",
        default=str(DEFAULT_PROCESSED_OUTPUT),
        help="Path to the processed JSON file.",
    )
    monopoly.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds.")
    monopoly.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between detail page requests, in seconds.",
    )
    monopoly.add_argument(
        "--refresh-raw",
        action="store_true",
        help="Download raw pages again instead of reusing the raw cache.",
    )
    monopoly.add_argument(
        "--process-only",
        action="store_true",
        help="Only process an existing raw cache. Fails if the raw file does not exist.",
    )

    args = parser.parse_args()
    if args.competitor is None:
        parser.print_help()
        return

    if args.competitor == "monopolygo-wiki":
        raw_path = Path(args.raw_output)
        if args.process_only and not raw_path.exists():
            raise FileNotFoundError(f"Raw cache does not exist: {raw_path}")

        if raw_path.exists() and not args.refresh_raw:
            raw_payload = json.loads(raw_path.read_text(encoding="utf-8"))
            print(f"Reused raw cache from {raw_path}")
        else:
            if args.process_only:
                raise FileNotFoundError(f"Raw cache does not exist: {raw_path}")
            raw_payload = MonopolyGoWikiRawCollector(timeout=args.timeout, request_delay=args.delay).collect_raw(
                pages=args.pages,
                max_posts=args.max_posts,
                source_url=args.source_url,
                supplemental_source_pages=args.supplemental_pages,
            )
            write_json(raw_path, raw_payload)
            print(f"Saved raw cache with {len(raw_payload['posts'])} posts to {raw_path}")

        payload = MonopolyGoWikiRawProcessor().process(raw_payload)
    else:
        raise ValueError(f"Unsupported competitor: {args.competitor}")

    processed_path = Path(args.processed_output)
    write_json(processed_path, payload)
    print(f"Saved {len(payload['events'])} processed events to {processed_path}")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
