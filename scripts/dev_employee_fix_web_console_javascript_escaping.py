#!/usr/bin/env python3
from pathlib import Path

path = Path('/home/admin/projects/oris/scripts/dev_employee_web_console.py')
text = path.read_text(encoding='utf-8')
old = 'def page() -> str:\n    return """<!doctype html>'
new = 'def page() -> str:\n    return r"""<!doctype html>'
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit('ERROR: page() HTML string marker not found')
path.write_text(text, encoding='utf-8')
print('WEB_CONSOLE_HTML_RAW_STRING=true')
