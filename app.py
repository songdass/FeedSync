import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Dict, List, Tuple

import altair as alt
import feedparser
import pandas as pd
import streamlit as st
from dateutil import parser as date_parser


st.set_page_config(
    page_title="한화 뉴스 트렌드 대시보드",
    page_icon="📰",
    layout="wide",
)


LANGUAGE_CONFIG = {
    "한국어": {"hl": "ko", "gl": "KR", "ceid": "KR:ko", "timezone": timezone(timedelta(hours=9))},
    "English": {"hl": "en", "gl": "US", "ceid": "US:en", "timezone": timezone.utc},
    "日本語": {"hl": "ja", "gl": "JP", "ceid": "JP:ja", "timezone": timezone(timedelta(hours=9))},
}

STOPWORDS = {
    "한화",
    "관련",
    "기사",
    "보도",
    "때문",
    "대한",
    "2024",
    "2025",
    "기자",
    "사진",
    "제공",
    "속보",
    "오늘",
    "지난",
    "대한민국",
    "한국",
    "최근",
    "업계",
    "이번",
    "고객",
    "기업",
    "선정",
    "발표",
    "대표",
    "출시",
    "진행",
}


def build_google_news_rss(query: str, language_key: str) -> Tuple[str, timezone]:
    config = LANGUAGE_CONFIG[language_key]
    base = "https://news.google.com/rss/search"
    params = f"?q={query}&hl={config['hl']}&gl={config['gl']}&ceid={config['ceid']}"
    return f"{base}{params}", config["timezone"]


@st.cache_data(ttl=1800, show_spinner=False)
def load_news(query: str, language_key: str) -> pd.DataFrame:
    rss_url, tz = build_google_news_rss(query, language_key)
    feed = feedparser.parse(rss_url)

    records: List[Dict] = []
    for entry in feed.entries:
        published = _parse_published(entry, tz)
        summary = _clean_html(entry.get("summary", ""))
        source = _extract_source(entry)

        records.append(
            {
                "title": entry.get("title", "").strip(),
                "summary": summary,
                "link": entry.get("link"),
                "source": source,
                "published_at": published,
                "published_date": published.date() if published else None,
            }
        )

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df = df.sort_values(by="published_at", ascending=False).reset_index(drop=True)
    return df


def _parse_published(entry, tz: timezone):
    if "published_parsed" in entry and entry.published_parsed:
        dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    elif "published" in entry:
        try:
            dt = date_parser.parse(entry.published)
        except (ValueError, TypeError):
            return None
    else:
        return None

    return dt.astimezone(tz)


def _clean_html(text: str) -> str:
    return re.sub("<[^<]+?>", "", text or "").strip()


def _extract_source(entry) -> str:
    source = entry.get("source")
    if isinstance(source, dict):
        return source.get("title", "").strip()
    if hasattr(source, "title"):
        return source.title.strip()
    return entry.get("author", "").strip()


@lru_cache(maxsize=128)
def extract_keywords(text: str) -> List[str]:
    # Basic tokenization suited for Korean and English mix
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = [token.lower() for token in text.split() if len(token) > 1]
    return [token for token in tokens if token not in STOPWORDS]


def get_keyword_counts(df: pd.DataFrame, max_keywords: int = 20) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["keyword", "count"])

    counter: Counter = Counter()
    for _, row in df.iterrows():
        tokens = extract_keywords(f"{row['title']} {row['summary']}")
        counter.update(tokens)

    most_common = counter.most_common(max_keywords)
    return pd.DataFrame(most_common, columns=["keyword", "count"])


def render_header(query: str, df: pd.DataFrame):
    st.title("📰 한화 뉴스 트렌드 대시보드")
    st.caption("Google News RSS 데이터를 활용해 실시간으로 한화 관련 뉴스를 수집하고 시각화합니다.")

    metrics = st.columns(3)
    metrics[0].metric("수집된 기사 수", f"{len(df):,}")

    if not df.empty and df["published_at"].notna().any():
        latest_time = df["published_at"].dropna().max()
        metrics[1].metric("가장 최근 기사", latest_time.strftime("%Y-%m-%d %H:%M"))

        hours = (datetime.now(latest_time.tzinfo) - latest_time).total_seconds() / 3600
        freshness = f"{hours:.1f}시간 전"
        metrics[2].metric("최신성", freshness)
    else:
        metrics[1].metric("가장 최근 기사", "-")
        metrics[2].metric("최신성", "-")


def render_trend_charts(df: pd.DataFrame):
    if df.empty:
        st.warning("표시할 뉴스 데이터가 없습니다. 검색어 또는 언어를 조정해 보세요.")
        return

    with st.container():
        st.subheader("트렌드 분석")
        chart_cols = st.columns((2, 1))

        counts_by_day = (
            df.groupby("published_date")
            .size()
            .reset_index(name="articles")
            .dropna()
        )
        if not counts_by_day.empty:
            timeline_chart = (
                alt.Chart(counts_by_day)
                .mark_area(interpolate="monotone", line=True, point=True)
                .encode(
                    x=alt.X("published_date:T", title="날짜"),
                    y=alt.Y("articles:Q", title="기사 수"),
                    tooltip=["published_date:T", "articles:Q"],
                )
                .properties(height=260)
            )
            chart_cols[0].altair_chart(timeline_chart, use_container_width=True)
        else:
            chart_cols[0].info("기사 날짜 정보가 충분하지 않습니다.")

        source_counts = (
            df.groupby("source")
            .size()
            .reset_index(name="articles")
            .sort_values("articles", ascending=False)
            .head(10)
        )
        if not source_counts.empty:
            source_chart = (
                alt.Chart(source_counts)
                .mark_bar()
                .encode(
                    x=alt.X("articles:Q", title="기사 수"),
                    y=alt.Y("source:N", sort="-x", title="언론사"),
                    tooltip=["source:N", "articles:Q"],
                    color=alt.Color(
                        "articles:Q", scale=alt.Scale(scheme="blues"), legend=None
                    ),
                )
                .properties(height=260)
            )
            chart_cols[1].altair_chart(source_chart, use_container_width=True)
        else:
            chart_cols[1].info("언론사 정보가 충분하지 않습니다.")


def render_keywords(df: pd.DataFrame):
    keywords = get_keyword_counts(df)
    if keywords.empty:
        st.info("키워드 통계를 계산할 수 있는 데이터가 부족합니다.")
        return

    st.subheader("핵심 키워드")
    keyword_chart = (
        alt.Chart(keywords)
        .mark_bar()
        .encode(
            x=alt.X("count:Q", title="빈도"),
            y=alt.Y("keyword:N", sort="-x", title="키워드"),
            tooltip=["keyword:N", "count:Q"],
            color=alt.Color("count:Q", scale=alt.Scale(scheme="orangered"), legend=None),
        )
        .properties(height=400)
    )
    st.altair_chart(keyword_chart, use_container_width=True)


def render_article_feed(df: pd.DataFrame):
    st.subheader("기사 피드")
    st.caption("최신 기사부터 순차적으로 스크롤 하면서 확인할 수 있습니다.")

    if df.empty:
        st.info("표시할 기사가 없습니다.")
        return

    for _, row in df.iterrows():
        with st.container():
            st.markdown(f"#### [{row['title']}]({row['link']})")
            meta = []
            if row["source"]:
                meta.append(row["source"])
            if row["published_at"]:
                meta.append(row["published_at"].strftime("%Y-%m-%d %H:%M"))
            st.caption(" · ".join(meta))
            if row["summary"]:
                st.write(row["summary"])
            st.divider()


def main():
    st.sidebar.header("검색 설정")
    query = st.sidebar.text_input("검색어", value="한화")
    language = st.sidebar.selectbox("언어", options=list(LANGUAGE_CONFIG.keys()), index=0)

    if st.sidebar.button("데이터 새로고침"):
        load_news.clear()
        st.experimental_rerun()

    with st.spinner("뉴스를 불러오는 중입니다..."):
        df = load_news(query.strip(), language)

    render_header(query, df)
    render_trend_charts(df)
    render_keywords(df)
    render_article_feed(df)


if __name__ == "__main__":
    main()
