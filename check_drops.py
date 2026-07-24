"""
Checks twitchdrops.app for changes to drop campaigns on a configured list of
games, and emails a summary if anything changed since the last check.

Runs daily via GitHub Actions, but only actually performs a check every
N days (set by check_interval_days in config.json), tracked in state.json.
This gives you a fixed N-day cadence regardless of cron's day-of-month
quirks. Pass FORCE_RUN=true as an env var (or trigger via workflow_dispatch)
to check immediately regardless of the last run time.

All personal customization lives in config.json (which games to track, and
how many days between checks) — this file shouldn't need to change for
typical use, which keeps forks easy to update from upstream.
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

import requests

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"
DEFAULT_CHECK_INTERVAL_DAYS = 3
CHATBOT_API = "https://twitchdrops.app/api/chatbot/{slug}"
REQUEST_TIMEOUT = 15


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def is_due(state, interval_days):
    if os.environ.get("FORCE_RUN", "").lower() == "true":
        print("FORCE_RUN set, running regardless of schedule.")
        return True
    last_checked = state.get("last_checked")
    if not last_checked:
        return True
    last_dt = datetime.fromisoformat(last_checked)
    due_at = last_dt + timedelta(days=interval_days)
    now = datetime.now(timezone.utc)
    if now >= due_at:
        return True
    print(f"Not due yet. Next check at {due_at.isoformat()} (now {now.isoformat()}).")
    return False


def fetch_slug_text(slug):
    url = CHATBOT_API.format(slug=slug)
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text.strip()
    except requests.RequestException as e:
        print(f"  ! Failed to fetch {slug}: {e}")
        return None


def send_email(subject, body):
    gmail_user = os.environ.get("GMAIL_USER")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    to_email = os.environ.get("TO_EMAIL")

    if not all([gmail_user, gmail_app_password, to_email]):
        print("Missing GMAIL_USER, GMAIL_APP_PASSWORD, or TO_EMAIL secret — skipping email, printing instead:\n")
        print(subject)
        print(body)
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_app_password)
        server.sendmail(gmail_user, [to_email], msg.as_string())
    print(f"Email sent to {to_email}.")


def main():
    config = load_json(CONFIG_FILE, {"games": {}})
    games = config.get("games", {})
    interval_days = config.get("check_interval_days", DEFAULT_CHECK_INTERVAL_DAYS)

    if not games:
        print(f"No games configured in {CONFIG_FILE} — nothing to do.")
        return

    state = load_json(STATE_FILE, {"last_checked": None, "data": {}})

    if not is_due(state, interval_days):
        return

    print(f"Checking {sum(len(v) for v in games.values())} slug(s) across {len(games)} game(s)...")

    is_first_run = state.get("last_checked") is None
    changes = []
    new_data = dict(state.get("data", {}))

    for display_name, slugs in games.items():
        for slug in slugs:
            print(f"  Fetching {display_name} ({slug})...")
            text = fetch_slug_text(slug)
            if text is None:
                continue  # leave old state untouched, don't treat fetch failure as a "change"

            previous = state.get("data", {}).get(slug)
            if previous != text:
                changes.append(
                    {
                        "display_name": display_name,
                        "slug": slug,
                        "previous": previous,
                        "current": text,
                    }
                )
            new_data[slug] = text

    state["data"] = new_data
    state["last_checked"] = datetime.now(timezone.utc).isoformat()
    save_json(STATE_FILE, state)

    if not changes:
        print("No changes detected.")
        return

    if is_first_run:
        subject = f"Twitch Drops tracker: initial sync ({len(changes)} game slug(s))"
        intro = "First run — here's the current state for everything you're tracking:\n\n"
    else:
        subject = f"Twitch Drops update: {len(changes)} change(s) detected"
        intro = "Something changed for the games you're tracking:\n\n"

    body_parts = [intro]
    for c in changes:
        body_parts.append(f"— {c['display_name']} ({c['slug']}) —")
        body_parts.append(c["current"])
        body_parts.append("")

    body = "\n".join(body_parts)
    send_email(subject, body)


if __name__ == "__main__":
    main()
