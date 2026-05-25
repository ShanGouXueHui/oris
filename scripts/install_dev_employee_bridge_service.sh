#!/usr/bin/env bash

ORIS_DIR="/home/admin/projects/oris"
UNIT_SRC="$ORIS_DIR/systemd/user/oris-dev-employee-bridge.service"
UNIT_DST="$HOME/.config/systemd/user/oris-dev-employee-bridge.service"
LOG_DIR="$ORIS_DIR/logs/dev_employee"
INSTALL_LOG="$LOG_DIR/install_dev_employee_bridge_service.log"

mkdir -p "$LOG_DIR" "$HOME/.config/systemd/user"

{
  echo "===== install ORIS Dev Employee bridge service ====="
  date -Iseconds
  whoami
  echo "HOME=$HOME"
  echo

  cd "$ORIS_DIR" || exit 10
  test -f "$UNIT_SRC" || exit 11
  test -f "$ORIS_DIR/scripts/dev_employee_supervised_bridge_v2.py" || exit 12

  echo "===== install unit ====="
  cp "$UNIT_SRC" "$UNIT_DST"
  systemctl --user daemon-reload
  systemctl --user enable oris-dev-employee-bridge.service
  systemctl --user restart oris-dev-employee-bridge.service

  echo
  echo "===== status ====="
  systemctl --user --no-pager status oris-dev-employee-bridge.service || true

  echo
  echo "===== journal tail ====="
  journalctl --user -u oris-dev-employee-bridge.service -n 80 --no-pager || true
} 2>&1 | tee "$INSTALL_LOG"
