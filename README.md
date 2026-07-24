# Twitch Drops Alerts

Checks [twitchdrops.app](https://twitchdrops.app) on a schedule you set for
changes to drop campaigns on a list of games you configure, and emails you a
summary when something changes. Uses the campaign list directly (not stream
scanning).

This is a personal project shared as a starter template. Click **Use this
template** above to get your own independent copy (no shared history, no
connection back to this repo), then follow the setup steps below with your
own secrets, schedule, and game list.

**If you fork instead of using "Use this template":** GitHub disables
scheduled workflows on forks by default, so the daily run won't start
automatically. Go to your fork's *Actions* tab, and you'll see a banner
prompting you to enable workflows, click through that and you're set.
(GitHub also auto-disables scheduled workflows on any public repo, fork or
not, after 60 days with no repo activity, a config edit or manual run
resets that clock.)

## Setup

1. **Create a Gmail App Password** (a regular Gmail password won't work for
   this) go to <https://myaccount.google.com/apppasswords>, sign in, and
   generate a 16-character app password. You'll need 2-Step Verification
   turned on for your Google account first.

2. **Add three repo secrets** go to your repo's *Settings → Secrets and
   variables → Actions → New repository secret* and add:
   - `GMAIL_USER` — the Gmail address you're sending *from*
   - `GMAIL_APP_PASSWORD` — the app password from step 1
   - `TO_EMAIL` — the address you want alerts sent *to* (can be the same as
     `GMAIL_USER` if you want to email yourself)

3. **Edit `config.json`** to list the games you actually want to track (see
   below) and set your schedule.

4. **The workflow runs automatically** on a daily schedule
   (`.github/workflows/check-drops.yml`), but only performs an actual check
   every N days (see "Changing how often it checks" below). It tracks the
   last check time in `state.json` and skips days in between. This avoids
   cron's day-of-month quirks, which don't line up to an exact "every N
   days" cadence on their own.

5. **First run**: you'll get one "initial sync" email listing the current
   state of everything you're tracking. After that, you'll only hear from
   it when something actually changes.

## Adding or removing games

Edit `config.json`. Under `"games"`, each entry is a display name mapped to
one or more twitchdrops.app slugs:

```json
{
  "check_interval_days": <N>,
  "games": {
    "Fortnite": ["fortnite"]
  }
}
```

To find a slug: go to `twitchdrops.app/game/<slug>` in your browser and the
slug is whatever comes after `/game/`.

All of your personal customization, games and check frequency, lives in
this one file. `check_drops.py` itself shouldn't need to change for typical
use, which means if you keep your copy connected to this template (e.g. via
a fork rather than a fully independent "Use this template" copy), you can
pull in future fixes or improvements to the script without conflicts.

## Changing how often it checks

Set this in `config.json`:

```json
{
  "check_interval_days": <N>
}
```

Set `<N>` to whatever cadence you want (e.g. `1` for daily, `3` for every
three days). The underlying Action already runs daily regardless, this
setting only controls how often the script decides it's actually due to
perform a real check.

## Running a check manually

Go to the *Actions* tab → *Check Twitch Drops* → *Run workflow*. This runs
the check immediately regardless of the scheduled interval.

## How it decides something "changed", and what the email actually contains

The script fetches a short status line for each game from twitchdrops.app's
public chatbot API and compares it byte-for-byte to what it saw last time.
Any difference — a new reward, a changed drop count, an expired campaign —
triggers an email.

Worth knowing: this status line lists **reward names and watch-time
requirements** (e.g. "2 rewards — Item A (30m), Item B (1h)"), not the
**campaign name** shown on the full twitchdrops.app page. If you want that
level of detail, you'd need to fetch and parse the full game page instead of
the chatbot endpoint, this template intentionally keeps things simple by using
the lighter endpoint.

## License

MIT — see `LICENSE`. Do whatever you'd like with this.
