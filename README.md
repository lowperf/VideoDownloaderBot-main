# VideoDownloaderBot

## A **self‑hosted Telegram bot** that downloads media from a link using **yt-dlp**.

> Paste a link → bot fetches info instantly → you choose how to receive it.
>
> **Video** (Telegram video) • **Document** (original file) • **Audio** (MP3)

Regular downloads follow the configured size limit. Facebook video downloads skip final-size estimation and the application-level download limit; Telegram's upload limits still apply. Audio remains subject to the configured size limit.

**Clean UX:** a single status message updates during download/upload, then **disappears on success** (only the media stays).

Works best on **Ubuntu 22.04 / 24.04**. **Docker is recommended.**

---

## Why this bot exists

Most “download bots” are either public (unstable / rate-limited / banned), or self-hosted but painful to set up.

**VideoDownloaderBot** is intentionally:

* **Self-hosted first** (VPS / home server)
* **Strict & predictable** size checks for supported media (Facebook video size is not estimated or capped by the application)
* **No nonsense setup** (one command installer)
* **Nice UX in Telegram** (buttons, progress, cancel)

---

## Features

✅ Supports many websites (YouTube, TikTok, X/Twitter, Reddit, and more — whatever yt-dlp supports)

✅ Inline buttons: **Video / Document / Audio**

✅ Progress feedback (**download + upload**) with message edits (Telegram-friendly throttling)

✅ **Queue + workers** (controlled concurrency)

✅ **Cancel** button during the process (download *and* upload)

✅ Safe filenames:

* uses video title
* removes hashtags
* sanitizes forbidden characters
* avoids weird trailing dots/spaces

✅ **Configured-size pre-check** for regular video/document downloads:

* if it won’t fit → bot tells you **before downloading**
* if it can’t reliably estimate size → bot refuses (by design)
* Facebook video size is not estimated or checked against the configured download-size cap; upload limits still depend on the Telegram Bot API server

✅ Designed for **private self-hosting** (not a public “open” downloader service)

---

## How it works (in one minute)

1. You send a URL.

2. Bot calls yt-dlp **metadata-only** (no download yet).

3. Bot builds a best-first list of **video candidates**:

* ranks Telegram-compatible H.264 MP4 by compatibility and quality
* supports both progressive MP4 and MP4 video + M4A audio without automatically preferring progressive
* for YouTube, prefers the uploader's original audio over regional automatic dubs, including after fallback retries
* handles deduplicated Instagram direct MP4 candidates whose codec metadata is missing

4. For regular video/document downloads, bot tries to **prove** final size is ≤ the configured size limit (500 MiB by default). Facebook video downloads skip size estimation and this size cap:

* uses `filesize` / `filesize_approx` when available
* if missing, tries a **Range probe** on direct media URLs (`Content-Range`) to get real byte size

5. If size can be proven and fits:

* it offers **Video / Document** (and Audio if available)

6. For **Audio (MP3)**:

* uses duration to pick the **highest MP3 bitrate** that will safely fit (with headroom)
* for YouTube, extracts the original audio track when YouTube exposes it; an automatic dub is only a fallback

7. During download/upload:

* status message updates with progress
* you can cancel anytime

8. On success:

* status message is deleted
* only the final media remains in chat

---

## Quick start (recommended): one‑line installer

Run on your Ubuntu server (SSH):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lowperf/VideoDownloaderBot-main/main/install.sh)
```

The installer will:

* Install **Git**, **Docker**, Compose, `flock`, `curl`, and Python 3 when needed
* Preserve an existing `.env`, `data/`, and `logs/`
* Ask for **BOT_TOKEN** and optionally **TELEGRAM_API_ID** / **TELEGRAM_API_HASH**
* Configure and start the local Telegram Bot API automatically when API credentials are provided, enabling uploads above 50 MB (500 MiB application limit by default)
* Build and validate the production image before replacing the container
* Enable automatic deployment from `origin/main` and nightly yt-dlp image updates

It clones the repository as your user and asks for `sudo` only for the
installation itself. To install from an existing checkout, run
`sudo bash install.sh` inside it; running it again later is safe and repairs
the installation.

> No Python knowledge required. One command on a fresh Ubuntu VPS.

---

## After installation

Go to the install folder printed by the script (default: `~/VideoDownloaderBot`) and use:

```bash
cd ~/VideoDownloaderBot

# logs
# (works with either docker compose v2 or docker-compose v1)
docker compose logs -f --tail=200 || docker-compose logs -f --tail=200

# restart
(docker compose restart || docker-compose restart)

# stop + remove container
(docker compose down || docker-compose down)

# start
(docker compose up -d || docker-compose up -d)
```

Runtime logs are also written to `logs/bot.log`. Downloads use per-job directories under `data/downloads/`; both directories survive deployment and rollback. Docker pins the download workspace to `/app/data/downloads`, so a legacy `.env` value cannot redirect media into the bounded `/tmp` tmpfs.

### Automatic deployment and rollback

`videodownloaderbot-deploy.timer` checks `origin/main` every two minutes and deploys a new commit once its GitHub checks pass (or after 30 minutes if CI never starts). A candidate image is built first; if it is identical to the running one — documentation or test changes — the checkout advances without a restart. Before replacement, deployment verifies Python imports, ffmpeg, ffprobe, Node, yt-dlp, and Telegram `getMe`.

If the build, those checks, container startup, or health stabilization fails, the previous commit and the exact image it ran are restored and the failed commit is skipped until a newer one arrives. For ten minutes after a release the timer keeps watching; a release that turns unhealthy or restarts is rolled back automatically. The bot counts as healthy only while its download workers run and Telegram answers its `getUpdates` requests.

`videodownloaderbot-rebuild.timer` rebuilds the running commit every night with a fresh `REBUILD_STAMP`, which refreshes yt-dlp without touching the slower OS layers. The bot restarts only when `python -m yt_dlp --version` reports a new version, and a new version goes through the same checks and rollback. Both schedules live in [`deploy.conf`](deploy.conf).

```bash
sudo bash scripts/status.sh            # running release, previous release, pending work
sudo bash scripts/deploy.sh --retry    # try a failed commit again
sudo bash scripts/rollback.sh          # return to the previous release (run again to undo)
docker compose restart videodownloaderbot # restart the service
docker compose ps # to show the bot status
docker compose logs -f --tail=100 videodownloaderbot # to show the logs
docker compose stop videodownloaderbot # stop the service
```

Deployment logs are stored in `logs/videodownloaderbot-deploy-YYYY-MM-DD.log` for 30 days.

---

## Bot usage

1. Open your bot in Telegram
2. Send any supported URL
3. You’ll see the title + buttons:

* **Download as Video**
* **Download as Document** (original file)
* **Download as Audio (MP3)** (only when it can fit)

During work you can press **Cancel**.

### What you’ll see in chat

* “Getting info…” (short)
* “Choose download method…” + size/quality info
* Status message updates:

  * ⬇️ Downloading…
  * ⬆️ Sending video/document/audio…
* On success: status message disappears, only media stays

---

## Commands

### `/start` and `/help`

Shows a short help message and the current upload limit.

### `/custom <url>` (kept as-is)

Fetches formats and lets you pick one.

> Note: after you pick a format, the bot returns to the same “choice UI” flow.

---

## Configuration

### The only required value

* `BOT_TOKEN` — Telegram bot token from BotFather

The installer creates `.env` from `.env-example` only when it does not exist:

```env
BOT_TOKEN=123456:ABCDEF...
OUTPUT_FOLDER=/app/data/downloads
LOGS_DIR=/app/logs
```

Operational settings are read through the validated `Settings` dataclass:

* `LOGS_CHAT_ID` — optional operator chat for critical failures
* `OUTPUT_FOLDER` — temporary per-job directories; Docker enforces `/app/data/downloads`
* `LOGS_DIR` — rotating application logs
* `MAX_FILESIZE` — strict upload limit; defaults to `524288000` bytes (500 MiB)
* `BOT_API_BASE_URL` — Bot API server origin; defaults to `https://api.telegram.org`
* `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` — credentials from [my.telegram.org](https://my.telegram.org); enter them during `install.sh` setup to enable uploads above 50 MB. The application limit defaults to 500 MiB and can be raised with `MAX_FILESIZE` up to the local Bot API limit (2000 MB).
* `WORKERS` — download workers; default `2`
* `MAX_QUEUE` — bounded queue size; default `200`
* `UPLOAD_WORKERS` — concurrent Telegram uploads; default `2`
* `JOB_TIMEOUT_SECONDS` — whole-job deadline; default `900`
* `PENDING_TTL_SECONDS` — button request lifetime; default `600`
* `YTDLP_CONCURRENT_FRAGMENTS` — segmented download concurrency; default `4`
* `YTDLP_JS_RUNTIMES` — yt-dlp JavaScript runtimes; default `node`
* `YTDLP_REMOTE_COMPONENTS` — optional yt-dlp remote components; empty disables them
* `YTDLP_YOUTUBE_PLAYER_CLIENTS` — ordered metadata fallback clients; default `default,android,ios`
* `YTDLP_INSTAGRAM_IMPERSONATE` — optional Instagram impersonation target
* `YTDLP_INSTAGRAM_RETRIES`, `YTDLP_INSTAGRAM_FRAGMENT_RETRIES`, `YTDLP_INSTAGRAM_SOCKET_TIMEOUT` — bounded Instagram retry/timeouts
* `YTDLP_GENERIC_IMPERSONATE` — optional browser impersonation target for generic sites; default `chrome`
* `METADATA_WORKERS` — maximum concurrent metadata operations; default `2`
* `METADATA_TIMEOUT_SECONDS` — metadata-stage timeout; default `60`
* `COOKIES_FILE` — optional cookies file, normally `/app/data/cookies.txt`
* `LOG_LEVEL` — `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`

---

## Manual installation (no installer)

If you prefer doing everything yourself:

```bash
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
  ca-certificates git python3 python3-venv python3-pip ffmpeg
# Install Node.js 22 or newer for current yt-dlp YouTube support.

git clone https://github.com/Avazbek22/VideoDownloaderBot.git
cd VideoDownloaderBot

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

# create .env
cat > .env <<'EOF'
BOT_TOKEN=PUT_YOUR_TOKEN_HERE
OUTPUT_FOLDER=./data/downloads
LOGS_DIR=./logs
EOF

# run
python -u main.py
```

### Manual Docker start

The image runs as UID/GID `10001`, so prepare the two writable bind mounts before starting it:

```bash
cp .env-example .env
# Set BOT_TOKEN in .env, then:
mkdir -p data logs
sudo chown -R 10001:10001 data logs
chmod 600 .env
docker compose build
docker compose up -d
docker compose ps
```

The container root filesystem is read-only. Only `data/`, `logs/`, and the in-memory `/tmp` filesystem are writable; Docker health is based on a fresh `/tmp/videodownloaderbot.healthy` marker, which is refreshed only while the download workers run and Telegram answers `getUpdates`. For non-Facebook video downloads, progress hooks stop a download when its actual byte count or reported total exceeds `MAX_FILESIZE`. Facebook video downloads do not estimate size or apply that application-level cap.

The configured upload limit defaults to 500 MiB. Telegram's public Bot API limits file uploads to 50 MiB; sending larger files requires the included local Bot API service, which supports uploads up to 2000 MB.

### Enable the local Bot API server

For a new installation, provide the API ID and hash when `install.sh` prompts for them. The installer writes them to `.env`, enables `COMPOSE_PROFILES=local-bot-api`, points the bot at the local server, and starts that server. Press Enter at the API ID prompt to keep using the public API (50 MiB upload limit).

When migrating an existing bot from the public API, the installer stops it and calls `logOut` on the public API before switching it. If setting up manually instead:

   ```bash
   docker compose stop videodownloaderbot
   set -a
   . ./.env
   set +a
   curl -fsS -X POST "https://api.telegram.org/bot${BOT_TOKEN}/logOut"
   ```

   Then set `BOT_API_BASE_URL=http://telegram-bot-api:8081`, `MAX_FILESIZE=524288000`, and `COMPOSE_PROFILES=local-bot-api` in `.env`, and start the local service and bot:

   ```bash
   docker compose --profile local-bot-api up -d telegram-bot-api
   docker compose up -d videodownloaderbot
   ```

The server is only reachable inside the Compose network and keeps its working data in the persistent `telegram-bot-api-data` volume. Keep `BOT_API_BASE_URL` at its default if you do not enable the local server.

---

## Requirements

* Ubuntu 22.04 / 24.04 (recommended)
* Python 3.11+ (Docker uses 3.12-slim)
* ffmpeg
* Node.js 22+
* Telegram bot token

Python dependencies (see `requirements.txt`):

* `yt-dlp`
* `pyTelegramBotAPI`
* `requests-toolbelt` (upload progress)

---

## Limitations (intentional)

### Configured size limit

Regular video/document downloads are intentionally strict and predictable.
If the bot expects a file won’t fit, it stops early and tells you **before downloading**. Facebook video size is not estimated, so the bot attempts the download without the application-level size cap; the Telegram Bot API server can still reject uploads above its own limit.

### Unknown-size videos are still offered

If the bot can't determine the final size up front, it still offers video/document download and lets the download-time size guard enforce the limit. This means an oversized file may only fail once the download reaches the Telegram limit instead of being refused immediately.

### Telegram compression behavior

Telegram compression depends on client/platform/codec/bitrate.
Sometimes “Video” looks nearly identical to “Document”. Document is always **as-is**.

---

## FAQ

### Why is there a configured size limit?

The configured limit protects regular downloads from using excessive bandwidth and storage. Facebook video size is not estimated and is not capped by the application; Telegram upload limits still apply.

### Is this a public bot?

No. This repository is intended for **self-hosted private use**.

### Why does Docker build show “Debian … trixie/bookworm …” packages?

That’s inside the container image (base `python:*‑slim` images are Debian-based). Your Ubuntu host is not being “converted”.

### YouTube prints warnings about JavaScript runtime

The production image installs a checksum-verified Node.js runtime. Check it with `docker compose exec videodownloaderbot node --version`. Manual installations require Node.js 22 or newer.

### I ran `install.sh` on Windows PowerShell and `chmod` is not found

`install.sh` is a Linux script. Run it on Ubuntu/WSL/your VPS via Bash.

---

## Troubleshooting

### “Request expired. Send the link again.”

The button UI has a TTL to prevent memory leaks. Just send the link again.

### “This video is too large…” even before download

That’s the strict pre-check working as intended.
Try a shorter video, or use Audio if available.

### Docker permission denied

If you installed Docker and your user can’t access the daemon, re-login or run:

```bash
sudo usermod -aG docker $USER
```

Then reconnect your SSH session.

---

## Project structure

```
.
├── app/                     # Settings, planner, URL security, logging, helpers
├── scripts/                 # Entrypoint, deploy, rollback, status, systemd units
├── tests/                   # Python and rollback shell tests
├── main.py                  # Existing Telegram UX and application lifecycle
├── Dockerfile
├── docker-compose.yml
├── deploy.conf              # Deployment and nightly rebuild settings
├── install.sh               # Idempotent production installer
├── .env-example
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Contributing

PRs are welcome.
If you want new features (better format picking, larger limits via local Bot API/MTProto, etc.) open an issue.

Ideas that fit this project’s philosophy:

* Better format selection *without* quality squeezing
* Better website-specific fallbacks
* Better website-specific runtime compatibility
* More robust size probing for edge sites

---

## License

MIT License

Copyright (c) 2025 Avazbek22

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
