"""Client for fetching Hanwha newsroom content via public APIs."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterator, List, Optional

import requests


LOGGER = logging.getLogger(__name__)


BASE_URL = "https://www.hanwha.co.kr"
MEDIA_LIST_ENDPOINT = f"{BASE_URL}/api/v1/news/media/list-ajax.do"


@dataclass(slots=True)
class NewsItem:
    """Normalized representation for Hanwha newsroom entries."""

    seq: str
    title: str
    category: str
    date: str
    link: str
    image_url: Optional[str]
    hashtags: List[str]


class HanwhaNewsClient:
    """Fetches press releases and other newsroom content."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout

    def fetch_press_releases(self, page: int = 1) -> List[NewsItem]:
        """Fetch a single page of press releases.

        Args:
            page: 1-indexed page number.

        Returns:
            A list of normalized :class:`NewsItem` objects.
        """

        payload = self._fetch_media_category("press", page)
        news_entries = payload.get("news", []) if isinstance(payload, dict) else []
        items = [self._normalize_media_item(entry) for entry in news_entries]
        return [item for item in items if item is not None]

    def fetch_press_releases_until(
        self, *, max_pages: Optional[int] = None
    ) -> Iterator[NewsItem]:
        """Yield press releases across pages.

        Args:
            max_pages: Maximum number of pages to fetch. If ``None`` the
                iterator runs until the API indicates there are no more pages.
        """

        page = 1
        pages_retrieved = 0

        while True:
            if max_pages is not None and pages_retrieved >= max_pages:
                break

            payload = self._fetch_media_category("press", page)
            if not payload:
                break

            news_entries = payload.get("news") if isinstance(payload, dict) else None
            if not news_entries:
                break

            for entry in news_entries:
                item = self._normalize_media_item(entry)
                if item:
                    yield item

            latest_total_page = payload.get("latestTotalPage") if isinstance(payload, dict) else None
            page += 1
            pages_retrieved += 1

            if latest_total_page is not None and page > int(latest_total_page):
                break

    def _fetch_media_category(self, category: str, page: int = 1) -> dict:
        params = {
            "category": category,
            "pageNum": page,
        }

        LOGGER.debug("Fetching media category %s page %s", category, page)

        response = self.session.get(
            MEDIA_LIST_ENDPOINT,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _normalize_media_item(self, entry: dict) -> Optional[NewsItem]:
        try:
            seq = str(entry.get("seq") or entry.get("link", ""))
            txt = entry.get("txt", {})
            title = self._clean_text(txt.get("title", "").strip())
            category = txt.get("category", entry.get("type", ""))
            date = txt.get("date", "")
            link = entry.get("link", "")
            full_link = f"{BASE_URL}{link}" if link and link.startswith("/") else link
            img = entry.get("img", {})
            image_src = img.get("src") if isinstance(img, dict) else None
            if image_src and image_src.startswith("/"):
                image_src = f"{BASE_URL}{image_src}"
            hashtags = []
            for tag in entry.get("hashtag", []) or []:
                title_value = tag.get("title") if isinstance(tag, dict) else None
                if title_value:
                    hashtags.append(self._clean_text(title_value))

            return NewsItem(
                seq=seq,
                title=title,
                category=category,
                date=date,
                link=full_link,
                image_url=image_src,
                hashtags=hashtags,
            )
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to normalize news entry: %s", exc, exc_info=True)
            return None

    @staticmethod
    def _clean_text(value: str) -> str:
        return value.replace("\r", " ").replace("\n", " ").strip()


__all__ = ["HanwhaNewsClient", "NewsItem"]
