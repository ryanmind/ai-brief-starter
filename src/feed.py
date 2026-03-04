"""RSS / Twitter / GitHub feed fetching logic."""
from __future__ import annotations

import hashlib
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
from dateutil import parser as dtparser

from src.config import (
    X_HOSTS,
    int_env,
)
from src.text_utils import (
    clean_text,
    extract_account_from_url,
    normalize_host,
    nitter_to_x_url,
    normalize_link_for_dedupe,
    parse_time,
)

logger = logging.getLogger(__name__)


_X_RESERVED_HANDLES = {
    "home",
    "explore",
    "search",
    "i",
    "messages",
    "notifications",
    "settings",
}

_twitterapi_io_cache: dict[tuple[str, str, int], tuple[list[dict[str, str]], str | None]] = {}
_twitterapi_io_cache_lock = Lock()


def is_twitterapi_io_enabled() -> bool:
    raw = os.getenv("TWITTERAPI_IO_ENABLED", "0").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def twitterapi_io_fallback_ready() -> bool:
    return is_twitterapi_io_enabled() and bool(os.getenv("TWITTERAPI_IO_KEY", "").strip())


def extract_x_handle_from_source(source: str) -> str:
    parsed = urlparse(source)
    host = normalize_host(parsed.netloc or "")
    if host not in X_HOSTS:
        return ""
    parts = [segment.strip() for segment in (parsed.path or "").split("/") if segment.strip()]
    if not parts:
        return ""
    handle = parts[0].lstrip("@").lower()
    if not handle or handle in _X_RESERVED_HANDLES:
        return ""
    return handle


def _pick_first_text(payload: Any) -> str:
    if isinstance(payload, str):
        return clean_text(payload)
    if isinstance(payload, dict):
        for key in ("full_text", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return clean_text(value)
    return ""


def _extract_twitterapi_io_tweets(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []

    candidate_keys = ("tweets", "data", "items", "results", "statuses")
    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            for nested_key in candidate_keys:
                nested_value = value.get(nested_key)
                if isinstance(nested_value, list):
                    return [item for item in nested_value if isinstance(item, dict)]
    return []


def _extract_twitterapi_io_error(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("error", "message", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return clean_text(value)[:200]
        if isinstance(value, dict):
            nested = _pick_first_text(value)
            if nested:
                return nested[:200]
    return ""


def _extract_tweet_datetime(tweet: dict[str, Any]) -> datetime | None:
    for key in ("created_at", "createdAt", "published_at", "publishedAt", "date"):
        value = tweet.get(key)
        if isinstance(value, str) and value.strip():
            try:
                dt = dtparser.parse(value)
            except Exception:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

    for key in ("timestamp", "created_timestamp"):
        value = tweet.get(key)
        if isinstance(value, (int, float)):
            ts_value = float(value)
            if ts_value > 1e12:
                ts_value /= 1000.0
            try:
                return datetime.fromtimestamp(ts_value, tz=timezone.utc)
            except Exception:
                continue
    return None


def _extract_tweet_text(tweet: dict[str, Any]) -> str:
    for key in ("full_text", "text", "content", "tweet_text", "description"):
        value = tweet.get(key)
        if isinstance(value, str) and value.strip():
            return clean_text(value)

    legacy = tweet.get("legacy")
    if isinstance(legacy, dict):
        legacy_text = _pick_first_text(legacy)
        if legacy_text:
            return legacy_text

    note_tweet = tweet.get("note_tweet")
    if isinstance(note_tweet, dict):
        note_text = _pick_first_text(note_tweet)
        if note_text:
            return note_text
    return ""


def _extract_tweet_id(tweet: dict[str, Any]) -> str:
    for key in ("id_str", "id", "tweet_id", "tweetId"):
        value = tweet.get(key)
        if value is None:
            continue
        raw = str(value).strip()
        if raw:
            return raw
    return ""


def _extract_tweet_author_handle(tweet: dict[str, Any], fallback_handle: str) -> str:
    for key in ("screen_name", "username", "user_name", "handle"):
        value = tweet.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lstrip("@")

    for key in ("user", "author"):
        candidate = tweet.get(key)
        if not isinstance(candidate, dict):
            continue
        for field in ("screen_name", "username", "user_name", "handle"):
            value = candidate.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip().lstrip("@")

    return fallback_handle


def _clone_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    return [dict(item) for item in items]


def fetch_from_twitterapi_io(
    handle: str,
    cutoff: datetime,
    per_source: int,
    source_hint: str = "",
) -> tuple[list[dict[str, str]], str | None]:
    api_key = os.getenv("TWITTERAPI_IO_KEY", "").strip()
    if not api_key:
        return [], "TWITTERAPI_IO_KEY missing"
    if not is_twitterapi_io_enabled():
        return [], "twitterapi_io disabled"

    normalized_handle = handle.strip().lstrip("@").lower()
    if not normalized_handle or normalized_handle in _X_RESERVED_HANDLES:
        return [], "invalid x handle"

    timeout = int_env("TWITTERAPI_IO_TIMEOUT", 8, min_value=2, max_value=30)
    base_url = os.getenv("TWITTERAPI_IO_BASE_URL", "https://api.twitterapi.io").strip().rstrip("/")
    endpoint = f"{base_url}/twitter/user/last_tweets"
    cache_key = (normalized_handle, cutoff.isoformat(), per_source)

    with _twitterapi_io_cache_lock:
        cached = _twitterapi_io_cache.get(cache_key)
    if cached is not None:
        cached_items, cached_error = cached
        return _clone_items(cached_items), cached_error

    try:
        response = requests.get(
            endpoint,
            headers={
                "X-API-Key": api_key,
                "Accept": "application/json",
                "User-Agent": "ai-brief-starter/1.0",
            },
            params={"userName": normalized_handle, "count": str(max(per_source, 1))},
            timeout=timeout,
        )
        response.raise_for_status()
        payload: Any = response.json()
    except requests.RequestException as exc:
        reason = f"twitterapi.io request failed: {exc}"
        with _twitterapi_io_cache_lock:
            _twitterapi_io_cache[cache_key] = ([], reason)
        return [], reason
    except ValueError as exc:
        reason = f"twitterapi.io invalid json: {exc}"
        with _twitterapi_io_cache_lock:
            _twitterapi_io_cache[cache_key] = ([], reason)
        return [], reason

    tweets = _extract_twitterapi_io_tweets(payload)
    if not tweets:
        payload_error = _extract_twitterapi_io_error(payload)
        reason = f"twitterapi.io response error: {payload_error}" if payload_error else None
        with _twitterapi_io_cache_lock:
            _twitterapi_io_cache[cache_key] = ([], reason)
        return [], reason

    parsed_items: list[dict[str, str]] = []
    for tweet in tweets:
        if len(parsed_items) >= per_source:
            break
        text = _extract_tweet_text(tweet)
        if not text:
            continue

        published_dt = _extract_tweet_datetime(tweet)
        if published_dt and published_dt < cutoff:
            continue

        tweet_id = _extract_tweet_id(tweet)
        author_handle = _extract_tweet_author_handle(tweet, fallback_handle=normalized_handle)
        raw_link = clean_text(str(tweet.get("url", "") or tweet.get("tweet_url", "") or tweet.get("permalink", "")))
        if not raw_link and tweet_id:
            raw_link = f"https://x.com/{author_handle}/status/{tweet_id}"
        if not raw_link:
            continue

        link = nitter_to_x_url(raw_link)
        title = text[:200]
        parsed_items.append(
            {
                "title": title,
                "link": link,
                "dedupe_link": link,
                "summary": text[:1000],
                "published": published_dt.isoformat() if published_dt else "",
            }
        )

    with _twitterapi_io_cache_lock:
        _twitterapi_io_cache[cache_key] = (_clone_items(parsed_items), None)

    if source_hint:
        logger.info(
            "twitterapi.io fallback success: source=%s handle=%s items=%d",
            source_hint,
            normalized_handle,
            len(parsed_items),
        )

    return parsed_items, None


def load_sources(path: str = "sources.txt") -> list[str]:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    raw_sources = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    expanded: list[str] = []
    for source in raw_sources:
        expanded.extend(expand_source_urls(source))
    return list(dict.fromkeys(expanded))


_nitter_alive_cache: list[str] | None = None


def probe_nitter_bases(bases: list[str], timeout: float = 5.0) -> list[str]:
    """探测哪些 Nitter 实例可用，返回存活列表（结果缓存）。"""
    global _nitter_alive_cache
    if _nitter_alive_cache is not None:
        return _nitter_alive_cache

    from urllib import error as urlerror, request as urlrequest

    alive: list[str] = []
    for base in bases:
        is_alive = False
        for method in ("HEAD", "GET"):
            try:
                req = urlrequest.Request(
                    f"{base}/",
                    method=method,
                    headers={"User-Agent": "ai-brief-starter/1.0"},
                )
                with urlrequest.urlopen(req, timeout=timeout):
                    is_alive = True
                    break
            except urlerror.HTTPError as exc:
                if 400 <= exc.code < 500:
                    is_alive = True
                    break
            except Exception:
                continue
        if is_alive:
            alive.append(base)
        else:
            logger.warning("nitter instance down: %s", base)
    if not alive:
        logger.error("all nitter instances are down, X/Twitter sources will be unavailable")
    else:
        logger.info("nitter alive instances: %d/%d", len(alive), len(bases))
    _nitter_alive_cache = alive
    return alive


def parse_github_changelog_feed(source_url: str) -> tuple[str, str, str, str] | None:
    parsed = urlparse(source_url)
    host = normalize_host(parsed.netloc or "")
    if host != "github.com":
        return None

    path = parsed.path.strip("/")
    match = re.match(
        r"([^/]+)/([^/]+)/commits/([^/]+)/(.+)\.atom$",
        path,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    owner, repo, branch, tracked_file = match.groups()
    return owner, repo, branch, tracked_file


def github_feed_fallback_urls(source_url: str) -> list[str]:
    feed_info = parse_github_changelog_feed(source_url)
    if not feed_info:
        return []

    owner, repo, branch, _tracked_file = feed_info
    return [
        f"https://github.com/{owner}/{repo}/releases.atom",
        f"https://github.com/{owner}/{repo}/commits/{branch}.atom",
    ]


def normalize_link_for_source(source_url: str, link: str) -> str:
    feed_info = parse_github_changelog_feed(source_url)
    if not feed_info:
        return link

    owner, repo, branch, tracked_file = feed_info
    if tracked_file.lower().endswith("changelog.md"):
        return f"https://github.com/{owner}/{repo}/blob/{branch}/{tracked_file}"
    return link


def expand_source_urls(source: str) -> list[str]:
    parsed = urlparse(source)
    host = (parsed.netloc or "").lower()

    if host in {"github.com", "www.github.com"}:
        path = (parsed.path or "").strip("/")
        match = re.match(
            r"([^/]+)/([^/]+)/blob/([^/]+)/(.+)$",
            path,
            flags=re.IGNORECASE,
        )
        if match:
            owner, repo, branch, tracked_file = match.groups()
            if tracked_file.lower().endswith("changelog.md"):
                return [f"https://github.com/{owner}/{repo}/commits/{branch}/{tracked_file}.atom"]

    if host in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
        path = (parsed.path or "").strip("/")
        handle = path.split("/", 1)[0] if path else ""
        if handle and handle.lower() not in _X_RESERVED_HANDLES:
            raw_bases = os.getenv(
                "NITTER_RSS_BASES",
                "https://nitter.net,https://nitter.poast.org,https://nitter.privacydev.net",
            )
            all_bases = [base.strip().rstrip("/") for base in raw_bases.split(",") if base.strip()]
            bases = probe_nitter_bases(list(dict.fromkeys(all_bases)))
            if not bases:
                if twitterapi_io_fallback_ready():
                    logger.warning("no alive nitter, fallback to twitterapi.io for: %s", source)
                    return [source]
                logger.warning("skipping X source (no alive nitter): %s", source)
                return []
            return [f"{base}/{handle}/rss" for base in bases]

    return [source]


def _fetch_single_source(
    source: str, cutoff: datetime, per_source: int,
) -> tuple[str, list[dict[str, str]], str | None]:
    """抓取单个 RSS 源，返回 (source_url, items, error_reason)。"""
    source_host = normalize_host(urlparse(source).netloc or "")
    source_handle = extract_x_handle_from_source(source)

    if source_host in {"x.com", "twitter.com"} and source_handle:
        fallback_items, fallback_error = fetch_from_twitterapi_io(
            handle=source_handle,
            cutoff=cutoff,
            per_source=per_source,
            source_hint=source,
        )
        return source, fallback_items, fallback_error

    active_source = source
    try:
        feed = feedparser.parse(active_source)
    except Exception as exc:
        if source_handle and source_host in X_HOSTS and twitterapi_io_fallback_ready():
            fallback_items, fallback_error = fetch_from_twitterapi_io(
                handle=source_handle,
                cutoff=cutoff,
                per_source=per_source,
                source_hint=source,
            )
            if fallback_items or fallback_error is None:
                return source, fallback_items, fallback_error
            return source, [], fallback_error
        return source, [], str(exc)

    entries = getattr(feed, "entries", [])
    bozo_exception = getattr(feed, "bozo_exception", "bozo")

    if getattr(feed, "bozo", 0) and not entries:
        for fallback_source in github_feed_fallback_urls(source):
            try:
                fallback_feed = feedparser.parse(fallback_source)
            except Exception:
                continue
            fallback_entries = getattr(fallback_feed, "entries", [])
            if getattr(fallback_feed, "bozo", 0) and not fallback_entries:
                continue
            if not fallback_entries:
                continue
            logger.info("source fallback: %s -> %s", source, fallback_source)
            active_source = fallback_source
            feed = fallback_feed
            entries = fallback_entries
            bozo_exception = getattr(fallback_feed, "bozo_exception", bozo_exception)
            break

    if getattr(feed, "bozo", 0) and not entries:
        if source_handle and source_host in X_HOSTS and twitterapi_io_fallback_ready():
            fallback_items, fallback_error = fetch_from_twitterapi_io(
                handle=source_handle,
                cutoff=cutoff,
                per_source=per_source,
                source_hint=source,
            )
            if fallback_items or fallback_error is None:
                return source, fallback_items, fallback_error
            return source, [], fallback_error
        return source, [], str(bozo_exception)
    if not entries:
        return source, [], None

    parsed_items: list[dict[str, str]] = []
    for entry in entries[:per_source]:
        title = clean_text(entry.get("title", ""))
        raw_link = (entry.get("link", "") or "").split("#")[0]
        link = normalize_link_for_source(source_url=active_source, link=raw_link)
        dedupe_link = raw_link or link
        summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
        published = parse_time(entry)

        if not title or not link:
            continue
        if published and published < cutoff:
            continue

        parsed_items.append(
            {
                "title": title[:200],
                "link": link,
                "dedupe_link": dedupe_link,
                "summary": summary[:1000],
                "published": published.isoformat() if published else "",
            }
        )
    return source, parsed_items, None


def fetch_items(
    sources: list[str], hours: int = 36, per_source: int = 30, max_workers: int = 10,
) -> list[dict[str, str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    source_stats: dict[str, int] = {"success": 0, "empty": 0, "error": 0}
    failed_sources: list[str] = []

    pool = ThreadPoolExecutor(max_workers=max_workers)
    futures: dict[Any, str] = {}
    try:
        futures = {
            pool.submit(_fetch_single_source, src, cutoff, per_source): src
            for src in sources
        }
        try:
            for future in as_completed(futures, timeout=180):
                source_hint = futures[future]
                try:
                    source, source_items, error = future.result()
                except Exception as exc:
                    source_stats["error"] += 1
                    failed_sources.append(source_hint)
                    logger.warning("source fetch crashed: %s (reason=%s)", source_hint, exc)
                    continue

                if error:
                    source_stats["error"] += 1
                    failed_sources.append(source)
                    logger.warning("source fetch failed: %s (reason=%s)", source, error)
                    continue
                if not source_items:
                    source_stats["empty"] += 1
                    continue

                source_stats["success"] += 1
                for parsed in source_items:
                    dedupe_link = parsed.get("dedupe_link", parsed.get("link", ""))
                    key = hashlib.md5(
                        (dedupe_link.split("?")[0] + "|" + parsed["title"].lower()).encode("utf-8")
                    ).hexdigest()
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append(parsed)
        except FuturesTimeoutError:
            logger.warning("source fetch timed out after 180s, pending sources will be cancelled")
        finally:
            for future, source in futures.items():
                if future.done():
                    continue
                future.cancel()
                source_stats["error"] += 1
                failed_sources.append(source)
    finally:
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            pool.shutdown(wait=False)

    logger.info(
        "source fetch stats: success=%s empty=%s error=%s total=%s",
        source_stats["success"], source_stats["empty"], source_stats["error"], len(sources),
    )
    if failed_sources:
        logger.warning("failed sources (%d): %s", len(failed_sources), ", ".join(failed_sources[:10]))

    items.sort(key=lambda x: x.get("published", ""), reverse=True)
    return items
