import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_all_production_files_are_tracked_sources() -> None:
    expected = [
        "Dockerfile",
        "docker-compose.yml",
        ".env-example",
        "deploy.conf",
        "scripts/docker-entrypoint.sh",
        "scripts/lib-production.sh",
        "scripts/deploy.sh",
        "scripts/rollback.sh",
        "scripts/status.sh",
        "scripts/smoke-test.sh",
        "scripts/systemd/telegram-bot-deploy.service",
        "scripts/systemd/telegram-bot-deploy.timer",
        "scripts/systemd/telegram-bot-rebuild.service",
        "scripts/systemd/telegram-bot-rebuild.timer",
    ]
    assert all((ROOT / path).is_file() for path in expected)


def test_docker_hardening_and_no_runtime_pip() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    deploy_conf = (ROOT / "deploy.conf").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "ARG REBUILD_STAMP" in dockerfile
    assert "read_only: true" in compose
    assert "no-new-privileges:true" in compose
    assert "OUTPUT_FOLDER: /app/data/downloads" in compose
    assert "aiogram/telegram-bot-api:latest" in compose
    assert "TELEGRAM_LOCAL: \"1\"" in compose
    assert "telegram-bot-api-data:/var/lib/telegram-bot-api" in compose
    assert "${APP_IMAGE_TAG:-local}" in compose
    assert 'REBUILD_VERSION_CMD="python -m yt_dlp --version"' in deploy_conf
    assert '"$health" == "healthy"' in (ROOT / "scripts/lib-production.sh").read_text(encoding="utf-8")
    assert "/tmp/videodownloaderbot.healthy" in (ROOT / "app/healthcheck.py").read_text(encoding="utf-8")


def test_main_is_import_safe() -> None:
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'if __name__ == "__main__":' in source
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import main, threading; assert main.bot is None; assert len(threading.enumerate()) == 1",
        ],
        cwd=ROOT,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0


def test_installer_preserves_existing_environment_and_uses_main() -> None:
    installer = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "set -Eeuo pipefail" in installer
    assert 'if [[ ! -f "$env_file" ]]' in installer
    assert 'if [[ -f "$ROOT_DIR/.env-example" ]]' in installer
    assert "No .env-example found; created a minimal environment file" in installer
    assert "set_env_value OUTPUT_FOLDER /app/data/downloads" in installer
    assert "set_env_value LOGS_DIR /app/logs" in installer
    assert 'chmod 600 "$env_file"' in installer
    assert "status --porcelain --untracked-files=no" in installer
    assert "write_docker_files" not in installer
    assert "systemctl enable --now docker" in installer
    assert "docker info" in installer
    assert "release_commit" in installer
    assert "yt-dlp-update" in installer


def test_installer_enables_local_bot_api_when_credentials_are_provided() -> None:
    installer = (ROOT / "install.sh").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "Telegram API ID (press Enter to keep the 50 MB public API limit)" in installer
    assert 'set_env_value TELEGRAM_API_ID "$api_id" "$env_file"' in installer
    assert 'set_env_value TELEGRAM_API_HASH "$api_hash" "$env_file"' in installer
    assert "set_env_value BOT_API_BASE_URL http://telegram-bot-api:8081" in installer
    assert 'profiles="${profiles:+$profiles,}local-bot-api"' in installer
    assert "app_compose up -d telegram-bot-api" in installer
    assert "switch_running_bot_to_local_api" in installer
    assert "TELEGRAM_API_ID: ${TELEGRAM_API_ID:-}" in compose
    assert "TELEGRAM_API_HASH: ${TELEGRAM_API_HASH:-}" in compose
