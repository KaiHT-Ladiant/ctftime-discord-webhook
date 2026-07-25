#!/usr/bin/env python3
"""Fetch newly listed CTFtime events and post them to a Discord webhook."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CTFTIME_API = "https://ctftime.org/api/v1/events/"
USER_AGENT = "ctftime-discord-webhook/1.0 (+https://github.com/ctftime-discord-webhook)"
SEEN_PATH = Path(__file__).resolve().parent / "data" / "seen_events.json"
DEFAULT_LOOKAHEAD_DAYS = 90
DEFAULT_TIMEZONE = "Asia/Seoul"
DEFAULT_LIMIT = 100
# Soft red accent, close to common CTFtime branding
EMBED_COLOR = 0xE74C3C


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def load_seen() -> set[int]:
    if not SEEN_PATH.exists():
        return set()
    data = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    return {int(x) for x in data.get("ids", [])}


def save_seen(ids: set[int]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ids": sorted(ids),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    SEEN_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def http_get_json(url: str) -> list | dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(url: str, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def fetch_upcoming_events(lookahead_days: int, limit: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    finish = now + timedelta(days=lookahead_days)
    query = urllib.parse.urlencode(
        {
            "limit": limit,
            "start": int(now.timestamp()),
            "finish": int(finish.timestamp()),
        }
    )
    events = http_get_json(f"{CTFTIME_API}?{query}")
    if not isinstance(events, list):
        raise RuntimeError(f"Unexpected CTFtime response type: {type(events)}")
    return events


def format_local_time(iso_value: str, tz_name: str) -> str:
    dt = datetime.fromisoformat(iso_value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone(ZoneInfo(tz_name))
    return local.strftime("%b %d, %Y %I:%M%p")


def build_embed(event: dict, tz_name: str) -> dict:
    title = event.get("title") or "Untitled CTF"
    start = format_local_time(event["start"], tz_name)
    end = format_local_time(event["finish"], tz_name)
    ctftime_url = (event.get("ctftime_url") or "").strip()
    event_url = (event.get("url") or "").strip()
    link = ctftime_url or event_url
    logo = (event.get("logo") or "").strip()

    fields = [
        {"name": "CTF Title", "value": title, "inline": False},
        {"name": "Start Time", "value": f"`{start}`", "inline": True},
        {"name": "End Time", "value": f"`{end}`", "inline": True},
    ]
    if link:
        fields.append({"name": "CTF URL", "value": link, "inline": False})

    embed: dict = {
        "title": "New CTF Time!",
        "color": EMBED_COLOR,
        "fields": fields,
        "footer": {"text": "CTFtime"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if link:
        embed["url"] = link
    if logo.startswith("http"):
        embed["thumbnail"] = {"url": logo}
    return embed


def post_to_discord(webhook_url: str, embed: dict) -> None:
    # Discord incoming webhooks are rate-limited; space posts out a bit.
    http_post_json(webhook_url, {"embeds": [embed]})
    time.sleep(1.2)


def main() -> int:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("DISCORD_WEBHOOK_URL is required", file=sys.stderr)
        return 1

    tz_name = os.getenv("TIMEZONE", DEFAULT_TIMEZONE).strip() or DEFAULT_TIMEZONE
    lookahead_days = env_int("LOOKAHEAD_DAYS", DEFAULT_LOOKAHEAD_DAYS)
    limit = env_int("EVENT_LIMIT", DEFAULT_LIMIT)
    bootstrap = os.getenv("BOOTSTRAP", "").lower() in {"1", "true", "yes"}

    print(f"Fetching upcoming CTFtime events (next {lookahead_days} days)...")
    events = fetch_upcoming_events(lookahead_days, limit)
    events.sort(key=lambda e: e.get("start", ""))

    seen = load_seen()
    current_ids = {int(e["id"]) for e in events if "id" in e}
    new_events = [e for e in events if int(e["id"]) not in seen]

    if not seen:
        # Empty state: record current events only (avoids channel spam).
        save_seen(current_ids)
        mode = "manual bootstrap" if bootstrap else "auto-bootstrap"
        print(
            f"{mode}: recorded {len(current_ids)} events, posted 0 messages."
        )
        return 0

    posted = 0
    for event in new_events:
        embed = build_embed(event, tz_name)
        try:
            post_to_discord(webhook_url, embed)
            seen.add(int(event["id"]))
            posted += 1
            print(f"Posted: {event.get('title')} (id={event['id']})")
        except urllib.error.HTTPError as exc:
            print(
                f"Failed to post event {event.get('id')}: HTTP {exc.code}",
                file=sys.stderr,
            )
            save_seen(seen)
            return 1

    # Keep seen set from growing forever: retain known + currently upcoming ids.
    pruned = (seen & current_ids) | {int(e["id"]) for e in new_events}
    # Also keep recently notified ids that may have finished already.
    pruned |= seen
    # Soft cap: keep at most last 2000 ids.
    if len(pruned) > 2000:
        pruned = set(sorted(pruned)[-2000:])

    save_seen(pruned)
    print(f"Done. new={len(new_events)} posted={posted} tracked={len(pruned)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
