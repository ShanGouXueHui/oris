# Runtime Automation

## systemd user service: quota / routing pipeline
The active runtime pipeline service file lives outside the Git repository:

~/.config/systemd/user/oris-quota-probe.service

Current content:

[Unit]
Description=ORIS quota/provider probe, scoring, free verification, route selection, and runtime planning

[Service]
Type=oneshot
WorkingDirectory=/home/admin/projects/oris
ExecStart=/bin/bash -lc '/usr/bin/python3 /home/admin/projects/oris/scripts/quota_probe.py && /usr/bin/python3 /home/admin/projects/oris/scripts/provider_scoreboard.py && /usr/bin/python3 /home/admin/projects/oris/scripts/free_eligibility.py && /usr/bin/python3 /home/admin/projects/oris/scripts/model_selector.py && /usr/bin/python3 /home/admin/projects/oris/scripts/runtime_plan.py'

## systemd user service: HTTP API
The active local HTTP API service file lives outside the Git repository:

~/.config/systemd/user/oris-http-api.service

Current content:

[Unit]
Description=ORIS HTTP API

[Service]
Type=simple
WorkingDirectory=/home/admin/projects/oris
ExecStart=/usr/bin/python3 /home/admin/projects/oris/scripts/oris_http_api.py
Restart=always
RestartSec=3

[Install]
WantedBy=default.target

## systemd user timer
The active timer file lives at:

~/.config/systemd/user/oris-quota-probe.timer

Purpose:
- run provider probe automatically every hour
- update provider scoreboard
- update strict free eligibility
- regenerate active routing automatically
- regenerate runtime failover plan automatically
