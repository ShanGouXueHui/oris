#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
CONFIG_DIR="$HOME/.config/oris"
ENV_FILE="$CONFIG_DIR/dev_employee_enqueue.env"
UNIT_DIR="$HOME/.config/systemd/user"
UNIT_FILE="$UNIT_DIR/oris-dev-employee-enqueue.service"
LOG_DIR="$ORIS_DIR/logs/dev_employee"
INSTALL_LOG="$LOG_DIR/install_dev_employee_enqueue_service.log"

mkdir -p "$CONFIG_DIR" "$UNIT_DIR" "$LOG_DIR"

{
  echo "===== install ORIS Dev Employee enqueue service ====="
  date -Iseconds
  whoami
  echo "HOME=$HOME"
  echo

  cd "$ORIS_DIR" || exit 10
  test -f "$ORIS_DIR/scripts/dev_employee_enqueue_server.py" || exit 11

  echo "===== prepare local env file ====="
  if [ ! -f "$ENV_FILE" ]; then
    TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
    {
      echo "ORIS_DEV_EMPLOYEE_ENQUEUE_HOST=127.0.0.1"
      echo "ORIS_DEV_EMPLOYEE_ENQUEUE_PORT=18891"
      echo "ORIS_DEV_EMPLOYEE_ENQUEUE_TOKEN=$TOKEN"
    } > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "CREATED_ENV_FILE=$ENV_FILE"
  else
    chmod 600 "$ENV_FILE"
    echo "EXISTING_ENV_FILE=$ENV_FILE"
  fi

  echo
  echo "===== install user systemd unit ====="
  cat > "$UNIT_FILE" <<'UNIT'
[Unit]
Description=ORIS Dev Employee Local Enqueue API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/admin/projects/oris
EnvironmentFile=%h/.config/oris/dev_employee_enqueue.env
ExecStart=/usr/bin/python3 /home/admin/projects/oris/scripts/dev_employee_enqueue_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT

  systemctl --user daemon-reload
  systemctl --user enable oris-dev-employee-enqueue.service
  systemctl --user restart oris-dev-employee-enqueue.service

  echo
  echo "===== status ====="
  systemctl --user --no-pager status oris-dev-employee-enqueue.service || true

  echo
  echo "===== health ====="
  curl -s http://127.0.0.1:18891/health || true
  echo

  echo "===== token note ====="
  echo "Token is stored locally only: $ENV_FILE"
  echo "Do not commit or paste the token. Use this to load it when testing:"
  echo "source $ENV_FILE"
} 2>&1 | tee "$INSTALL_LOG"
