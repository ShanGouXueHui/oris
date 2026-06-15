#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

PATH = Path('/home/admin/projects/oris/scripts/dev_employee_web_console.py')
text = PATH.read_text(encoding='utf-8')

if 'APP_JS =' in text and '<script src="/app.js" defer></script>' in text:
    print('EXTERNAL_JS_ALREADY_APPLIED=true')
    raise SystemExit(0)

match = re.search(r'<script>\n(?P<js>.*?)\n</script>', text, flags=re.DOTALL)
if not match:
    raise SystemExit('ERROR: inline script block not found')

js = match.group('js')
listeners = """
document.getElementById('submit_goal_button').addEventListener('click', submitGoal);
document.getElementById('reload_projects_button').addEventListener('click', loadProjects);
document.getElementById('load_status_button').addEventListener('click', loadStatus);
""".strip()
if "reload_projects_button').addEventListener" not in js:
    js = js.rstrip() + '\n' + listeners + '\n'

replacements = {
    '<button onclick="submitGoal()">Submit goal</button>': '<button id="submit_goal_button">Submit goal</button>',
    '<button class="secondary" onclick="loadProjects()">Reload projects</button>': '<button id="reload_projects_button" class="secondary">Reload projects</button>',
    '<button onclick="loadStatus()">Load status</button>': '<button id="load_status_button">Load status</button>',
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f'ERROR: expected HTML control not found: {old}')
    text = text.replace(old, new, 1)

text = text[:match.start()] + '<script src="/app.js" defer></script>' + text[match.end():]

marker = 'def page() -> str:\n'
if marker not in text:
    raise SystemExit('ERROR: page() marker not found')
text = text.replace(marker, f'APP_JS = {js!r}\n\n\n{marker}', 1)

old_html_headers = '''    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))'''
new_html_headers = '''    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))'''
if old_html_headers not in text:
    raise SystemExit('ERROR: html response header block not found')
text = text.replace(old_html_headers, new_html_headers, 1)

intake_marker = '\ndef intake_request(method: str, path: str, body: dict[str, Any] | None = None, auth: bool = False) -> tuple[int, Any]:\n'
if intake_marker not in text:
    raise SystemExit('ERROR: intake_request marker not found')
js_response = '''
def javascript_response(handler: BaseHTTPRequestHandler, status: int, content: str) -> None:
    body = content.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/javascript; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)

'''
text = text.replace(intake_marker, '\n' + js_response + intake_marker.lstrip('\n'), 1)

health_marker = '''        if path == "/health":
            return json_response(self, 200, {"status": "ok", "service": "dev_employee_web_console"})'''
health_replacement = '''        if path == "/app.js":
            return javascript_response(self, 200, APP_JS)
        if path == "/health":
            return json_response(self, 200, {"status": "ok", "service": "dev_employee_web_console"})'''
if health_marker not in text:
    raise SystemExit('ERROR: health route marker not found')
text = text.replace(health_marker, health_replacement, 1)

text = text.replace(
    'Local-only prototype over the verified intake/status service. Do not expose publicly without auth/reverse-proxy policy.',
    'Secured public console over the verified local intake/status service.',
    1,
)
text = text.replace(
    'Stored only in this browser localStorage. Do not expose publicly without reverse-proxy auth.',
    'Stored only in this browser localStorage. Protected by Basic Auth and the Console API token.',
    1,
)

PATH.write_text(text, encoding='utf-8')
print('EXTERNAL_JS_APPLIED=true')
