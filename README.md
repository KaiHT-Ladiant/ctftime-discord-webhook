# ctftime-discord-webhook

Notify a Discord channel when new CTF events appear on [CTFtime](https://ctftime.org/).

Runs on **GitHub Actions** every hour — no always-on server required.

## Setup

### 1. Create a Discord webhook

1. Open your Discord server and choose a channel
2. Channel settings → **Integrations** → **Webhooks** → **New Webhook**
3. Copy the webhook URL

### 2. Configure the GitHub secret

1. Push this repository to GitHub (or fork it)
2. Repository → **Settings** → **Secrets and variables** → **Actions**
3. Create a secret:
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: your Discord webhook URL

### 3. First run (recommended)

Open **Actions** → **CTFtime Discord Notify** → **Run workflow**

- Set `bootstrap` to **true**
- This records currently listed events **without** posting messages
- After that, only newly listed events are sent

### 4. Automatic runs

The workflow runs hourly (UTC). Scheduled runs may be delayed by a few minutes.

## Local test

```bash
# PowerShell
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
$env:TIMEZONE="Asia/Seoul"
$env:BOOTSTRAP="true"
python notify.py
```

## How it works

1. Fetches upcoming CTFtime events (default: next 90 days)
2. Posts only events that are not in `data/seen_events.json`
3. Saves notified event IDs and commits the updated state from Actions

Each notification is a Discord embed with title, start/end time, and CTF URL.

## Environment variables

| Name | Description | Default |
|------|-------------|---------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL (required) | — |
| `TIMEZONE` | Timezone for displayed start/end times | `Asia/Seoul` |
| `LOOKAHEAD_DAYS` | How far ahead to scan for events | `90` |
| `BOOTSTRAP` | If `true` and seen state is empty, record only (no posts) | `false` |
