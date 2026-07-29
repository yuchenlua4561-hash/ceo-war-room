"""Refresh the public AI Cooling intelligence feed.

Market quotes remain unchanged until licensed market providers are configured.
News collection uses public RSS feeds, keeps source links and publication times,
and preserves the previous feed when every source is unavailable.
"""
from __future__ import annotations

import html
import json
import os
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dashboard.json"
TAIPEI = ZoneInfo("Asia/Taipei")
MAX_NEWS = 12

KEYWORDS = {
    "液冷散熱": (
        "liquid cooling", "direct-to-chip", "direct liquid", "immersion cooling",
        "cooling distribution unit", "thermal management", "heat rejection",
        "液冷", "水冷", "浸沒式冷卻",
    ),
    "CDU／幫浦": (
        "cdu", "pump", "pumping", "coolant distribution", "cooling distribution",
        "quick disconnect", "manifold", "幫浦", "泵", "分歧管",
    ),
    "冷板／機櫃": (
        "cold plate", "coldplate", "rack cooling", "rear door heat exchanger",
        "high density rack", "冷板", "高密度機櫃",
    ),
    "資料中心": (
        "data center", "datacenter", "ai factory", "hyperscale", "gigawatt",
        "資料中心", "ai 工廠",
    ),
}

COMPETITORS = {
    "Schneider Electric／Motivair": ("schneider", "motivair"),
    "CoolIT Systems": ("coolit",),
    "Vertiv": ("vertiv",),
    "Boyd": ("boyd",),
    "Delta Electronics": ("delta electronics", "台達"),
    "STULZ": ("stulz",),
    "nVent": ("nvent",),
    "Johnson Controls": ("johnson controls",),
}

DIRECT_FEEDS = (
    ("NVIDIA Blog", "https://blogs.nvidia.com/feed/"),
    ("NVIDIA Newsroom", "https://nvidianews.nvidia.com/rss.xml"),
    ("CoolIT Systems", "https://www.coolitsystems.com/feed/"),
    ("Schneider Electric Blog", "https://blog.se.com/feed/"),
)

GOOGLE_QUERIES = (
    '"AI data center" ("liquid cooling" OR CDU OR "cold plate") when:7d',
    '("cooling distribution unit" OR "liquid cooling pump") data center when:14d',
    '(Motivair OR CoolIT OR Vertiv OR Boyd OR STULZ OR nVent) cooling when:14d',
    'AI server (thermal OR cooling OR coolant) supply chain when:7d',
)


def google_news_url(query: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )


def strip_markup(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def published_at(value: str) -> datetime:
    if value:
        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(TAIPEI)
        except (TypeError, ValueError):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
                    TAIPEI
                )
            except ValueError:
                pass
    return datetime.now(TAIPEI)


def child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node.iter():
        if child.tag.rsplit("}", 1)[-1] in names and child.text:
            return child.text.strip()
    return ""


def parse_feed(url: str) -> list[dict]:
    request = Request(
        url,
        headers={
            "User-Agent": "CEO-War-Room/1.0 (+public market intelligence)",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )
    with urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())
    nodes = [
        node for node in root.iter()
        if node.tag.rsplit("}", 1)[-1] in {"item", "entry"}
    ]
    entries = []
    for node in nodes[:30]:
        link = child_text(node, ("link",))
        if not link:
            for child in node.iter():
                if child.tag.rsplit("}", 1)[-1] == "link" and child.attrib.get("href"):
                    link = child.attrib["href"]
                    break
        entries.append(
            {
                "title": child_text(node, ("title",)),
                "summary": child_text(node, ("description", "summary", "content")),
                "published": child_text(node, ("pubDate", "published", "updated")),
                "source": child_text(node, ("source",)),
                "link": link,
            }
        )
    return entries


def category_for(text: str) -> str | None:
    lowered = text.casefold()
    for category, words in KEYWORDS.items():
        if any(word.casefold() in lowered for word in words):
            return category
    return None


def collect_news() -> tuple[list[dict], list[str]]:
    now = datetime.now(TAIPEI)
    cutoff = now - timedelta(days=21)
    sources = list(DIRECT_FEEDS) + [
        ("Google News", google_news_url(query)) for query in GOOGLE_QUERIES
    ]
    articles: list[dict] = []
    failures: list[str] = []

    for fallback_source, url in sources:
        try:
            entries = parse_feed(url)
        except Exception as error:
            failures.append(f"{fallback_source}: {type(error).__name__}")
            continue
        for entry in entries:
            headline = strip_markup(entry["title"])
            summary = strip_markup(entry["summary"])
            category = category_for(f"{headline} {summary}")
            when = published_at(entry["published"])
            link = entry["link"]
            if not headline or not category or when < cutoff:
                continue
            if urlparse(link).scheme not in {"http", "https"}:
                continue
            articles.append(
                {
                    "category": category,
                    "headline": headline,
                    "summary": summary[:260] or "請開啟來源閱讀完整內容。",
                    "source": strip_markup(entry["source"]) or fallback_source,
                    "published_at": when.isoformat(timespec="seconds"),
                    "url": link,
                    "data_type": "live",
                    "data_label": "公開情報",
                }
            )

    unique: dict[str, dict] = {}
    for item in sorted(articles, key=lambda x: x["published_at"], reverse=True):
        key = re.sub(r"\W+", "", item["headline"].casefold())
        unique.setdefault(key, item)
    return list(unique.values())[:MAX_NEWS], failures


def competitor_updates(news: list[dict], previous: list[dict]) -> list[dict]:
    previous_by_company = {item["company"]: item for item in previous}
    updates: list[dict] = []
    for company, aliases in COMPETITORS.items():
        match = next(
            (
                item
                for item in news
                if any(alias in item["headline"].casefold() for alias in aliases)
            ),
            None,
        )
        if match:
            updates.append(
                {
                    "company": company,
                    "product": match["category"],
                    "move": match["headline"],
                    "implication": (
                        f"公開情報更新於 {match['published_at']}；"
                        "請由來源頁確認產品規格、客戶與量產時程。"
                    ),
                    "url": match["url"],
                }
            )
        elif company in previous_by_company:
            updates.append(previous_by_company[company])
    return updates


def validate(data: dict) -> None:
    required = {
        "ceo_summary", "risk", "markets", "liquid_cooling_pumps",
        "competitors", "news", "supply_chain",
    }
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Missing dashboard fields: {sorted(missing)}")
    for item in data["news"]:
        if urlparse(item.get("url", "")).scheme not in {"http", "https"}:
            raise ValueError("Every news item must have an HTTP(S) source URL")


def collect(previous: dict) -> dict:
    data = deepcopy(previous)
    news, failures = collect_news()
    if news:
        data["news"] = news
        data["competitors"] = competitor_updates(news, previous["competitors"])
        data["intel_updated_at"] = datetime.now(TAIPEI).isoformat(timespec="seconds")
        data["intel_status"] = {
            "state": "ok" if not failures else "partial",
            "collected": len(news),
            "source_failures": failures[:5],
        }
    else:
        data["intel_status"] = {
            "state": "fallback",
            "collected": len(previous.get("news", [])),
            "source_failures": failures[:5],
            "message": "所有情報來源暫時無法使用；保留前次已驗證內容。",
        }

    if not os.getenv("MARKET_API_KEY"):
        print(
            "::warning title=Market data not refreshed::"
            "Market API is not configured; verified market quotes were preserved."
        )
    return data


def main() -> None:
    previous = json.loads(OUTPUT.read_text(encoding="utf-8"))
    data = collect(previous)
    validate(data)
    OUTPUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
