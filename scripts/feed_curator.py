#!/usr/bin/env python3
"""
Zero-cost feed curator for Hamkor Top.

Pipeline:
1) Collect fresh items from Google News RSS (no API key required)
2) Enrich each item via Gemini Free Tier when GEMINI_API_KEY is set
3) Fallback to local heuristic summary when AI is unavailable
4) Save final cards to docs/feed.json

No Aizor tokens are used.
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parents[1]
FEED_PATH = BASE_DIR / "docs" / "feed.json"

FEED_SIZE = int(os.getenv("FEED_SIZE", "7"))
RSS_LANG = os.getenv("RSS_LANG", "ru")
RSS_REGION = os.getenv("RSS_REGION", "UZ")

RSS_QUERIES = [
    "IT стартапы карьера AI Узбекистан",
    "remote work career development engineering",
    "product management startups Central Asia",
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

USER_AGENT = "HamkorTopFeedBot/1.0 (+https://github.com/Seva02091995/hamkor-top)"

BADGE_RULES = [
    ("🤖 AI", ["ai", "ml", "machine learning", "llm", "генератив", "искусственный интеллект"]),
    ("🚀 Стартапы", ["startup", "funding", "venture", "seed", "series", "стартап", "инвести"]),
    ("💼 Карьера", ["career", "job", "hiring", "cv", "resume", "ваканс", "карьер", "собесед"]),
    ("🌍 Удалёнка", ["remote", "distributed", "freelance", "digital nomad", "удал", "фриланс"]),
    ("📈 Тренд", ["trend", "growth", "рынок", "report", "analytics", "аналит"]),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_pub_date(raw: str) -> datetime:
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(tz=timezone.utc)


def google_news_rss_url(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    return (
        "https://news.google.com/rss/search"
        f"?q={q}&hl={RSS_LANG}&gl={RSS_REGION}&ceid={RSS_REGION}:{RSS_LANG}"
    )


def fetch_url(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_rss_items(url: str) -> List[Dict]:
    xml_text = fetch_url(url)
    root = ET.fromstring(xml_text)
    out: List[Dict] = []

    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc_raw = item.findtext("description") or ""
        desc = strip_html(desc_raw)
        pub_raw = item.findtext("pubDate") or ""
        pub_dt = parse_pub_date(pub_raw)

        if not title or not link:
            continue

        out.append(
            {
                "title": title,
                "link": link,
                "snippet": desc,
                "published": pub_dt.isoformat(),
                "published_ts": pub_dt.timestamp(),
            }
        )

    return out


def dedupe_items(items: List[Dict]) -> List[Dict]:
    seen = set()
    result = []
    for it in sorted(items, key=lambda x: x.get("published_ts", 0), reverse=True):
        key = (it.get("link") or "").strip().lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(it)
    return result


def pick_badge(text: str) -> str:
    low = text.lower()
    for badge, keywords in BADGE_RULES:
        if any(k in low for k in keywords):
            return badge
    return "📰 Новости"


def fallback_card(item: Dict) -> Dict:
    title = item["title"].strip()
    snippet = (item.get("snippet") or "").strip()
    short = snippet[:180].rstrip(" .")
    if short:
        ru = f"{short}. Подробнее: {item['link']}"
    else:
        ru = f"Свежая публикация по теме карьеры и технологий. Подробнее: {item['link']}"

    badge = pick_badge(f"{title} {snippet}")

    return {
        "badge": badge,
        "t": {
            "ru": title,
            "uz": title,
            "en": title,
        },
        "b": {
            "ru": ru,
            "uz": ru,
            "en": ru,
        },
    }


def call_gemini(item: Dict) -> Optional[Dict]:
    if not GEMINI_API_KEY:
        return None

    prompt = (
        "Ты редактор короткой ленты Hamkor Top для аудитории 16-45 лет. "
        "Верни СТРОГО JSON без markdown и без пояснений. Формат:\n"
        "{\n"
        "  \"badge\": \"эмодзи+категория\",\n"
        "  \"t\": {\"ru\":\"...\",\"uz\":\"...\",\"en\":\"...\"},\n"
        "  \"b\": {\"ru\":\"1-2 предложения\",\"uz\":\"1-2 gap\",\"en\":\"1-2 sentences\"}\n"
        "}\n"
        "Требования: простой язык, полезность для карьеры/технологий/стартапов, "
        "без кликбейта, максимум 220 символов в каждом описании.\n\n"
        f"Заголовок: {item['title']}\n"
        f"Сниппет: {item.get('snippet','')}\n"
        f"Ссылка: {item['link']}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 350,
            "responseMimeType": "application/json",
        },
    }

    url = f"{GEMINI_URL}?key={urllib.parse.quote(GEMINI_API_KEY)}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        method="POST",
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        obj = json.loads(body)
        text = obj["candidates"][0]["content"]["parts"][0]["text"]
        card = json.loads(text)

        if not isinstance(card, dict):
            return None
        if "badge" not in card or "t" not in card or "b" not in card:
            return None

        card.setdefault("t", {})
        card.setdefault("b", {})
        for lang in ("ru", "uz", "en"):
            card["t"].setdefault(lang, item["title"])
            card["b"].setdefault(lang, fallback_card(item)["b"]["ru"])

        return card
    except Exception as e:
        log(f"[WARN] Gemini fallback for '{item['title'][:60]}...': {e}")
        return None


def build_cards(items: List[Dict]) -> List[Dict]:
    cards: List[Dict] = []
    ai_count = 0

    for item in items:
        card = call_gemini(item)
        if card is None:
            card = fallback_card(item)
        else:
            ai_count += 1
        cards.append(card)

    random.shuffle(cards)
    cards = cards[:FEED_SIZE]
    log(f"Cards prepared: total={len(cards)}, ai={ai_count}, fallback={len(cards)-ai_count}")
    return cards


def main() -> int:
    all_items: List[Dict] = []

    for q in RSS_QUERIES:
        url = google_news_rss_url(q)
        try:
            batch = fetch_rss_items(url)
            log(f"RSS '{q}': fetched {len(batch)}")
            all_items.extend(batch)
        except Exception as e:
            log(f"[WARN] RSS failed for '{q}': {e}")

    unique_items = dedupe_items(all_items)
    if not unique_items:
        raise RuntimeError("No RSS items fetched from sources")

    selected = unique_items[: max(FEED_SIZE * 3, FEED_SIZE)]
    cards = build_cards(selected)

    FEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEED_PATH.write_text(json.dumps(cards, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Feed refreshed: {len(cards)} cards written to {FEED_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"[ERROR] feed refresh failed: {exc}")
        raise
