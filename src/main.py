"""Command line entry-point for exporting Hanwha updates into Excel."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from hanwha.api import HanwhaNewsClient
from hanwha.excel import ExcelExporter
from hanwha.sns import HanwhaSocialClient, TweetItem, TwitterClient


LOGGER = logging.getLogger("hanwha")


def positive_int(value: str) -> int:
    ivalue = int(value)
    if ivalue <= 0:
        raise argparse.ArgumentTypeError("Value must be positive")
    return ivalue


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Hanwha newsroom and social updates to Excel")

    parser.add_argument(
        "--press-pages",
        type=positive_int,
        default=1,
        help="Number of press-release pages to fetch (12 items per page)",
    )
    parser.add_argument(
        "--social-pages",
        type=positive_int,
        default=1,
        help="Number of social feed pages to fetch",
    )
    parser.add_argument(
        "--twitter-user",
        dest="twitter_users",
        action="append",
        default=["hanwha_official"],
        help="Twitter username to scrape without @. Repeat flag for multiple accounts",
    )
    parser.add_argument(
        "--twitter-limit",
        type=positive_int,
        default=20,
        help="Max tweets to collect per Twitter account",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("hanwha_updates.xlsx"),
        help="Path for the resulting Excel file",
    )
    parser.add_argument(
        "--no-twitter",
        action="store_true",
        help="Skip Twitter scraping",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )

    return parser.parse_args(argv)


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="[%(levelname)s] %(message)s",
    )


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    configure_logging(args.log_level)

    news_client = HanwhaNewsClient()
    social_client = HanwhaSocialClient()
    exporter = ExcelExporter()

    LOGGER.info("Fetching press releases (pages=%s)", args.press_pages)
    press_releases = list(news_client.fetch_press_releases_until(max_pages=args.press_pages))
    LOGGER.info("Collected %s press releases", len(press_releases))

    LOGGER.info("Fetching social feed (pages=%s)", args.social_pages)
    social_posts = list(social_client.fetch_social_posts_until(max_pages=args.social_pages))
    LOGGER.info("Collected %s social posts", len(social_posts))

    tweets: List[TweetItem] = []
    if not args.no_twitter and args.twitter_users:
        try:
            twitter_client = TwitterClient()
        except RuntimeError as exc:
            LOGGER.warning("Twitter scraping disabled: %s", exc)
        else:
            for username in args.twitter_users:
                LOGGER.info("Fetching tweets for @%s (limit=%s)", username, args.twitter_limit)
                account_tweets = twitter_client.fetch_user_tweets(username, limit=args.twitter_limit)
                LOGGER.info("Collected %s tweets for @%s", len(account_tweets), username)
                tweets.extend(account_tweets)
    else:
        LOGGER.info("Skipping Twitter scraping")

    output_path = exporter.export(press_releases, social_posts, tweets, args.output)
    LOGGER.info("Excel written to %s", output_path)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
