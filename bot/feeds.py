"""RSS/Atom kaynaklarını okuyup yeni haberleri toplar."""

import calendar
import hashlib
import html
import logging
import re
import time
from dataclasses import dataclass

import feedparser
import requests
import yaml

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; KrizMasasiBot/1.0)"
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Item:
    id: str
    source: str
    tier: int
    title: str
    summary: str
    link: str
    published: float  # unix zaman damgası
    image: str = ""   # akışta varsa haberin fotoğrafı


def load_sources(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


def clean(text: str, limit: int) -> str:
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    text = " ".join(text.split())
    return text[:limit]


def item_id(link: str, title: str) -> str:
    return hashlib.sha1((link or title).encode("utf-8")).hexdigest()[:16]


def entry_image(entry) -> str:
    """Akış kaydındaki fotoğraf adresini bulur (media:content, media:thumbnail, enclosure)."""
    for media in entry.get("media_content", []):
        if media.get("url") and media.get("medium", "image") == "image" \
                and not media.get("type", "image/").startswith("video"):
            return media["url"]
    for thumb in entry.get("media_thumbnail", []):
        if thumb.get("url"):
            return thumb["url"]
    for link in entry.get("links", []):
        if link.get("rel") == "enclosure" and link.get("type", "").startswith("image") and link.get("href"):
            return link["href"]
    return ""


OG_IMAGE_RES = [
    re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\']', re.I),
]


def page_image(url: str) -> str:
    """Haber sayfasının paylaşım görselini (og:image) bulur. Bulamazsa boş döner."""
    if not url or "news.google.com" in url:
        return ""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        page = resp.text[:300_000]
        for pattern in OG_IMAGE_RES:
            if match := pattern.search(page):
                return html.unescape(match.group(1))
        return ""
    except requests.RequestException:
        return ""


def fetch_source(source: dict, max_age_hours: float) -> list[Item]:
    resp = requests.get(source["url"], headers={"User-Agent": USER_AGENT}, timeout=20)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"akış okunamadı: {feed.bozo_exception}")

    now = time.time()
    items = []
    for entry in feed.entries:
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        published = calendar.timegm(parsed) if parsed else now
        if now - published > max_age_hours * 3600:
            continue
        title = clean(entry.get("title", ""), 300)
        link = entry.get("link", "")
        if not title:
            continue
        items.append(Item(
            id=item_id(link, title),
            source=source["name"],
            tier=int(source.get("tier", 2)),
            title=title,
            summary=clean(entry.get("summary", ""), 600),
            link=link,
            published=published,
            image=entry_image(entry),
        ))
    return items


def fetch_all(sources: list[dict], max_age_hours: float) -> tuple[list[Item], list[str]]:
    """Bütün kaynakları okur. (haberler, çalışmayan kaynaklar) döner."""
    items, failed = [], []
    for source in sources:
        try:
            got = fetch_source(source, max_age_hours)
            log.info("%-25s %3d haber", source["name"], len(got))
            items.extend(got)
        except Exception as exc:  # bir kaynağın bozulması diğerlerini durdurmasın
            log.warning("%-25s HATA: %s", source["name"], exc)
            failed.append(source["name"])
    items.sort(key=lambda i: i.published, reverse=True)
    return items, failed
