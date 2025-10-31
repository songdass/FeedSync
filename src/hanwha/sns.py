"""Social media collectors for Hanwha group updates."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, List, Optional

import requests

from .api import BASE_URL, MEDIA_LIST_ENDPOINT


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class SocialItem:
    seq: str
    platform: str
    title: str
    date: str
    link: str
    image_url: Optional[str]
    hashtags: List[str]


@dataclass(slots=True)
class TweetItem:
    tweet_id: str
    username: str
    display_name: str
    content: str
    created_at: datetime
    url: str
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int


class HanwhaSocialClient:
    """Fetches Hanwha social feed entries via the newsroom API."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_social_posts(self, page: int = 1) -> List[SocialItem]:
        payload = self._fetch_category(page)
        entries = payload.get("news", []) if isinstance(payload, dict) else []
        items = [self._normalize_social_entry(entry) for entry in entries]
        return [item for item in items if item is not None]

    def fetch_social_posts_until(
        self, *, max_pages: Optional[int] = None
    ) -> Iterator[SocialItem]:
        page = 1
        retrieved = 0

        while True:
            if max_pages is not None and retrieved >= max_pages:
                break

            payload = self._fetch_category(page)
            if not payload:
                break

            entries = payload.get("news") if isinstance(payload, dict) else None
            if not entries:
                break

            for entry in entries:
                item = self._normalize_social_entry(entry)
                if item:
                    yield item

            latest_total_page = payload.get("latestTotalPage") if isinstance(payload, dict) else None
            page += 1
            retrieved += 1

            if latest_total_page is not None and page > int(latest_total_page):
                break

    def _fetch_category(self, page: int) -> dict:
        params = {
            "category": "social",
            "pageNum": page,
        }
        LOGGER.debug("Fetching social feed page %s", page)
        response = self.session.get(
            MEDIA_LIST_ENDPOINT,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _normalize_social_entry(self, entry: dict) -> Optional[SocialItem]:
        try:
            seq = str(entry.get("seq") or entry.get("link", ""))
            platform = entry.get("social") or entry.get("type", "")
            txt = entry.get("txt", {})
            title = self._clean_text(txt.get("title", ""))
            date = txt.get("date", "")
            link = entry.get("link", "")
            image_src = None
            img = entry.get("img") or {}
            if isinstance(img, dict):
                image_src = img.get("src")
            if image_src and image_src.startswith("/"):
                image_src = f"{BASE_URL}{image_src}"
            hashtags = []
            for tag in entry.get("hashtag", []) or []:
                title_value = tag.get("title") if isinstance(tag, dict) else None
                if title_value:
                    hashtags.append(self._clean_text(title_value))

            return SocialItem(
                seq=seq,
                platform=platform,
                title=title,
                date=date,
                link=link,
                image_url=image_src,
                hashtags=hashtags,
            )
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to normalize social entry: %s", exc, exc_info=True)
            return None

    @staticmethod
    def _clean_text(value: str) -> str:
        return value.replace("\r", " ").replace("\n", " ").strip()


class TwitterClient:
    """Wrapper around snscrape to fetch tweets without API keys."""

    def __init__(self) -> None:
        try:
            import snscrape.modules.twitter as sntwitter  # type: ignore

            self._scraper_mod = sntwitter
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError(
                "snscrape is required for Twitter scraping. Install it via `pip install snscrape`."
            ) from exc

    def fetch_user_tweets(
        self,
        username: str,
        *,
        limit: int = 50,
    ) -> List[TweetItem]:
        """Return latest tweets from a given username."""

        scraper = self._scraper_mod.TwitterUserScraper(username)
        tweets: List[TweetItem] = []

        for idx, tweet in enumerate(scraper.get_items()):
            if idx >= limit:
                break
            tweets.append(
                TweetItem(
                    tweet_id=str(tweet.id),
                    username=tweet.user.username,
                    display_name=tweet.user.displayname,
                    content=tweet.rawContent,
                    created_at=tweet.date,
                    url=f"https://twitter.com/{tweet.user.username}/status/{tweet.id}",
                    like_count=getattr(tweet, "likeCount", 0) or 0,
                    retweet_count=getattr(tweet, "retweetCount", 0) or 0,
                    reply_count=getattr(tweet, "replyCount", 0) or 0,
                    quote_count=getattr(tweet, "quoteCount", 0) or 0,
                )
            )

        return tweets


__all__ = [
    "HanwhaSocialClient",
    "SocialItem",
    "TwitterClient",
    "TweetItem",
]
