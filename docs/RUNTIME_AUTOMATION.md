# Runtime Automation

## systemd user service
The active runtime service file lives outside the Git repository:

~/.config/systemd/user/oris-quota-probe.service

Current content:

[Unit]
Description=ORIS quota/provider probe, scoring, and route selection

[Service]
Type=oneshot
WorkingDirectory=/home/admin/projects/oris
ExecStart=/bin/bash -lc '/usr/bin/python3 /home/admin/projects/oris/scripts/quota_probe.py && /usr/bin/python3 /home/admin/projects/oris/scripts/provider_scoreboard.py && /usr/bin/python3 /home/admin/projects/oris/scripts/model_selector.py'

## systemd user timer
The active timer file lives at:

~/.config/systemd/user/oris-quota-probe.timer

Purpose:
- run provider probe automatically every hour
- update provider scoreboard
- regenerate active routing automatically
