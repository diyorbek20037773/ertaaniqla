#!/usr/bin/env bash
# Telegram notification helper (spec §11.5 alerts). No-op when the bot is not configured.
# Usage: source /scripts/notify.sh; notify_telegram "message"
notify_telegram() {
  local text="$1"
  if [[ -z "${TELEGRAM_BOT_TOKEN:-}" || -z "${TELEGRAM_ALERT_CHAT_ID:-}" ]]; then
    return 0
  fi
  curl -fsS --max-time 10 -o /dev/null \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    --data-urlencode "chat_id=${TELEGRAM_ALERT_CHAT_ID}" \
    --data-urlencode "text=${text}" \
    --data-urlencode "disable_web_page_preview=true" || true
}
