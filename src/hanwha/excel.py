"""Excel export helpers."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import pandas as pd

from .api import NewsItem
from .sns import SocialItem, TweetItem


class ExcelExporter:
    """Write collected datasets into a multi-sheet Excel file."""

    def export(
        self,
        press_releases: Sequence[NewsItem],
        social_posts: Sequence[SocialItem],
        tweets: Sequence[TweetItem],
        output_path: Path,
    ) -> Path:
        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            if press_releases:
                df_press = pd.DataFrame([asdict(item) for item in press_releases])
            else:
                df_press = pd.DataFrame(columns=["seq", "title", "category", "date", "link", "image_url", "hashtags"])
            df_press.to_excel(writer, sheet_name="PressReleases", index=False)

            if social_posts:
                df_social = pd.DataFrame([asdict(item) for item in social_posts])
            else:
                df_social = pd.DataFrame(columns=["seq", "platform", "title", "date", "link", "image_url", "hashtags"])
            df_social.to_excel(writer, sheet_name="SocialMedia", index=False)

            if tweets:
                df_tweets = pd.DataFrame([self._tweet_to_dict(item) for item in tweets])
            else:
                df_tweets = pd.DataFrame(
                    columns=[
                        "tweet_id",
                        "username",
                        "display_name",
                        "content",
                        "created_at",
                        "url",
                        "like_count",
                        "retweet_count",
                        "reply_count",
                        "quote_count",
                    ]
                )
            df_tweets.to_excel(writer, sheet_name="Twitter", index=False)

        return output_path

    @staticmethod
    def _tweet_to_dict(item: TweetItem) -> dict:
        data = asdict(item)
        data["created_at"] = item.created_at.isoformat()
        return data


__all__ = ["ExcelExporter"]
